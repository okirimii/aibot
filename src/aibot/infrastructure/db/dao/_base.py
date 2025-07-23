import os
import re
from typing import TYPE_CHECKING

import pytz

if TYPE_CHECKING:
    from pytz.tzinfo import BaseTzInfo


class DAOBase:
    DB_NAME: str = os.getenv("DB_NAME", "aibot.db")

    _tz: str = os.getenv("TIMEZONE", "Asia/Tokyo")
    TIMEZONE: "BaseTzInfo" = pytz.timezone(_tz)

    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """Only letters, numbers, and underscores are allowed."""
        pattern = r"^[A-Za-z0-9_]+$"
        return bool(re.match(pattern, table_name))
