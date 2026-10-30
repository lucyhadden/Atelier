"""The analysis orchestration, with the model's answer stubbed out.

These do not call Claude. They check the part we own: that a model response
lands in the database correctly, that re-running replaces rather than
duplicates, and that an unknown category cannot corrupt the taxonomy.
"""

import pytest

from atelier.models import Board, Pin
from atelier.vision import analyze
from atelier.vision.schemas import DetectedItem, ItemAttribute, PinAnalysis


def make_analysis(*, category="lighting-table", name="brass table lamp"):
    return PinAnalysis(
        scene_summary="A warm corner with a lamp on an oak table.",
        items=[
            DetectedItem(
                name=name,
                category=category,
                description="A small brass lamp. It carries the warmth of the corner.",
                attributes=[
                    ItemAttribute(key="material", value="brass"),
                    ItemAttribute(key="finish", value="brushed"),
                ],
                search_terms=["brass table lamp", "mushroom lamp"],
                est_tier="mid",
                confidence=0.82,
                is_hero=True,
                bbox=[0.1, 0.2, 0.3, 0.4],
            )
        ],
    )


@pytest.fixture
def board_with_pin(db, sample_image):
    board = Board(name="Future home", domain="interior", source="local", external_id="/tmp/x")
    db.add(board)
    db.flush()
    pin = Pin(board_id=board.id, title="lamp", image_file=sample_image)
    db.add(pin)
    db.commit()
    db.refresh(pin)
    return board, pin


def test_analyze_pin_writes_items(db, board_with_pin, monkeypatch):
    _, pin = board_with_pin
    monkeypatch.setattr(analyze, "parse_with_images", lambda **_: make_analysis())

    analyze.analyze_pin(db, pin)

    assert pin.analyzed_at is not None
    assert pin.scene_summary.startswith("A warm corner")
    assert len(pin.items) == 1
    item = pin.items[0]
    assert item.name == "brass table lamp"
    assert item.category == "lighting-table"
    assert item.attributes == {"material": "brass", "finish": "brushed"}
    assert item.is_hero is True
    assert item.bbox == [0.1, 0.2, 0.3, 0.4]


def test_reanalysis_replaces_rather_than_duplicates(db, board_with_pin, monkeypatch):
    _, pin = board_with_pin
    monkeypatch.setattr(analyze, "parse_with_images", lambda **_: make_analysis())
    analyze.analyze_pin(db, pin)

    monkeypatch.setattr(
        analyze, "parse_with_images", lambda **_: make_analysis(name="opal glass lamp")
    )
    analyze.analyze_pin(db, pin, force=True)

    assert len(pin.items) == 1, "re-reading a pin must not stack duplicate items"
    assert pin.items[0].name == "opal glass lamp"


def test_analyze_pin_skips_already_done_unless_forced(db, board_with_pin, monkeypatch):
    _, pin = board_with_pin
    calls = []

    def fake(**_):
        calls.append(1)
        return make_analysis()

    monkeypatch.setattr(analyze, "parse_with_images", fake)
    analyze.analyze_pin(db, pin)
    analyze.analyze_pin(db, pin)
    assert len(calls) == 1


def test_unknown_category_is_coerced_not_stored(db, board_with_pin, monkeypatch):
    """A hallucinated category must not silently enter the taxonomy."""
    _, pin = board_with_pin
    monkeypatch.setattr(
        analyze, "parse_with_images", lambda **_: make_analysis(category="vibe-object")
    )
    analyze.analyze_pin(db, pin)
    assert pin.items[0].category == "decor-object"


def test_board_analysis_reports_failures_without_aborting(db, board_with_pin, monkeypatch):
    from atelier.vision.client import AnalysisError

    board, pin = board_with_pin
    second = Pin(board_id=board.id, title="two", image_file=pin.image_file)
    db.add(second)
    db.commit()

    seen = []

    def flaky(**_):
        seen.append(1)
        if len(seen) == 1:
            raise AnalysisError("model declined")
        return make_analysis()

    monkeypatch.setattr(analyze, "parse_with_images", flaky)
    report = analyze.analyze_board(db, board)

    assert report["analyzed"] == 1
    assert len(report["failed"]) == 1
    assert "model declined" in report["failed"][0]["error"]
