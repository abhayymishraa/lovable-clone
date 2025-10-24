from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import json
from agent.service import agent_service

app = FastAPI(title="lovable")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_sockets: dict[str, WebSocket] = {}
active_runs: dict[str, asyncio.Task] = {}


class ChatPayload(BaseModel):
    prompt: str


@app.post("/chat/{id}")
async def create_project(id: str, payload: dict):
    prompt = payload.get("prompt")
    if not prompt:
        return JSONResponse({"error": "Too short or no description"}, status_code=400)
    
    if id in active_runs:
        return JSONResponse({"error": "Project is being created. Kindly wait"}, status_code=400)
    
    async def agent_task():
        try:
            while id not in active_sockets:
                await asyncio.sleep(0.2)
            socket = active_sockets[id]
            await agent_service.run_agent_stream(prompt=prompt, id=id, socket=socket)
        except Exception as e:
            print(f"Error in agent task for project {id}: {e}")
        finally:
            active_runs.pop(id, None)
    
    active_runs[id] = asyncio.create_task(agent_task())
    return {
        "status": "success",
        "message": f"Agent started for project {id}. Connect via WebSocket to see progress."
    }


@app.get("/projects/{id}/files")
async def get_project_files(id: str):
    sandbox = agent_service.sandboxes.get(id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Project sandbox not found or not active.")
    
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
async def ws_listener(websocket: WebSocket, id: str):
    await websocket.accept()
    print(f"WebSocket connected for project {id}")
    active_sockets[id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for project {id}")
    finally:
        active_sockets.pop(id, None)
