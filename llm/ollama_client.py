import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")

_MAX_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 1.5


def chat(system: str, user: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }

    last_exc = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except requests.RequestException as exc:
            body = exc.response.text if exc.response is not None else str(exc)
            last_exc = RuntimeError(f"Ollama API call failed ({OLLAMA_URL}): {body}")
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY_SECONDS)

    raise last_exc


def chat_json(system: str, user: str, fallback: dict) -> dict:
    raw = chat(system + "\nReturn ONLY a JSON object, no prose.", user)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return fallback
