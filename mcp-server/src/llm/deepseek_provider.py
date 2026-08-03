"""
DeepSeek LLM Provider

DeepSeek API is OpenAI-compatible, so we use the OpenAI SDK with custom base_url.
"""
import os
import time
from typing import List, Dict, Any, AsyncIterator, Optional
from loguru import logger

from .base_provider import BaseLLMProvider
from ..utils.rate_limiter import RateLimiter
from ..utils.llm_cache import LLMCache
from ..utils.retry import retry_with_backoff


class DeepSeekProvider(BaseLLMProvider):
    """
    DeepSeek LLM Provider using OpenAI-compatible API

    Supported models:
    - deepseek-chat
    - deepseek-coder

    API docs: https://platform.deepseek.com/api-docs/

    Features:
    - Rate limiting (60 req/min by default)
    - Response caching (1 hour TTL)
    - Automatic retry with exponential backoff
    - Detailed logging with token counting
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DeepSeek provider with production features

        Args:
            config: Provider configuration
        """
        super().__init__(config)

        # Initialize rate limiter (DeepSeek free tier: 60 req/min)
        rate_limit = self.config.get("rate_limit", 60)
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit,
            time_window=60.0
        )

        # Initialize response cache
        cache_ttl = self.config.get("cache_ttl", 3600)
        cache_size = self.config.get("cache_size", 1000)
        self.cache = LLMCache(
            ttl_seconds=cache_ttl,
            max_size=cache_size
        )

        # Retry configuration
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)

        logger.info(
            f"DeepSeekProvider initialized: "
            f"model={self.config['model']}, "
            f"rate_limit={rate_limit}/min, "
            f"cache_ttl={cache_ttl}s"
        )

    def _validate_config(self) -> None:
        """Validate DeepSeek configuration"""
        api_key = self.config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")

        if not api_key:
            raise ValueError(
                "DeepSeek API key not found. "
                "Set DEEPSEEK_API_KEY environment variable or pass 'api_key' in config."
            )

        self.config["api_key"] = api_key

        # Default model
        if "model" not in self.config:
            self.config["model"] = "deepseek-chat"

        # Default base URL
        if "base_url" not in self.config:
            self.config["base_url"] = "https://api.deepseek.com"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Send chat request to DeepSeek API

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            **kwargs: Optional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response
        """
        temperature = kwargs.get("temperature", self.config.get("temperature", 0.7))
        model = self.config["model"]

        # Try cache first
        cached_response = self.cache.get(messages, model, temperature)
        if cached_response:
            logger.info("Using cached response")
            return cached_response

        # Acquire rate limit permission
        await self.rate_limiter.acquire()

        # Start timing
        start_time = time.time()

        # Count input tokens (rough estimate)
        prompt_tokens = self._estimate_tokens(messages)

        logger.info(
            f"LLM Request: model={model}, temperature={temperature}, "
            f"messages={len(messages)}, prompt_tokens~{prompt_tokens}"
        )

        try:
            # Call API with retry
            response = await retry_with_backoff(
                lambda: self._chat_impl(messages, **kwargs),
                max_retries=self.max_retries,
                base_delay=self.retry_delay
            )

            # Calculate metrics
            elapsed = time.time() - start_time
            completion_tokens = self._estimate_tokens([{"role": "assistant", "content": response}])
            total_tokens = prompt_tokens + completion_tokens
            cost = self._calculate_cost(prompt_tokens, completion_tokens)

            logger.info(
                f"LLM Response: "
                f"prompt_tokens~{prompt_tokens}, "
                f"completion_tokens~{completion_tokens}, "
                f"total_tokens~{total_tokens}, "
                f"cost~${cost:.4f}, "
                f"elapsed={elapsed:.2f}s"
            )

            # Cache the response
            self.cache.set(messages, model, temperature, response)

            return response

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            logger.error(
                f"LLM Error: {error_msg} (elapsed={elapsed:.2f}s)",
                exc_info=True
            )
            raise

    async def _chat_impl(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Internal implementation of chat API call

        Args:
            messages: List of message dicts
            **kwargs: Optional parameters

        Returns:
            Generated text response
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        # Create client with DeepSeek endpoint
        client = AsyncOpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )

        # Prepare parameters
        params = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
        }

        # Add optional parameters
        if "max_tokens" in kwargs or "max_tokens" in self.config:
            params["max_tokens"] = kwargs.get("max_tokens", self.config.get("max_tokens", 1000))

        if "top_p" in kwargs or "top_p" in self.config:
            params["top_p"] = kwargs.get("top_p", self.config.get("top_p"))

        if "frequency_penalty" in kwargs or "frequency_penalty" in self.config:
            params["frequency_penalty"] = kwargs.get(
                "frequency_penalty",
                self.config.get("frequency_penalty")
            )

        # Call API
        response = await client.chat.completions.create(**params)

        return response.choices[0].message.content

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Send streaming chat request to DeepSeek API

        Args:
            messages: List of message dicts
            **kwargs: Optional parameters

        Yields:
            Text chunks as they arrive
        """
        # Acquire rate limit permission
        await self.rate_limiter.acquire()

        start_time = time.time()
        model = self.config["model"]

        logger.info(f"LLM Stream Request: model={model}, messages={len(messages)}")

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        # Create client with DeepSeek endpoint
        client = AsyncOpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["base_url"]
        )

        # Prepare parameters
        params = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            "stream": True
        }

        # Add optional parameters
        if "max_tokens" in kwargs or "max_tokens" in self.config:
            params["max_tokens"] = kwargs.get("max_tokens", self.config.get("max_tokens", 1000))

        try:
            # Call streaming API
            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            elapsed = time.time() - start_time
            logger.info(f"LLM Stream Complete: elapsed={elapsed:.2f}s")

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            logger.error(f"LLM Stream Error: {error_msg} (elapsed={elapsed:.2f}s)", exc_info=True)
            raise

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for messages

        Rough approximation: 1 token ≈ 4 characters

        Args:
            messages: List of message dicts

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return int(total_chars / 4)

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate API call cost

        DeepSeek pricing (as of 2026-08):
        - Input: $0.14 / 1M tokens
        - Output: $0.28 / 1M tokens

        Args:
            prompt_tokens: Input token count
            completion_tokens: Output token count

        Returns:
            Cost in USD
        """
        input_cost_per_1m = 0.14
        output_cost_per_1m = 0.28

        input_cost = (prompt_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (completion_tokens / 1_000_000) * output_cost_per_1m

        return input_cost + output_cost

    def get_stats(self) -> Dict[str, Any]:
        """
        Get provider statistics

        Returns:
            Dict with cache, rate limiter stats
        """
        return {
            "provider": "deepseek",
            "model": self.config["model"],
            "cache": self.cache.get_stats(),
            "rate_limiter": self.rate_limiter.get_stats()
        }
