"""Pinterest API v5 client.

Uses the official API with OAuth, which means: you register your own app, you
click "authorize" once in your own browser, and this reads your boards through
the documented endpoints. It does not automate a login or scrape the site - that
breaks Pinterest's terms and stops working without warning.

Setup, once:
  1. Create an app at https://developers.pinterest.com/apps/
  2. Add  http://localhost:8787/api/pinterest/callback  as a redirect URI
  3. Put the client id and secret in .env
  4. Open http://localhost:8787/api/pinterest/login
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

AUTH_URL = "https://www.pinterest.com/oauth/"
API_BASE = "https://api.pinterest.com/v5"
SCOPES = ("boards:read", "pins:read", "user_accounts:read")

# Preferred image sizes from a pin's media payload, largest usable first.
IMAGE_SIZES = ("1200x", "originals", "600x315", "400x300", "150x150")


class PinterestError(RuntimeError):
    pass


class PinterestNotConnected(PinterestError):
    pass


def _token_path() -> Path:
    return get_settings().data_dir / "pinterest_token.json"


def save_token(payload: dict) -> None:
    data = dict(payload)
    if "expires_in" in data:
        expiry = datetime.now(UTC) + timedelta(seconds=int(data["expires_in"]))
        data["expires_at"] = expiry.isoformat()
    path = _token_path()
    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o600)


def load_token() -> dict | None:
    path = _token_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def is_connected() -> bool:
    token = load_token()
    return bool(token and token.get("access_token"))


def disconnect() -> None:
    _token_path().unlink(missing_ok=True)


def login_url() -> tuple[str, str]:
    """Returns (url, state). Caller is responsible for checking state back."""
    settings = get_settings()
    if not settings.pinterest_configured:
        raise PinterestError(
            "Pinterest is not configured. Add PINTEREST_CLIENT_ID and "
            "PINTEREST_CLIENT_SECRET to .env, then restart the server."
        )
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.pinterest_client_id,
        "redirect_uri": settings.pinterest_redirect_uri,
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}", state


def exchange_code(code: str) -> dict:
    settings = get_settings()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{API_BASE}/oauth/token",
            auth=(settings.pinterest_client_id, settings.pinterest_client_secret),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.pinterest_redirect_uri,
            },
        )
    if resp.status_code != 200:
        raise PinterestError(f"Token exchange failed ({resp.status_code}): {resp.text[:300]}")
    payload = resp.json()
    save_token(payload)
    return payload


def refresh() -> dict:
    token = load_token()
    if not token or not token.get("refresh_token"):
        raise PinterestNotConnected("No refresh token stored; reconnect Pinterest.")
    settings = get_settings()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{API_BASE}/oauth/token",
            auth=(settings.pinterest_client_id, settings.pinterest_client_secret),
            data={"grant_type": "refresh_token", "refresh_token": token["refresh_token"]},
        )
    if resp.status_code != 200:
        raise PinterestError(f"Token refresh failed ({resp.status_code}): {resp.text[:300]}")
    payload = resp.json()
    # Pinterest may not return the refresh token again; keep the old one.
    payload.setdefault("refresh_token", token["refresh_token"])
    save_token(payload)
    return payload


def _get(path: str, params: dict | None = None, *, retry_auth: bool = True) -> dict:
    token = load_token()
    if not token or not token.get("access_token"):
        raise PinterestNotConnected("Pinterest is not connected yet.")

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{API_BASE}{path}",
            params=params or {},
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )

    if resp.status_code == 401 and retry_auth:
        refresh()
        return _get(path, params, retry_auth=False)
    if resp.status_code == 429:
        raise PinterestError("Pinterest rate limit hit. Wait a few minutes and retry.")
    if resp.status_code != 200:
        raise PinterestError(f"Pinterest API {resp.status_code} on {path}: {resp.text[:300]}")
    return resp.json()


def _paginate(path: str, params: dict | None = None, *, max_pages: int = 20) -> list[dict]:
    items: list[dict] = []
    bookmark = None
    for _ in range(max_pages):
        page_params = dict(params or {})
        page_params["page_size"] = 100
        if bookmark:
            page_params["bookmark"] = bookmark
        payload = _get(path, page_params)
        items.extend(payload.get("items") or [])
        bookmark = payload.get("bookmark")
        if not bookmark:
            break
    return items


def list_boards() -> list[dict]:
    boards = _paginate("/boards")
    return [
        {
            "external_id": b.get("id"),
            "name": b.get("name") or "Untitled board",
            "description": b.get("description"),
            "pin_count": (b.get("pin_count") or 0),
            "privacy": b.get("privacy"),
        }
        for b in boards
    ]


def pick_image_url(pin: dict) -> str | None:
    images = ((pin.get("media") or {}).get("images")) or {}
    for size in IMAGE_SIZES:
        entry = images.get(size)
        if isinstance(entry, dict) and entry.get("url"):
            return entry["url"]
    # Fall back to whatever is there.
    for entry in images.values():
        if isinstance(entry, dict) and entry.get("url"):
            return entry["url"]
    return None


def list_pins(board_external_id: str) -> list[dict]:
    pins = _paginate(f"/boards/{board_external_id}/pins")
    out = []
    for p in pins:
        url = pick_image_url(p)
        if not url:
            continue
        out.append(
            {
                "external_id": p.get("id"),
                "title": p.get("title") or p.get("alt_text"),
                "note": p.get("description") or p.get("note"),
                "link": p.get("link"),
                "image_url": url,
            }
        )
    return out
