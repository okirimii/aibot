import datetime

import aiosqlite

from ._base import DAOBase


class SystemDAO(DAOBase):
    """Data Access Object for managing system settings.

    Attributes
    ----------
    TABLE_NAME : str
        Name of the database table for system settings.
    """

    TABLE_NAME: str = "system"

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
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def get_setting(self, key: str) -> str | None:
        """Get a system setting value by key.

        Parameters
        ----------
        key : str
            The setting key to retrieve.

        Returns
        -------
        str | None
            The setting value, or None if the key doesn't exist.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT value
            FROM system
            WHERE key = ?;
            """
            cursor = await conn.execute(query, (key,))
            row = await cursor.fetchone()
            return row[0] if row else None
        finally:
            await conn.close()

    async def set_setting(self, key: str, value: str, user_id: int) -> bool:
        """Set a system setting value.

        Parameters
        ----------
        key : str
            The setting key.
        value : str
            The setting value.
        user_id : int
            The ID of the user updating the setting.

        Returns
        -------
        bool
            True if the setting was successfully updated, False otherwise.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        updated_at = datetime.datetime.now(super().TIMEZONE)
        try:
            query = """
            INSERT OR REPLACE INTO system (key, value, updated_at, updated_by)
            VALUES (?, ?, ?, ?);
            """
            cursor = await conn.execute(
                query,
                (
                    key,
                    value,
                    updated_at,
                    user_id,
                ),
            )
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    async def delete_setting(self, key: str) -> bool:
        """Delete a system setting by key.

        Parameters
        ----------
        key : str
            The setting key to delete.

        Returns
        -------
        bool
            True if the setting was successfully deleted, False otherwise.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            DELETE FROM system
            WHERE key = ?;
            """
            cursor = await conn.execute(query, (key,))
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()
