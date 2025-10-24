import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from .prompts import INITPROMPT


load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)


# llm_with_tools = llm.bind_tools(tools=tools)

# agent_executor = create_react_agent(llm, tools,prompt=INITPROMPT)
