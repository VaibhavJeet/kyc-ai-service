"""
LangChain Tools for AI Service
Defines tools that agents can use for various tasks
"""

from typing import Optional, Dict, Any, List
from langchain_core.tools import tool
from app.services.llm_service import get_llm_service
from app.services.face_service import get_face_service
from app.services.ocr_service import get_ocr_service


@tool
def generate_title(description: str) -> str:
    """Generate a concise title for a given task description."""
    import asyncio
    llm = get_llm_service()
    if not llm.is_available():
        return "Untitled Task"
    return asyncio.get_event_loop().run_until_complete(
        llm.generate_title(description)
    )


@tool
def generate_description(title: str, context: str = "") -> str:
    """Generate a detailed description for a task given its title and optional context."""
    import asyncio
    llm = get_llm_service()
    if not llm.is_available():
        return f"Task: {title}"
    return asyncio.get_event_loop().run_until_complete(
        llm.generate_description(title, context)
    )


@tool
def suggest_budget(title: str, description: str, category: str = "", currency: str = "INR") -> Dict[str, Any]:
    """Suggest a budget range for a task based on title, description, and category."""
    import asyncio
    llm = get_llm_service()
    if not llm.is_available():
        return {"min": 500, "max": 5000, "recommended": 1500, "currency": currency}
    result = asyncio.get_event_loop().run_until_complete(
        llm.suggest_budget(title, description, category, currency)
    )
    result["currency"] = currency
    return result


@tool
def chat_response(message: str, history: str = "") -> str:
    """Generate a chat response given a message and optional conversation history."""
    import asyncio
    llm = get_llm_service()
    if not llm.is_available():
        return "I'm sorry, I'm not able to respond right now."

    messages = []
    if history:
        # Parse history if provided
        for line in history.split("\n"):
            if line.startswith("User:"):
                messages.append({"role": "user", "content": line[5:].strip()})
            elif line.startswith("Assistant:"):
                messages.append({"role": "assistant", "content": line[10:].strip()})

    messages.append({"role": "user", "content": message})

    return asyncio.get_event_loop().run_until_complete(
        llm.chat(messages)
    )


def get_all_tools() -> List:
    """Get all available tools"""
    return [
        generate_title,
        generate_description,
        suggest_budget,
        chat_response,
    ]
