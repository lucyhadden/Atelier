"""Pinterest OAuth + board syncing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..api_schemas import SyncBoardIn
from ..db import get_db
from ..domains import DOMAINS
from ..ingest import pinterest, sync

log = logging.getLogger(__name__)
router = APIRouter(prefix="/pinterest", tags=["pinterest"])

# OAuth state, held in memory. A restart mid-flow just means starting over.
_pending_state: set[str] = set()

_CALLBACK_PAGE = """<!doctype html>
<meta charset="utf-8"><title>Pinterest connected</title>
<style>
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 34rem;
         margin: 15vh auto; padding: 0 1.5rem; color: #1a1a1a; }}
  code {{ background: #f0ede8; padding: .15em .4em; border-radius: 3px; }}
</style>
<h1>{heading}</h1>
<p>{body}</p>
<p>You can close this tab and go back to Atelier.</p>
"""


@router.get("/status")
def status():
    from ..config import get_settings

    s = get_settings()
    payload = {
        "configured": s.pinterest_configured,
        "connected": pinterest.is_connected(),
        "redirect_uri": s.pinterest_redirect_uri,
        "scopes": list(pinterest.SCOPES),
        "account": None,
    }
    if payload["connected"]:
        # Show whose account this is, so a wrong-account connection is obvious
        # before you sync a board. A failure here must not break the page.
        try:
            payload["account"] = pinterest.user_account()
        except pinterest.PinterestError as exc:
            log.warning("could not read the connected account: %s", exc)
            payload["account_error"] = str(exc)
    return payload


@router.get("/login")
def login():
    try:
        url, state = pinterest.login_url()
    except pinterest.PinterestError as exc:
        raise HTTPException(400, str(exc)) from exc
    _pending_state.add(state)
    return RedirectResponse(url)


@router.get("/callback", response_class=HTMLResponse)
def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(
            _CALLBACK_PAGE.format(
                heading="Pinterest declined", body=f"Pinterest returned: <code>{error}</code>"
            ),
            status_code=400,
        )
    if not code:
        return HTMLResponse(
            _CALLBACK_PAGE.format(heading="Missing code", body="No authorization code arrived."),
            status_code=400,
        )
    if state not in _pending_state:
        # Guards against someone else's callback landing here.
        return HTMLResponse(
            _CALLBACK_PAGE.format(
                heading="State mismatch",
                body="That callback did not match a login started here. Try again from Atelier.",
            ),
            status_code=400,
        )
    _pending_state.discard(state)

    try:
        pinterest.exchange_code(code)
    except pinterest.PinterestError as exc:
        return HTMLResponse(
            _CALLBACK_PAGE.format(heading="Could not connect", body=str(exc)), status_code=502
        )
    return HTMLResponse(
        _CALLBACK_PAGE.format(
            heading="Pinterest connected",
            body="Atelier can now read your boards and pins.",
        )
    )


@router.post("/disconnect")
def disconnect():
    pinterest.disconnect()
    return {"connected": False}


@router.get("/boards")
def remote_boards():
    """Your Pinterest boards, straight from the API - not yet imported."""
    try:
        return {"boards": pinterest.list_boards()}
    except pinterest.PinterestNotConnected as exc:
        raise HTTPException(401, str(exc)) from exc
    except pinterest.PinterestError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/sync")
def sync_board(payload: SyncBoardIn, db: Session = Depends(get_db)):
    """Download a board's pins into the local database."""
    if payload.domain not in DOMAINS:
        raise HTTPException(400, f"Unknown domain {payload.domain!r}")
    try:
        return sync.sync_board(
            db, payload.external_id, domain=payload.domain, name=payload.name
        )
    except pinterest.PinterestNotConnected as exc:
        raise HTTPException(401, str(exc)) from exc
    except pinterest.PinterestRateLimited as exc:
        # 429 upstream is a 429 here, so the UI can say "wait and retry"
        # rather than presenting it as a broken sync.
        raise HTTPException(429, str(exc)) from exc
    except pinterest.PinterestError as exc:
        raise HTTPException(502, str(exc)) from exc
