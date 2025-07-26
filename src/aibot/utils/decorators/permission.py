import os
from collections.abc import Callable
from typing import TypeVar

from discord import Interaction, app_commands

from src.aibot.infrastructure.db.dao.permission import PermissionDAO

T = TypeVar("T")


def is_admin_user() -> Callable[[T], T]:
    """Check if the user has administrative access level.

    Returns
    -------
    Callable[[T], T]
        A decorator that checks whether the user executing command is
        listed in the environment variable `ADMIN_USER_IDS`.
    """

    def predicate(interaction: Interaction) -> bool:
        return interaction.user.id in [int(i) for i in os.getenv("ADMIN_USER_IDS", "").split(",")]

    return app_commands.check(predicate)


def is_not_blocked_user() -> Callable[[T], T]:
    """Check if user has not been blocked.

    Returns
    -------
    Callable[[T], T]
        A decorator that checks whether the user executing command is not
        listed in the table `permissions` with the permission `blocked`.
    """

    async def predicate(interaction: Interaction) -> bool:
        blocked_user_ids = await PermissionDAO().fetch_user_ids_by_permission(permission="blocked")
        return interaction.user.id not in blocked_user_ids

    return app_commands.check(predicate)
