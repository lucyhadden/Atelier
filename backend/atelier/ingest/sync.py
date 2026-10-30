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
    remote_pins = pinterest.list_pins(board_external_id)

    added, failed = 0, []
    for rp in remote_pins:
        if rp["external_id"] in known:
            continue
        try:
            filename = store_from_url(rp["image_url"], prefix="pin")
        except ImageError as exc:
            failed.append({"pin": rp["external_id"], "error": str(exc)})
            continue
        db.add(
            Pin(
                board_id=board.id,
                external_id=rp["external_id"],
                title=rp["title"],
                note=rp["note"],
                link=rp["link"],
                image_file=filename,
                source_url=rp["image_url"],
            )
        )
        added += 1

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
    }
