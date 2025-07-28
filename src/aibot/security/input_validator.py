import re
from typing import ClassVar

from src.aibot.cli import logger


class InputValidator:
    """Input validation and prompt injection detection."""

    # 文字数制限
    MAX_CHAT_MESSAGE_LENGTH: ClassVar[int] = 2000
    MAX_SYSTEM_INSTRUCTION_LENGTH: ClassVar[int] = 1024
    MAX_CODE_INPUT_LENGTH: ClassVar[int] = 4000

    @staticmethod
    def validate_code_input(content: str) -> tuple[bool, str]:
        """Validate code input with security pattern detection.

        Parameters
        ----------
        content : str
            Code content to validate

        Returns
        -------
        tuple[bool, str]
            (validation result, error message)
        """
        # Check length
        if len(content) > InputValidator.MAX_CODE_INPUT_LENGTH:
            return False, f"コードが長すぎます(最大{InputValidator.MAX_CODE_INPUT_LENGTH}文字)"

        # Check empty string
        if not content.strip():
            return False, "コードが空です"

        # Check dangerous code patterns
        dangerous_code_patterns = [
            r"(?i)(rm\s+-rf|del\s+/|format\s+c:)",
            r"(?i)(curl|wget|http://|https://)",
            r"(?i)(exec|eval|system|subprocess)",
        ]

        for pattern in dangerous_code_patterns:
            if re.search(pattern, content):
                logger.warning("Potentially dangerous code pattern detected")
                return False, "潜在的に危険なコードパターンが検出されました"

        return True, ""
