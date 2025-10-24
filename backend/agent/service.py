from functools import partial
import json
import os

from .tools import create_tools_with_context

from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent

from utils.store import load_json_store, save_json_store
from typing import Dict
from e2b_code_interpreter import AsyncSandbox
from dotenv import load_dotenv
from agent.prompts import INITPROMPT
from fastapi import WebSocket
from .agent import llm
from langchain_core.messages import HumanMessage, SystemMessage
load_dotenv()

TEMPLATE_ID = "63i6x6z8nd0uzadokgzg"
base_path = "/home/user/react-app" 
class Service:

    def __init__(self) -> None:
        self.sandboxes: Dict[str, AsyncSandbox] = {}
    
    async def get_e2b_sandbox(self, id:str) -> AsyncSandbox:
        if id not in self.sandboxes:
            print(f"Initializing new sandbox for project id = {id}")
            self.sandboxes[id] = await AsyncSandbox.create(template=TEMPLATE_ID, timeout=600)
            print("Sandbox created with react enviornment")
        return self.sandboxes[id]
    
    async def close_sandbox(self, id: str):
        if id in self.sandboxes:
            sandbox = self.sandboxes.pop(id)
            await sandbox.kill()
            print(f"closed sandbox: {id}")
    


    async def run_agent_stream(self, prompt: str, id: str, socket: WebSocket):
        await socket.send_json({
            "e": "started",
            "message": "Starting to build - checking existing project structure first"
        })
        sandbox = await self.get_e2b_sandbox(id=id)

        # Create tools with sandbox and socket context
        tools = create_tools_with_context(sandbox, socket)
        
        # Restore React agent approach with proper tool handling
        agent_executor = create_react_agent(llm, tools=tools)
        config = {"recursion_limit": 10}

        host = sandbox.get_host(port=5173)
        url = f"https://{host}"
        
        messages = [
            SystemMessage(content=INITPROMPT),
            HumanMessage(content=prompt)
        ]

        if socket:
            await socket.send_json({
                "e": "starting",
                "message": "starting to run the agent stream"
            })
        try:
            async for event in agent_executor.astream_events({ "messages": messages}, version="v1", config=config):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        await socket.send_json({
                           "e" :"thinking",
                           "message": content
                        })
                
                elif kind == "on_tool_start":
                    data = event.get("data", {})
                    tool_name = event.get("name")
                    tool_input = data.get("input", {})
                    print(f"Tool start event: {event}")
                    await socket.send_json({
                        "e": "tool_started",
                        "tool": tool_name,
                        "args": tool_input
                    })
                    
                elif kind == "on_tool_end":
                    data = event.get("data", {})
                    tool_name = event.get("name")
                    tool_output = data.get("output")
                    
                    # Extract content from ToolMessage if it's not a string
                    if hasattr(tool_output, 'content'):
                        tool_output = tool_output.content
                    elif not isinstance(tool_output, str):
                        tool_output = str(tool_output)
                    
                    # Tool already executed and returned result to LLM
                    # Just notify frontend
                    await socket.send_json({
                        "e": "tool_ended",
                        "tool": tool_name,
                        "output": tool_output,
                        "message": f"Tool {tool_name} completed successfully"
                    })

                    
            host = sandbox.get_host(port=5173)
            url = f"https://{host}"
            print(f"\nProject live at: {url}\n")
            await socket.send_json({
                "e" : "completed",
                "url": url
            })
        except Exception as  e:
            print(f"Error during agent execution: {e}")
            await socket.send_json({"e": "error", "message": str(e)})
            raise



agent_service = Service()