import os

from aibot.core.entities.chat import ChatMessage
from src.aibot.cli import logger
from src.aibot.infrastructure.api._params import ClaudeParams, GeminiParams, GPTParams, ParamsUnion
from src.aibot.services.provider import ProviderManager, ProviderType

from ._anthropic import generate_anthropic_response
from ._gemini import generate_gemini_response
from ._openai import generate_openai_response

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4096"))
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.62"))
DEFAULT_TOP_P = float(os.getenv("DEFAULT_TOP_P", "0.96"))


class ApiFactory:
    """Factory class for generating responses from different AI providers.

    Methods
    -------
    generate_response
        Generate a response using the specified or current provider.
    """

    def __init__(self) -> None:
        """Initialize the API factory."""
        self._provider_manager = ProviderManager.get_instance()

    def _create_model_params(self, provider: ProviderType) -> ParamsUnion:
        """Create model parameters based on the provider type."""
        if provider == "anthropic":
            return ClaudeParams(
                model=ANTHROPIC_MODEL,
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
                top_p=DEFAULT_TOP_P,
            )
        elif provider == "google":  # noqa: RET505
            return GeminiParams(
                model=GEMINI_MODEL,
                temperature=DEFAULT_TEMPERATURE,
                top_p=DEFAULT_TOP_P,
            )
        elif provider == "openai":
            return GPTParams(
                model=OPENAI_MODEL,
                max_tokens=DEFAULT_MAX_TOKENS,
                temperature=DEFAULT_TEMPERATURE,
                top_p=DEFAULT_TOP_P,
            )
        return None

    async def generate_response(
        self,
        messages: list[ChatMessage],
        system: str,
        provider: ProviderType | None = None,
    ) -> ChatMessage:
        """Generate a response using the specified or current provider.

        Parameters
        ----------
        messages : list[ChatMessage]
            The conversation messages.
        system : str
            The system prompt to use.
        provider : ProviderType | None
            Optional provider override. If None, uses current setting.

        Returns
        -------
        ResponseResult
            The response from the AI provider.

        Raises
        ------
        ValueError
            If the provider is unsupported or model is not configured.
        """
        if provider is None:
            provider = self._provider_manager.get_provider()

        model_params = self._create_model_params(provider)

        logger.info("Generating response using provider: %s", provider)

        if provider == "anthropic":
            return await generate_anthropic_response(
                messages=messages,
                system=system,
                model_params=model_params,
            )
        elif provider == "google":  # noqa: RET505
            return await generate_gemini_response(
                messages=messages,
                system=system,
                model_params=model_params,
            )
        elif provider == "openai":
            return await generate_openai_response(
                messages=messages,
                system=system,
                model_params=model_params,
            )
        return None
