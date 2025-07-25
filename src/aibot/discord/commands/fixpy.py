import os

from discord import (
    Interaction,
    TextStyle,
)
from discord.ui import Modal, TextInput

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage
from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.services.instruction import InstructionService
from src.aibot.services.provider import ProviderManager

api_factory = ApiFactory()
client: BotClient = BotClient.get_instance()
instruction_service = InstructionService()
provider_manager = ProviderManager.get_instance()


class CodeModal(Modal):
    """Modal for entering Python code to fix."""

    code_input: TextInput

    def __init__(self) -> None:
        """Initialize the code modal with AI parameters."""
        super().__init__(title="Pythonバグ修正")

        self.code_input = TextInput(
            label="Pythonコード",
            style=TextStyle.long,
            placeholder="Pythonコードを入力してください",
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
        await interaction.response.defer(thinking=True)

        try:
            code = self.code_input.value

            system_instruction = instruction_service.load_static_instruction("fixpy")

            # Get FIXPY_MODEL from environment, if specified
            fixpy_model = os.getenv("FIXPY_MODEL")
            model_params = {"model": fixpy_model} if fixpy_model else None

            logger.debug("Using model parameters for fixpy: %s", model_params)

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
            msg = f"Error processing fixpy command request: {err!s}"
            logger.exception(msg)
            await interaction.followup.send(
                "**ERROR** - `/fixpy`コマンドの処理中にエラーが発生しました",
                ephemeral=True,
            )


@client.tree.command(name="fixpy", description="Pythonコードのバグを特定し修正します")
async def fixpy_command(
    interaction: Interaction,
) -> None:
    """Detect and fix bugs in Python code.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.
    """
    try:
        user = interaction.user
        logger.info("User ( %s ) executed 'fixpy' command", user)

        # Show the modal to input code
        modal = CodeModal()
        await interaction.response.send_modal(modal)

    except Exception as err:
        msg = f"Error showing fixpy modal: {err!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "**ERROR** - `/fixpy`コマンドの実行中にエラーが発生しました",
            ephemeral=True,
        )
