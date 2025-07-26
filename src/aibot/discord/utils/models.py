import os

from discord import app_commands


def parse_models(env_var: str) -> list[app_commands.Choice[str]]:
    """Parse environment variable to generate model choices for Discord commands.

    Parameters
    ----------
    env_var : str
        Environment variable name (e.g., "FIXME_MODELS")
        Format: "model-id:display-name,model-id2:display-name2"

    Returns
    -------
    list[app_commands.Choice[str]]
        List of Discord app command choices for model selection
    """
    models_config = os.getenv(env_var, "")
    if not models_config:
        return []

    choices = []
    for model_entry in models_config.split(","):
        model_entry = model_entry.strip()
        if ":" in model_entry:
            model_id, display_name = model_entry.split(":", 1)
            choices.append(
                app_commands.Choice(
                    name=display_name.strip(),  # Display name shown in Discord UI
                    value=model_id.strip(),  # Actual model ID received in code
                ),
            )

    return choices
