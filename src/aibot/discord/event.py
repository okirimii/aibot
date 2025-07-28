from discord import Message as DiscordMessage

from src.aibot.discord.client import BotClient

client = BotClient().get_instance()


@client.event
async def on_message(user_msg: DiscordMessage) -> None:
    """Event handler for Discord message events.

    Parameters
    ----------
    user_msg : DiscordMessage
        A message received from discord.
    """
