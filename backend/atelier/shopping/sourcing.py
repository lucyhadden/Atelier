"""Find places to buy an item.

Two modes, and the difference matters:

  "search" sources are deep links into a retailer's own search results. They are
  generated locally, cost nothing, and always point somewhere real - but you
  still have to look through the results yourself.

  "product" sources are specific named products with prices, found by letting
  Claude search the web. They cost tokens and take ~20s, and they are the only
  mode that can tell you "this exact lamp is £180 at Heal's".
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Item, Source
from ..vision import prompts
from ..vision.client import AnalysisError, research, structure
from ..vision.schemas import ProductFindings
from . import retailers
from .query import build_url, search_queries

log = logging.getLogger(__name__)


def search_sources(item: Item, *, region: str | None = None, per_tier: int = 3) -> list[dict]:
    """Deep search links, grouped by tier. Pure local computation."""
    region = region or get_settings().atelier_region
    queries = search_queries(item)
    primary = queries[0] if queries else item.name
    grouped = retailers.by_tier(
        item.domain, region=region, category=item.category, per_tier=per_tier
    )

    out: list[dict] = []
    for tier in retailers.TIERS:
        for r in grouped.get(tier, []):
            out.append(
                {
                    "tier": tier,
                    "retailer": r.name,
                    "url": build_url(r.search, primary),
                    "kind": "search",
                    "product_name": None,
                    "price": None,
                    "note": r.note or None,
                }
            )
    return out


def _research_prompt(item: Item, region: str) -> str:
    attrs = ", ".join(f"{k}: {v}" for k, v in (item.attributes or {}).items())
    shops = retailers.by_tier(item.domain, region=region, category=item.category, per_tier=4)
    shop_lines = "\n".join(
        f"  {retailers.TIER_LABELS[t]}: {', '.join(r.name for r in rs)}"
        for t, rs in shops.items()
        if rs
    )
    return f"""Find real, currently-listed products matching this:

  What it is: {item.name}
  Category: {item.category}
  Details: {attrs or "none recorded"}
  Described as: {item.description}
  Search terms to try: {", ".join(item.search_terms or [item.name])}
  Shopping region: {region}

Find up to two products in each of these price tiers:

  Splurge - the closest thing to the original, price no object
  Middle - a good version at a sensible price
  Budget - the cheapest thing that still gets the look
  Secondhand - vintage, resale or marketplace

Retailers worth trying in this region (you are not limited to these):
{shop_lines}

For each product give the retailer, the exact product name, the full URL of its
product page, and the price as listed. Then say in one clause how it differs
from the original. Skip any tier where you cannot find something credible."""


def product_sources(item: Item, *, region: str | None = None) -> tuple[list[dict], str]:
    """Live web search for specific products. Returns (sources, caveat)."""
    settings = get_settings()
    region = region or settings.atelier_region

    write_up = research(
        system=prompts.SOURCING_RESEARCH,
        prompt=_research_prompt(item, region),
    )
    if not write_up:
        return [], "Web search returned nothing for this item."

    findings: ProductFindings = structure(
        system=prompts.SOURCING_STRUCTURE,
        prompt=f"Structure these sourcing findings:\n\n{write_up}",
        output_format=ProductFindings,
    )

    valid_tiers = set(retailers.TIERS)
    out: list[dict] = []
    for f in findings.findings:
        # Drop anything without a plausible absolute URL rather than storing a
        # link that will 404.
        if not f.url.startswith(("http://", "https://")):
            log.warning("dropping finding with unusable url: %r", f.url)
            continue
        out.append(
            {
                "tier": f.tier if f.tier in valid_tiers else "mid",
                "retailer": f.retailer,
                "url": f.url,
                "kind": "product",
                "product_name": f.product_name,
                "price": None if f.price.lower() == "unknown" else f.price,
                "note": f.note,
            }
        )
    return out, findings.caveat


def source_item(
    db: Session, item: Item, *, use_web_search: bool | None = None, region: str | None = None
) -> dict:
    """Populate an item's sources. Always writes search links; adds live product
    findings when web search is enabled."""
    settings = get_settings()
    if use_web_search is None:
        use_web_search = settings.atelier_web_search

    rows = search_sources(item, region=region)
    caveat = ""
    error = None

    if use_web_search:
        try:
            found, caveat = product_sources(item, region=region)
            rows = found + rows
        except AnalysisError as exc:
            # A failed web search must not lose the search links.
            log.warning("web sourcing failed for item %s: %s", item.id, exc)
            error = str(exc)

    for existing in list(item.sources):
        db.delete(existing)
    db.flush()
    for row in rows:
        db.add(Source(item_id=item.id, **row))
    db.commit()
    db.refresh(item)

    return {
        "item_id": item.id,
        "count": len(rows),
        "products": sum(1 for r in rows if r["kind"] == "product"),
        "caveat": caveat,
        "web_search_error": error,
    }
