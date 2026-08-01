import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime

class Database:
    """Manages SQLite database operations for tracking product status and prices."""

    def __init__(self, db_path: str = "tracker.db") -> None:
        """Initializes the database connection and creates tables if they don't exist.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Creates tables if they don't already exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS product_states (
                    url TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    site TEXT NOT NULL,
                    last_status TEXT,
                    last_price REAL,
                    last_notified_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.commit()

    def get_product_state(self, url: str) -> Optional[Dict[str, Any]]:
        """Retrieves the last stored state for a product URL.

        Args:
            url: The product URL.

        Returns:
            A dictionary containing product state if found, else None.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM product_states WHERE url = ?", (url,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_product_state(
        self,
        url: str,
        name: str,
        site: str,
        status: str,
        price: Optional[float],
        last_notified_at: Optional[str] = None
    ) -> None:
        """Updates or inserts the product state in the database.

        Args:
            url: The product URL.
            name: The product name.
            site: The site name (amazon or flipkart).
            status: The current availability status.
            price: The current price (optional).
            last_notified_at: ISO formatted timestamp of the last sent notification.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Fetch existing last_notified_at if not provided, to avoid overwriting it with None
            if last_notified_at is None:
                cursor.execute("SELECT last_notified_at FROM product_states WHERE url = ?", (url,))
                row = cursor.fetchone()
                if row:
                    last_notified_at = row[0]

            cursor.execute(
                """
                INSERT INTO product_states (url, name, site, last_status, last_price, last_notified_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    name=excluded.name,
                    site=excluded.site,
                    last_status=excluded.last_status,
                    last_price=excluded.last_price,
                    last_notified_at=excluded.last_notified_at
                """,
                (url, name, site, status, price, last_notified_at)
            )
            conn.commit()

    def get_metadata(self, key: str, default_value: Optional[str] = None) -> Optional[str]:
        """Retrieves a metadata value by key.

        Args:
            key: Metadata key.
            default_value: Value to return if key is not found.

        Returns:
            The stored value or the default value.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return default_value

    def set_metadata(self, key: str, value: str) -> None:
        """Saves a metadata key-value pair.

        Args:
            key: Metadata key.
            value: Metadata value to store.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO app_metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, value)
            )
            conn.commit()

