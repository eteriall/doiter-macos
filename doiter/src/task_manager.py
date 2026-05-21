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

    def toggle_color_tag(self, task_id: str, tag_key: str) -> Optional[Dict]:
        """Toggle a color tag on a task and return the updated task."""
        result = self.db.toggle_color_tag(task_id, tag_key)
        if result:
            self.notify_observers()
            return result
        return None

    def set_deadline(self, task_id: str, deadline_at: Optional[float]) -> Optional[Dict]:
        """Set or clear the task deadline."""
        result = self.db.update_schedule(task_id, deadline_at=deadline_at)
        if result:
            self.notify_observers()
        return result

    def set_planned_slot(
        self,
        task_id: str,
        planned_start_at: Optional[float],
        planned_end_at: Optional[float],
    ) -> Optional[Dict]:
        """Set or clear the planned completion slot."""
        result = self.db.update_schedule(
            task_id,
            planned_start_at=planned_start_at,
            planned_end_at=planned_end_at,
        )
        if result:
            self.notify_observers()
        return result

    def start_timer(self, task_id: str, started_at: float, duration_seconds: int) -> Optional[Dict]:
        """Start a countdown timer on a task."""
        result = self.db.update_schedule(
            task_id,
            timer_started_at=started_at,
            timer_ends_at=started_at + duration_seconds,
            timer_duration_seconds=duration_seconds,
            timer_paused_remaining_seconds=None,
        )
        if result:
            self.notify_observers()
        return result

    def pause_timer(self, task_id: str, remaining_seconds: int) -> Optional[Dict]:
        """Pause a running countdown timer on a task."""
        result = self.db.update_schedule(
            task_id,
            timer_started_at=None,
            timer_ends_at=None,
            timer_paused_remaining_seconds=max(0, int(remaining_seconds)),
        )
        if result:
            self.notify_observers()
        return result

    def resume_timer(self, task_id: str, started_at: float, remaining_seconds: int) -> Optional[Dict]:
        """Resume a paused countdown timer on a task."""
        result = self.db.update_schedule(
            task_id,
            timer_started_at=started_at,
            timer_ends_at=started_at + remaining_seconds,
            timer_paused_remaining_seconds=None,
        )
        if result:
            self.notify_observers()
        return result

    def cancel_timer(self, task_id: str) -> Optional[Dict]:
        """Cancel the countdown timer on a task."""
        result = self.db.update_schedule(
            task_id,
            timer_started_at=None,
            timer_ends_at=None,
            timer_duration_seconds=None,
            timer_paused_remaining_seconds=None,
        )
        if result:
            self.notify_observers()
        return result

    def swap_task_positions(self, task_id: str, other_task_id: str) -> Optional[Dict]:
        """Swap two task positions and return the moved task."""
        result = self.db.swap_task_positions(task_id, other_task_id)
        if result:
            self.notify_observers()
        return result

    def get_tasks(self, filter_text: str = "", sort_by: str = "position") -> List[Dict]:
        """Get tasks filtered by search text and sorted by specified mode."""
        self.current_filter = filter_text
        if filter_text:
            return self.db.search_tasks(filter_text, sort_by)
        return self.db.get_all_tasks(sort_by)

    def undo(self) -> Optional[Dict]:
        """Undo the last operation."""
        result = self.db.undo()
        if result:
            self.notify_observers()
            return result
        return None

    def redo(self) -> Optional[Dict]:
        """Redo the last undone operation."""
        result = self.db.redo()
        if result:
            self.notify_observers()
            return result
        return None

    def get_task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.db.get_all_tasks())

    def close(self):
        """Close database connection."""
        self.db.close()
