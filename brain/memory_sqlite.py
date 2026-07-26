"""SQLite-backed memory with FTS5 full-text search.

Inspired by JARVIS memory.py - persistent memory with automatic
context injection for LLM prompts.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "memory.db"


class SQLiteMemory:
    """Persistent memory store with FTS5 search."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'fact',
                    metadata TEXT DEFAULT '{}',
                    importance INTEGER DEFAULT 1,
                    created_at REAL DEFAULT 0
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    due_date TEXT DEFAULT '',
                    project TEXT DEFAULT '',
                    created_at REAL DEFAULT 0,
                    completed_at REAL DEFAULT 0
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL DEFAULT 0
                )
            """
            )
            # FTS5 for memories
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(content, type, content=memories, content_rowid=id)
            """
            )
            # Triggers to keep FTS in sync
            for trigger_sql in [
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, type)
                    VALUES (new.id, new.content, new.type);
                END
                """,
                """
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    DELETE FROM memories_fts WHERE rowid = old.id;
                END
                """,
                """
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    DELETE FROM memories_fts WHERE rowid = old.id;
                    INSERT INTO memories_fts(rowid, content, type)
                    VALUES (new.id, new.content, new.type);
                END
                """,
            ]:
                conn.execute(trigger_sql)
            conn.commit()

    # ---- Memories ----

    def remember(
        self,
        content: str,
        mem_type: str = "fact",
        metadata: Optional[Dict] = None,
        importance: int = 1,
    ) -> int:
        """Store a memory. Returns memory ID."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO memories (content, type, metadata, importance, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (content, mem_type, json.dumps(metadata or {}), importance, time.time()),
            )
            conn.commit()
            return cur.lastrowid

    def search_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """Search memories using FTS5."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT m.id, m.content, m.type, m.importance, m.created_at
                FROM memories_fts fts
                JOIN memories m ON fts.rowid = m.id
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def recall(self, query: str, limit: int = 5) -> List[str]:
        """Simple recall - returns content strings."""
        return [m["content"] for m in self.search_memories(query, limit)]

    def get_important(self, limit: int = 10) -> List[Dict]:
        """Get high-importance memories."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories WHERE importance >= 3 "
                "ORDER BY importance DESC, created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ---- Tasks ----

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: str = "",
        project: str = "",
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, description, priority, due_date, project, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title, description, priority, due_date, project, time.time()),
            )
            conn.commit()
            return cur.lastrowid

    def complete_task(self, task_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status='completed', completed_at=? WHERE id=?",
                (time.time(), task_id),
            )
            conn.commit()
            return True

    def get_open_tasks(self, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status != 'completed' "
                "ORDER BY priority DESC, due_date ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_tasks(self, query: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE title LIKE ? OR description LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [dict(r) for r in rows]

    # ---- Notes ----

    def create_note(self, topic: str, content: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO notes (topic, content, created_at) VALUES (?, ?, ?)",
                (topic, content, time.time()),
            )
            conn.commit()
            return cur.lastrowid

    def search_notes(self, query: str) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM notes WHERE topic LIKE ? OR content LIKE ?",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [dict(r) for r in rows]

    # ---- Context Building ----

    def build_context(self) -> str:
        """Build a context string for LLM prompt injection."""
        lines = []

        # Important memories
        important = self.get_important(5)
        if important:
            lines.append("KEY FACTS:")
            for m in important:
                lines.append(f"- {m['content'][:100]}")

        # Open tasks
        tasks = self.get_open_tasks(5)
        if tasks:
            lines.append("\nOPEN TASKS:")
            for t in tasks:
                due = f" (due: {t['due_date']})" if t.get("due_date") else ""
                lines.append(f"- [{t['priority']}] {t['title']}{due}")

        return "\n".join(lines) if lines else ""
