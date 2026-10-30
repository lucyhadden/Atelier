"""Query building and sourcing - the parts that must never invent a link."""

import pytest

from atelier.models import Board, Item, Pin
from atelier.shopping import retailers, sourcing
from atelier.shopping.query import build_url, search_queries
from atelier.vision.client import AnalysisError
from atelier.vision.schemas import ProductFind, ProductFindings


@pytest.fixture
def item(db):
    board = Board(name="b", domain="interior", source="local", external_id="/tmp/b")
    db.add(board)
    db.flush()
    pin = Pin(board_id=board.id, image_file="x.jpg")
    db.add(pin)
    db.flush()
    row = Item(
        pin_id=pin.id,
        domain="interior",
        category="lighting-table",
        name="ribbed opal glass table lamp",
        description="desc",
        attributes={"material": "opal glass", "finish": "brass"},
        search_terms=["gorgeous ribbed opal glass lamp"],
        confidence=0.8,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_search_queries_strip_mood_words(item):
    queries = search_queries(item)
    assert "gorgeous" not in queries[0], "mood words return nothing in a shop's search box"
    assert "ribbed opal glass lamp" in queries[0]


def test_search_queries_always_end_with_a_plain_noun(item):
    assert "table lamp" in search_queries(item)[-1]


def test_build_url_encodes_both_shapes():
    assert build_url("https://x.com/s?q={q}", "wool coat") == "https://x.com/s?q=wool+coat"
    # Path-segment shops take a slug, not a query string.
    assert build_url("https://x.com/search/{q}", "wool coat") == "https://x.com/search/wool-coat"


def test_every_tier_has_somewhere_to_look_in_every_region():
    for domain in ("interior", "wardrobe"):
        for region in retailers.REGIONS:
            grouped = retailers.by_tier(domain, region=region)
            for tier in retailers.TIERS:
                assert grouped[tier], f"{domain}/{region} has no {tier} retailer"


def test_region_is_a_preference_not_a_filter():
    """An AU shopper still sees overseas sellers, but after the local ones."""
    rows = retailers.by_tier("interior", region="AU")["splurge"]
    assert rows, "AU has no splurge retailers"
    locals_ = [r for r in rows if retailers.is_local(r, "AU")]
    assert locals_, "AU splurge tier has no Australian option"
    # Every local option precedes every overseas one.
    flags = [retailers.is_local(r, "AU") for r in rows]
    assert flags == sorted(flags, reverse=True), "overseas sellers jumped the queue"


def test_international_can_be_turned_off():
    with_intl = retailers.by_tier("wardrobe", region="AU", include_international=True)
    without = retailers.by_tier("wardrobe", region="AU", include_international=False)
    assert sum(len(v) for v in with_intl.values()) >= sum(len(v) for v in without.values())
    for rows in without.values():
        for r in rows:
            assert retailers.is_local(r, "AU"), f"{r.name} is not an AU seller"


def test_turning_international_on_never_displaces_a_local_seller():
    off = retailers.by_tier("interior", region="AU", include_international=False)
    on = retailers.by_tier("interior", region="AU", include_international=True)
    for tier in retailers.TIERS:
        local_off = {r.name for r in off[tier]}
        local_on = {r.name for r in on[tier] if retailers.is_local(r, "AU")}
        assert local_off <= local_on, f"{tier}: a local seller was pushed out"


def test_the_retailers_lucy_asked_for_are_present():
    """Freedom, Myer, David Jones and IKEA must be reachable for an AU shopper."""
    names = {r.name for r in retailers.for_domain("interior", region="AU")}
    for expected in ("Freedom", "Myer", "David Jones", "IKEA AU"):
        assert expected in names, f"{expected} missing from the AU interior set"


def test_every_search_template_has_a_query_placeholder():
    for r in retailers.ALL:
        assert "{q}" in r.search, f"{r.name} has no query placeholder"


def test_narrow_category_still_fills_every_tier():
    """A category hint must never leave a tier empty."""
    grouped = retailers.by_tier("interior", region="US", category="paint-colour")
    for tier in retailers.TIERS:
        assert grouped[tier]


def test_search_sources_cover_all_four_tiers(item):
    tiers = {s["tier"] for s in sourcing.search_sources(item)}
    assert tiers == set(retailers.TIERS)


def test_search_sources_record_where_a_seller_ships_from(item):
    rows = sourcing.search_sources(item, region="AU")
    assert rows
    assert all(r["ships"] in ("local", "overseas") for r in rows)
    assert any(r["ships"] == "local" for r in rows), "no Australian seller offered"
    for r in rows:
        if r["ships"] == "local":
            assert r["region"] == "AU"


def test_source_item_drops_findings_without_a_real_url(db, item, monkeypatch):
    """A product with an unusable URL is dropped, not stored as a dead link."""
    monkeypatch.setattr(
        sourcing,
        "product_sources",
        lambda *a, **k: (
            [
                {
                    "tier": "mid",
                    "retailer": "Real Shop",
                    "url": "https://realshop.com/lamp",
                    "kind": "product",
                    "product_name": "Opal lamp",
                    "price": "$180",
                    "note": "close",
                }
            ],
            "",
        ),
    )
    sourcing.source_item(db, item, use_web_search=True)
    products = [s for s in item.sources if s.kind == "product"]
    assert len(products) == 1
    assert all(s.url.startswith("http") for s in item.sources)


def test_web_search_failure_still_leaves_search_links(db, item, monkeypatch):
    """A failed web search must not cost the user their search links."""

    def boom(*a, **k):
        raise AnalysisError("rate limited")

    monkeypatch.setattr(sourcing, "product_sources", boom)
    result = sourcing.source_item(db, item, use_web_search=True)

    assert result["web_search_error"] == "rate limited"
    assert result["products"] == 0
    assert len(item.sources) > 0
    assert {s.tier for s in item.sources} == set(retailers.TIERS)


def test_product_sources_rejects_relative_urls(item, monkeypatch):
    from atelier.shopping import sourcing as mod

    monkeypatch.setattr(mod, "research", lambda **_: "found some things")
    monkeypatch.setattr(
        mod,
        "structure",
        lambda **_: ProductFindings(
            findings=[
                ProductFind(
                    retailer="Shop",
                    product_name="Lamp",
                    url="/products/lamp",
                    price="$10",
                    tier="mid",
                    note="n",
                    ships_to_region="yes",
                ),
                ProductFind(
                    retailer="Shop",
                    product_name="Good Lamp",
                    url="https://shop.com/lamp",
                    price="unknown",
                    tier="mid",
                    note="n",
                    ships_to_region="unknown",
                ),
            ],
            caveat="",
        ),
    )
    rows, _ = mod.product_sources(item)
    assert len(rows) == 1
    assert rows[0]["url"] == "https://shop.com/lamp"
    assert rows[0]["price"] is None, "'unknown' must not be shown as a price"
    assert rows[0]["ships"] == "unknown", "an unverified shop must not be called local"


def test_unrecognised_shop_is_only_called_local_when_research_is_definite(item, monkeypatch):
    from atelier.shopping import sourcing as mod

    monkeypatch.setattr(mod, "research", lambda **_: "found")

    def finding(answer):
        return ProductFindings(
            findings=[
                ProductFind(
                    retailer="Some Local Shop",
                    product_name="Lamp",
                    url="https://local.example/lamp",
                    price="$99",
                    tier="mid",
                    note="n",
                    ships_to_region=answer,
                )
            ],
            caveat="",
        )

    for answer, expected in (("yes", "local"), ("no", "overseas"), ("maybe", "unknown")):
        monkeypatch.setattr(mod, "structure", lambda answer=answer, **_: finding(answer))
        rows, _ = mod.product_sources(item, region="AU")
        assert rows[0]["ships"] == expected, f"{answer!r} -> {rows[0]['ships']!r}"


def test_sourcing_is_idempotent(db, item, monkeypatch):
    monkeypatch.setattr(sourcing, "product_sources", lambda *a, **k: ([], ""))
    first = sourcing.source_item(db, item, use_web_search=False)
    second = sourcing.source_item(db, item, use_web_search=False)
    assert first["count"] == second["count"]
    assert len(item.sources) == second["count"]
