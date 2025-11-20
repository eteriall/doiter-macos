from typing import List, Dict, Optional, Callable
from .database import Database


class TaskManager:
    """Manages task operations and provides interface for UI."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize task manager with database."""
        self.db = Database(db_path)
        self.current_filter = ""
        self.observers: List[Callable] = []

    def add_observer(self, callback: Callable):
        """Add an observer that will be notified on task changes."""
        self.observers.append(callback)

    def notify_observers(self):
        """Notify all observers of changes."""
        for observer in self.observers:
            observer()

    def add_task(self, text: str) -> Optional[Dict]:
        """Add a new task."""
        if not text.strip():
            return None

        task = self.db.add_task(text.strip())
        self.notify_observers()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        result = self.db.delete_task(task_id)
        if result:
            self.notify_observers()
            return True
        return False

    def update_task(self, task_id: str, new_text: str) -> bool:
        """Update a task's text."""
        if not new_text.strip():
            return False

        result = self.db.update_task(task_id, new_text.strip())
        if result:
            self.notify_observers()
            return True
        return False

    def get_tasks(self, filter_text: str = "") -> List[Dict]:
        """Get tasks filtered by search text."""
        self.current_filter = filter_text
        if filter_text:
            return self.db.search_tasks(filter_text)
        return self.db.get_all_tasks()

    def undo(self) -> bool:
        """Undo the last operation."""
        success = self.db.undo()
        if success:
            self.notify_observers()
        return success

    def redo(self) -> bool:
        """Redo the last undone operation."""
        success = self.db.redo()
        if success:
            self.notify_observers()
        return success

    def get_task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.db.get_all_tasks())

    def close(self):
        """Close database connection."""
        self.db.close()
