from discord import (
    Interaction,
    TextStyle,
    app_commands,
)
from discord.ui import Modal, TextInput

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.permission import is_not_blocked_user
from src.aibot.discord.decorators.usage import has_daily_usage_left
from src.aibot.discord.utils.models import parse_models
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.infrastructure.db.dao.usage import UsageDAO
from src.aibot.security.input_validator import InputValidator
from src.aibot.services.instruction import InstructionService
from src.aibot.services.provider import ProviderManager

api_factory = ApiFactory()
client: BotClient = BotClient.get_instance()
instruction_service = InstructionService()
provider_manager = ProviderManager.get_instance()

# Generate model choices from environment variable
FIXME_MODEL_CHOICES = parse_models("FIXME_MODELS")


class CodeModal(Modal):
    """Modal for entering code to fix."""

    code_input: TextInput

    def __init__(self, selected_model: str | None = None) -> None:
        """Initialize the code modal with AI parameters.

        Parameters
        ----------
        selected_model : str | None, optional
            User-selected model ID from command argument
        """
        super().__init__(title="コード修正")
        self.selected_model = selected_model

        self.code_input = TextInput(
            label="コード",
            style=TextStyle.long,
            placeholder="修正したいコードを入力してください",
            required=True,
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: Interaction) -> None:
        """Handle the submission of the modal.

        Parameters
        ----------
        interaction : Interaction
            The interaction object from Discord.
        """
        try:
            code = self.code_input.value

            # Input validation
            is_valid, error_message = InputValidator.validate_code_input(code)
            if not is_valid:
                await interaction.response.send_message(
                    f"入力エラー: {error_message}",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(thinking=True)

            # Track usage
            usage_dao = UsageDAO()
            await usage_dao.increment_usage_count(interaction.user.id)

            system_instruction = instruction_service.load_static_instruction("fixme")

            # Use user-selected model if provided, otherwise use ProviderManager default
            model_params = {"model": self.selected_model} if self.selected_model else None

            logger.debug("Using model parameters for fixme: %s", model_params)

            message = [ChatMessage(role="user", content=code)]

            response = await api_factory.generate_response(
                system=system_instruction,
                messages=message,
                model_params=model_params,
            )

            if response.content is not None:
                await interaction.followup.send(
                    f"{response.content}",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "**ERROR** - AIサービスからの応答の生成に失敗しました",
                    ephemeral=True,
                )
        except Exception as err:
            msg = f"Error processing fixme command request: {err!s}"
            logger.exception(msg)
            await interaction.followup.send(
                "**ERROR** - `/fixme`コマンドの処理中にエラーが発生しました",
                ephemeral=True,
            )


@client.tree.command(name="fixme", description="コードのバグを特定し修正します")
@is_not_blocked_user()
@has_daily_usage_left()
@app_commands.choices(model=FIXME_MODEL_CHOICES) if FIXME_MODEL_CHOICES else lambda f: f
async def fixme_command(
    interaction: Interaction,
    model: str | None = None,
) -> None:
    """Detect and fix bugs in code.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.
    """
    try:
        user = interaction.user
        logger.info("User ( %s ) executed 'fixme' command", user)

        # Show the modal to input code
        modal = CodeModal(selected_model=model)
        await interaction.response.send_modal(modal)

    except Exception as err:
        msg = f"Error showing fixme modal: {err!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "**ERROR** - `/fixme`コマンドの実行中にエラーが発生しました",
            ephemeral=True,
        )
