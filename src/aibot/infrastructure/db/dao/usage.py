import datetime
from typing import cast

import aiosqlite

from ._base import DAOBase


class UsageDAO(DAOBase):
    """Data Access Object for managing usage data.

    Attributes
    ----------
    TABLE_NAME : str
        Name of the database table for usage data.
    """

    TABLE_NAME: str = "user_limits"

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
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL UNIQUE,
                daily_limit  INTEGER NOT NULL DEFAULT 10,
                last_updated TIMESTAMP NOT NULL
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def create_usage_tracking_table(self) -> None:
        """Create table for tracking API usage if it doesn't exist.

        Raises
        ------
        ValueError
            If the table name contains invalid characters
        """
        table_name = "daily_usage"
        if not self.validate_table_name(table_name):
            msg = "Invalid table name: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                usage_date  DATE NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, usage_date)
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def set_default_daily_limit(self, daily_limit: int) -> None:
        """Set or update the default daily usage limit for all regular users.

        Parameters
        ----------
        daily_limit : int
            Maximum number of API calls allowed per day.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)
        try:
            # Use a special user_id (0) to represent the default limit
            query = """
            INSERT INTO user_limits (user_id, daily_limit, last_updated)
            -- 0 is a special user_id that represents the default limit
            VALUES (0, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                daily_limit = ?,
                last_updated = ?
            """
            await conn.execute(
                query,
                (
                    daily_limit,
                    now,
                    daily_limit,
                    now,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def set_user_daily_limit(self, user_id: int, daily_limit: int) -> None:
        """Set or update daily usage limit for a user.

        Parameters
        ----------
        user_id : int
            ID of the user to set the limit for.
        daily_limit : int
            Maximum number of API calls allowed per day.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)
        try:
            query = """
            INSERT INTO user_limits (user_id, daily_limit, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                daily_limit = ?,
                last_updated = ?
            """
            await conn.execute(
                query,
                (
                    user_id,
                    daily_limit,
                    now,
                    daily_limit,
                    now,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def get_default_daily_limit(self) -> int:
        """Get the default daily usage limit for regular users.

        Returns
        -------
        int
            Default maximum number of API calls allowed per day.
            Returns 10 if no default limit is set.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT daily_limit FROM user_limits WHERE user_id = 0
            """
            cursor = await conn.execute(query)
            row = await cursor.fetchone()
            return cast("int", row[0] if row else 10)  # Default limit is 10
        finally:
            await conn.close()

    async def get_user_daily_limit(self, user_id: int) -> int:
        """Get daily usage limit for a user.

        Parameters
        ----------
        user_id : int
            ID of the user to get the limit for.

        Returns
        -------
        int
            Maximum number of API calls allowed per day.
            Returns 10 as default if no limit is set.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT daily_limit FROM user_limits WHERE user_id = ?
            """
            cursor = await conn.execute(query, (user_id,))
            row = await cursor.fetchone()

            if row:
                return cast("int", row[0])

            # If no user-specific limit is set, get the default limit
            return await self.get_default_daily_limit()
        finally:
            await conn.close()

    async def get_user_daily_usage(self, user_id: int) -> int:
        """Get the current day's usage count for a user.

        Parameters
        ----------
        user_id : int
            ID of the user to get usage for.

        Returns
        -------
        int
            Number of API calls used today. Returns 0 if no record found.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        today = datetime.datetime.now(super().TIMEZONE).date()
        try:
            query = """
            SELECT usage_count FROM daily_usage
            WHERE user_id = ? AND usage_date = ?
            """
            cursor = await conn.execute(query, (user_id, today))
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await conn.close()

    async def increment_usage_count(self, user_id: int) -> None:
        """Increment the usage count for a user on the current day.

        Parameters
        ----------
        user_id : int
            ID of the user to increment usage for.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        today = datetime.datetime.now(super().TIMEZONE).date()
        try:
            query = """
            INSERT INTO daily_usage (user_id, usage_date, usage_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET
                usage_count = usage_count + 1
            """
            await conn.execute(query, (user_id, today))
            await conn.commit()
        finally:
            await conn.close()

    async def reset_all_usage_counts(self) -> None:
        """Reset all usage counts by removing records from current day.

        This is meant to be called at midnight.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        yesterday = (datetime.datetime.now(super().TIMEZONE) - datetime.timedelta(days=1)).date()
        try:
            # Delete data older than yesterday
            query = """
            DELETE FROM daily_usage
            WHERE usage_date < ?
            """
            await conn.execute(query, (yesterday,))
            await conn.commit()
        finally:
            await conn.close()
