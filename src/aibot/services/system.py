from typing import Any

from src.aibot.cli import logger
from src.aibot.infrastructure.db.dao.system import SystemDAO


class SystemSettingsService:
    """Service class for managing system settings."""

    def __init__(self) -> None:
        self.dao = SystemDAO()

    async def is_force_mode_enabled(self) -> bool:
        """Check if force system mode is enabled.

        Returns
        -------
        bool
            True if force mode is enabled, False otherwise.
        """
        try:
            value = await self.dao.get_setting("force_system_mode")
            return value == "true"
        except Exception as e:
            logger.exception("Error checking force mode status: %s", e)
            return False

    async def set_force_mode(self, *, enabled: bool, user_id: int) -> dict[str, Any]:
        """Set force system mode state.

        Parameters
        ----------
        enabled : bool
            True to enable force mode, False to disable.
        user_id : int
            The ID of the user changing the setting.

        Returns
        -------
        dict[str, Any]
            Result dictionary with success status and message.
        """
        try:
            value = "true" if enabled else "false"
            success = await self.dao.set_setting("force_system_mode", value, user_id)

            if not success:
                return {"success": False, "message": "設定の更新に失敗しました。"}

            mode_status = "Enabled" if enabled else "Disabled"
            logger.info("Force mode %s by user %d", mode_status, user_id)

            if enabled:
                message = "システム指示をデフォルトに固定しました。"
            else:
                message = "カスタム指示が有効になりました。"

            return {
                "success": True,
                "message": message,
            }

        except Exception as e:
            action = "有効化" if enabled else "無効化"
            logger.exception("Error %s force mode: %s", action, e)
            return {
                "success": False,
                "message": "設定の変更中にエラーが発生しました。",
            }

    async def get_setting(self, key: str) -> str | None:
        """Get a system setting value.

        Parameters
        ----------
        key : str
            The setting key.

        Returns
        -------
        str | None
            The setting value, or None if not found.
        """
        try:
            return await self.dao.get_setting(key)
        except Exception as e:
            logger.exception("Error getting setting %s: %s", key, e)
            return None

    async def set_setting(self, key: str, value: str, user_id: int) -> bool:
        """Set a system setting value.

        Parameters
        ----------
        key : str
            The setting key.
        value : str
            The setting value.
        user_id : int
            The ID of the user setting the value.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """
        try:
            return await self.dao.set_setting(key, value, user_id)
        except Exception as e:
            logger.exception("Error setting %s=%s: %s", key, value, e)
            return False

    async def delete_setting(self, key: str) -> bool:
        """Delete a system setting.

        Parameters
        ----------
        key : str
            The setting key to delete.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """
        try:
            return await self.dao.delete_setting(key)
        except Exception as e:
            logger.exception("Error deleting setting %s: %s", key, e)
            return False
