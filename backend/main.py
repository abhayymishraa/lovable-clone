from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import json
from fastapi import Depends
from datetime import datetime, timezone

from sqlalchemy import select
from agent.service import agent_service
from auth.router import router
from db.models import User, Chat
from auth.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db

from auth.utils import decode_token


app = FastAPI(title="lovable")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router)

active_sockets: dict[str, WebSocket] = {}
active_runs: dict[str, asyncio.Task] = {}


class ChatPayload(BaseModel):
    prompt: str


@app.get("/")
async def get_health():
    return {"message": "Welome", "status": "Healthy"}


@app.post("/chat/{id}")
async def create_project(
    id: str,
    payload: ChatPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    prompt = payload.prompt

    if not prompt:
        return JSONResponse({"error": "Too short or no description"}, status_code=400)

    if id in active_runs:
        return JSONResponse(
            {"error": "Project is being created. Kindly wait"}, status_code=400
        )

    new_chat = Chat(
        id=id,
        user_id=current_user.id,
        title=prompt[:100] if len(prompt) > 100 else prompt,
    )

    db.add(new_chat)
    await db.commit()

    async def agent_task():
        try:
            while id not in active_sockets:
                await asyncio.sleep(0.2)
            socket = active_sockets[id]
            await agent_service.run_agent_stream(prompt=prompt, id=id, socket=socket)
        except Exception as e:
            print(f"Error in agent task for project {id}: {e}")
            print(f"Error type: {type(e)}")
            import traceback

            traceback.print_exc()
        finally:
            active_runs.pop(id, None)

    active_runs[id] = asyncio.create_task(agent_task())
    return {
        "status": "success",
        "message": f"Agent started for project {id}. Connect via WebSocket to see progress.",
    }


@app.get("/projects/{id}/files")
async def get_project_files(id: str):
    sandbox = agent_service.sandboxes.get(id)
    if not sandbox:
        raise HTTPException(
            status_code=404, detail="Project sandbox not found or not active."
        )

    with open("inject.py", "r") as f:
        inject_spread = f.read()

    proc = await sandbox.commands.run(f'python -c "{inject_spread}"')
    files = json.loads(proc.stdout)

    return {
        "project_id": id,
        "files": files,
        "sandbox_id": sandbox.sandbox_id,
        "sandbox_active": True,
    }


@app.websocket("/ws/{id}")
async def ws_listener(websocket: WebSocket, id: str, token: str = None):
    """WebSocket endpoint for real-time chat communication with JWT authentication"""

    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:

        payload = decode_token(token)

        if payload is None:
            await websocket.close(code=1008, reason="Invalid token")
            return

        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid token payload")
            return

        async for db in get_db():
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()

            if user is None:
                await websocket.close(code=1008, reason="User not found")
                return

            result = await db.execute(select(Chat).where(Chat.id == id))
            chat = result.scalar_one_or_none()

            if chat is None:
                await websocket.close(code=1008, reason="Invalid token payload")
                return

            elif chat.user_id != user.id:
                await websocket.close(
                    code=1008, reason="Unauthorized: Chat belongs to another user"
                )
                return

            break  # Exit the async generator after first iteration

    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=1011, reason="Authentication failed")
        return

    await websocket.accept()
    print(f"WebSocket connected for project {id} by user {user_id}")
    active_sockets[id] = websocket

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat_message":
                prompt = data.get("prompt")

                if not prompt:
                    await websocket.send_json(
                        {"e": "error", "message": "No prompt provided"}
                    )
                    continue

                # Check rate limiting before processing query
                async for db in get_db():
                    result = await db.execute(
                        select(User).where(User.id == int(user_id))
                    )
                    current_user = result.scalar_one_or_none()

                    if not current_user.can_make_query():
                        time_since_last = (
                            datetime.now(timezone.utc) - current_user.last_query_at
                        )
                        hours_remaining = 24 - (time_since_last.total_seconds() / 3600)
                        await websocket.send_json(
                            {
                                "e": "error",
                                "message": f"Rate limit exceeded. You can make one query per 24 hours. Please try again in {hours_remaining:.1f} hours.",
                            }
                        )
                        break

                    current_user.update_last_query()
                    await db.commit()
                    break

                if id in active_runs:
                    await websocket.send_json(
                        {
                            "e": "error",
                            "message": "Project is being created. Please wait for the current build to complete.",
                        }
                    )
                    continue

                # Start the agent task
                async def agent_task():
                    try:
                        await agent_service.run_agent_stream(
                            prompt=prompt, id=id, socket=websocket
                        )
                    except Exception as e:
                        print(f"Error in agent task for project {id}: {e}")
                        print(f"Error type: {type(e)}")
                        import traceback

                        traceback.print_exc()
                        await websocket.send_json(
                            {"e": "error", "message": f"Build failed: {str(e)}"}
                        )
                    finally:
                        active_runs.pop(id, None)

                active_runs[id] = asyncio.create_task(agent_task())

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for project {id}")
    finally:
        active_sockets.pop(id, None)
        if id in active_runs:
            active_runs[id].cancel()
            active_runs.pop(id, None)
