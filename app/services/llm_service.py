"""
LLM Service - Ultra-Lightweight Local LLM
Uses Gemma 3 270M Q4 via llama-cpp-python
~200MB model, ~450MB RAM, ~6-10 tokens/sec on CPU
"""

import structlog
import hashlib
import time
from typing import Optional, Dict, Any, List, Tuple
from llama_cpp import Llama
from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Simple in-memory cache for budget suggestions (TTL: 1 hour)
_budget_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


class LLMService:
    """Lightweight LLM service using llama.cpp"""

    def __init__(self):
        self.settings = get_settings()
        self.model: Optional[Llama] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the LLM model"""
        if self._initialized:
            return True

        try:
            logger.info("Initializing LLM", model=self.settings.llm_model_path)

            self.model = Llama(
                model_path=self.settings.llm_model_path,
                n_ctx=self.settings.llm_context_size,
                n_threads=self.settings.llm_threads,
                verbose=False,
            )

            self._initialized = True
            logger.info("LLM initialized successfully")
            return True

        except FileNotFoundError:
            logger.warning(
                "LLM model not found",
                path=self.settings.llm_model_path,
                hint="Download Gemma 3 270M GGUF model"
            )
            return False
        except Exception as e:
            logger.error("Failed to initialize LLM", error=str(e))
            return False

    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self._initialized and self.model is not None

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Generate text completion"""
        if not self.is_available():
            raise RuntimeError("LLM not initialized")

        response = self.model(
            prompt,
            max_tokens=max_tokens or self.settings.llm_max_tokens,
            temperature=temperature or self.settings.llm_temperature,
            stop=stop or ["</s>", "<|end|>", "<|eot_id|>"],
            echo=False,
        )

        return response["choices"][0]["text"].strip()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Chat completion with message history"""
        if not self.is_available():
            raise RuntimeError("LLM not initialized")

        response = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens or self.settings.llm_max_tokens,
            temperature=temperature or self.settings.llm_temperature,
        )

        return response["choices"][0]["message"]["content"].strip()

    async def generate_title(self, description: str) -> str:
        """Generate a title for a task description"""
        prompt = f"""Generate a short, concise title (5-10 words) for this task:

Task: {description}

Title:"""

        return await self.generate(prompt, max_tokens=32, temperature=0.5)

    async def generate_description(self, title: str, context: str = "") -> str:
        """Generate a detailed description for a task"""
        prompt = f"""Write a brief, professional description for this task:

Title: {title}
Context: {context if context else "General task"}

Description:"""

        return await self.generate(prompt, max_tokens=150, temperature=0.7)

    async def suggest_budget(
        self,
        title: str,
        description: str,
        category: str = "",
        currency: str = "INR"
    ) -> Dict[str, Any]:
        """Suggest a budget range for a task with caching"""
        global _budget_cache

        # Create cache key from normalized inputs
        cache_key = hashlib.md5(
            f"{title.lower().strip()}:{description.lower().strip()[:100]}:{category.lower()}:{currency}".encode()
        ).hexdigest()

        # Check cache
        if cache_key in _budget_cache:
            cached_result, cached_time = _budget_cache[cache_key]
            if time.time() - cached_time < CACHE_TTL_SECONDS:
                logger.info("Budget cache hit", cache_key=cache_key[:8])
                return cached_result
            else:
                # Expired, remove from cache
                del _budget_cache[cache_key]

        logger.info("Budget cache miss, calling LLM", cache_key=cache_key[:8])

        prompt = f"""Estimate a fair budget range for this task in {currency}.

Title: {title}
Description: {description}
Category: {category if category else "General"}

Respond with ONLY a JSON object like: {{"min": 500, "max": 2000, "recommended": 1000}}

Budget:"""

        response = await self.generate(prompt, max_tokens=50, temperature=0.3)

        # Parse JSON response
        result = {"min": 500, "max": 5000, "recommended": 1500}  # Default fallback
        try:
            import json
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
        except:
            pass

        # Cache the result
        _budget_cache[cache_key] = (result, time.time())

        # Limit cache size to prevent memory issues (keep last 100 entries)
        if len(_budget_cache) > 100:
            oldest_key = min(_budget_cache.keys(), key=lambda k: _budget_cache[k][1])
            del _budget_cache[oldest_key]

        return result

    def unload(self):
        """Unload model to free memory"""
        if self.model:
            del self.model
            self.model = None
            self._initialized = False
            logger.info("LLM model unloaded")


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
