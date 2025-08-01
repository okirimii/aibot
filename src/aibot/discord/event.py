import os

from discord import ChannelType
from discord import Message as DiscordMessage

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage
from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.infrastructure.db.dao.usage import UsageDAO
from src.aibot.services.instruction import InstructionService
from src.aibot.services.moderation import ModerationService
from src.aibot.services.thread_session import ThreadSessionService

client = BotClient().get_instance()
api_factory = ApiFactory()
instruction_service = InstructionService()
moderation_service = ModerationService()
thread_session_service = ThreadSessionService.get_instance()

BOT_ID = int(os.getenv("BOT_ID", "0"))


@client.event
async def on_message(user_msg: DiscordMessage) -> None:
    """Event handler for Discord message events.

    Parameters
    ----------
    user_msg : DiscordMessage
        A message received from discord.
    """
    # Ignore messages from the bot itself
    if user_msg.author.id == BOT_ID:
        return

    # Only process messages in public threads
    if user_msg.channel.type != ChannelType.public_thread:
        return

    thread = user_msg.channel

    # Check if this thread has an active session
    session = thread_session_service.get_session(thread.id)
    if session is None:
        return

    try:
        user = user_msg.author

        # Moderate content before processing
        is_flagged = await moderation_service.moderate_content(
            content=user_msg.content,
            user_id=user.id,
            request_type="thread_chat",
        )

        if is_flagged:
            await thread.send(
                "モデレーションシステムにより、入力が拒否されました。",
                ephemeral=True,
            )
            return

        # Add user message to conversation history
        user_chat_message = ChatMessage(role="user", content=user_msg.content)
        thread_session_service.add_message_to_session(thread.id, user_chat_message)

        # Track usage
        usage_dao = UsageDAO()
        await usage_dao.increment_usage_count(user.id)

        # Get system instruction for talk command
        system_instruction = await instruction_service.get_active_instruction("talk")
        if system_instruction is None:
            logger.warning("No active instruction found for talk, using static instruction")
            system_instruction = instruction_service.load_static_instruction("talk")

        async with thread.typing():
            # Generate AI response using session configuration and conversation history
            response = await api_factory.generate_response(
                system=system_instruction,
                messages=session["conversation_history"],
                model_params={
                    "model": session["model"],
                    "temperature": session["temperature"],
                    "max_tokens": session["max_tokens"],
                    "top_p": session["top_p"],
                },
            )

        # Add AI response to conversation history
        ai_chat_message = ChatMessage(role="assistant", content=response.content)
        thread_session_service.add_message_to_session(thread.id, ai_chat_message)

        # Send response to thread
        await thread.send(response.content)

    except Exception as err:
        msg = f"Error processing thread message: {err!s}"
        logger.exception(msg)
        try:
            await thread.send(
                "メッセージの処理中にエラーが発生しました。",
            )
        except Exception:
            logger.exception("Failed to send error message to thread")
