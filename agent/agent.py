import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)
llm_gemini_pro = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key)

llm_gemini_flash = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)


llm = llm_gemini

llm_claude = ChatAnthropic(
    model="claude-sonnet-4-5-20250929", 
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0, 
)

