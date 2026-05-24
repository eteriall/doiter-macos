from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthTests(APITestCase):
    def test_register_login_me_logout(self):
        response = self.client.post("/api/auth/register/", {"username": "alex", "password": "strong-pass-123"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        response = self.client.post("/api/auth/login/", {"username": "alex", "password": "strong-pass-123"}, format="json")
        self.assertEqual(response.status_code, 200)
        access = response.data["access"]
        refresh = response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(self.client.get("/api/auth/me/").data["username"], "alex")
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json").status_code, 204)


class TaskAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="strong-pass-123")
        self.other = User.objects.create_user(username="other", password="strong-pass-123")
        self.refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh.access_token}")

    def task_payload(self, task_id="11111111-1111-1111-1111-111111111111", text="task", position=1):
        return {
            "task_id": task_id,
            "text": text,
            "created_at": 1770000000.0,
            "updated_at": 1770000000.0,
            "completed": False,
            "completed_at": None,
            "position": position,
            "color_tags": ["red"],
            "deadline_at": 1770003600.0,
            "planned_start_at": None,
            "planned_end_at": None,
            "timer_started_at": None,
            "timer_ends_at": None,
            "timer_duration_seconds": None,
            "timer_paused_remaining_seconds": None,
            "client_updated_at": 1770000000.0,
        }

    def test_task_round_trip_and_user_isolation(self):
        response = self.client.post("/api/tasks/", self.task_payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["text"], "task")
        self.assertEqual(response.data["color_tags"], ["red"])

        response = self.client.patch(
            "/api/tasks/11111111-1111-1111-1111-111111111111/",
            {"text": "edited"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "edited")

        other_token = RefreshToken.for_user(self.other)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token.access_token}")
        response = self.client.get("/api/tasks/11111111-1111-1111-1111-111111111111/")
        self.assertEqual(response.status_code, 404)

    def test_duplicate_post_for_same_user_updates_task(self):
        response = self.client.post("/api/tasks/", self.task_payload(text="first"), format="json")
        self.assertEqual(response.status_code, 201)

        payload = self.task_payload(text="second", position=7)
        response = self.client.post("/api/tasks/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "second")
        self.assertEqual(response.data["position"], 7)
        self.assertEqual(len(self.client.get("/api/tasks/").data), 1)

    def test_patch_completed_and_reopen_task(self):
        task_id = "11111111-1111-1111-1111-111111111111"
        response = self.client.post("/api/tasks/", self.task_payload(task_id=task_id), format="json")
        self.assertEqual(response.status_code, 201)

        response = self.client.patch(
            f"/api/tasks/{task_id}/",
            {"completed": True, "updated_at": 1770000100.0, "client_updated_at": 1770000100.0},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["completed"])
        self.assertEqual(response.data["completed_at"], 1770000100.0)

        response = self.client.patch(
            f"/api/tasks/{task_id}/",
            {"completed": False, "updated_at": 1770000200.0, "client_updated_at": 1770000200.0},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["completed"])
        self.assertIsNone(response.data["completed_at"])

    def test_completed_at_can_be_client_provided(self):
        payload = self.task_payload("11111111-1111-1111-1111-111111111111")
        payload["completed"] = True
        payload["completed_at"] = 1770000050.0
        response = self.client.post("/api/tasks/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["completed"])
        self.assertEqual(response.data["completed_at"], 1770000050.0)

    def test_uppercase_uuid_detail_url_updates_task(self):
        task_id = "5b7e08b3-1027-4209-be14-663608279ce4"
        response = self.client.post("/api/tasks/", self.task_payload(task_id=task_id), format="json")
        self.assertEqual(response.status_code, 201)

        payload = self.task_payload(task_id=task_id, text="updated")
        response = self.client.put(f"/api/tasks/{task_id.upper()}/", payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["task_id"], task_id)
        self.assertEqual(response.data["text"], "updated")

    def test_reorder_and_schema(self):
        first = self.task_payload("11111111-1111-1111-1111-111111111111", "first", 1)
        second = self.task_payload("22222222-2222-2222-2222-222222222222", "second", 2)
        self.client.post("/api/tasks/", first, format="json")
        self.client.post("/api/tasks/", second, format="json")

        response = self.client.post(
            "/api/tasks/reorder/",
            {"tasks": [
                {"task_id": first["task_id"], "position": 10},
                {"task_id": second["task_id"], "position": 9},
            ]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["position"], 10)

        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
