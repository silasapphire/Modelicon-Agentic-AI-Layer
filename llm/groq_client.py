"""
groq_client.py

Single interface for all LLM interactions.

Every agent should import either:
    chat()
or
    chat_json()

Changing the LLM provider or model later only requires
modifying this file.
"""

import json
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
 
# Load environment variables


load_dotenv()

# Create one shared Groq client


llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0
)



# Plain text completion


def chat(system: str, user: str) -> str:
    """
    Returns a plain text response.

    Parameters
    ----------
    system : str
        System prompt.

    user : str
        User prompt.

    Returns
    -------
    str
        Model response.
    """

    response = llm.invoke(
        [
            ("system", system),
            ("human", user)
        ]
    )

    return response.content.strip()



# JSON completion

def chat_json(system: str, user: str, fallback: dict) -> dict:
    """
    Returns a JSON object.

    If the model produces invalid JSON,
    the fallback dictionary is returned.

    Parameters
    ----------
    system : str

    user : str

    fallback : dict

    Returns
    -------
    dict
    """

    raw = chat(
        system + "\nReturn ONLY valid JSON.",
        user
    )

    # Remove markdown formatting if present
    raw = (
        raw.replace("```json", "")
           .replace("```", "")
           .strip()
    )

    try:
        return json.loads(raw)

    except Exception:
        return fallback