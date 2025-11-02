import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEndpoint


load_dotenv()

hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")


# Google models (keeping as fallback)
llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)
llm_gemini_pro = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)

# OpenAI models for different tasks
llm_openai = ChatOpenAI(model="gpt-5-mini", temperature=0.7)  # Main UI generation
llm_openai_min = ChatOpenAI(
    model="gpt-5-nano", temperature=0.3
)  # Security checks and minimal tasks

# Set the main LLM to use GPT-5 for UI generation
llm = llm_openai


llm_huggingface = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen3-VL-30B-A3B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=hf_token,
    temperature=0.7,
)

# Model usage:
# - llm_openai (GPT-5): Main UI generation and React development
# - llm_openai_min (GPT-5-nano): Security checks, prompt enhancement, minimal tasks
# - llm_gemini: Fallback models (keeping for compatibility)
