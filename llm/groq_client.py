import json
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0,
)


def chat(system: str, user: str) -> str:
    response = llm.invoke([("system", system), ("human", user)])
    return response.content.strip()


def chat_json(system: str, user: str, fallback: dict) -> dict:
    raw = chat(system + "\nReturn ONLY a JSON object, no prose.", user)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return fallback
