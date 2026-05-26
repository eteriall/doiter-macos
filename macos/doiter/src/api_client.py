"""HTTP client, config storage, and Keychain token helpers for doiter sync."""

import json
import platform
import subprocess
import threading
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, List, Optional


APP_SUPPORT = Path.home() / "Library" / "Application Support" / "doiter"
CONFIG_PATH = APP_SUPPORT / "config.json"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api"
KEYCHAIN_SERVICE = "com.doiter.app"
KEYCHAIN_ACCOUNT = "api-token"


class APIError(RuntimeError):
    def __init__(self, message: str, status: Optional[int] = None, url: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.url = url


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict:
        if not self.path.exists():
            return {"api_base_url": DEFAULT_API_BASE_URL}
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            data = {}
        data.setdefault("api_base_url", DEFAULT_API_BASE_URL)
        return data

    def save(self, data: Dict):
        current = self.load()
        current.update(data)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(current, fh, indent=2, sort_keys=True)

    def get_api_base_url(self) -> str:
        return self.load()["api_base_url"].rstrip("/")

    def set_api_base_url(self, value: str):
        self.save({"api_base_url": value.rstrip("/")})

    def get_device_id(self) -> str:
        data = self.load()
        device_id = data.get("device_id")
        if not device_id:
            device_id = str(uuid.uuid4())
            self.save({"device_id": device_id})
        return device_id


class KeychainTokenStore:
    def _load(self) -> Dict:
        value = self._read_raw()
        if not value:
            return {}
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return {"access": value, "refresh": ""}
        if not isinstance(data, dict):
            return {}
        return data

    def _read_raw(self) -> Optional[str]:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        token = result.stdout.strip()
        return token or None

    def get(self) -> Optional[str]:
        return self._load().get("access") or None

    def get_refresh(self) -> Optional[str]:
        return self._load().get("refresh") or None

    def set(self, token: str):
        self.set_tokens(token, "")

    def set_tokens(self, access: str, refresh: str):
        self.clear()
        value = json.dumps({"access": access, "refresh": refresh})
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
                value,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    def clear(self):
        subprocess.run(
            [
                "security",
                "delete-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
            ],
            capture_output=True,
            text=True,
            check=False,
        )


class DoiterAPIClient:
    def __init__(self, config: ConfigStore, token_store: KeychainTokenStore):
        self.config = config
        self.token_store = token_store
        self._refresh_lock = threading.Lock()

    @property
    def token(self) -> Optional[str]:
        return self.token_store.get()

    @property
    def refresh_token(self) -> Optional[str]:
        get_refresh = getattr(self.token_store, "get_refresh", None)
        if not get_refresh:
            return None
        return get_refresh()

    def request(self, method: str, path: str, data: Optional[Dict] = None, auth: bool = True, retry_on_unauthorized: bool = True):
        access_token = self.token if auth else None
        try:
            return self._request_once(method, path, data, auth, access_token)
        except APIError as exc:
            if auth and retry_on_unauthorized and exc.status == 401 and self._refresh_auth(access_token):
                return self._request_once(method, path, data, auth)
            raise

    def _request_once(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        auth: bool = True,
        access_token: Optional[str] = None,
    ):
        url = f"{self.config.get_api_base_url()}/{path.lstrip('/')}"
        body = None
        headers = {
            "Accept": "application/json",
            "X-Doiter-Device-Id": self.config.get_device_id(),
            "X-Doiter-Device-Name": platform.node() or "unknown",
            "X-Doiter-Device-Platform": platform.platform(),
        }
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            token = access_token if access_token is not None else self.token
            if token:
                headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                content = response.read()
                if not content:
                    return None
                return json.loads(content.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = self._error_message(exc, url)
            raise APIError(detail, exc.code, url) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise APIError("Server unavailable", url=url) from exc

    def _refresh_auth(self, failed_access_token: Optional[str] = None) -> bool:
        with self._refresh_lock:
            if failed_access_token and self.token and self.token != failed_access_token:
                return True

            refresh = self.refresh_token
            if not refresh:
                return False
            try:
                result = self.request(
                    "POST",
                    "auth/refresh/",
                    {"refresh": refresh},
                    auth=False,
                    retry_on_unauthorized=False,
                )
            except APIError as exc:
                if exc.status in (400, 401, 403) and self.refresh_token == refresh:
                    self.token_store.clear()
                    return False
                raise
            access = result.get("access")
            if not access:
                if self.refresh_token == refresh:
                    self.token_store.clear()
                return False
            self.token_store.set_tokens(access, result.get("refresh") or refresh)
            return True

    def _error_message(self, exc: urllib.error.HTTPError, url: str) -> str:
        body = exc.read().decode("utf-8", errors="replace")
        content_type = exc.headers.get("Content-Type", "")
        if "application/json" in content_type and body:
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                if "detail" in data:
                    return f"HTTP {exc.code}: {data['detail']}"
                first_key = next(iter(data), None)
                if first_key:
                    value = data[first_key]
                    if isinstance(value, list) and value:
                        return f"HTTP {exc.code}: {first_key} {value[0]}"
                    return f"HTTP {exc.code}: {first_key} {value}"
        return f"HTTP {exc.code}: {url}"

    def register(self, username: str, password: str) -> Dict:
        result = self.request("POST", "auth/register/", {"username": username, "password": password}, auth=False)
        self.token_store.set_tokens(result["access"], result["refresh"])
        return result

    def login(self, username: str, password: str) -> Dict:
        result = self.request("POST", "auth/login/", {"username": username, "password": password}, auth=False)
        self.token_store.set_tokens(result["access"], result["refresh"])
        return result

    def logout(self):
        try:
            refresh = self.refresh_token
            if refresh:
                self.request("POST", "auth/logout/", {"refresh": refresh})
        finally:
            self.token_store.clear()

    def me(self) -> Dict:
        return self.request("GET", "auth/me/")

    def list_tasks(self) -> List[Dict]:
        return self.request("GET", "tasks/")

    def create_task(self, task: Dict) -> Dict:
        return self.request("POST", "tasks/", task)

    def update_task(self, task_id: str, task: Dict) -> Dict:
        return self.request("PATCH", f"tasks/{task_id}/", task)

    def delete_task(self, task_id: str):
        return self.request("DELETE", f"tasks/{task_id}/")

    def reorder(self, tasks: List[Dict]) -> List[Dict]:
        return self.request("POST", "tasks/reorder/", {"tasks": tasks})
