from discord import Interaction, app_commands

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.usage import has_daily_usage_left
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.infrastructure.db.dao.usage import UsageDAO
from src.aibot.services.instruction import InstructionService
from src.aibot.services.moderation import ModerationService
from src.aibot.services.provider import ProviderManager

api_factory = ApiFactory()
client = BotClient().get_instance()
instruction_service = InstructionService()
moderation_service = ModerationService()
provider_manager = ProviderManager.get_instance()


@client.tree.command(name="chat", description="AIとシングルターンのチャットを行います")
@has_daily_usage_left()
@app_commands.rename(user_msg="message")
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

        # Moderate content before processing
        is_flagged = await moderation_service.moderate_content(
            content=user_msg,
            user_id=user.id,
            request_type="chat",
        )

        if is_flagged:
            await interaction.followup.send(
                "入力内容がコミュニティガイドラインに違反している可能性があります。",
                ephemeral=True,
            )
            return

        message = ChatMessage(role="user", content=user_msg)

        # Track usage
        usage_dao = UsageDAO()
        await usage_dao.increment_usage_count(user.id)

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
