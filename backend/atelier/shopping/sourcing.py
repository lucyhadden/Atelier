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
    settings = get_settings()
    region = region or settings.atelier_region
    queries = search_queries(item)
    primary = queries[0] if queries else item.name
    grouped = retailers.by_tier(
        item.domain,
        region=region,
        category=item.category,
        per_tier=per_tier,
        include_international=settings.atelier_include_international,
    )

    out: list[dict] = []
    for tier in retailers.TIERS:
        for r in grouped.get(tier, []):
            local = retailers.is_local(r, region)
            out.append(
                {
                    "tier": tier,
                    "retailer": r.name,
                    "url": build_url(r.search, primary),
                    "kind": "search",
                    "product_name": None,
                    "price": None,
                    "note": r.note or None,
                    "ships": "local" if local else "overseas",
                    "region": r.regions[0] if r.regions else None,
                }
            )
    return out


REGION_NAMES = {"AU": "Australia", "NZ": "New Zealand", "UK": "the UK", "US": "the US"}


def _research_prompt(item: Item, region: str) -> str:
    settings = get_settings()
    attrs = ", ".join(f"{k}: {v}" for k, v in (item.attributes or {}).items())
    shops = retailers.by_tier(
        item.domain,
        region=region,
        category=item.category,
        per_tier=4,
        include_international=settings.atelier_include_international,
    )
    shop_lines = "\n".join(
        f"  {retailers.TIER_LABELS[t]}: "
        + ", ".join(
            r.name if retailers.is_local(r, region) else f"{r.name} (overseas)" for r in rs
        )
        for t, rs in shops.items()
        if rs
    )
    return f"""Find real, currently-listed products matching this:

  What it is: {item.name}
  Category: {item.category}
  Details: {attrs or "none recorded"}
  Described as: {item.description}
  Search terms to try: {", ".join(item.search_terms or [item.name])}
  Shopping region: {REGION_NAMES.get(region, region)}

Find up to two products in each of these price tiers:

  Splurge - the closest thing to the original, price no object
  Middle - a good version at a sensible price
  Budget - the cheapest thing that still gets the look
  Secondhand - vintage, resale or marketplace

Retailers worth trying (you are not limited to these):
{shop_lines}

Prefer retailers that ship within {REGION_NAMES.get(region, region)}, and quote
prices in the local currency where you can. Overseas options are welcome too -
this shopper is happy to order from abroad - but say so and flag the shipping
cost or import duty if the page shows it. Do not silently present an overseas
listing as if it were a local one.

For each product give the retailer, the exact product name, the full URL of its
product page, and the price as listed. Say whether it ships to
{REGION_NAMES.get(region, region)} - answer "unknown" rather than assuming.
Then say in one clause how it differs from the original. Skip any tier where you
cannot find something credible."""


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
        # Match the finding back to a known retailer so we can say whether it
        # ships locally; an unrecognised shop is reported as unknown, not local.
        known = next(
            (
                r
                for r in retailers.ALL
                if r.domain == item.domain and r.name.lower() == f.retailer.lower().strip()
            ),
            None,
        )
        if known:
            ships = "local" if retailers.is_local(known, region) else "overseas"
        else:
            # An unrecognised shop: trust the research only when it is definite.
            answer = (f.ships_to_region or "unknown").strip().lower()
            ships = {"yes": "local", "no": "overseas"}.get(answer, "unknown")
        out.append(
            {
                "tier": f.tier if f.tier in valid_tiers else "mid",
                "retailer": f.retailer,
                "url": f.url,
                "kind": "product",
                "product_name": f.product_name,
                "price": None if f.price.lower() == "unknown" else f.price,
                "note": f.note,
                "ships": ships,
                "region": known.regions[0] if known and known.regions else None,
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
