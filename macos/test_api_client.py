import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from doiter.src.api_client import APIError, ConfigStore, DoiterAPIClient
from doiter.src.sync_service import SyncService


class TokenStore:
    def __init__(self, token="token", refresh="refresh"):
        self.value = token
        self.refresh = refresh
        self.cleared = False

    def get(self):
        return self.value

    def get_refresh(self):
        return self.refresh

    def set(self, token):
        self.value = token

    def set_tokens(self, access, refresh):
        self.value = access
        self.refresh = refresh

    def clear(self):
        self.value = None
        self.refresh = None
        self.cleared = True


class APIClientTests(unittest.TestCase):
    def make_client(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        config = ConfigStore(Path(tmp.name) / "config.json")
        return DoiterAPIClient(config, TokenStore())

    def test_html_404_is_compact(self):
        client = self.make_client()
        html = b"<html><body>huge django debug page</body></html>"
        error = urllib.error.HTTPError(
            "http://127.0.0.1:8000/apis/auth/me/",
            404,
            "Not Found",
            {"Content-Type": "text/html"},
            io.BytesIO(html),
        )

        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(APIError) as raised:
                client.me()

        self.assertEqual(raised.exception.status, 404)
        self.assertIn("HTTP 404", str(raised.exception))
        self.assertNotIn("<html>", str(raised.exception))

    def test_json_error_uses_detail(self):
        client = self.make_client()
        error = urllib.error.HTTPError(
            "http://127.0.0.1:8000/api/auth/me/",
            401,
            "Unauthorized",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"detail":"Invalid token."}'),
        )

        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(APIError) as raised:
                client.me()

        self.assertEqual(str(raised.exception), "HTTP 401: Invalid token.")


class SyncServiceTests(unittest.TestCase):
    def test_fetch_failure_without_pending_changes_is_silent(self):
        class TaskManager:
            def get_pending_sync_items(self):
                return []

            def flush_pending_sync(self, api_client):
                raise AssertionError("no pending changes to flush")

            def apply_remote_tasks(self, tasks):
                raise AssertionError("should not apply when fetch fails")

        class Client:
            token = "token"
            token_store = TokenStore()

            def list_tasks(self):
                raise APIError("HTTP 404: bad url", 404)

        statuses = []
        service = SyncService(TaskManager(), Client(), statuses.append)
        service.sync_once()

        self.assertEqual(statuses, [])

    def test_pending_sync_failure_is_reported_once(self):
        class TaskManager:
            def get_pending_sync_items(self):
                return [{"id": 1, "action": "upsert", "task_id": "task"}]

            def flush_pending_sync(self, api_client):
                raise APIError("HTTP 404: bad url", 404)

        class Client:
            token = "token"
            token_store = TokenStore()

        statuses = []
        service = SyncService(TaskManager(), Client(), statuses.append)
        service.sync_once()
        service.sync_once()

        self.assertEqual(statuses, ["Syncing...", "Sync error: HTTP 404: bad url"])

    def test_pending_sync_success_reports_once(self):
        class TaskManager:
            def __init__(self):
                self.pending = [{"id": 1, "action": "upsert", "task_id": "task"}]

            def get_pending_sync_items(self):
                return self.pending

            def flush_pending_sync(self, api_client):
                self.pending = []

            def apply_remote_tasks(self, tasks):
                self.tasks = tasks

        class Client:
            token = "token"
            token_store = TokenStore()

            def list_tasks(self):
                return []

        statuses = []
        service = SyncService(TaskManager(), Client(), statuses.append)
        service.sync_once()
        service.sync_once()

        self.assertEqual(statuses, ["Syncing...", "Synced"])

    def test_auth_failure_clears_token(self):
        class TaskManager:
            def get_pending_sync_items(self):
                return []

            def flush_pending_sync(self, api_client):
                raise AssertionError("no pending changes to flush")

        token_store = TokenStore()

        class Client:
            token = "token"

            def list_tasks(self):
                raise APIError("HTTP 401: invalid", 401)

        Client.token_store = token_store
        statuses = []
        service = SyncService(TaskManager(), Client(), statuses.append)
        service.sync_once()

        self.assertTrue(token_store.cleared)
        self.assertEqual(statuses, ["Logged out"])


if __name__ == "__main__":
    unittest.main()
