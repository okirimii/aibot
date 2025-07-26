import os

from discord import Interaction, SelectOption, TextStyle, ui

from src.aibot.cli import logger
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.permission import is_admin_user
from src.aibot.services.instruction import InstructionService

client = BotClient().get_instance()
instruction_service = InstructionService()

MAX_CHARS_PER_MESSAGE = int(os.getenv("MAX_CHARS_PER_MESSAGE", "1000"))


class SystemInstructionModal(ui.Modal, title="システム指示設定"):
    """Modal for setting system instructions."""

    def __init__(self) -> None:
        """Initialize the modal."""
        super().__init__()

    instruction_input: ui.TextInput = ui.TextInput(
        label="システム指示",
        placeholder="システム指示を入力してください",
        style=TextStyle.paragraph,
        required=True,
        max_length=1024,
    )

    async def on_submit(self, interaction: Interaction) -> None:
        """Handle modal submission."""
        try:
            user = interaction.user
            logger.info("User ( %s ) is setting system instruction", user)

            await interaction.response.defer(ephemeral=True)

            # Create and activate instruction through service layer
            result = await instruction_service.create_and_activate_instruction(
                content=self.instruction_input.value,
                created_by=user.id,
            )

            if result and result.get("success"):
                logger.info(
                    "System instruction created and activated (ID: %d) for user %s",
                    result["instruction_id"],
                    user,
                )
                await interaction.followup.send(
                    "システム指示が設定されました",
                    ephemeral=True,
                )
            else:
                logger.error("Failed to create system instruction for user %s", user)
                await interaction.followup.send(
                    "システム指示の設定に失敗しました",
                    ephemeral=True,
                )

        except Exception as err:
            msg = f"Error in system command modal: {err!s}"
            logger.exception(msg)
            await interaction.followup.send(
                "システム指示の設定中にエラーが発生しました",
                ephemeral=True,
            )


class SystemInstructionSelect(ui.Select):
    """Select menu for choosing system instructions."""

    def __init__(self, files_info: list[dict], action: str) -> None:
        """Initialize the select menu."""
        self.files_info = files_info
        self.action = action

        options = [
            SelectOption(
                label=file_info["preview"],
                value=file_info["filename"],
            )
            for file_info in files_info  # files_info is already limited to 25 items
        ]

        if not options:
            options.append(
                SelectOption(
                    label="利用可能な指示ファイルがありません",
                    value="none",
                ),
            )

        super().__init__(
            placeholder="システム指示を選択してください...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction) -> None:
        """Handle select menu callback."""
        try:
            if self.values[0] == "none":
                await interaction.response.send_message(
                    "利用可能な指示ファイルがありません。",
                    ephemeral=True,
                )
                return

            filename = self.values[0]
            file_info = next((f for f in self.files_info if f["filename"] == filename), None)

            if not file_info:
                await interaction.response.send_message(
                    "選択されたファイルが見つかりません。",
                    ephemeral=True,
                )
                return

            if self.action == "view":
                # Display the full content
                content = file_info["content"]
                if len(content) > MAX_CHARS_PER_MESSAGE:
                    content = content[:MAX_CHARS_PER_MESSAGE] + "\n..."

                await interaction.response.send_message(
                    f"**{filename}** の内容:\n```\n{content}\n```",
                    ephemeral=True,
                )

            elif self.action == "activate":
                await interaction.response.defer(ephemeral=True)

                # Activate the selected instruction as a new instruction
                result = await instruction_service.create_and_activate_instruction(
                    content=file_info["content"],
                    created_by=interaction.user.id,
                )

                if result and result.get("success"):
                    await interaction.followup.send(
                        f"**{filename}** をシステム指示として設定しました。",
                        ephemeral=True,
                    )
                else:
                    error_message = (
                        result.get("message", "指示の設定に失敗しました。")
                        if result
                        else "指示の設定に失敗しました。"
                    )
                    await interaction.followup.send(
                        f"エラー: {error_message}",
                        ephemeral=True,
                    )

        except Exception as e:
            logger.exception("Error in system instruction select callback: %s", e)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "エラーが発生しました。",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "エラーが発生しました。",
                    ephemeral=True,
                )


async def _handle_instruction_files_interaction(interaction: Interaction, action: str) -> None:
    """Handle instruction files interaction for list and activate commands.

    Parameters
    ----------
    interaction : Interaction
        The Discord interaction.
    action : str
        The action to perform ("view" for list, "activate" for activate).
    """
    try:
        user = interaction.user
        action_name = "viewing" if action == "view" else "activating"
        logger.info("User ( %s ) is %s system instruction files", user, action_name)

        # Get instruction files with content
        files_info = instruction_service.get_instruction_files_with_content()

        if not files_info:
            await interaction.response.send_message(
                "利用可能なシステム指示ファイルがありません。",
                ephemeral=True,
            )
            return

        # Create view with select menu
        view = SystemInstructionView(files_info, action)

        if action == "view":
            message = f"**利用可能なシステム指示一覧 （{len(files_info)}件）**"  # noqa: RUF001
        else:
            message = f"**システム指示の設定 （{len(files_info)}件）**"  # noqa: RUF001

        await interaction.response.send_message(
            message,
            view=view,
            ephemeral=True,
        )

    except Exception as err:
        msg = f"Error in {action} instruction files interaction: {err!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "エラーが発生しました。システム管理者にお問い合わせください。",
            ephemeral=True,
        )


class SystemInstructionView(ui.View):
    """View for system instruction selection."""

    def __init__(self, files_info: list[dict], action: str) -> None:
        """Initialize the view."""
        super().__init__(timeout=300)
        self.add_item(SystemInstructionSelect(files_info, action))


@client.tree.command(name="create", description="システム指示を設定します")
async def create_command(interaction: Interaction) -> None:
    """Create system instruction for chat commands."""
    try:
        user = interaction.user
        logger.info("User ( %s ) is opening system instruction modal", user)

        # Check if force mode is enabled and user is not admin
        if await instruction_service.system_service.is_force_mode_enabled():
            admin_user_ids = [int(i) for i in os.getenv("ADMIN_USER_IDS", "").split(",")]
            if user.id not in admin_user_ids:
                await interaction.response.send_message(
                    "管理者により指示変更が制限されています。デフォルト指示が適用されます。",
                    ephemeral=True,
                )
                return

        modal = SystemInstructionModal()
        await interaction.response.send_modal(modal)

    except Exception as err:
        msg = f"Error in create command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "システム指示の設定中にエラーが発生しました",
            ephemeral=True,
        )


@client.tree.command(
    name="list",
    description="利用可能なシステム指示を一覧表示します",
)
async def list_command(interaction: Interaction) -> None:
    """List available system instructions."""
    await _handle_instruction_files_interaction(interaction, "view")


@client.tree.command(name="activate", description="過去のシステム指示を再設定します")
async def activate_command(interaction: Interaction) -> None:
    """Activate a previous system instruction."""
    try:
        # Check if force mode is enabled and user is not admin
        if await instruction_service.system_service.is_force_mode_enabled():
            admin_user_ids = [int(i) for i in os.getenv("ADMIN_USER_IDS", "").split(",")]
            if interaction.user.id not in admin_user_ids:
                await interaction.response.send_message(
                    "管理者により指示変更が制限されています。デフォルト指示が適用されます。",
                    ephemeral=True,
                )
                return

        await _handle_instruction_files_interaction(interaction, "activate")
    except Exception as err:
        msg = f"Error in activate command: {err!s}"
        logger.exception(msg)
        await interaction.response.send_message(
            "システム指示の再設定中にエラーが発生しました",
            ephemeral=True,
        )


@client.tree.command(
    name="lock",
    description="システム指示をデフォルトに固定し、ユーザーのカスタム設定を無効化します",
)
@is_admin_user()
async def lock_command(interaction: Interaction) -> None:
    """Force default system instructions and disable user customization."""
    try:
        user = interaction.user
        logger.info("Admin ( %s ) is enabling force system mode", user)

        await interaction.response.defer(ephemeral=True)

        # Enable force system mode
        result = await instruction_service.enable_force_mode(user.id)

        if result.get("success"):
            await interaction.followup.send(
                f"{result['message']}",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"エラー: {result['message']}",
                ephemeral=True,
            )

    except Exception as err:
        msg = f"Error in lock command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "設定の変更中にエラーが発生しました。",
            ephemeral=True,
        )


@client.tree.command(
    name="unlock",
    description="デフォルト固定を解除し、ユーザーのカスタム設定を有効化します",
)
@is_admin_user()
async def unlock_command(interaction: Interaction) -> None:
    """Unlock system commands and re-enable user customization."""
    try:
        user = interaction.user
        logger.info("Admin ( %s ) is disabling force system mode", user)

        await interaction.response.defer(ephemeral=True)

        # Disable force system mode
        result = await instruction_service.disable_force_mode(user.id)

        if result.get("success"):
            await interaction.followup.send(
                f"{result['message']}",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"エラー: {result['message']}",
                ephemeral=True,
            )

    except Exception as err:
        msg = f"Error in unlock command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "設定の変更中にエラーが発生しました。",
            ephemeral=True,
        )


@client.tree.command(name="reset", description="システム指示をデフォルトにリセットします")
async def reset_command(interaction: Interaction) -> None:
    """Reset system instruction to default instructions."""
    try:
        user = interaction.user
        logger.info("User ( %s ) is resetting system instruction to default", user)

        await interaction.response.defer(ephemeral=True)

        # Check if force mode is enabled and user is not admin
        if await instruction_service.system_service.is_force_mode_enabled():
            admin_user_ids = [int(i) for i in os.getenv("ADMIN_USER_IDS", "").split(",")]
            if user.id not in admin_user_ids:
                await interaction.followup.send(
                    "管理者により指示変更が制限されています。デフォルト指示が適用されます。",
                    ephemeral=True,
                )
                return

        # Reset to default through service layer
        result = await instruction_service.reset_to_default()

        await interaction.followup.send(
            f"{result['message']}",
            ephemeral=True,
        )

    except Exception as err:
        msg = f"Error in reset command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "システム指示のリセット中にエラーが発生しました。",
            ephemeral=True,
        )
