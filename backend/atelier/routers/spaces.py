"""Spaces: a room (or a wardrobe brief), its floor plans, and its plan."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..api_schemas import BuildPlanIn, FloorPlanOut, PlanOut, SpaceIn, SpaceOut
from ..db import get_db
from ..domains import DOMAINS
from ..ingest.images import ImageError, store_from_bytes
from ..models import Board, FloorPlan, Plan, Space
from ..vision import analyze
from ..vision.client import AnalysisError

router = APIRouter(prefix="/spaces", tags=["spaces"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _get_space(db: Session, space_id: int) -> Space:
    space = db.get(Space, space_id)
    if space is None:
        raise HTTPException(404, f"No space with id {space_id}")
    return space


@router.get("", response_model=list[SpaceOut])
def list_spaces(domain: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Space)
    if domain:
        query = query.filter(Space.domain == domain)
    return [SpaceOut.model_validate(s) for s in query.order_by(Space.created_at.desc()).all()]


@router.post("", response_model=SpaceOut)
def create_space(payload: SpaceIn, db: Session = Depends(get_db)):
    if payload.domain not in DOMAINS:
        raise HTTPException(400, f"Unknown domain {payload.domain!r}")
    space = Space(**payload.model_dump())
    db.add(space)
    db.commit()
    db.refresh(space)
    return SpaceOut.model_validate(space)


@router.get("/{space_id}", response_model=SpaceOut)
def get_space(space_id: int, db: Session = Depends(get_db)):
    return SpaceOut.model_validate(_get_space(db, space_id))


@router.delete("/{space_id}")
def delete_space(space_id: int, db: Session = Depends(get_db)):
    space = _get_space(db, space_id)
    db.delete(space)
    db.commit()
    return {"deleted": space_id}


@router.post("/{space_id}/plans", response_model=FloorPlanOut)
async def upload_plan(
    space_id: int,
    file: UploadFile = File(...),
    kind: str = Form("floorplan"),
    label: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a floor plan or a room photo."""
    space = _get_space(db, space_id)
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is larger than 25MB")
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        filename = store_from_bytes(data, file.filename or "upload.jpg", prefix="plan")
    except ImageError as exc:
        raise HTTPException(400, str(exc)) from exc

    plan = FloorPlan(
        space_id=space.id,
        image_file=filename,
        kind=kind if kind in ("floorplan", "photo") else "floorplan",
        label=label,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return FloorPlanOut.model_validate(plan)


@router.post("/{space_id}/plans/{plan_id}/analyze", response_model=FloorPlanOut)
def analyze_plan(space_id: int, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(FloorPlan, plan_id)
    if plan is None or plan.space_id != space_id:
        raise HTTPException(404, "Floor plan not found on this space")
    try:
        return FloorPlanOut.model_validate(analyze.read_floorplan(db, plan))
    except AnalysisError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.delete("/{space_id}/plans/{plan_id}")
def delete_plan(space_id: int, plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(FloorPlan, plan_id)
    if plan is None or plan.space_id != space_id:
        raise HTTPException(404, "Floor plan not found on this space")
    db.delete(plan)
    db.commit()
    return {"deleted": plan_id}


@router.post("/{space_id}/design", response_model=PlanOut)
def build_design(space_id: int, payload: BuildPlanIn, db: Session = Depends(get_db)):
    """The payoff: apply a board's aesthetic to this space."""
    space = _get_space(db, space_id)
    board = None
    if payload.board_id is not None:
        board = db.get(Board, payload.board_id)
        if board is None:
            raise HTTPException(404, f"No board with id {payload.board_id}")
        if board.domain != space.domain:
            raise HTTPException(
                400,
                f"Board is a {board.domain} board but the space is {space.domain}.",
            )
    try:
        return PlanOut.model_validate(analyze.build_plan(db, space, board, payload.brief))
    except AnalysisError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/{space_id}/designs", response_model=list[PlanOut])
def list_designs(space_id: int, db: Session = Depends(get_db)):
    _get_space(db, space_id)
    plans = (
        db.query(Plan).filter(Plan.space_id == space_id).order_by(Plan.created_at.desc()).all()
    )
    return [PlanOut.model_validate(p) for p in plans]
