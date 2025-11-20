import sqlite3
import uuid
import time
import json
import os
from typing import List, Dict, Optional, Any
from pathlib import Path

from .color_tags import COLOR_TAG_KEY_ORDER


class Database:
    """Manages SQLite database for tasks and undo/redo operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection and create tables if needed."""
        if db_path is None:
            app_support = Path.home() / "Library" / "Application Support" / "doiter"
            app_support.mkdir(parents=True, exist_ok=True)
            db_path = str(app_support / "doiter.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()

    def _init_database(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0,
                color_tags TEXT DEFAULT '[]'
            )
        """)
        self._ensure_color_tags_column(cursor)

        # Undo stack table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS undo_stack (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                task_snapshot TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)

        # Redo stack table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS redo_stack (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                task_snapshot TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)

        self.conn.commit()

    def _ensure_color_tags_column(self, cursor: sqlite3.Cursor):
        """Add the color_tags column to existing installs."""
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "color_tags" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN color_tags TEXT DEFAULT '[]'")
            self.conn.commit()

    def add_task(self, text: str, record_undo: bool = True) -> Dict:
        """Add a new task and optionally record in undo stack."""
        task_id = str(uuid.uuid4())
        now = time.time()

        # Get max position
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(position) as max_pos FROM tasks")
        result = cursor.fetchone()
        max_pos = result['max_pos'] if result['max_pos'] is not None else -1

        task = {
            'task_id': task_id,
            'text': text,
            'created_at': now,
            'updated_at': now,
            'completed': 0,
            'position': max_pos + 1,
            'color_tags': []
        }

        cursor.execute("""
            INSERT INTO tasks (task_id, text, created_at, updated_at, completed, position, color_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task['task_id'], task['text'], task['created_at'],
              task['updated_at'], task['completed'], task['position'],
              json.dumps(task['color_tags'])))

        self.conn.commit()

        if record_undo:
            self._record_undo('add', task)
            self._clear_redo_stack()

        return task

    def delete_task(self, task_id: str, record_undo: bool = True) -> Optional[Dict]:
        """Delete a task by ID and optionally record in undo stack."""
        cursor = self.conn.cursor()

        # Get task before deleting
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()

        if not row:
            return None

        task = self._row_to_task(row)

        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        self.conn.commit()

        if record_undo:
            self._record_undo('delete', task)
            self._clear_redo_stack()

        return task

    def update_task(self, task_id: str, new_text: str, record_undo: bool = True) -> Optional[Dict]:
        """Update a task's text and optionally record in undo stack."""
        cursor = self.conn.cursor()

        # Get task before updating
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()

        if not row:
            return None

        old_task = self._row_to_task(row)
        now = time.time()

        # Update the task
        cursor.execute("""
            UPDATE tasks
            SET text = ?, updated_at = ?
            WHERE task_id = ?
        """, (new_text, now, task_id))

        self.conn.commit()

        if record_undo:
            self._record_undo('update', old_task)
            self._clear_redo_stack()

        # Return updated task
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        updated_row = cursor.fetchone()
        return self._row_to_task(updated_row) if updated_row else None

    def get_all_tasks(self) -> List[Dict]:
        """Get all tasks ordered by position (newest first)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY position DESC")
        return [self._row_to_task(row) for row in cursor.fetchall()]

    def search_tasks(self, query: str) -> List[Dict]:
        """Search tasks with case-insensitive fuzzy matching."""
        if not query:
            return self.get_all_tasks()

        cursor = self.conn.cursor()
        # Simple fuzzy search: contains all characters in order
        like_pattern = '%' + '%'.join(query.lower()) + '%'
        cursor.execute("""
            SELECT * FROM tasks
            WHERE LOWER(text) LIKE ?
            ORDER BY position DESC
        """, (like_pattern,))

        return [self._row_to_task(row) for row in cursor.fetchall()]

    def _record_undo(self, action: str, task: Dict):
        """Record an action in the undo stack."""
        cursor = self.conn.cursor()
        task_snapshot = json.dumps(task)
        timestamp = time.time()

        cursor.execute("""
            INSERT INTO undo_stack (action, task_snapshot, timestamp)
            VALUES (?, ?, ?)
        """, (action, task_snapshot, timestamp))

        self.conn.commit()

    def _record_redo(self, action: str, task: Dict):
        """Record an action in the redo stack."""
        cursor = self.conn.cursor()
        task_snapshot = json.dumps(task)
        timestamp = time.time()

        cursor.execute("""
            INSERT INTO redo_stack (action, task_snapshot, timestamp)
            VALUES (?, ?, ?)
        """, (action, task_snapshot, timestamp))

        self.conn.commit()

    def _clear_redo_stack(self):
        """Clear the redo stack (called when new action is performed)."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM redo_stack")
        self.conn.commit()

    def undo(self) -> Optional[Dict]:
        """Undo the last operation and return action info."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM undo_stack
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if not row:
            return None

        action = row['action']
        task = json.loads(row['task_snapshot'])

        # Perform reverse operation
        if action == 'add':
            # Undo add = delete the task
            self.delete_task(task['task_id'], record_undo=False)
            self._record_redo('add', task)
        elif action == 'delete':
            # Undo delete = add the task back
            cursor.execute("""
                INSERT INTO tasks (task_id, text, created_at, updated_at, completed, position, color_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task['task_id'], task['text'], task['created_at'],
                  task['updated_at'], task['completed'], task['position'],
                  json.dumps(task.get('color_tags', []))))
            self.conn.commit()
            self._record_redo('delete', task)
        elif action == 'update':
            # Undo update = restore old text
            cursor.execute("""
                UPDATE tasks
                SET text = ?, color_tags = ?, updated_at = ?
                WHERE task_id = ?
            """, (task['text'], json.dumps(task.get('color_tags', [])),
                  task['updated_at'], task['task_id']))
            self.conn.commit()
            self._record_redo('update', task)

        # Remove from undo stack
        cursor.execute("DELETE FROM undo_stack WHERE id = ?", (row['id'],))
        self.conn.commit()

        return {
            'action': action,
            'task': task
        }

    def redo(self) -> Optional[Dict]:
        """Redo the last undone operation and return action info."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM redo_stack
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if not row:
            return None

        action = row['action']
        task = json.loads(row['task_snapshot'])

        # Perform the operation again
        if action == 'add':
            # Redo add = add the task back
            cursor.execute("""
                INSERT INTO tasks (task_id, text, created_at, updated_at, completed, position, color_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task['task_id'], task['text'], task['created_at'],
                  task['updated_at'], task['completed'], task['position'],
                  json.dumps(task.get('color_tags', []))))
            self.conn.commit()
            self._record_undo('add', task)
        elif action == 'delete':
            # Redo delete = delete the task
            self.delete_task(task['task_id'], record_undo=True)
        elif action == 'update':
            # Redo update = restore the text again
            cursor.execute("""
                UPDATE tasks
                SET text = ?, color_tags = ?, updated_at = ?
                WHERE task_id = ?
            """, (task['text'], json.dumps(task.get('color_tags', [])),
                  task['updated_at'], task['task_id']))
            self.conn.commit()
            self._record_undo('update', task)

        # Remove from redo stack
        cursor.execute("DELETE FROM redo_stack WHERE id = ?", (row['id'],))
        self.conn.commit()

        return {
            'action': action,
            'task': task
        }

    def close(self):
        """Close database connection."""
        self.conn.close()

    def toggle_color_tag(self, task_id: str, tag_key: str) -> Optional[Dict]:
        """Toggle a color tag on the specified task."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None

        original_task = self._row_to_task(row)
        tags = original_task.get('color_tags', [])
        if tag_key in tags:
            tags = [tag for tag in tags if tag != tag_key]
        else:
            tags = tags + [tag_key]
        tags = self._ordered_tags(tags)

        now = time.time()
        cursor.execute("""
            UPDATE tasks
            SET color_tags = ?, updated_at = ?
            WHERE task_id = ?
        """, (json.dumps(tags), now, task_id))
        self.conn.commit()

        self._record_undo('update', original_task)
        self._clear_redo_stack()

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        updated_row = cursor.fetchone()
        return self._row_to_task(updated_row) if updated_row else None

    def _ordered_tags(self, tags: List[str]) -> List[str]:
        """Order tags consistently based on the palette definition."""
        unique = []
        for tag in COLOR_TAG_KEY_ORDER:
            if tag in tags and tag not in unique:
                unique.append(tag)
        extras = []
        for tag in tags:
            if tag not in COLOR_TAG_KEY_ORDER and tag not in extras:
                extras.append(tag)
        return unique + extras

    def _row_to_task(self, row: Any) -> Dict:
        """Convert a sqlite row into a normalized task dictionary."""
        if row is None:
            return {}
        task = dict(row)
        raw_tags = task.get('color_tags')
        if isinstance(raw_tags, str):
            try:
                task['color_tags'] = json.loads(raw_tags) if raw_tags else []
            except json.JSONDecodeError:
                task['color_tags'] = []
        elif isinstance(raw_tags, list):
            task['color_tags'] = raw_tags
        else:
            task['color_tags'] = []
        return task
