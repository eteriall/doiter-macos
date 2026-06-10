# doiter

Minimal macOS todo app with a Django sync backend.

## Layout

- `macos/` contains the PyObjC menu-bar app, local SQLite cache, py2app packaging, and macOS tests.
- `backend/` contains the Django/DRF API, token auth, task sync endpoints, Unfold admin, and OpenAPI docs.

## Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

For persistent logins across server restarts, keep the same database file/volume and set a stable `DOITER_SECRET_KEY` in the server environment. JWT refresh tokens are per app/device and valid for 365 days unless that specific device logs out.

API docs:

- OpenAPI schema: `http://127.0.0.1:8000/api/schema/`
- Swagger UI: `http://127.0.0.1:8000/api/docs/`
- Admin: `http://127.0.0.1:8000/admin/`
- Human API notes: `backend/docs/API.md`

### Docker Compose

Create a `.env` from `.env.example`, set a long random `DOITER_SECRET_KEY`, and set `DOITER_ALLOWED_HOSTS` to the public hostname used by Nginx Proxy Manager. For production, the default public hostname is `doiter.rasskazchikov.de` and the CSRF trusted origin is `https://doiter.rasskazchikov.de`.

```bash
docker network create proxy
docker compose up -d --build
```

Compose stores the backend SQLite database in the named volume `doiter-sqlite`, joins only the external `proxy` network, and does not publish host ports. In Nginx Proxy Manager, proxy to:

```text
Forward Hostname / IP: doiter-backend
Forward Port: 8000
```

## macOS App

```bash
cd macos
pip3 install -r requirements.txt
./build.sh
cp -r dist/doiter.app /Applications/
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```

The app stores its JWT access and refresh tokens in macOS Keychain. The server URL is configured from the menu-bar Settings window and defaults to:

```text
http://127.0.0.1:8000/api
```

On first login, the app asks whether existing local tasks should be imported into the authenticated account. Tasks remain cached locally for offline use and sync when the backend is reachable.

## Basic Operations

- `Cmd + E` - Open/close the overlay
- Type immediately - Cursor auto-focuses
- `Cmd + /` - Show keyboard shortcuts
- Type text - Search existing tasks or enter a new task
- `Enter` - Add or edit a task
- `Up/Down` - Navigate through tasks
- `Cmd + Up/Down` - Move selected task up or down
- `Backspace` - Delete selected task
- `Cmd + Z` - Undo last operation locally
- `Cmd + Shift + Z` - Redo locally
- `Cmd + D` - Set deadline
- `Cmd + Shift + D` - Clear deadline
- `Cmd + L` - Set planned slot
- `Cmd + Shift + L` - Clear planned slot
- `Cmd + P` - Copy current task list view
- `Cmd + T` - Start, stop, or continue countdown timer
- `Cmd + Shift + T` - Cancel selected task timer
- `Esc` - Close the overlay

## Troubleshooting

If the global hotkey does not work, grant Accessibility permissions:

1. System Settings > Privacy & Security > Accessibility
2. Add `doiter.app` or enable it in the list

To reset local app data:

```bash
rm ~/Library/Application\ Support/doiter/doiter.db
rm ~/Library/Application\ Support/doiter/config.json
security delete-generic-password -s com.doiter.app -a api-token
```
