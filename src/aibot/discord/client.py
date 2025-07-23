from discord import Client, Intents, app_commands

from aibot.cli import logger

intents = Intents.default()
intents.message_content = True
intents.members = True


class BotClient(Client):
    """A singleton bot client for Discord applications.

    Attributes
    ----------
    _instance : BotClient
        The singleton instance of the BotClient class.
    tree : app_commands.CommandTree
        The command tree for registering and managing slash commands.
    """

    _instance: "BotClient"
    tree: app_commands.CommandTree

    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    @classmethod
    def get_instance(cls) -> "BotClient":
        """Get the singleton instance of the BotClient class.

        Returns
        -------
        BotClient
            The instance of the BotClient class.
        """
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    async def setup_hook(self) -> None:
        """Set up the bot before connecting to the Discord gateway."""
        logger.debug("Setting up bot...")
        logger.debug("Registered commands: %s", [cmd.name for cmd in self.tree.get_commands()])
        await self.tree.sync()
        logger.info("Command tree synchronized")

    async def on_ready(self) -> None:
        """Event handler called when the bot is ready."""
        logger.info("%s is ready!!", self.user)
        logger.debug(
            "Available slash commands: %s",
            [cmd.name for cmd in self.tree.get_commands()],
        )

    async def cleanup_hook(self) -> None:
        """Clean up resources when the bot is shutting down."""
        logger.info("%s is shutting down...", self.user)
