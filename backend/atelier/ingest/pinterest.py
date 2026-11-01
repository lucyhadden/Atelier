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
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

AUTH_URL = "https://www.pinterest.com/oauth/"
API_BASE = "https://api.pinterest.com/v5"
# Read-only scopes. The `_secret` variants matter more than they look: a board
# you have marked secret on Pinterest - which a half-finished house plan very
# often is - is invisible to `boards:read` alone. Scopes are fixed at the moment
# you authorise, so asking for too few means reconnecting later.
SCOPES = (
    "boards:read",
    "boards:read_secret",
    "pins:read",
    "pins:read_secret",
    "user_accounts:read",
)

# Preferred image sizes from a pin's media payload, largest usable first.
IMAGE_SIZES = ("1200x", "originals", "600x315", "400x300", "150x150")

# One page is 100 items; this caps a single board at 5,000 pins. Hitting it is
# reported rather than silently truncating the board.
MAX_PAGES = 50

# How many times to wait out a 429 before giving up on a request.
MAX_RATE_LIMIT_RETRIES = 3

# Refresh the access token this long before it actually expires, so a sync does
# not die halfway through a board.
REFRESH_MARGIN = timedelta(minutes=5)


class PinterestError(RuntimeError):
    pass


class PinterestNotConnected(PinterestError):
    pass


class PinterestRateLimited(PinterestError):
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


def _expired(token: dict) -> bool:
    """True when the access token has expired, or is about to."""
    stamp = token.get("expires_at")
    if not stamp:
        return False
    try:
        expiry = datetime.fromisoformat(stamp)
    except ValueError:
        return False
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return datetime.now(UTC) + REFRESH_MARGIN >= expiry


def _access_token() -> str:
    token = load_token()
    if not token or not token.get("access_token"):
        raise PinterestNotConnected("Pinterest is not connected yet.")
    # Refresh ahead of expiry so a long board sync does not die halfway through.
    if _expired(token) and token.get("refresh_token"):
        log.info("access token near expiry, refreshing")
        token = refresh()
    return token["access_token"]


def _get(path: str, params: dict | None = None, *, retry_auth: bool = True) -> dict:
    access = _access_token()

    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{API_BASE}{path}",
                params=params or {},
                headers={"Authorization": f"Bearer {access}"},
            )

        if resp.status_code == 401 and retry_auth:
            refresh()
            return _get(path, params, retry_auth=False)

        if resp.status_code == 429:
            if attempt >= MAX_RATE_LIMIT_RETRIES:
                raise PinterestRateLimited(
                    "Pinterest rate limit reached. Trial access allows about 1,000 "
                    "calls a day; wait and run the sync again - already-downloaded "
                    "pins are kept, so it will pick up where it stopped."
                )
            # Respect Retry-After when Pinterest sends it, else back off.
            wait = _retry_after_seconds(resp) or min(60, 2 ** (attempt + 2))
            log.warning("rate limited on %s, waiting %ss", path, wait)
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            raise PinterestError(
                f"Pinterest API {resp.status_code} on {path}: {resp.text[:300]}"
            )
        return resp.json()

    raise PinterestRateLimited("Pinterest rate limit reached.")


def _retry_after_seconds(resp: httpx.Response) -> int | None:
    raw = resp.headers.get("retry-after")
    if not raw:
        return None
    try:
        # Cap it: a pathological value should not hang the request for an hour.
        return max(1, min(120, int(float(raw))))
    except ValueError:
        return None


def _paginate(
    path: str, params: dict | None = None, *, max_pages: int = MAX_PAGES
) -> tuple[list[dict], bool]:
    """Walk every page. Returns (items, truncated).

    `truncated` is True when the page cap was hit with more still to come -
    the caller reports that rather than quietly returning a partial board."""
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
            return items, False
    return items, True


def user_account() -> dict:
    """Who is actually connected - shown in the UI so you can tell at a glance."""
    data = _get("/user_account")
    return {
        "username": data.get("username"),
        "account_type": data.get("account_type"),
        "pin_count": data.get("pin_count"),
        "board_count": data.get("board_count"),
    }


def list_boards() -> list[dict]:
    boards, truncated = _paginate("/boards")
    if truncated:
        log.warning("more boards exist than were listed (page cap reached)")
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


def _best_image(images: dict) -> str | None:
    for size in IMAGE_SIZES:
        entry = images.get(size)
        if isinstance(entry, dict) and entry.get("url"):
            return entry["url"]
    for entry in images.values():
        if isinstance(entry, dict) and entry.get("url"):
            return entry["url"]
    return None


def pick_image_url(pin: dict) -> str | None:
    """The best still image for a pin, whatever kind of pin it is.

    A standard pin carries `media.images`. A video or idea pin instead carries
    `media.items`, each with its own cover images - without this, every idea pin
    on a board is silently skipped."""
    media = pin.get("media") or {}

    direct = _best_image(media.get("images") or {})
    if direct:
        return direct

    # Video and idea pins: take the first frame that has a usable cover.
    items = media.get("items")
    if isinstance(items, dict):
        items = list(items.values())
    for entry in items or []:
        if not isinstance(entry, dict):
            continue
        cover = _best_image(entry.get("images") or {})
        if cover:
            return cover
        if entry.get("cover_image_url"):
            return entry["cover_image_url"]

    return media.get("cover_image_url") or None


def list_sections(board_external_id: str) -> list[dict]:
    sections, _ = _paginate(f"/boards/{board_external_id}/sections")
    return [
        {"external_id": s.get("id"), "name": s.get("name") or "Untitled section"}
        for s in sections
        if s.get("id")
    ]


def _shape_pin(raw: dict, section: str | None = None) -> dict | None:
    url = pick_image_url(raw)
    if not url:
        return None
    return {
        "external_id": raw.get("id"),
        "title": raw.get("title") or raw.get("alt_text"),
        "note": raw.get("description") or raw.get("note"),
        "link": raw.get("link"),
        "image_url": url,
        "section": section,
    }


def list_pins(board_external_id: str) -> dict:
    """Every pin on a board, including the ones filed inside sections.

    The board-pins endpoint does not reliably return pins that sit inside a
    board section, so sections are walked separately and merged. Pins are
    deduplicated by id, because whether a pin appears in both listings is not
    something to depend on either way.

    Returns {"pins": [...], "truncated": bool, "skipped_no_image": int,
             "sections": [...]}.
    """
    raw_pins, truncated = _paginate(f"/boards/{board_external_id}/pins")

    sections = list_sections(board_external_id)
    by_id: dict[str, dict] = {}
    skipped = 0

    for raw in raw_pins:
        shaped = _shape_pin(raw)
        if shaped and shaped["external_id"]:
            by_id[shaped["external_id"]] = shaped
        elif not shaped:
            skipped += 1

    for section in sections:
        section_pins, section_truncated = _paginate(
            f"/boards/{board_external_id}/sections/{section['external_id']}/pins"
        )
        truncated = truncated or section_truncated
        for raw in section_pins:
            shaped = _shape_pin(raw, section=section["name"])
            if not shaped:
                skipped += 1
                continue
            pin_id = shaped["external_id"]
            if not pin_id:
                continue
            # Keep the section name even when the pin also came back unsectioned.
            if pin_id in by_id:
                by_id[pin_id]["section"] = section["name"]
            else:
                by_id[pin_id] = shaped

    return {
        "pins": list(by_id.values()),
        "truncated": truncated,
        "skipped_no_image": skipped,
        "sections": [s["name"] for s in sections],
    }
