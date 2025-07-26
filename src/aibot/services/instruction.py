from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.aibot.cli import logger
from src.aibot.infrastructure.db.dao.instruction import InstructionDAO
from src.aibot.services.system import SystemSettingsService

PREVIEW_LENGTH = 20  # 20 characters
MAX_INSTRUCTION_FILES = 100  # 100 files


class InstructionFileService:
    """Service class for managing instruction files."""

    def __init__(self) -> None:
        self.dao = InstructionDAO()
        self.instruction_dir = Path("resources/gen")
        self._ensure_instruction_directory()

    def _ensure_instruction_directory(self) -> None:
        """Ensure the generated instructions directory exists."""
        try:
            self.instruction_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create instruction directory: %s", e)

    def _get_instruction_files(self) -> list[Path]:
        """Get all instruction txt files, sorted by modification time (newest first).

        Returns
        -------
        list[Path]
            List of instruction file paths sorted by modification time.
        """
        if not self.instruction_dir.exists():
            return []

        txt_files = list(self.instruction_dir.glob("*.txt"))
        # Sort by modification time, newest first
        return sorted(txt_files, key=lambda f: f.stat().st_mtime, reverse=True)

    def _cleanup_old_files(self) -> None:
        """Remove old instruction files if count exceeds MAX_INSTRUCTION_FILES."""
        files = self._get_instruction_files()

        if len(files) > MAX_INSTRUCTION_FILES:
            # Remove oldest files
            files_to_remove = files[MAX_INSTRUCTION_FILES:]
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    logger.info("Removed old instruction file: %s", file_path.name)
                except OSError as e:
                    logger.error("Failed to remove file %s: %s", file_path.name, e)

    def save_instruction_to_file(self, content: str, filename: str | None = None) -> str | None:
        """Save instruction content to a txt file.

        Parameters
        ----------
        content : str
            The instruction content to save.
        filename : str | None, optional
            Specific filename to use. If None, generates a new timestamped filename.

        Returns
        -------
        str | None
            The filename of the created/updated file, or None on error.
        """
        self._ensure_instruction_directory()

        try:
            if filename is None:
                # Generate new filename with timestamp using DAO's timezone
                now = datetime.now(self.dao.TIMEZONE)
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}.txt"
                file_path = self.instruction_dir / filename

                # Ensure unique filename for new files
                counter = 1
                while file_path.exists():
                    filename = f"{timestamp}_{counter:03d}.txt"
                    file_path = self.instruction_dir / filename
                    counter += 1

                is_new_file = True
            else:
                # Use existing filename
                file_path = self.instruction_dir / filename
                is_new_file = not file_path.exists()

            # Write content to file
            self._write_instruction_to_file(file_path, content.strip())

            # Only cleanup old files when creating new files
            if is_new_file:
                self._cleanup_old_files()

            action = "Created" if is_new_file else "Updated"
            logger.info("%s instruction file: %s", action, filename)
            return filename

        except Exception as e:
            logger.error("Failed to save instruction file %s: %s", filename or "new", e)
            return None

    def _write_instruction_to_file(self, file_path: Path, content: str) -> None:
        """Write instruction content to a file."""
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    def load_instruction_from_file(self, filename: str) -> str | None:
        """Load instruction content from a file in the gen directory.

        Parameters
        ----------
        filename : str
            The filename to load (e.g., "20250725_170000.txt").

        Returns
        -------
        str | None
            The file content, or None if file doesn't exist or can't be read.
        """
        try:
            file_path = self.instruction_dir / filename
            if not file_path.exists():
                logger.warning("Instruction file not found: %s", filename)
                return None

            with file_path.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else None

        except Exception as e:
            logger.error("Failed to load instruction file %s: %s", filename, e)
            return None

    def list_available_instruction_files(self) -> list[str]:
        """List available instruction files with content previews.

        Returns
        -------
        list[str]
            List of content previews from generated instruction files.
        """
        previews = []
        txt_files = self._get_instruction_files()

        for file_path in txt_files:
            try:
                content = self.load_instruction_from_file(file_path.name)
                if content is None:
                    continue

                # Create preview (first PREVIEW_LENGTH characters)
                preview = content[:PREVIEW_LENGTH]
                if len(content) > PREVIEW_LENGTH:
                    preview += "..."

                previews.append(preview)

            except Exception as e:
                logger.error("Error processing file %s: %s", file_path.name, e)
                continue

        return previews

    def get_instruction_files_with_content(self) -> list[dict]:
        """Get instruction files with preview and full content.

        Returns
        -------
        list[dict]
            List of dictionaries containing filename, preview, and full content.
            Maximum 25 items (Discord SelectMenu limit).
            Sorted by modification time (newest first).
        """
        files_info = []
        txt_files = self._get_instruction_files()

        for file_path in txt_files[:25]:  # Discord limit: 25 options
            try:
                content = self.load_instruction_from_file(file_path.name)
                if content is None:
                    continue

                # Create preview (first PREVIEW_LENGTH characters)
                preview = content[:PREVIEW_LENGTH]
                if len(content) > PREVIEW_LENGTH:
                    preview += "..."

                files_info.append(
                    {
                        "filename": file_path.name,
                        "preview": preview,
                        "content": content,
                    },
                )

            except Exception as e:
                logger.error("Error processing file %s: %s", file_path.name, e)
                continue

        return files_info


class InstructionService:
    """Service class for managing system instructions."""

    def __init__(self) -> None:
        self.dao = InstructionDAO()
        self.file_service = InstructionFileService()
        self.system_service = SystemSettingsService()
        self.static_instruction_file = Path("resources/instructions.yml")

    def load_static_instruction(self, name: str) -> str | None:
        """Load static instructions from YAML file.

        Returns
        -------
        str | None
            Static instruction content, or None if file not found.
        """
        if not self.static_instruction_file.exists():
            logger.warning("Static instruction file not found: %s", self.static_instruction_file)
            return None

        try:
            with self.static_instruction_file.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f).get(name)
        except Exception as e:
            logger.error("Failed to load static instructions: %s", e)
            return None

    async def create_and_activate_instruction(
        self,
        content: str,
        created_by: int,
    ) -> dict[str, Any]:
        """Create a new instruction and activate it (deactivating any existing active instruction).

        Parameters
        ----------
        content : str
            The instruction content.
        created_by : int
            User ID who created the instruction.

        Returns
        -------
        dict[str, any]
            Result dictionary with success status and instruction_id if successful.
        """
        try:
            # Save to file first
            filename = self.file_service.save_instruction_to_file(content)
            if not filename:
                return {"success": False, "message": "ファイルの保存に失敗しました。"}

            # Save to database
            instruction_id = await self.dao.save_instruction(
                instruction=content,
                file_path=filename,
                created_by=created_by,
            )

            if instruction_id is None:
                return {"success": False, "message": "データベースへの保存に失敗しました。"}

            # Deactivate any existing active instruction (ensure single active instruction)
            await self.dao.deactivate_all_instructions()

            # Activate the new instruction
            success = await self.dao.activate_instruction(instruction_id)
            if not success:
                return {"success": False, "message": "指示のアクティブ化に失敗しました。"}

            logger.info(
                "Created and activated instruction with ID %d for user %d",
                instruction_id,
                created_by,
            )
            return {
                "success": True,
                "instruction_id": instruction_id,
                "message": "システム指示が正常に作成・設定されました。",
            }

        except Exception as e:
            logger.exception("Error creating and activating instruction: %s", e)
            return {"success": False, "message": "指示の作成中にエラーが発生しました。"}

    async def reset_to_default(self) -> dict[str, Any]:
        """Reset system instructions to default by deactivating all custom instructions.

        Returns
        -------
        dict[str, any]
            Result dictionary with success status and message.
        """
        try:
            # Deactivate all custom instructions (static instructions are not in DB)
            deactivated_count = await self.dao.deactivate_all_instructions()

            logger.info(
                "Reset to default instructions, deactivated %d custom instructions",
                deactivated_count,
            )
            return {
                "success": True,
                "message": "システム指示をデフォルトにリセットしました。",
            }

        except Exception as e:
            logger.exception("Error resetting to default: %s", e)
            return {"success": False, "message": "リセット中にエラーが発生しました。"}

    async def get_active_instruction(self, command_name: str) -> str | None:
        """Get the content of the currently active system instruction.

        Parameters
        ----------
        command_name : str
            The command name to get static instruction for

        Returns
        -------
        str | None
            The active instruction content, or None if no active instruction.
        """
        try:
            # Force mode: always return static instruction for the command
            if await self.system_service.is_force_mode_enabled():
                return self.load_static_instruction(command_name)

            # Normal mode: return custom instruction if available, otherwise static
            custom_instruction = await self.dao.fetch_active_instruction()
            return custom_instruction or self.load_static_instruction(command_name)
        except Exception as e:
            logger.exception("Error fetching active instruction: %s", e)
            return None

    def list_available_instruction_files(self) -> list[str]:
        """List available instruction files with content previews."""
        return self.file_service.list_available_instruction_files()

    def get_instruction_files_with_content(self) -> list[dict]:
        """Get instruction files with preview and full content."""
        return self.file_service.get_instruction_files_with_content()

    async def reactivate_instruction_by_file_path(self, file_path: str) -> dict[str, Any]:
        """Reactivate an existing instruction by its file path.

        Parameters
        ----------
        file_path : str
            The file path of the instruction to reactivate.

        Returns
        -------
        dict[str, Any]
            Result dictionary with success status and message.
        """
        try:
            # Get existing instruction record by file path
            instruction_record = await self.dao.get_instruction_by_file_path(file_path)

            if not instruction_record:
                return {
                    "success": False,
                    "message": "指定されたファイルに対応する指示が見つかりません。",
                }

            instruction_id = instruction_record["id"]

            # Deactivate all existing active instructions
            await self.dao.deactivate_all_instructions()

            # Activate the existing instruction
            success = await self.dao.activate_instruction(instruction_id)
            if not success:
                return {"success": False, "message": "指示の再活性化に失敗しました。"}

            logger.info(
                "Reactivated instruction with ID %d (file: %s)",
                instruction_id,
                file_path,
            )
            return {
                "success": True,
                "instruction_id": instruction_id,
                "message": "システム指示が正常に再設定されました。",
            }

        except Exception as e:
            logger.exception("Error reactivating instruction by file path: %s", e)
            return {"success": False, "message": "指示の再設定中にエラーが発生しました。"}

    async def enable_force_mode(self, user_id: int) -> dict[str, Any]:
        """Enable force system mode.

        Parameters
        ----------
        user_id : int
            The ID of the user enabling force mode.

        Returns
        -------
        dict[str, Any]
            Result dictionary with success status and message.
        """
        try:
            # Enable force mode in settings
            result = await self.system_service.set_force_mode(enabled=True, user_id=user_id)
            if not result["success"]:
                return result

            # Deactivate all custom instructions
            deactivated_count = await self.dao.deactivate_all_instructions()

            logger.info(
                "Force mode enabled by user %d, deactivated %d custom instructions",
                user_id,
                deactivated_count,
            )
            return {
                "success": True,
                "message": "システム指示をデフォルトに固定しました。",
            }

        except Exception as e:
            logger.exception("Error enabling force mode: %s", e)
            return {"success": False, "message": "設定の変更中にエラーが発生しました。"}

    async def disable_force_mode(self, user_id: int) -> dict[str, Any]:
        """Disable force system mode.

        Parameters
        ----------
        user_id : int
            The ID of the user disabling force mode.

        Returns
        -------
        dict[str, Any]
            Result dictionary with success status and message.
        """
        try:
            # Disable force mode in settings
            result = await self.system_service.set_force_mode(enabled=False, user_id=user_id)
            if not result["success"]:
                return result

            logger.info("Force mode disabled by user %d", user_id)
            return {
                "success": True,
                "message": "カスタム指示が有効になりました。",
            }

        except Exception as e:
            logger.exception("Error disabling force mode: %s", e)
            return {"success": False, "message": "設定の変更中にエラーが発生しました。"}
