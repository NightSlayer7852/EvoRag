import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.config import COLD_STORAGE_DB_PATH
from app.schemas.chunk_metadata_schema import ChunkMetadata


class ArchiveService:
    """
    Cold-tier storage service managing archived/obsolete vector chunks in SQLite DB.
    Enables low-cost historical preservation and metrics query support for frontend UI.
    """

    def __init__(self, db_path: str = COLD_STORAGE_DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """
        Creates the 'archived_chunks' table in SQLite if it does not already exist.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archived_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT,
                    status TEXT,
                    version INTEGER,
                    created_at TEXT,
                    updated_at TEXT,
                    supersedes TEXT,
                    superseded_by TEXT,
                    conflicts_with TEXT,
                    archived_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def archive_chunk(self, chunk: ChunkMetadata) -> None:
        """
        Stores a ChunkMetadata object in cold storage SQLite DB.

        Args:
            chunk (ChunkMetadata): Vector chunk metadata to archive.
        """
        self.init_db()
        archived_at_iso = datetime.now(timezone.utc).isoformat()
        conflicts_str = json.dumps(chunk.conflicts_with) if chunk.conflicts_with else None

        created_str = chunk.created_at.isoformat() if isinstance(chunk.created_at, datetime) else str(chunk.created_at)
        updated_str = chunk.updated_at.isoformat() if isinstance(chunk.updated_at, datetime) else str(chunk.updated_at)
        status_str = chunk.status.value if hasattr(chunk.status, "value") else str(chunk.status)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO archived_chunks (
                    chunk_id, content, source, status, version,
                    created_at, updated_at, supersedes, superseded_by,
                    conflicts_with, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.chunk_id,
                chunk.content,
                chunk.source,
                status_str,
                chunk.version,
                created_str,
                updated_str,
                chunk.supersedes,
                chunk.superseded_by,
                conflicts_str,
                archived_at_iso
            ))
            conn.commit()

    def get_archived_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single archived chunk record by chunk_id.

        Args:
            chunk_id (str): UUID string of archived chunk.

        Returns:
            Optional[Dict[str, Any]]: Dictionary representation of archived chunk or None.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM archived_chunks WHERE chunk_id = ?", (chunk_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("conflicts_with"):
                try:
                    res["conflicts_with"] = json.loads(res["conflicts_with"])
                except Exception:
                    pass
            return res

    def list_archived(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Returns recent archived records for frontend DB status monitoring.

        Args:
            limit (int): Maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: List of recent archived chunk dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM archived_chunks ORDER BY archived_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                if item.get("conflicts_with"):
                    try:
                        item["conflicts_with"] = json.loads(item["conflicts_with"])
                    except Exception:
                        pass
                results.append(item)
            return results
