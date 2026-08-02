"""
Base LLM Provider abstract class
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers

    All LLM providers (OpenAI, Anthropic, local models) must implement this interface.
    This ensures consistent API across different LLM backends.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the provider with configuration

        Args:
            config: Provider-specific configuration (API keys, model names, etc.)
        """
        self.config = config or {}
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        Validate provider-specific configuration

        Raises:
            ValueError: If required configuration is missing
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Send chat messages and get response

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Example: [{"role": "user", "content": "Hello"}]
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text response

        Raises:
            Exception: If API call fails
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Any:
        """
        Send chat messages and get streaming response

        Args:
            messages: List of message dicts
            **kwargs: Provider-specific parameters

        Yields:
            Text chunks as they arrive

        Raises:
            Exception: If API call fails
        """
        pass

    def get_model_name(self) -> str:
        """
        Get the model name being used

        Returns:
            Model identifier string
        """
        return self.config.get("model", "unknown")

    def get_provider_name(self) -> str:
        """
        Get the provider name

        Returns:
            Provider identifier (e.g., "openai", "anthropic")
        """
        return self.__class__.__name__.replace("Provider", "").lower()
