"""
LLM Provider Factory
Creates provider instances based on configuration
"""
from typing import Dict, Any, Optional
from .base_provider import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances

    Usage:
        config = {"provider": "openai", "api_key": "sk-...", "model": "gpt-4o-mini"}
        provider = LLMProviderFactory.create(config)
        response = await provider.chat(messages)
    """

    _providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    @classmethod
    def create(
        cls,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseLLMProvider:
        """
        Create a provider instance based on configuration

        Args:
            config: Configuration dict with 'provider' key and provider-specific settings
                   Example: {"provider": "openai", "api_key": "...", "model": "gpt-4"}

        Returns:
            Initialized provider instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        config = config or {}
        provider_name = config.get("provider", "openai").lower()

        if provider_name not in cls._providers:
            raise ValueError(
                f"Unsupported provider: {provider_name}. "
                f"Supported providers: {', '.join(cls._providers.keys())}"
            )

        provider_class = cls._providers[provider_name]
        return provider_class(config)

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type
    ) -> None:
        """
        Register a custom provider

        Args:
            name: Provider name (e.g., "custom")
            provider_class: Provider class (must inherit from BaseLLMProvider)

        Raises:
            TypeError: If provider_class doesn't inherit from BaseLLMProvider
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError(
                f"Provider class must inherit from BaseLLMProvider, "
                f"got {provider_class.__name__}"
            )

        cls._providers[name.lower()] = provider_class

    @classmethod
    def list_providers(cls) -> list:
        """
        Get list of registered provider names

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
