# doiter API

The backend exposes a DRF JSON API under `/api/` and an OpenAPI schema at `/api/schema/`.
Interactive schema docs are available at `/api/docs/` when the Django server is running.
The committed schema snapshot is `backend/docs/openapi.yaml`.

## Development

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Default local API base URL for the macOS app:

```text
http://127.0.0.1:8000/api
```

## Authentication

All task endpoints require:

```http
Authorization: Bearer <access-token>
```

Access tokens are short-lived. Use the refresh token to get a new access token without logging in again.
Refresh tokens last 365 days, are stored per device/app, and survive server restarts as long as the database and `DOITER_SECRET_KEY` stay unchanged.

### Register

`POST /api/auth/register/`

```json
{"username": "alex", "password": "strong-pass-123"}
```

Response `201`:

```json
{"access": "...", "refresh": "...", "user": {"id": 1, "username": "alex"}}
```

### Login

`POST /api/auth/login/`

```json
{"username": "alex", "password": "strong-pass-123"}
```

Response `200`:

```json
{"access": "...", "refresh": "...", "user": {"id": 1, "username": "alex"}}
```

### Refresh

`POST /api/auth/refresh/`

```json
{"refresh": "..."}
```

Response `200`:

```json
{"access": "...", "refresh": "..."}
```

### Current User

`GET /api/auth/me/`

### Logout

`POST /api/auth/logout/`

```json
{"refresh": "..."}
```

Logout blacklists only the submitted refresh token, so other devices remain logged in.

## Tasks

Task timestamps are local/UTC epoch seconds in API payloads so the macOS SQLite cache and server model can round trip without format conversion in callers.

### List

`GET /api/tasks/`

### Create

`POST /api/tasks/`

```json
{
  "task_id": "11111111-1111-1111-1111-111111111111",
  "text": "Write release notes",
  "created_at": 1770000000.0,
  "updated_at": 1770000000.0,
  "completed": false,
  "position": 1,
  "color_tags": ["blue"],
  "deadline_at": null,
  "planned_start_at": null,
  "planned_end_at": null,
  "timer_started_at": null,
  "timer_ends_at": null,
  "timer_duration_seconds": null,
  "timer_paused_remaining_seconds": null,
  "client_updated_at": 1770000000.0
}
```

### Update

`PATCH /api/tasks/{task_id}/`

```json
{"text": "Write release notes v2", "updated_at": 1770000100.0}
```

### Delete

`DELETE /api/tasks/{task_id}/`

### Reorder

`POST /api/tasks/reorder/`

```json
{
  "tasks": [
    {"task_id": "11111111-1111-1111-1111-111111111111", "position": 10},
    {"task_id": "22222222-2222-2222-2222-222222222222", "position": 9}
  ]
}
```
