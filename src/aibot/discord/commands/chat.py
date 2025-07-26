from discord import Interaction

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage
from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.services.instruction import InstructionService
from src.aibot.services.provider import ProviderManager

api_factory = ApiFactory()
client = BotClient().get_instance()
instruction_service = InstructionService()
provider_manager = ProviderManager.get_instance()


@client.tree.command(name="chat", description="AIとシングルターンのチャットを行います")
async def chat_command(interaction: Interaction, user_msg: str) -> None:
    """Single-turn chat with the bot.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.

    user_msg : str
        The message to send to the bot.
    """
    try:
        user = interaction.user
        logger.info("User ( %s ) is executing chat command", user)

        await interaction.response.defer()

        message = ChatMessage(role="user", content=user_msg)

        # Get dynamic system prompt or fallback to static
        system_instruction = await instruction_service.get_active_instruction("chat")
        if system_instruction is None:
            logger.warning("No active instruction found, using static instruction")
            system_instruction = instruction_service.load_static_instruction("chat")

        # Get current provider and generate response
        current_provider = provider_manager.get_provider()
        logger.debug("Using AI provider: %s for chat", current_provider)

        response = await api_factory.generate_response(
            system=system_instruction,
            messages=[message],
        )

        await interaction.followup.send(f"{response.content}")
    except Exception as err:
        msg = f"Error in chat command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "`/chat` コマンドの実行中にエラーが発生しました。",
            ephemeral=True,
        )
