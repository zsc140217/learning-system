"""
DeepSeek LLM Provider

DeepSeek API is OpenAI-compatible, so we use the OpenAI SDK with custom base_url.
"""
import os
from typing import List, Dict, Any, AsyncIterator
from .base_provider import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """
    DeepSeek LLM Provider using OpenAI-compatible API

    Supported models:
    - deepseek-chat
    - deepseek-coder

    API docs: https://platform.deepseek.com/api-docs/
    """

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

        # Call streaming API
        stream = await client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
