from typing import Literal

from aibot.cli import logger

ProviderType = Literal["anthropic", "google", "openai"]


class ProviderManager:
    """Manages the AI provider setting for the application."""

    _instance: "ProviderManager | None" = None
    _provider: ProviderType = "openai"  # Default

    def __new__(cls) -> "ProviderManager":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ProviderManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_provider(self, provider: ProviderType) -> None:
        """Set the current AI provider."""
        if provider not in ["anthropic", "google", "openai"]:
            msg = f"Invalid provider: {provider}. Must be one of: anthropic, google, openai"
            raise ValueError(msg)

        self._provider = provider
        logger.info("AI provider changed to: %s", provider)

    def get_provider(self) -> ProviderType:
        """Get the current AI provider."""
        return self._provider

    def get_provider_display_name(self) -> str:
        """Get the display name of the current provider."""
        display_names = {
            "anthropic": "Anthropic",
            "google": "Google",
            "openai": "OpenAI",
        }
        return display_names[self._provider]
