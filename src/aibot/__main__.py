import asyncio
import os

from dotenv import load_dotenv

# Load environment variables here
# This must happen before importing modules that rely on env vars
load_dotenv()

from src.aibot.cli import logger  # noqa: E402
from src.aibot.discord.client import BotClient  # noqa: E402
from src.aibot.discord.commands import *  # noqa: F403, E402
from src.aibot.infrastructure.db.dao.instruction import InstructionDAO  # noqa: E402
from src.aibot.infrastructure.db.dao.moderation import ModerationDAO  # noqa: E402
from src.aibot.infrastructure.db.dao.permission import PermissionDAO  # noqa: E402
from src.aibot.infrastructure.db.dao.system import SystemDAO  # noqa: E402
from src.aibot.infrastructure.db.dao.usage import UsageDAO  # noqa: E402


async def main() -> None:
    await InstructionDAO().create_table()
    await ModerationDAO().create_table()
    await PermissionDAO().create_table()
    await SystemDAO().create_table()

    usage_dao = UsageDAO()
    await usage_dao.create_table()
    await usage_dao.create_usage_tracking_table()

    DISCORD_BOT_TOKEN: str = os.environ["DISCORD_BOT_TOKEN"]  # noqa: N806

    client = BotClient.get_instance()

    try:
        await client.start(DISCORD_BOT_TOKEN)
    except Exception:
        logger.exception("An unexpected error occurred")
    finally:
        logger.info("Cleanup process finished")


if __name__ == "__main__":
    asyncio.run(main())
