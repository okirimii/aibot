from discord import Interaction, SelectOption, User
from discord.ui import Select, View

from src.aibot.cli import logger
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.permission import is_admin_user
from src.aibot.infrastructure.db.dao.permission import PermissionDAO

client = BotClient().get_instance()
permission_dao = PermissionDAO()


async def _validate_guild_and_user(interaction: Interaction, user: User) -> tuple[bool, int]:
    """Validate that the command is run in a guild and the user exists in the guild.

    Parameters
    ----------
    interaction : Interaction
        The Discord interaction context.
    user : User
        The target Discord user to validate.

    Returns
    -------
    tuple[bool, int]
        A tuple containing:
        - bool: True if validation passed, False if failed
        - int: The user ID if validation passed, 0 if failed
    """
    target_user_id: int = user.id

    if interaction.guild is None:
        await interaction.response.send_message(
            "サーバー内でのみ実行できます",
            ephemeral=True,
        )
        return False, 0

    target_user = interaction.guild.get_member(target_user_id)
    if target_user is None:
        await interaction.response.send_message(
            "ユーザーがサーバーに参加していません",
            ephemeral=True,
        )
        return False, 0

    return True, target_user_id


class PermissionAddSelector(Select):
    """Discord UI selector for granting permissions to users.

    This class creates a dropdown menu that allows administrators to
    select permissions ('beta' or 'blocked') to grant to a user.

    Parameters
    ----------
    user_id : int
        The Discord user ID to grant permission to.
    options : list[SelectOption]
        List of SelectOption objects representing available permissions.
    """

    def __init__(self, user_id: int, options: list[SelectOption]) -> None:
        self.user_id = user_id
        super().__init__(
            placeholder="権限を選択してください",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction) -> None:
        """Handle the user's selection of access level to grant.

        Parameters
        ----------
        interaction : Interaction
            The Discord interaction context.

        Notes
        -----
        This callback inserts the selected access level for the user into the database
        and sends a confirmation message.
        """
        chosen = self.values[0]  # "beta" or "blocked"
        if chosen == "beta":
            await permission_dao.grant(user_id=self.user_id, permission="beta")
        elif chosen == "blocked":
            await permission_dao.grant(user_id=self.user_id, permission="blocked")

        await interaction.response.send_message(
            f"{chosen}権限がユーザー (ID: {self.user_id}) に付与されました",
            ephemeral=True,
        )
        logger.info(
            "権限 <%s> がユーザー (ID: %s) に付与されました",
            chosen,
            self.user_id,
        )


class PermissionRemoveSelector(Select):
    """Discord UI selector for removing permissions for users.

    This class creates a dropdown menu that allows administrators to
    select permissions ('beta' or 'blocked') to remove for a user.

    Parameters
    ----------
    user_id : int
        The Discord user ID to remove permission for.
    options : list[SelectOption]
        List of SelectOption objects representing available permissions.
    """

    def __init__(self, user_id: int, options: list[SelectOption]) -> None:
        self.user_id = user_id
        super().__init__(
            placeholder="権限を選択してください",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction) -> None:
        chosen = self.values[0]  # "beta" or "blocked"

        # Check if the user currently has the selected access level
        user_ids_with_access = await permission_dao.fetch_user_ids_by_permission(chosen)

        if self.user_id in user_ids_with_access:
            await permission_dao.disable(user_id=self.user_id, permission=chosen)
            await interaction.response.send_message(
                f"{chosen}権限がユーザー (ID: {self.user_id}) から削除されました",
                ephemeral=True,
            )
            logger.info(
                "権限 <%s> がユーザー (ID: %s) から削除されました",
                chosen,
                self.user_id,
            )
        else:
            await interaction.response.send_message(
                f"{chosen}権限がユーザー (ID: {self.user_id}) に付与されていません",
                ephemeral=True,
            )


@client.tree.command(name="add-pm", description="ユーザーに権限を付与します")
@is_admin_user()
async def add_permission_command(interaction: Interaction, user: User) -> None:
    """Grant access level to a Discord user.

    Parameters
    ----------
    interaction : Interaction
        The Discord interaction context.
    user : User
        The target Discord user to grant access level to.

    Notes
    -----
    This function grants 'advanced' or 'blocked' access level to the specified user.
    """
    is_valid, target_user_id = await _validate_guild_and_user(interaction, user)
    if not is_valid:
        return

    options = [
        SelectOption(label="beta", value="beta"),
        SelectOption(label="blocked", value="blocked"),
    ]

    select = PermissionAddSelector(user_id=target_user_id, options=options)
    view = View()
    view.add_item(select)

    await interaction.response.send_message(
        "権限を付与するユーザーを選択してください",
        view=view,
        ephemeral=True,
    )


@client.tree.command(name="ck-pm", description="ユーザーの権限を確認します")
@is_admin_user()
async def check_permission_command(interaction: Interaction, user: User) -> None:
    """Check the permission of a Discord user.

    Parameters
    ----------
    interaction : Interaction
        The Discord interaction context.
    user : User
        The target Discord user to check permission for.

    Notes
    -----
    This function displays whether the user has 'beta' or 'blocked' permission.
    """
    is_valid, target_user_id = await _validate_guild_and_user(interaction, user)
    if not is_valid:
        return

    beta_user_ids = await permission_dao.fetch_user_ids_by_permission("beta")
    blocked_user_ids = await permission_dao.fetch_user_ids_by_permission("blocked")

    if target_user_id in beta_user_ids and target_user_id in blocked_user_ids:
        await interaction.response.send_message(
            f"ユーザー (ID: {target_user_id}) は beta 権限と blocked 権限を両方持っています",
            ephemeral=True,
        )
        return
    if target_user_id in beta_user_ids:
        await interaction.response.send_message(
            f"ユーザー (ID: {target_user_id}) は beta 権限を持っています",
            ephemeral=True,
        )
        return
    if target_user_id in blocked_user_ids:
        await interaction.response.send_message(
            f"ユーザー (ID: {target_user_id}) は blocked 権限を持っています",
            ephemeral=True,
        )
        return
    await interaction.response.send_message(
        f"ユーザー (ID: {target_user_id}) は権限を持っていません",
        ephemeral=True,
    )


@client.tree.command(name="rm-pm", description="ユーザーの権限を削除します")
@is_admin_user()
async def remove_permission_command(interaction: Interaction, user: User) -> None:
    """Remove permission for a Discord user.

    Parameters
    ----------
    interaction : Interaction
        The Discord interaction context.
    user : User
        The target Discord user to remove permission for.

    Notes
    -----
    This function removes 'beta' or 'blocked' permission for the specified user.
    """
    is_valid, target_user_id = await _validate_guild_and_user(interaction, user)
    if not is_valid:
        return

    options = [
        SelectOption(label="beta", value="beta"),
        SelectOption(label="blocked", value="blocked"),
    ]

    select = PermissionRemoveSelector(user_id=target_user_id, options=options)
    view = View()
    view.add_item(select)

    await interaction.response.send_message(
        "権限を削除するユーザーを選択してください",
        view=view,
        ephemeral=True,
    )
