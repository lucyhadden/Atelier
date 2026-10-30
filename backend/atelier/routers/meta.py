"""Status and reference data the UI needs to render itself."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api_schemas import StatusOut
from ..config import get_settings
from ..db import get_db
from ..domains import DOMAINS
from ..ingest import pinterest
from ..models import Board, Item
from ..shopping import retailers

router = APIRouter(tags=["meta"])


@router.get("/status", response_model=StatusOut)
def status(db: Session = Depends(get_db)) -> StatusOut:
    s = get_settings()
    return StatusOut(
        claude_configured=s.claude_configured,
        model=s.atelier_model,
        effort=s.atelier_effort,
        region=s.atelier_region,
        web_search_enabled=s.atelier_web_search,
        pinterest_configured=s.pinterest_configured,
        pinterest_connected=pinterest.is_connected(),
        board_count=db.query(Board).count(),
        item_count=db.query(Item).count(),
    )


@router.get("/domains")
def list_domains() -> list[dict]:
    return [
        {
            "key": d.key,
            "label": d.label,
            "unit": d.unit,
            "categories": d.categories,
            "attributes": d.attributes,
            "axes": d.aesthetic_axes,
        }
        for d in DOMAINS.values()
    ]


@router.get("/retailers")
def list_retailers(domain: str = "interior", region: str | None = None) -> dict:
    region = region or get_settings().atelier_region
    grouped = retailers.by_tier(domain, region=region, per_tier=99)
    return {
        "region": region,
        "tiers": [
            {
                "tier": tier,
                "label": retailers.TIER_LABELS[tier],
                "retailers": [
                    {"name": r.name, "note": r.note, "categories": list(r.category_hints)}
                    for r in grouped.get(tier, [])
                ],
            }
            for tier in retailers.TIERS
        ],
    }
