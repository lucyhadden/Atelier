"""Identified items and where to buy them."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..api_schemas import ItemOut, SourceItemIn
from ..db import get_db
from ..models import Board, Item, Pin
from ..shopping import sourcing
from ..vision.client import AnalysisError

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemOut])
def list_items(
    domain: str | None = None,
    board_id: int | None = None,
    category: str | None = None,
    hero_only: bool = False,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    if domain:
        query = query.filter(Item.domain == domain)
    if category:
        query = query.filter(Item.category == category)
    if hero_only:
        query = query.filter(Item.is_hero.is_(True))
    if board_id is not None:
        query = query.join(Pin, Item.pin_id == Pin.id).filter(Pin.board_id == board_id)
    items = (
        query.order_by(Item.is_hero.desc(), Item.confidence.desc()).limit(limit).all()
    )
    return [ItemOut.model_validate(i) for i in items]


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, f"No item with id {item_id}")
    return ItemOut.model_validate(item)


@router.get("/{item_id}/search-links")
def search_links(item_id: int, region: str | None = None, db: Session = Depends(get_db)):
    """Instant, free tiered search links - no Claude call."""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, f"No item with id {item_id}")
    return {"item_id": item_id, "sources": sourcing.search_sources(item, region=region)}


@router.post("/{item_id}/source", response_model=ItemOut)
def source_item(
    item_id: int, payload: SourceItemIn | None = None, db: Session = Depends(get_db)
):
    """Find places to buy this item. With web search on, this takes ~20s and
    returns named products with prices; with it off, it is instant search links."""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, f"No item with id {item_id}")
    payload = payload or SourceItemIn()
    try:
        sourcing.source_item(
            db, item, use_web_search=payload.use_web_search, region=payload.region
        )
    except AnalysisError as exc:
        raise HTTPException(502, str(exc)) from exc
    db.refresh(item)
    return ItemOut.model_validate(item)


@router.get("/by-category/summary")
def category_summary(domain: str = "interior", db: Session = Depends(get_db)):
    """Everything saved, grouped by category - the 'what do I actually like'
    view across every board in a domain."""
    items = db.query(Item).filter(Item.domain == domain).all()
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(
            {
                "id": item.id,
                "name": item.name,
                "attributes": item.attributes,
                "is_hero": item.is_hero,
                "confidence": item.confidence,
                "pin_id": item.pin_id,
                "sourced": bool(item.sources),
            }
        )
    boards = {b.id: b.name for b in db.query(Board).filter(Board.domain == domain).all()}
    return {
        "domain": domain,
        "boards": boards,
        "categories": [
            {"category": cat, "count": len(rows), "items": rows}
            for cat, rows in sorted(grouped.items(), key=lambda kv: -len(kv[1]))
        ],
    }
