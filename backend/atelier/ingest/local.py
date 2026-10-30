"""Import images without touching the Pinterest API.

Two routes in:

  A folder of images - drag whatever you have saved into a directory and point
  Atelier at it. The folder name becomes the board name.

  A Pinterest data export - request yours at
  https://www.pinterest.com/settings/account-settings/ ("Request your data").
  The export is a zip; point this at the unzipped folder and it will pick up the
  images and, where present, the board names from the accompanying CSV/JSON.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Board, Pin
from .images import ALLOWED_SUFFIXES, ImageError, store_from_path

log = logging.getLogger(__name__)


def _iter_images(folder: Path) -> list[Path]:
    return sorted(
        p
        for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES and not p.name.startswith(".")
    )


def import_folder(
    db: Session,
    folder: Path,
    *,
    domain: str = "interior",
    board_name: str | None = None,
) -> dict:
    """Treat a folder of images as a board."""
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"Not a folder: {folder}")

    files = _iter_images(folder)
    if not files:
        raise ValueError(f"No images found in {folder}")

    name = board_name or folder.name.replace("-", " ").replace("_", " ").strip()
    external = str(folder)

    board = (
        db.query(Board)
        .filter(Board.source == "local", Board.external_id == external)
        .one_or_none()
    )
    if board is None:
        board = Board(name=name, domain=domain, source="local", external_id=external)
        db.add(board)
        db.flush()
    else:
        board.name = name
        board.domain = domain

    existing = {p.note for p in board.pins if p.note}
    added, failed = 0, []
    for path in files:
        marker = str(path.relative_to(folder))
        if marker in existing:
            continue
        try:
            filename = store_from_path(path, prefix="local")
        except (ImageError, OSError) as exc:
            failed.append({"file": marker, "error": str(exc)})
            continue
        db.add(
            Pin(
                board_id=board.id,
                title=path.stem.replace("-", " ").replace("_", " "),
                note=marker,
                image_file=filename,
                source_url=f"file://{path}",
            )
        )
        added += 1

    board.synced_at = datetime.now(UTC)
    db.commit()
    db.refresh(board)
    return {
        "board_id": board.id,
        "board_name": board.name,
        "added": added,
        "skipped": len(files) - added - len(failed),
        "failed": failed,
    }


def _export_board_names(root: Path) -> dict[str, str]:
    """Best-effort: map image filenames to board names from export metadata.

    Pinterest's export format has changed more than once, so this reads what it
    recognises and silently gives up on the rest - a missing mapping just means
    the folder structure is used instead.
    """
    mapping: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".json" and "board" in path.name.lower():
                payload = json.loads(path.read_text())
                records = payload if isinstance(payload, list) else payload.get("boards", [])
                for rec in records:
                    if isinstance(rec, dict) and rec.get("name") and rec.get("image"):
                        mapping[Path(str(rec["image"])).name] = str(rec["name"])
            elif path.suffix.lower() == ".csv" and "pin" in path.name.lower():
                with path.open(newline="", encoding="utf-8", errors="replace") as fh:
                    for row in csv.DictReader(fh):
                        board = row.get("Board Name") or row.get("board_name") or row.get("board")
                        image = row.get("Image URL") or row.get("image_url") or row.get("image")
                        if board and image:
                            mapping[Path(str(image).split("?")[0]).name] = str(board)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError, csv.Error) as exc:
            log.debug("skipping export metadata %s: %s", path.name, exc)
    return mapping


def import_pinterest_export(db: Session, root: Path, *, domain: str = "interior") -> dict:
    """Import an unzipped Pinterest data export.

    Each subfolder containing images becomes a board; metadata board names are
    used when they can be matched.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Not a folder: {root}")

    names = _export_board_names(root)
    folders: dict[Path, list[Path]] = {}
    for image in _iter_images(root):
        folders.setdefault(image.parent, []).append(image)

    if not folders:
        raise ValueError(f"No images found anywhere under {root}")

    results = []
    for folder, images in sorted(folders.items()):
        named = next((names[i.name] for i in images if i.name in names), None)
        label = named or folder.name.replace("-", " ").replace("_", " ")
        if folder == root:
            label = named or "Pinterest export"
        results.append(import_folder(db, folder, domain=domain, board_name=label))

    return {
        "boards": results,
        "total_added": sum(r["added"] for r in results),
        "metadata_matched": bool(names),
    }
