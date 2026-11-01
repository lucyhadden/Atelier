"""Pull Pinterest boards and pins into the local database."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..models import Board, Pin
from . import pinterest
from .images import ImageError, store_from_url

log = logging.getLogger(__name__)


def sync_board(
    db: Session, board_external_id: str, *, domain: str = "interior", name: str | None = None
) -> dict:
    """Create or update a board and download any pins we do not already have."""
    board = (
        db.query(Board)
        .filter(Board.source == "pinterest", Board.external_id == board_external_id)
        .one_or_none()
    )
    if board is None:
        remote = next(
            (b for b in pinterest.list_boards() if b["external_id"] == board_external_id), None
        )
        if remote is None and name is None:
            raise pinterest.PinterestError(
                f"Board {board_external_id} not found on your Pinterest account."
            )
        board = Board(
            name=name or (remote or {}).get("name") or "Untitled board",
            description=(remote or {}).get("description"),
            domain=domain,
            source="pinterest",
            external_id=board_external_id,
        )
        db.add(board)
        db.flush()
    elif name:
        board.name = name

    known = {p.external_id for p in board.pins if p.external_id}
    result = pinterest.list_pins(board_external_id)
    remote_pins = result["pins"]

    added, failed = 0, []
    for rp in remote_pins:
        if rp["external_id"] in known:
            continue
        try:
            filename = store_from_url(rp["image_url"], prefix="pin")
        except ImageError as exc:
            failed.append({"pin": rp["external_id"], "error": str(exc)})
            continue
        # A pin filed in a board section keeps that section name as its note,
        # so the grouping you made on Pinterest is not lost on import.
        note = rp["note"]
        if rp.get("section"):
            note = f"[{rp['section']}] {note}" if note else f"[{rp['section']}]"
        db.add(
            Pin(
                board_id=board.id,
                external_id=rp["external_id"],
                title=rp["title"],
                note=note,
                link=rp["link"],
                image_file=filename,
                source_url=rp["image_url"],
            )
        )
        added += 1

    # Pins removed on Pinterest since the last sync. Reported, never deleted -
    # losing a catalogued piece because a pin was tidied away would be worse
    # than carrying a stale one.
    remote_ids = {rp["external_id"] for rp in remote_pins}
    removed = sorted(known - remote_ids) if remote_ids else []

    board.synced_at = datetime.now(UTC)
    db.commit()
    db.refresh(board)
    return {
        "board_id": board.id,
        "board_name": board.name,
        "remote_pins": len(remote_pins),
        "added": added,
        "already_had": len(known),
        "failed": failed,
        "sections": result["sections"],
        "skipped_no_image": result["skipped_no_image"],
        "truncated": result["truncated"],
        "gone_from_pinterest": len(removed),
    }
