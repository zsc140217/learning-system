"""
OpenAI Provider implementation
"""
import os
from typing import List, Dict, Any, AsyncIterator
from .base_provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API provider

    Supports: GPT-4, GPT-4-turbo, GPT-3.5-turbo, etc.

    Configuration:
        - api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        - model: Model name (default: gpt-4o-mini)
        - temperature: Sampling temperature (default: 0.7)
        - max_tokens: Maximum tokens to generate
    """

    def _validate_config(self) -> None:
        """Validate OpenAI configuration"""
        # Get API key from config or environment
        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set 'api_key' in config or OPENAI_API_KEY environment variable"
            )
        self.config["api_key"] = api_key

        # Set default model if not specified
        if "model" not in self.config:
            self.config["model"] = "gpt-4o-mini"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Send chat request to OpenAI API

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response
        """
        try:
            # Import here to avoid requiring openai package if not used
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        client = AsyncOpenAI(api_key=self.config["api_key"])

        # Merge config and kwargs
        params = {
            "model": self.config.get("model", "gpt-4o-mini"),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
        }

        if "max_tokens" in kwargs or "max_tokens" in self.config:
            params["max_tokens"] = kwargs.get("max_tokens", self.config.get("max_tokens"))

        # Make API call
        response = await client.chat.completions.create(**params)

        return response.choices[0].message.content

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Send streaming chat request to OpenAI API

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Yields:
            Text chunks as they arrive
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        client = AsyncOpenAI(api_key=self.config["api_key"])

        params = {
            "model": self.config.get("model", "gpt-4o-mini"),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            "stream": True,
        }

        if "max_tokens" in kwargs or "max_tokens" in self.config:
            params["max_tokens"] = kwargs.get("max_tokens", self.config.get("max_tokens"))

        stream = await client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
