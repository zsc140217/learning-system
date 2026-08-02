"""
Anthropic Provider implementation
"""
import os
from typing import List, Dict, Any, AsyncIterator
from .base_provider import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic API provider

    Supports: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku, etc.

    Configuration:
        - api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
        - model: Model name (default: claude-3-5-sonnet-20241022)
        - temperature: Sampling temperature (default: 0.7)
        - max_tokens: Maximum tokens to generate (default: 4096)
    """

    def _validate_config(self) -> None:
        """Validate Anthropic configuration"""
        # Get API key from config or environment
        api_key = self.config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set 'api_key' in config or ANTHROPIC_API_KEY environment variable"
            )
        self.config["api_key"] = api_key

        # Set default model if not specified
        if "model" not in self.config:
            self.config["model"] = "claude-3-5-sonnet-20241022"

        # Anthropic requires max_tokens to be specified
        if "max_tokens" not in self.config:
            self.config["max_tokens"] = 4096

    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Send chat request to Anthropic API

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response
        """
        try:
            # Import here to avoid requiring anthropic package if not used
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        client = AsyncAnthropic(api_key=self.config["api_key"])

        # Merge config and kwargs
        params = {
            "model": self.config.get("model", "claude-3-5-sonnet-20241022"),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
        }

        # Make API call
        response = await client.messages.create(**params)

        return response.content[0].text

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Send streaming chat request to Anthropic API

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Yields:
            Text chunks as they arrive
        """
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        client = AsyncAnthropic(api_key=self.config["api_key"])

        params = {
            "model": self.config.get("model", "claude-3-5-sonnet-20241022"),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4096)),
        }

        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text
