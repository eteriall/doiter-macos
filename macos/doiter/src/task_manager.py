import threading
from typing import List, Dict, Optional, Callable
from .database import Database

REORDER_COMMIT_DELAY_SECONDS = 1.0


class TaskManager:
    """Manages task operations and provides interface for UI."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize task manager with database."""
        self.db = Database(db_path)
        self.current_filter = ""
        self.observers: List[Callable] = []
        self.sync_trigger: Optional[Callable] = None
        self._applying_remote = False
        self._reorder_lock = threading.Lock()
        self._reorder_timer: Optional[threading.Timer] = None
        self._pending_reorder_before: Optional[List[Dict]] = None
        self._repair_positions_if_needed()

    def add_observer(self, callback: Callable):
        """Add an observer that will be notified on task changes."""
        self.observers.append(callback)

    def notify_observers(self):
        """Notify all observers of changes."""
        for observer in self.observers:
            observer()

    def set_sync_trigger(self, callback: Callable):
        """Set a callback invoked after local mutations should sync."""
        self.sync_trigger = callback
        if self.db.has_pending_sync() and self.sync_trigger:
            self.sync_trigger()

    def _queue_sync(self, action: str, task: Optional[Dict]):
        if self._applying_remote or not task:
            return
        self.db.queue_sync(action, task)
        if self.sync_trigger:
            self.sync_trigger()

    def add_task(self, text: str) -> Optional[Dict]:
        """Add a new task."""
        if not text.strip():
            return None

        task = self.db.add_task(text.strip())
        self._queue_sync("upsert", task)
        self.notify_observers()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        result = self.db.delete_task(task_id)
        if result:
            self._queue_sync("delete", result)
            self.notify_observers()
            return True
        return False

    def update_task(self, task_id: str, new_text: str) -> bool:
        """Update a task's text."""
        if not new_text.strip():
            return False

        result = self.db.update_task(task_id, new_text.strip())
        if result:
            self._queue_sync("upsert", result)
            self.notify_observers()
            return True
        return False

    def mark_completed(self, task_id: str) -> Optional[Dict]:
        """Mark a task completed."""
        result = self.db.set_task_completed(task_id, True)
        if result:
            self._queue_sync("upsert", result)
            self.notify_observers()
        return result

    def reopen_task(self, task_id: str) -> Optional[Dict]:
        """Mark a completed task active again."""
        result = self.db.set_task_completed(task_id, False)
        if result:
            self._queue_sync("upsert", result)
            self.notify_observers()
        return result

    def toggle_color_tag(self, task_id: str, tag_key: str) -> Optional[Dict]:
        """Toggle a color tag on a task and return the updated task."""
        result = self.db.toggle_color_tag(task_id, tag_key)
        if result:
            self._queue_sync("upsert", result)
            self.notify_observers()
            return result
        return None

    def set_deadline(self, task_id: str, deadline_at: Optional[float]) -> Optional[Dict]:
        """Set or clear the task deadline."""
        result = self.db.update_schedule(task_id, deadline_at=deadline_at)
        if result:
            self._queue_sync("upsert", result)
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
            self._queue_sync("upsert", result)
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
            self._queue_sync("upsert", result)
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
            self._queue_sync("upsert", result)
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
            self._queue_sync("upsert", result)
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
            self._queue_sync("upsert", result)
            self.notify_observers()
        return result

    def swap_task_positions(self, task_id: str, other_task_id: str) -> Optional[Dict]:
        """Swap two task positions and debounce the reorder commit."""
        before = self.db.get_all_tasks()
        result = self.db.swap_task_positions(task_id, other_task_id, record_undo=False)
        if result:
            self._schedule_reorder_commit(before)
            self.notify_observers()
        return result

    def _repair_positions_if_needed(self):
        repaired_tasks = self.db.normalize_positions_if_needed()
        if not repaired_tasks:
            return
        for task in repaired_tasks:
            self.db.queue_sync("upsert", task)

    def reorder_visible_tasks(self, reordered_task_ids: List[str]) -> Optional[Dict]:
        """Apply visible task order and debounce the reorder sync/undo commit."""
        before = self.db.get_all_tasks()
        result = self.db.reorder_visible_tasks(reordered_task_ids, record_undo=False)
        if result:
            self._schedule_reorder_commit(before)
            self.notify_observers()
        return result

    def _schedule_reorder_commit(self, before: List[Dict]):
        with self._reorder_lock:
            if self._pending_reorder_before is None:
                self._pending_reorder_before = before
            if self._reorder_timer:
                self._reorder_timer.cancel()
            self._reorder_timer = threading.Timer(
                REORDER_COMMIT_DELAY_SECONDS,
                self.commit_pending_reorder,
            )
            self._reorder_timer.daemon = True
            self._reorder_timer.start()

    def commit_pending_reorder(self):
        """Commit a debounced reorder after the user stops moving tasks."""
        with self._reorder_lock:
            before = self._pending_reorder_before
            self._pending_reorder_before = None
            self._reorder_timer = None

        if not before:
            return

        after = self.db.get_all_tasks()
        if not self._position_snapshot_changed(before, after):
            return

        self.db.record_reorder(before, after)
        for task in after:
            self._queue_sync("upsert", task)

    def _flush_pending_reorder(self):
        with self._reorder_lock:
            timer = self._reorder_timer
            self._reorder_timer = None
        if timer:
            timer.cancel()
        self.commit_pending_reorder()

    def _has_pending_reorder(self) -> bool:
        with self._reorder_lock:
            return self._pending_reorder_before is not None

    def _position_snapshot_changed(self, before: List[Dict], after: List[Dict]) -> bool:
        before_positions = {
            task["task_id"]: task.get("position", 0)
            for task in before
        }
        after_positions = {
            task["task_id"]: task.get("position", 0)
            for task in after
        }
        return before_positions != after_positions

    def get_tasks(self, filter_text: str = "", sort_by: str = "position") -> List[Dict]:
        """Get tasks filtered by search text and sorted by specified mode."""
        self.current_filter = filter_text
        if filter_text:
            return self.db.search_tasks(filter_text, sort_by)
        return self.db.get_all_tasks(sort_by)

    def undo(self) -> Optional[Dict]:
        """Undo the last operation."""
        self._flush_pending_reorder()
        result = self.db.undo()
        if result:
            self._queue_sync_after_history_action(result, is_redo=False)
            self.notify_observers()
            return result
        return None

    def redo(self) -> Optional[Dict]:
        """Redo the last undone operation."""
        self._flush_pending_reorder()
        result = self.db.redo()
        if result:
            self._queue_sync_after_history_action(result, is_redo=True)
            self.notify_observers()
            return result
        return None

    def _queue_sync_after_history_action(self, result: Dict, is_redo: bool):
        action = result.get("action")
        task = result.get("task")
        if action == "add":
            self._queue_sync("upsert" if is_redo else "delete", task)
        elif action == "delete":
            self._queue_sync("delete" if is_redo else "upsert", task)
        elif action == "update":
            current = self.db.get_task(task.get("task_id")) if task else None
            self._queue_sync("upsert", current or task)
        elif action == "reorder":
            for local_task in self.db.get_all_tasks():
                self._queue_sync("upsert", local_task)

    def flush_pending_sync(self, api_client):
        """Push queued local mutations to the backend."""
        self._flush_pending_reorder()
        for item in self.db.get_pending_sync():
            action = item["action"]
            task_id = item["task_id"]
            if action == "delete":
                try:
                    api_client.delete_task(task_id)
                except Exception as exc:
                    if getattr(exc, "status", None) != 404:
                        raise
                self.db.mark_sync_done(item["id"])
                continue

            payload = item["payload"]
            try:
                api_client.update_task(task_id, payload)
            except Exception as exc:
                if getattr(exc, "status", None) == 404:
                    api_client.create_task(payload)
                else:
                    raise
            self.db.mark_task_synced(task_id)
            self.db.mark_sync_done(item["id"])

    def get_pending_sync_items(self) -> List[Dict]:
        return self.db.get_pending_sync()

    def pending_sync_count(self) -> int:
        return self.db.pending_sync_count()

    def apply_remote_tasks(self, tasks: List[Dict]):
        """Apply server state without creating new local sync queue entries."""
        if self._has_pending_reorder():
            return
        self._applying_remote = True
        try:
            self.db.apply_remote_tasks(tasks)
        finally:
            self._applying_remote = False
        self.notify_observers()

    def import_local_tasks_to_sync_queue(self):
        self.db.import_local_tasks_to_sync_queue()
        if self.sync_trigger:
            self.sync_trigger()

    def get_task_count(self) -> int:
        """Get total number of tasks."""
        return len(self.db.get_all_tasks())

    def close(self):
        """Close database connection."""
        self._flush_pending_reorder()
        self.db.close()
