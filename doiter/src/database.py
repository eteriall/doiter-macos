import sqlite3
import uuid
import time
import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from .color_tags import COLOR_TAG_KEY_ORDER

SCHEDULING_COLUMNS = [
    "deadline_at",
    "planned_start_at",
    "planned_end_at",
    "timer_started_at",
    "timer_ends_at",
    "timer_duration_seconds",
    "timer_paused_remaining_seconds",
]


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
                color_tags TEXT DEFAULT '[]',
                deadline_at REAL,
                planned_start_at REAL,
                planned_end_at REAL,
                timer_started_at REAL,
                timer_ends_at REAL,
                timer_duration_seconds INTEGER,
                timer_paused_remaining_seconds INTEGER
            )
        """)
        self._ensure_task_columns(cursor)

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

    def _ensure_task_columns(self, cursor: sqlite3.Cursor):
        """Add newly introduced task columns to existing installs."""
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "color_tags" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN color_tags TEXT DEFAULT '[]'")
        for column in SCHEDULING_COLUMNS:
            if column not in columns:
                column_type = "INTEGER" if column == "timer_duration_seconds" else "REAL"
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column} {column_type}")
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
            'color_tags': [],
            'deadline_at': None,
            'planned_start_at': None,
            'planned_end_at': None,
            'timer_started_at': None,
            'timer_ends_at': None,
            'timer_duration_seconds': None,
            'timer_paused_remaining_seconds': None
        }

        cursor.execute("""
            INSERT INTO tasks (
                task_id, text, created_at, updated_at, completed, position, color_tags,
                deadline_at, planned_start_at, planned_end_at,
                timer_started_at, timer_ends_at, timer_duration_seconds,
                timer_paused_remaining_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task['task_id'], task['text'], task['created_at'],
              task['updated_at'], task['completed'], task['position'],
              json.dumps(task['color_tags']), task['deadline_at'],
              task['planned_start_at'], task['planned_end_at'],
              task['timer_started_at'], task['timer_ends_at'],
              task['timer_duration_seconds'], task['timer_paused_remaining_seconds']))

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
            updated_task = self.get_task(task_id)
            self._record_undo('update', {'before': old_task, 'after': updated_task})
            self._clear_redo_stack()

        # Return updated task
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        updated_row = cursor.fetchone()
        return self._row_to_task(updated_row) if updated_row else None

    def get_all_tasks(self, sort_by: str = "position") -> List[Dict]:
        """Get all tasks ordered by position (newest first) or by tags."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY position DESC")
        tasks = [self._row_to_task(row) for row in cursor.fetchall()]

        if sort_by == "tags":
            return self._sort_by_tags(tasks)
        return tasks

    def search_tasks(self, query: str, sort_by: str = "position") -> List[Dict]:
        """Search tasks with case-insensitive fuzzy matching."""
        if not query:
            return self.get_all_tasks(sort_by)

        cursor = self.conn.cursor()
        # Simple fuzzy search: contains all characters in order
        like_pattern = '%' + '%'.join(query.lower()) + '%'
        cursor.execute("""
            SELECT * FROM tasks
            WHERE LOWER(text) LIKE ?
            ORDER BY position DESC
        """, (like_pattern,))

        tasks = [self._row_to_task(row) for row in cursor.fetchall()]
        if sort_by == "tags":
            return self._sort_by_tags(tasks)
        return tasks

    def _sort_by_tags(self, tasks: List[Dict]) -> List[Dict]:
        """Sort tasks by their most important color tag (1-7), then by position."""
        # Color tag priority: red=1, orange=2, yellow=3, green=4, blue=5, purple=6, gray=7
        tag_priority = {
            'red': 1,
            'orange': 2,
            'yellow': 3,
            'green': 4,
            'blue': 5,
            'purple': 6,
            'gray': 7
        }

        def get_min_tag_priority(task: Dict) -> int:
            """Get the minimum (most important) tag priority for a task."""
            tags = task.get('color_tags', [])
            if not tags:
                return 999  # Tasks without tags go to the end

            priorities = [tag_priority.get(tag, 999) for tag in tags]
            return min(priorities)

        # Sort by tag priority (ascending), then by position (descending for newest first)
        return sorted(tasks, key=lambda t: (get_min_tag_priority(t), -t.get('position', 0)))

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

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Return a single task by id."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        return self._row_to_task(row) if row else None

    def _insert_task_snapshot(self, task: Dict):
        """Insert a task snapshot exactly as stored in undo history."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (
                task_id, text, created_at, updated_at, completed, position, color_tags,
                deadline_at, planned_start_at, planned_end_at,
                timer_started_at, timer_ends_at, timer_duration_seconds,
                timer_paused_remaining_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task['task_id'], task['text'], task['created_at'],
              task['updated_at'], task.get('completed', 0), task.get('position', 0),
              json.dumps(task.get('color_tags', [])), task.get('deadline_at'),
              task.get('planned_start_at'), task.get('planned_end_at'),
              task.get('timer_started_at'), task.get('timer_ends_at'),
              task.get('timer_duration_seconds'), task.get('timer_paused_remaining_seconds')))
        self.conn.commit()

    def _restore_task_snapshot(self, task: Dict):
        """Restore every mutable field from a task snapshot."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET text = ?, updated_at = ?, completed = ?, position = ?, color_tags = ?,
                deadline_at = ?, planned_start_at = ?, planned_end_at = ?,
                timer_started_at = ?, timer_ends_at = ?, timer_duration_seconds = ?,
                timer_paused_remaining_seconds = ?
            WHERE task_id = ?
        """, (task['text'], task['updated_at'], task.get('completed', 0),
              task.get('position', 0), json.dumps(task.get('color_tags', [])),
              task.get('deadline_at'), task.get('planned_start_at'),
              task.get('planned_end_at'), task.get('timer_started_at'),
              task.get('timer_ends_at'), task.get('timer_duration_seconds'),
              task.get('timer_paused_remaining_seconds'), task['task_id']))
        self.conn.commit()

    def _snapshot_before(self, payload: Dict) -> Dict:
        return payload.get('before', payload)

    def _snapshot_after(self, payload: Dict) -> Dict:
        return payload.get('after', payload)

    def _restore_reorder_snapshot(self, tasks: List[Dict]):
        """Restore positions for multiple tasks from a reorder snapshot."""
        cursor = self.conn.cursor()
        now = time.time()
        for task in tasks:
            cursor.execute("""
                UPDATE tasks
                SET position = ?, updated_at = ?
                WHERE task_id = ?
            """, (task.get('position', 0), now, task['task_id']))
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
        payload = json.loads(row['task_snapshot'])
        task = self._snapshot_before(payload)

        # Perform reverse operation
        if action == 'add':
            # Undo add = delete the task
            self.delete_task(task['task_id'], record_undo=False)
            self._record_redo('add', task)
        elif action == 'delete':
            # Undo delete = add the task back
            self._insert_task_snapshot(task)
            self._record_redo('delete', task)
        elif action == 'update':
            self._restore_task_snapshot(task)
            self._record_redo('update', payload)
        elif action == 'reorder':
            before_tasks = payload.get('before', [])
            self._restore_reorder_snapshot(before_tasks)
            self._record_redo('reorder', payload)

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
        payload = json.loads(row['task_snapshot'])
        task = self._snapshot_after(payload) if action == 'update' else self._snapshot_before(payload)

        # Perform the operation again
        if action == 'add':
            # Redo add = add the task back
            self._insert_task_snapshot(task)
            self._record_undo('add', task)
        elif action == 'delete':
            # Redo delete = delete the task
            self.delete_task(task['task_id'], record_undo=False)
            self._record_undo('delete', task)
        elif action == 'update':
            self._restore_task_snapshot(task)
            self._record_undo('update', payload)
        elif action == 'reorder':
            after_tasks = payload.get('after', [])
            self._restore_reorder_snapshot(after_tasks)
            self._record_undo('reorder', payload)

        # Remove from redo stack
        cursor.execute("DELETE FROM redo_stack WHERE id = ?", (row['id'],))
        self.conn.commit()

        return {
            'action': action,
            'task': task
        }

    def swap_task_positions(self, task_id: str, other_task_id: str) -> Optional[Dict]:
        """Swap two task positions and record a reorder undo entry."""
        first = self.get_task(task_id)
        second = self.get_task(other_task_id)
        if not first or not second:
            return None

        before = [first, second]
        now = time.time()
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET position = ?, updated_at = ?
            WHERE task_id = ?
        """, (second.get('position', 0), now, first['task_id']))
        cursor.execute("""
            UPDATE tasks
            SET position = ?, updated_at = ?
            WHERE task_id = ?
        """, (first.get('position', 0), now, second['task_id']))
        self.conn.commit()

        after = [self.get_task(task_id), self.get_task(other_task_id)]
        self._record_undo('reorder', {'before': before, 'after': after})
        self._clear_redo_stack()
        return self.get_task(task_id)

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

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        updated_row = cursor.fetchone()
        updated_task = self._row_to_task(updated_row) if updated_row else None
        if updated_task:
            self._record_undo('update', {'before': original_task, 'after': updated_task})
            self._clear_redo_stack()
        return updated_task

    def update_schedule(self, task_id: str, **fields) -> Optional[Dict]:
        """Update scheduling fields for a task and record undo."""
        allowed = set(SCHEDULING_COLUMNS)
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return self.get_task(task_id)

        original_task = self.get_task(task_id)
        if not original_task:
            return None

        updates['updated_at'] = time.time()
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [task_id]
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE task_id = ?", values)
        self.conn.commit()

        updated_task = self.get_task(task_id)
        self._record_undo('update', {'before': original_task, 'after': updated_task})
        self._clear_redo_stack()
        return updated_task

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
        for column in SCHEDULING_COLUMNS:
            task.setdefault(column, None)
        return task
