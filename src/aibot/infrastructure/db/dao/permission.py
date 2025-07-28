import datetime

import aiosqlite

from ._base import DAOBase


class PermissionDAO(DAOBase):
    """Data Access Object for managing permissions.

    Attributes
    ----------
    TABLE_NAME : str
        Name of the database table for permissions.
    """

    TABLE_NAME: str = "permissions"

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
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                permission  TEXT NOT NULL,
                granted_at  DATE NOT NULL,
                disabled_at DATE DEFAULT NULL
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def grant(self, user_id: int, permission: str) -> None:
        """Insert a new permission record for a user.

        Parameters
        ----------
        user_id : int
            ID of the user receiving permissions.
        permission : str
            Type of permission being granted.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        date = datetime.datetime.now(super().TIMEZONE).date()
        try:
            query = """
            INSERT INTO permissions (user_id, permission, granted_at)
            VALUES (?, ?, ?);
            """
            await conn.execute(query, (user_id, permission, date))
            await conn.commit()
        finally:
            await conn.close()

    async def fetch_user_ids_by_permission(self, permission: str) -> list[int]:
        """Fetch IDs of users who have a specific active permission.

        Parameters
        ----------
        permission : str
            Type of permission to filter by.

        Returns
        -------
        list[int]
            List of user IDs with the specified active permission.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT user_id FROM permissions WHERE permission = ? AND disabled_at IS NULL;
            """
            cursor = await conn.execute(query, (permission,))
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            await conn.close()

    async def disable(self, user_id: int, permission: str) -> None:
        """Disable a specific permission for a user.

        Parameters
        ----------
        user_id : int
            ID of the user whose permission is being disabled.
        permission : str
            Type of permission to disable.
        """
        conn = await aiosqlite.connect(super().DB_NAME)
        date = datetime.datetime.now(super().TIMEZONE).date()
        try:
            query = """
            UPDATE permissions SET disabled_at = ? WHERE user_id = ? AND permission = ?;
            """
            await conn.execute(query, (date, user_id, permission))
            await conn.commit()
        finally:
            await conn.close()
