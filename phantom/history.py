import sqlite3
from datetime import datetime
from pathlib import Path

MAX_ENTRIES = 50


class History:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else Path.home() / "phantom"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.data_dir / "history.db"
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def add(self, text: str, mode: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO history (text, mode, timestamp) VALUES (?, ?, ?)",
                (text, mode, now),
            )
            self._prune(conn)

    def _prune(self, conn: sqlite3.Connection):
        conn.execute(
            """DELETE FROM history WHERE id NOT IN (
                SELECT id FROM history ORDER BY id DESC LIMIT ?
            )""",
            (MAX_ENTRIES,),
        )

    def get_all(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, text, mode, timestamp FROM history ORDER BY id DESC"
            ).fetchall()
        return [
            {"id": r[0], "text": r[1], "mode": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def get_by_id(self, entry_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, text, mode, timestamp FROM history WHERE id = ?",
                (entry_id,),
            ).fetchone()
        if row is None:
            return None
        return {"id": row[0], "text": row[1], "mode": row[2], "timestamp": row[3]}
