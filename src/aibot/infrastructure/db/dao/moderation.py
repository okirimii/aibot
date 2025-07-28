import datetime
import json
from typing import Any

import aiosqlite

from src.aibot.cli import logger

from ._base import DAOBase


class ModerationDAO(DAOBase):
    """Data Access Object for managing moderation logs.

    Attributes
    ----------
    TABLE_NAME : str
        Name of the database table for moderation logs.
    """

    TABLE_NAME: str = "moderation_logs"

    async def create_table(self) -> None:
        """Create table if it doesn't exist.

        Raises
        ------
        ValueError
            If the table name contains invalid characters.
        """
        if not self.validate_table_name(self.TABLE_NAME):
            msg = "Invalid tablename: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                request_type TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                flagged BOOLEAN NOT NULL,

                -- Category flags
                sexual BOOLEAN DEFAULT FALSE,
                sexual_minors BOOLEAN DEFAULT FALSE,
                harassment BOOLEAN DEFAULT FALSE,
                harassment_threatening BOOLEAN DEFAULT FALSE,
                violence BOOLEAN DEFAULT FALSE,
                violence_graphic BOOLEAN DEFAULT FALSE,
                hate BOOLEAN DEFAULT FALSE,
                hate_threatening BOOLEAN DEFAULT FALSE,
                self_harm BOOLEAN DEFAULT FALSE,
                self_harm_intent BOOLEAN DEFAULT FALSE,
                self_harm_instructions BOOLEAN DEFAULT FALSE,
                illicit BOOLEAN DEFAULT FALSE,
                illicit_violent BOOLEAN DEFAULT FALSE,

                -- Key scores for analysis
                violence_score REAL DEFAULT 0.0,
                harassment_score REAL DEFAULT 0.0,
                sexual_score REAL DEFAULT 0.0,

                -- Complete JSON response for detailed analysis
                raw_response TEXT NOT NULL,

                created_at TIMESTAMP NOT NULL,

                UNIQUE(user_id, content_hash, request_type)
            );
            """
            await conn.execute(query)

            # Create indexes for performance
            indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_flagged "
                f"ON {self.TABLE_NAME}(flagged, created_at)",
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_user "
                f"ON {self.TABLE_NAME}(user_id, created_at)",
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_violence "
                f"ON {self.TABLE_NAME}(violence_score DESC)",
                f"CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_type "
                f"ON {self.TABLE_NAME}(request_type, flagged)",
            ]

            for index_query in indexes:
                await conn.execute(index_query)

            await conn.commit()
        finally:
            await conn.close()

    async def log_moderation_result(
        self,
        user_id: int,
        request_type: str,
        content: str,
        moderation_result: dict[str, Any],
    ) -> bool:
        """Log moderation result to database.

        Parameters
        ----------
        user_id : int
            ID of the user whose content was moderated.
        request_type : str
            Type of request ('chat', 'instruction', etc.).
        content : str
            The content that was moderated.
        moderation_result : dict[str, Any]
            Full moderation result from OpenAI API.

        Returns
        -------
        bool
            True if successfully logged, False otherwise.
        """
        try:
            # Generate content hash for deduplication
            content_hash = str(hash(content))[:16]

            # Extract data from moderation result
            result = moderation_result.get("results", [{}])[0]
            categories = result.get("categories", {})
            category_scores = result.get("category_scores", {})

            conn = await aiosqlite.connect(super().DB_NAME)
            now = datetime.datetime.now(super().TIMEZONE)

            try:
                query = """
                INSERT OR IGNORE INTO moderation_logs (
                    user_id, request_type, content_hash, flagged,
                    sexual, sexual_minors, harassment, harassment_threatening,
                    violence, violence_graphic, hate, hate_threatening,
                    self_harm, self_harm_intent, self_harm_instructions,
                    illicit, illicit_violent,
                    violence_score, harassment_score, sexual_score,
                    raw_response, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                values = (
                    user_id,
                    request_type,
                    content_hash,
                    result.get("flagged", False),
                    # Category flags
                    categories.get("sexual", False),
                    categories.get("sexual/minors", False),
                    categories.get("harassment", False),
                    categories.get("harassment/threatening", False),
                    categories.get("violence", False),
                    categories.get("violence/graphic", False),
                    categories.get("hate", False),
                    categories.get("hate/threatening", False),
                    categories.get("self-harm", False),
                    categories.get("self-harm/intent", False),
                    categories.get("self-harm/instructions", False),
                    categories.get("illicit", False),
                    categories.get("illicit/violent", False),
                    # Key scores
                    float(category_scores.get("violence", 0.0)),
                    float(category_scores.get("harassment", 0.0)),
                    float(category_scores.get("sexual", 0.0)),
                    # Raw response
                    json.dumps(moderation_result),
                    now,
                )

                cursor = await conn.execute(query, values)
                await conn.commit()

                if cursor.rowcount > 0:
                    logger.info(
                        "Moderation result logged for user %d, type %s, flagged: %s",
                        user_id,
                        request_type,
                        result.get("flagged", False),
                    )
                    return True

                # If no row was inserted (duplicate), still return True
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error("Failed to log moderation result: %s", e)
            return False

    async def get_flagged_content_count(self, user_id: int) -> int:
        """Get count of flagged content for a user in recent days.

        Parameters
        ----------
        user_id : int
            ID of the user.

        Returns
        -------
        int
            Count of flagged content.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT COUNT(*)
            FROM  moderation_logs
            WHERE user_id = ? AND flagged = TRUE
              AND created_at > datetime('now', '-7 days')
            """
            cursor = await conn.execute(query, (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await conn.close()

    async def get_recent_violations(self, limit: int = 50) -> list[dict]:
        """Get recent moderation violations for admin review.

        Parameters
        ----------
        limit : int, optional
            Maximum number of records to return, by default 50.

        Returns
        -------
        list[dict]
            List of recent violations with key information.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT user_id, request_type, flagged, violence_score,
                   harassment_score, sexual_score, created_at
            FROM   moderation_logs
            WHERE  flagged = TRUE
            ORDER BY created_at DESC
            LIMIT ?
            """
            cursor = await conn.execute(query, (limit,))
            rows = await cursor.fetchall()

            return [
                {
                    "user_id": row[0],
                    "request_type": row[1],
                    "flagged": bool(row[2]),
                    "violence_score": row[3],
                    "harassment_score": row[4],
                    "sexual_score": row[5],
                    "created_at": row[6],
                }
                for row in rows
            ]
        finally:
            await conn.close()

    async def cleanup_old_logs(self) -> int:
        """Clean up old moderation logs.

        Returns
        -------
        int
            Number of records deleted.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            DELETE FROM moderation_logs
            WHERE created_at < datetime('now', '-30 days')
            """
            cursor = await conn.execute(query)
            await conn.commit()
            deleted_count = cursor.rowcount or 0

            if deleted_count > 0:
                logger.info("Cleaned up %d old moderation log records", deleted_count)

            return deleted_count
        finally:
            await conn.close()
