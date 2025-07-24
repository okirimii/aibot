import os

from aibot.core.entities.chat import ChatMessage
from src.aibot.cli import logger
from src.aibot.infrastructure.api._params import ClaudeParams, GeminiParams, GPTParams, ParamsUnion
from src.aibot.services.provider import ProviderManager, ProviderType

from ._anthropic import generate_anthropic_response
from ._gemini import generate_gemini_response
from ._openai import generate_openai_response

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")

DEFAULT_ANTHROPIC_MODEL = os.getenv("DEFAULT_ANTHROPIC_MODEL")
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL")
DEFAULT_OPENAI_MODEL = os.getenv("DEFAULT_OPENAI_MODEL")

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

    def _detect_provider_from_model(self, model: str) -> ProviderType | None:
        """Detect provider from model name prefix.

        Parameters
        ----------
        model : str
            The model name to analyze.

        Returns
        -------
        ProviderType | None
            The detected provider type, or None if not detectable.
        """
        if model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gemini"):  # noqa: RET505
            return "google"
        elif model.startswith("gpt"):
            return "openai"
        return None

    def _get_default_model(self, provider: ProviderType) -> str | None:
        """Get default model for the specified provider.

        Parameters
        ----------
        provider : ProviderType
            The provider type.

        Returns
        -------
        str | None
            The default model name, or None if not configured.
        """
        model_mapping = {
            "anthropic": DEFAULT_ANTHROPIC_MODEL or ANTHROPIC_MODEL,
            "google": DEFAULT_GEMINI_MODEL or GEMINI_MODEL,
            "openai": DEFAULT_OPENAI_MODEL or OPENAI_MODEL,
        }
        return model_mapping.get(provider)

    def _create_model_params(
        self,
        model_params: dict | None = None,
    ) -> tuple[ProviderType, ParamsUnion]:
        """Create model parameters with optional overrides.

        Parameters
        ----------
        model_params : dict | None
            Optional dictionary containing model parameters to override defaults.
            Can contain: model, temperature, max_tokens, top_p

        Returns
        -------
        tuple[ProviderType, ParamsUnion]
            Tuple of (provider, model_params) determined from model or current setting.
        """
        # Extract model from params if provided
        model = model_params.get("model") if model_params else None

        # Determine provider and model
        if model:
            # Detect provider from model name prefix
            provider = self._detect_provider_from_model(model)
            if provider is None:
                # Fallback to current provider if model prefix is not recognized
                provider = self._provider_manager.get_provider()
            actual_model = model
        else:
            # Use current provider setting
            provider = self._provider_manager.get_provider()
            actual_model = self._get_default_model(provider)

        # Extract other parameters with defaults
        temperature = (
            model_params.get("temperature", DEFAULT_TEMPERATURE)
            if model_params
            else DEFAULT_TEMPERATURE
        )
        max_tokens = (
            model_params.get("max_tokens", DEFAULT_MAX_TOKENS)
            if model_params
            else DEFAULT_MAX_TOKENS
        )
        top_p = model_params.get("top_p", DEFAULT_TOP_P) if model_params else DEFAULT_TOP_P

        # Create provider-specific params
        if provider == "anthropic":
            params = ClaudeParams(
                model=actual_model,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        elif provider == "google":
            params = GeminiParams(
                model=actual_model,
                temperature=temperature,
                top_p=top_p,
            )
        elif provider == "openai":
            params = GPTParams(
                model=actual_model,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        else:
            msg = f"Unsupported provider: {provider}"
            raise ValueError(msg)

        return provider, params

    async def generate_response(
        self,
        messages: list[ChatMessage],
        system: str,
        model_params: dict | None = None,
    ) -> ChatMessage:
        """Generate a response using the specified model parameters.

        Parameters
        ----------
        messages : list[ChatMessage]
            The conversation messages.
        system : str
            The system prompt to use.
        model_params : dict | None
            Optional model parameters. Can contain: model, temperature, max_tokens, top_p.
            If None, uses current provider setting and default parameters.

        Returns
        -------
        ChatMessage
            The response from the AI provider.

        Raises
        ------
        ValueError
            If the provider is unsupported or model is not configured.
        """
        provider, params = self._create_model_params(model_params)

        logger.info("Generating response using provider: %s", provider)

        if provider == "anthropic":
            return await generate_anthropic_response(
                messages=messages,
                system=system,
                model_params=params,
            )
        elif provider == "google":  # noqa: RET505
            return await generate_gemini_response(
                messages=messages,
                system=system,
                model_params=params,
            )
        elif provider == "openai":
            return await generate_openai_response(
                messages=messages,
                system=system,
                model_params=params,
            )
        else:
            msg = f"Unsupported provider: {provider}"
            raise ValueError(msg)
