import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def chat(system: str, user: str) -> str:
    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def chat_json(system: str, user: str, fallback: dict) -> dict:
    raw = chat(system + "\nReturn ONLY a JSON object, no prose.", user)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return fallback
