"""
Agent Router - Lightweight Intent-Based Routing
Routes requests to appropriate handlers without heavy agent overhead
Uses simple classification instead of full agent loops (~40-60MB RAM)
"""

import structlog
from typing import Optional, Dict, Any, List
from enum import Enum
from app.services.llm_service import get_llm_service

logger = structlog.get_logger(__name__)


class Intent(str, Enum):
    """Supported intents for routing"""
    CHAT = "chat"
    GENERATE_TITLE = "generate_title"
    GENERATE_DESCRIPTION = "generate_description"
    SUGGEST_BUDGET = "suggest_budget"
    GENERAL = "general"


class AgentRouter:
    """
    Lightweight router that classifies intent and routes to handlers.
    No heavy agent loops - just simple classification + direct function calls.
    """

    def __init__(self):
        self.llm = get_llm_service()

    async def classify_intent(self, query: str) -> Intent:
        """
        Classify user intent using rule-based matching first,
        then LLM for ambiguous cases.
        """
        query_lower = query.lower()

        # Rule-based classification (fast, no LLM call)
        if any(word in query_lower for word in ["title", "heading", "name for"]):
            return Intent.GENERATE_TITLE

        if any(word in query_lower for word in ["describe", "description", "explain", "detail"]):
            return Intent.GENERATE_DESCRIPTION

        if any(word in query_lower for word in ["budget", "cost", "price", "estimate", "how much"]):
            return Intent.SUGGEST_BUDGET

        if any(word in query_lower for word in ["chat", "talk", "hello", "hi", "help"]):
            return Intent.CHAT

        # Default to general for ambiguous cases
        return Intent.GENERAL

    async def route(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route query to appropriate handler based on intent.
        Returns structured response.
        """
        context = context or {}
        intent = await self.classify_intent(query)

        logger.info("Routing request", intent=intent.value, query=query[:50])

        if intent == Intent.GENERATE_TITLE:
            return await self._handle_title(query, context)

        elif intent == Intent.GENERATE_DESCRIPTION:
            return await self._handle_description(query, context)

        elif intent == Intent.SUGGEST_BUDGET:
            return await self._handle_budget(query, context)

        elif intent == Intent.CHAT:
            return await self._handle_chat(query, context)

        else:
            return await self._handle_general(query, context)

    async def _handle_title(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a title for the given content"""
        llm = get_llm_service()
        if not llm.is_available():
            return {
                "intent": Intent.GENERATE_TITLE.value,
                "success": False,
                "error": "LLM not available"
            }

        # Extract the content to title from query
        content = context.get("content", query)
        title = await llm.generate_title(content)

        return {
            "intent": Intent.GENERATE_TITLE.value,
            "success": True,
            "title": title
        }

    async def _handle_description(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a description"""
        llm = get_llm_service()
        if not llm.is_available():
            return {
                "intent": Intent.GENERATE_DESCRIPTION.value,
                "success": False,
                "error": "LLM not available"
            }

        title = context.get("title", query)
        extra_context = context.get("context", "")
        description = await llm.generate_description(title, extra_context)

        return {
            "intent": Intent.GENERATE_DESCRIPTION.value,
            "success": True,
            "description": description
        }

    async def _handle_budget(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest a budget"""
        llm = get_llm_service()
        if not llm.is_available():
            return {
                "intent": Intent.SUGGEST_BUDGET.value,
                "success": False,
                "error": "LLM not available",
                "budget": {"min": 500, "max": 5000, "recommended": 1500}
            }

        title = context.get("title", "Task")
        description = context.get("description", query)
        category = context.get("category", "")
        currency = context.get("currency", "INR")

        budget = await llm.suggest_budget(title, description, category, currency)

        return {
            "intent": Intent.SUGGEST_BUDGET.value,
            "success": True,
            "budget": budget
        }

    async def _handle_chat(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle chat messages"""
        llm = get_llm_service()
        if not llm.is_available():
            return {
                "intent": Intent.CHAT.value,
                "success": False,
                "error": "LLM not available"
            }

        history = context.get("history", [])
        messages = history + [{"role": "user", "content": query}]

        response = await llm.chat(messages)

        return {
            "intent": Intent.CHAT.value,
            "success": True,
            "response": response
        }

    async def _handle_general(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general queries"""
        llm = get_llm_service()
        if not llm.is_available():
            return {
                "intent": Intent.GENERAL.value,
                "success": False,
                "error": "LLM not available"
            }

        response = await llm.generate(query)

        return {
            "intent": Intent.GENERAL.value,
            "success": True,
            "response": response
        }


# Singleton
_router: Optional[AgentRouter] = None


def get_router() -> AgentRouter:
    """Get or create router instance"""
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router
