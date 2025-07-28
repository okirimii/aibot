import hashlib

from src.aibot.cli import logger
from src.aibot.infrastructure.api._openai import get_openai_moderation_result
from src.aibot.infrastructure.db.dao.moderation import ModerationDAO


class ModerationService:
    """Service for content moderation using OpenAI moderation API."""

    def __init__(self) -> None:
        """Initialize moderation service."""
        self.dao = ModerationDAO()

    async def moderate_content(
        self,
        content: str,
        user_id: int,
        request_type: str,
    ) -> bool:
        """Moderate content and log flagged results to database.

        Parameters
        ----------
        content : str
            Content to moderate.
        user_id : int
            ID of the user submitting the content.
        request_type : str
            Type of request ('chat', 'instruction', etc.).

        Returns
        -------
        bool
            True if content is flagged
        """
        try:
            # Call OpenAI moderation API through infrastructure layer
            moderation_result = await get_openai_moderation_result(content)

            is_flagged = moderation_result.get("results", [{}])[0].get("flagged", False)

            # Only log to database if content is flagged (violation detected)
            if is_flagged:
                logger.warning(
                    "Content flagged by moderation for user %d, type %s",
                    user_id,
                    request_type,
                )

                # Log violation to database
                success = await self.dao.log_moderation_result(
                    user_id=user_id,
                    request_type=request_type,
                    content=content,
                    moderation_result=moderation_result,
                )

                if not success:
                    logger.warning("Failed to log moderation violation to database")

            return is_flagged

        except Exception as e:
            logger.error("Error during content moderation: %s", e)
            # Return safe default (not flagged)
            return False

    async def check_user_violation_history(self, user_id: int, days: int = 7) -> int:
        """Check user's recent violation history.

        Parameters
        ----------
        user_id : int
            ID of the user to check.
        days : int, optional
            Number of days to look back, by default 7.

        Returns
        -------
        int
            Number of flagged content in the specified period.
        """
        return await self.dao.get_flagged_content_count(user_id, days)

    def _hash_content(self, content: str) -> str:
        """Generate hash for content deduplication.

        Parameters
        ----------
        content : str
            Content to hash.

        Returns
        -------
        str
            Hexadecimal hash string.
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]
