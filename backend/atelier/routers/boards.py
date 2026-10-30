"""Boards, pins and the analysis that runs over them."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api_schemas import BoardOut, ImportFolderIn, PinOut, StyleProfileOut
from ..db import get_db
from ..domains import DOMAINS
from ..ingest import local
from ..models import Board, Pin, StyleProfile
from ..vision import analyze
from ..vision.client import AnalysisError

router = APIRouter(prefix="/boards", tags=["boards"])


def _board_out(board: Board) -> BoardOut:
    out = BoardOut.model_validate(board)
    out.pin_count = len(board.pins)
    out.analyzed_count = sum(1 for p in board.pins if p.analyzed_at)
    out.item_count = sum(len(p.items) for p in board.pins)
    return out


def _get_board(db: Session, board_id: int) -> Board:
    board = db.get(Board, board_id)
    if board is None:
        raise HTTPException(404, f"No board with id {board_id}")
    return board


@router.get("", response_model=list[BoardOut])
def list_boards(domain: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Board)
    if domain:
        query = query.filter(Board.domain == domain)
    return [_board_out(b) for b in query.order_by(Board.created_at.desc()).all()]


@router.get("/{board_id}", response_model=BoardOut)
def get_board(board_id: int, db: Session = Depends(get_db)):
    return _board_out(_get_board(db, board_id))


@router.delete("/{board_id}")
def delete_board(board_id: int, db: Session = Depends(get_db)):
    board = _get_board(db, board_id)
    db.delete(board)
    db.commit()
    return {"deleted": board_id}


@router.get("/{board_id}/pins", response_model=list[PinOut])
def list_pins(board_id: int, db: Session = Depends(get_db)):
    board = _get_board(db, board_id)
    return [PinOut.model_validate(p) for p in board.pins]


@router.post("/import-folder")
def import_folder(payload: ImportFolderIn, db: Session = Depends(get_db)):
    if payload.domain not in DOMAINS:
        raise HTTPException(400, f"Unknown domain {payload.domain!r}")
    path = Path(payload.path)
    try:
        if payload.is_pinterest_export:
            return local.import_pinterest_export(db, path, domain=payload.domain)
        return local.import_folder(
            db, path, domain=payload.domain, board_name=payload.board_name
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{board_id}/analyze")
def analyze_board(board_id: int, force: bool = False, db: Session = Depends(get_db)):
    """Catalogue every pin on the board. Synchronous and slow by design - one
    Claude call per image - so the UI shows progress by polling the board."""
    board = _get_board(db, board_id)
    if not board.pins:
        raise HTTPException(400, "This board has no pins yet.")
    return analyze.analyze_board(db, board, force=force)


@router.post("/{board_id}/pins/{pin_id}/analyze", response_model=PinOut)
def analyze_single_pin(
    board_id: int, pin_id: int, force: bool = True, db: Session = Depends(get_db)
):
    pin = db.get(Pin, pin_id)
    if pin is None or pin.board_id != board_id:
        raise HTTPException(404, "Pin not found on this board")
    try:
        return PinOut.model_validate(analyze.analyze_pin(db, pin, force=force))
    except AnalysisError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/{board_id}/style", response_model=StyleProfileOut)
def read_style(board_id: int, db: Session = Depends(get_db)):
    board = _get_board(db, board_id)
    try:
        return StyleProfileOut.model_validate(analyze.read_style(db, board))
    except AnalysisError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/{board_id}/style", response_model=StyleProfileOut | None)
def latest_style(board_id: int, db: Session = Depends(get_db)):
    _get_board(db, board_id)
    profile = (
        db.query(StyleProfile)
        .filter(StyleProfile.board_id == board_id)
        .order_by(StyleProfile.created_at.desc())
        .first()
    )
    return StyleProfileOut.model_validate(profile) if profile else None
