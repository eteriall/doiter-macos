"""Background task synchronization for the macOS app."""

import threading
import time
from typing import Callable, Optional

from PyObjCTools import AppHelper

from .api_client import APIError, DoiterAPIClient


class SyncService:
    def __init__(self, task_manager, api_client: DoiterAPIClient, status_callback: Optional[Callable] = None):
        self.task_manager = task_manager
        self.api_client = api_client
        self.status_callback = status_callback
        self._timer = None
        self._stopped = True
        self.interval_seconds = 5
        self._sync_lock = threading.Lock()
        self._last_syncing_key = None
        self._last_terminal_key = None

    def start(self):
        if not self._stopped:
            return
        self._stopped = False
        self.sync_async()
        self._schedule_next()

    def stop(self):
        self._stopped = True
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def sync_async(self):
        if self._stopped:
            return
        thread = threading.Thread(target=self.sync_once, daemon=True)
        thread.start()

    def sync_once(self):
        if not self.api_client.token:
            return
        if not self._sync_lock.acquire(blocking=False):
            return
        try:
            pending_key = self._pending_key()
            if pending_key and pending_key != self._last_syncing_key:
                self._status("Syncing...")
                self._last_syncing_key = pending_key

            if pending_key:
                try:
                    self.task_manager.flush_pending_sync(self.api_client)
                except APIError as exc:
                    if self._handle_api_error(exc, pending_key):
                        return
                    return
                terminal_key = ("synced", pending_key)
                if terminal_key != self._last_terminal_key:
                    self._status("Synced")
                    self._last_terminal_key = terminal_key

            try:
                remote_tasks = self.api_client.list_tasks()
                AppHelper.callAfter(self.task_manager.apply_remote_tasks, remote_tasks)
            except APIError as exc:
                self._handle_api_error(exc, None)
        finally:
            self._sync_lock.release()

    def _schedule_next(self):
        if self._stopped:
            return
        self._timer = threading.Timer(self.interval_seconds, self._poll)
        self._timer.daemon = True
        self._timer.start()

    def _poll(self):
        self.sync_once()
        self._schedule_next()

    def _pending_key(self):
        items = self.task_manager.get_pending_sync_items()
        if not items:
            return None
        return tuple((item.get("id"), item.get("action"), item.get("task_id")) for item in items)

    def _status_once(self, message: str, key):
        if key == self._last_terminal_key:
            return
        self._last_terminal_key = key
        self._status(message)

    def _status(self, message: str):
        if self.status_callback:
            self.status_callback(message)

    def _handle_api_error(self, exc: APIError, pending_key):
        if exc.status in (401, 403):
            self.api_client.token_store.clear()
            self._status_once("Logged out", ("auth", exc.status))
            return True
        if pending_key:
            self._status_once(f"Sync error: {exc}", ("error", pending_key, exc.status, str(exc)))
        return False
