import asyncio

from discord import (
    Embed,
    Interaction,
    app_commands,
)

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.usage import has_daily_usage_left
from src.aibot.discord.utils.models import parse_models
from src.aibot.infrastructure.api.factory import ApiFactory
from src.aibot.infrastructure.db.dao.usage import UsageDAO
from src.aibot.services.instruction import InstructionService
from src.aibot.services.moderation import ModerationService
from src.aibot.services.provider import ProviderManager
from src.aibot.services.thread_session import ThreadSessionService

api_factory = ApiFactory()
client = BotClient().get_instance()
instruction_service = InstructionService()
moderation_service = ModerationService()
provider_manager = ProviderManager.get_instance()
thread_session_service = ThreadSessionService.get_instance()

TALK_MODEL_CHOICES = parse_models("TALK_MODELS")


@client.tree.command(
    name="talk",
    description="スレッドを作成し、AIとの会話を開始します",
)
@has_daily_usage_left()
@app_commands.rename(user_msg="message")
@app_commands.choices(model=TALK_MODEL_CHOICES) if TALK_MODEL_CHOICES else lambda f: f
async def talk_command(
    interaction: Interaction,
    user_msg: str,
    model: app_commands.Choice[str] | None = None,
) -> None:
    user = interaction.user
    try:
        # Moderate content before processing
        is_flagged = await moderation_service.moderate_content(
            content=user_msg,
            user_id=user.id,
            request_type="talk",
        )

        if is_flagged:
            await interaction.followup.send(
                "モデレーションシステムにより入力が拒否されました",
                ephemeral=True,
            )
            return

        # Get model name - use default if no choice provided
        model_name = model.value if model else provider_manager.get_provider()

        embed = Embed(
            description=f"<@{user.id}> **started the talk!**",
            color=0xF4B3C2,
        )
        embed.add_field(name="model", value=model_name, inline=True)
        embed.add_field(name="message", value=user_msg)

        await interaction.response.send_message(embed=embed)
        original_response = await interaction.original_response()

        # Create thread with 1-hour auto archive
        thread = await original_response.create_thread(
            name=f">> {user_msg[:20]}",
            auto_archive_duration=60,  # 1 hour
        )

        # Small delay to ensure thread is fully initialized
        await asyncio.sleep(0.1)

        # Track usage
        usage_dao = UsageDAO()
        await usage_dao.increment_usage_count(user.id)

        # Create thread session
        session = thread_session_service.create_session(
            thread_id=thread.id,
            model=model_name,
            creator_id=user.id,
        )

        # Add initial user message to conversation history
        user_chat_message = ChatMessage(role="user", content=user_msg)
        thread_session_service.add_message_to_session(thread.id, user_chat_message)

        # Get system instruction for talk command
        system_instruction = await instruction_service.get_active_instruction("talk")
        if system_instruction is None:
            logger.warning("No active instruction found for talk, using static instruction")
            system_instruction = instruction_service.load_static_instruction("talk")

        # Generate initial AI response
        response = await api_factory.generate_response(
            system=system_instruction,
            messages=[user_chat_message],
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

        # Send initial response to thread
        await thread.send(response.content)

        logger.info(
            "Created talk thread %d for user %d with model %s",
            thread.id,
            user.id,
            model_name,
        )

    except Exception as err:
        msg = f"Error in talk command: {err!s}"
        logger.exception(msg)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "`/talk` コマンドの実行中にエラーが発生しました。",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "`/talk` コマンドの実行中にエラーが発生しました。",
                    ephemeral=True,
                )
        except Exception:
            logger.exception("Failed to send error message for talk command")
