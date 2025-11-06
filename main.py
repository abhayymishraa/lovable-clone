from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import os
import io
import zipfile
from fastapi import Depends
from datetime import datetime, timezone

from sqlalchemy import select
from agent.service import agent_service
from auth.router import router
from db.models import User, Chat, Message
from auth.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db
import uuid

from auth.utils import decode_token


app = FastAPI(title="lovable")

origins = [
    "http://localhost:3000",
    "https://webbuilder.elevenai.xyz",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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


@app.get("/chats/{id}/messages")
async def get_chat_messages(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get message history for a chat"""
    # Verify the chat exists and belongs to the user
    result = await db.execute(select(Chat).where(Chat.id == id))
    chat = result.scalar_one_or_none()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this chat")

    # Get all messages for the chat
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "app_url": chat.app_url,
            "created_at": chat.created_at
        },
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "event_type": msg.event_type,
                "created_at": msg.created_at
            }
            for msg in messages
        ]
    }


@app.post("/chat")
async def create_project(
    payload: ChatPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    
    # Generate UUID on backend
    chat_id = str(uuid.uuid4())

    prompt = payload.prompt

    if not prompt:
        return JSONResponse({"error": "Too short or no description"}, status_code=400)

    # Check if user has tokens/credits remaining
    if not current_user.can_make_query():
        hours_remaining = current_user.get_time_until_reset()
        return JSONResponse(
            {
                "error": "No tokens remaining",
                "message": f"You have used all your tokens. You get 2 tokens per 24 hours. Reset in {hours_remaining:.1f} hours.",
                "tokens_remaining": current_user.tokens_remaining,
                "reset_in_hours": hours_remaining
            },
            status_code=403
        )
    
    # Use one token for this request
    if not current_user.use_token():
        return JSONResponse(
            {"error": "Failed to consume token", "message": "Unable to process request"},
            status_code=500
        )
    
    # Commit the token usage
    await db.commit()
    await db.refresh(current_user)

    if chat_id in active_runs:
        return JSONResponse(
            {"error": "Project is being created. Kindly wait"}, status_code=400
        )

    new_chat = Chat(
        id=chat_id,
        user_id=current_user.id,
        title=prompt[:100] if len(prompt) > 100 else prompt,
    )

    db.add(new_chat)
    await db.commit()

    async def agent_task():
        try:
            while chat_id not in active_sockets:
                await asyncio.sleep(0.2)
            socket = active_sockets[chat_id]
            await agent_service.run_agent_stream(prompt=prompt, id=chat_id, socket=socket)
        except Exception as e:
            print(f"Error in agent task for project {chat_id}: {e}")
            print(f"Error type: {type(e)}")
            import traceback

            traceback.print_exc()
        finally:
            active_runs.pop(chat_id, None)

    active_runs[chat_id] = asyncio.create_task(agent_task())
    return {
        "status": "success",
        "message": f"Agent started for project {chat_id}. Connect via WebSocket to see progress.",
        "chat_id": chat_id,
        "tokens_remaining": current_user.tokens_remaining,
        "reset_in_hours": current_user.get_time_until_reset()
    }


@app.get("/projects/{id}/files")
async def get_project_files(id: str):
    sandbox = agent_service.sandboxes.get(id)
    if not sandbox:
        raise HTTPException(
            status_code=404, detail="Project sandbox not found or not active."
        )

    try:
        # Use a simple Python script to list files, excluding node_modules and other unnecessary files
        list_files_script = """
import os
import json

def should_exclude(path):
    # Exclude patterns
    exclude_dirs = ['node_modules', '.git', '__pycache__', '.next', 'dist', 'build', '.venv', 'venv']
    exclude_files = ['.DS_Store', 'package-lock.json', 'yarn.lock']
    
    parts = path.split(os.sep)
    
    # Check if any part of the path matches excluded directories
    for part in parts:
        if part in exclude_dirs:
            return True
    
    # Check if filename matches excluded files
    filename = os.path.basename(path)
    if filename in exclude_files:
        return True
    
    return False

def list_files_recursive(path):
    file_structure = []
    for root, dirs, files in os.walk(path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.next', 'dist', 'build', '.venv', 'venv']]
        
        for name in files:
            relative_path = os.path.relpath(os.path.join(root, name), path)
            if not should_exclude(relative_path):
                file_structure.append(relative_path)
    return file_structure

react_app_path = "/home/user/react-app"
if os.path.exists(react_app_path):
    files = list_files_recursive(react_app_path)
    print(json.dumps(files))
else:
    print(json.dumps([]))
"""
        
        # Write the script to sandbox and execute it
        await sandbox.files.write("/tmp/list_files.py", list_files_script)
        proc = await sandbox.commands.run("python /tmp/list_files.py", cwd="/tmp")
        
        if proc.exit_code != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to list files: {proc.stderr}"
            )
        
        files = json.loads(proc.stdout)

        return {
            "project_id": id,
            "files": files,
            "sandbox_id": sandbox.sandbox_id,
            "sandbox_active": True,
        }
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse file list: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching files: {str(e)}"
        )


@app.get("/projects/{id}/files/{file_path:path}")
async def get_file_content(id: str, file_path: str):
    """Get the content of a specific file from the project"""
    sandbox = agent_service.sandboxes.get(id)
    if not sandbox:
        raise HTTPException(
            status_code=404, detail="Project sandbox not found or not active."
        )

    try:
        full_path = f"/home/user/react-app/{file_path}"
        content = await sandbox.files.read(full_path)
        
        return {
            "file_path": file_path,
            "content": content,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )


@app.get("/projects/{id}/download")
async def download_all_files(id: str):
    """Download all project files as a ZIP archive"""
    sandbox = agent_service.sandboxes.get(id)
    if not sandbox:
        raise HTTPException(
            status_code=404, detail="Project sandbox not found or not active."
        )

    try:
        # Get list of files first (excluding node_modules, etc.)
        list_files_script = """
import os
import json

def should_exclude(path):
    # Exclude patterns
    exclude_dirs = ['node_modules', '.git', '__pycache__', '.next', 'dist', 'build', '.venv', 'venv']
    exclude_files = ['.DS_Store', 'package-lock.json', 'yarn.lock']
    
    parts = path.split(os.sep)
    
    # Check if any part of the path matches excluded directories
    for part in parts:
        if part in exclude_dirs:
            return True
    
    # Check if filename matches excluded files
    filename = os.path.basename(path)
    if filename in exclude_files:
        return True
    
    return False

def list_files_recursive(path):
    file_structure = []
    for root, dirs, files in os.walk(path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.next', 'dist', 'build', '.venv', 'venv']]
        
        for name in files:
            relative_path = os.path.relpath(os.path.join(root, name), path)
            if not should_exclude(relative_path):
                file_structure.append(relative_path)
    return file_structure

react_app_path = "/home/user/react-app"
if os.path.exists(react_app_path):
    files = list_files_recursive(react_app_path)
    print(json.dumps(files))
else:
    print(json.dumps([]))
"""
        
        await sandbox.files.write("/tmp/list_files.py", list_files_script)
        proc = await sandbox.commands.run("python /tmp/list_files.py", cwd="/tmp")
        
        if proc.exit_code != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to list files: {proc.stderr}"
            )
        
        files = json.loads(proc.stdout)
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in files:
                try:
                    full_path = f"/home/user/react-app/{file_path}"
                    content = await sandbox.files.read(full_path)
                    zip_file.writestr(file_path, content)
                except Exception as e:
                    print(f"Failed to add {file_path} to ZIP: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={id}-project.zip"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating ZIP: {str(e)}"
        )


@app.get("/projects")
async def list_user_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all Projects per user"""
    result = await db.execute(
        select(Chat).where(Chat.user_id == current_user.id)
    )
    projects = result.scalars().all()
    return {
        "projects" : projects
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

    # Check if there's already an active connection for this chat
    if id in active_sockets:
        print(f"⚠️ Connection already exists for {id}, rejecting new connection")
        await websocket.close(code=1008, reason="Connection already active for this chat")
        return

    await websocket.accept()
    print(f"✅ WebSocket accepted and connected for project {id} by user {user_id}")
    active_sockets[id] = websocket

    # Send message history on connect
    try:
        async for db in get_db():
            # Get chat info including app_url
            chat_result = await db.execute(
                select(Chat).where(Chat.id == id)
            )
            chat = chat_result.scalar_one_or_none()
            
            print(f"📊 Chat info for {id}: {chat}")
            print(f"🔗 App URL: {chat.app_url if chat else 'No chat found'}")
            
            result = await db.execute(
                select(Message)
                .where(Message.chat_id == id)
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()
            
            print(f"📨 Sending history with {len(messages)} messages and app_url: {chat.app_url if chat else None}")
            
            if messages:  # Only send if there are messages
                await websocket.send_json({
                    "type": "history",
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "event_type": msg.event_type,
                            "created_at": msg.created_at.isoformat(),
                            "tool_calls": msg.tool_calls if hasattr(msg, 'tool_calls') else None
                        }
                        for msg in messages
                    ],
                    "app_url": chat.app_url if chat else None
                })
            else:
                # Send empty history for new chats
                await websocket.send_json({
                    "type": "history",
                    "messages": [],
                    "app_url": chat.app_url if chat else None
                })
            print(f"✅ Successfully sent history for {id}")
            break
    except Exception as e:
        print(f"❌ Error sending message history: {e}")
        import traceback
        traceback.print_exc()
        # Continue anyway, this is not critical

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except RuntimeError as e:
                # WebSocket was closed (probably replaced by new connection)
                print(f"WebSocket receive error for {id}: {e}")
                break

            if data.get("type") == "chat_message":
                prompt = data.get("prompt")

                if not prompt:
                    await websocket.send_json(
                        {"e": "error", "message": "No prompt provided"}
                    )
                    continue

                # Check token/credit availability before processing query
                async for db in get_db():
                    result = await db.execute(
                        select(User).where(User.id == int(user_id))
                    )
                    current_user = result.scalar_one_or_none()

                    if not current_user.can_make_query():
                        hours_remaining = current_user.get_time_until_reset()
                        await websocket.send_json(
                            {
                                "e": "error",
                                "message": f"No tokens remaining. You have used all your tokens. You get 2 tokens per 24 hours. Reset in {hours_remaining:.1f} hours.",
                                "tokens_remaining": current_user.tokens_remaining,
                                "reset_in_hours": hours_remaining
                            }
                        )
                        break

                    # Use one token for this query
                    if not current_user.use_token():
                        await websocket.send_json(
                            {
                                "e": "error",
                                "message": "Failed to consume token. Please try again."
                            }
                        )
                        break
                    
                    await db.commit()
                    
                    # Send token status to client
                    await websocket.send_json(
                        {
                            "type": "token_update",
                            "tokens_remaining": current_user.tokens_remaining,
                            "reset_in_hours": current_user.get_time_until_reset()
                        }
                    )
                    break

                if id in active_runs:
                    await websocket.send_json(
                        {
                            "e": "error",
                            "message": "Project is being created. Please wait for the current build to complete.",
                        }
                    )
                    continue

                # Store the user message
                async for db in get_db():
                    user_message = Message(
                        id=str(uuid.uuid4()),
                        chat_id=id,
                        role="user",
                        content=prompt
                    )
                    db.add(user_message)
                    await db.commit()
                    break

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
                        # Store the error message
                        try:
                            async for db in get_db():
                                error_message = Message(
                                    id=str(uuid.uuid4()),
                                    chat_id=id,
                                    role="assistant",
                                    content=f"Build failed: {str(e)}",
                                    event_type="error"
                                )
                                db.add(error_message)
                                await db.commit()
                                break
                        except Exception as db_err:
                            print(f"Failed to store error message: {db_err}")

                        # Try to send error to client, but don't fail if WebSocket is closed
                        try:
                            await websocket.send_json(
                                {"e": "error", "message": f"Build failed: {str(e)}"}
                            )
                        except Exception as ws_err:
                            print(f"Failed to send error to WebSocket: {ws_err}")
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
