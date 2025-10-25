from .tools import create_tools_with_context
from langgraph.prebuilt import create_react_agent

from typing import Dict
from e2b_code_interpreter import AsyncSandbox
from dotenv import load_dotenv
from agent.prompts import INITPROMPT
from fastapi import WebSocket
from .agent import llm_gemini
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
            await self.sandboxes[id].set_timeout(1200) 
            print("Sandbox created with react enviornment")
        return self.sandboxes[id]
    
    async def close_sandbox(self, id: str):
        if id in self.sandboxes:
            sandbox = self.sandboxes.pop(id)
            await sandbox.kill()
            print(f"closed sandbox: {id}")
    


    async def run_agent_stream(self, prompt: str, id: str, socket: WebSocket):
        # await self.sandboxes[id].set_timeout(1200) 
        await socket.send_json({
            "e": "started",
            "message": "Starting to build - checking existing project structure first"
        })
        sandbox = await self.get_e2b_sandbox(id=id)

        tools = create_tools_with_context(sandbox, socket)
        
        agent_executor = create_react_agent(llm_gemini, tools=tools)

        config = {"recursion_limit": 40}

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
            print(f"Starting agent execution with prompt: {prompt}")
            print(f"Sandbox ID: {id}")
            print(f"Messages: {messages}")
            
            async for event in agent_executor.astream_events({ "messages": messages}, version="v1", config=config):
                kind = event["event"]
                print(f"Agent event: {kind}")

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        print(f"LLM thinking: {content}")
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
                    
                    if hasattr(tool_output, 'content'):
                        tool_output = tool_output.content
                    elif not isinstance(tool_output, str):
                        tool_output = str(tool_output)
                    
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
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            await socket.send_json({"e": "error", "message": str(e)})
            raise



agent_service = Service()