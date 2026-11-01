"""The Pinterest client, with the HTTP layer stubbed.

These cover the things that silently lose pins or break a long sync: board
sections, idea pins, page caps, token expiry and rate limits. None of them call
Pinterest.
"""

from datetime import UTC, datetime, timedelta

import pytest

from atelier.ingest import pinterest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("ATELIER_DATA_DIR", str(tmp_path))
    from atelier.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------- scopes


def test_secret_boards_are_in_scope():
    """A board marked secret is invisible without the _secret scopes, and a
    half-finished house plan is very often secret."""
    assert "boards:read_secret" in pinterest.SCOPES
    assert "pins:read_secret" in pinterest.SCOPES


def test_no_write_scopes_are_requested():
    for scope in pinterest.SCOPES:
        assert ":read" in scope, f"{scope} is not a read-only scope"


# ---------------------------------------------------------------- images


def test_standard_pin_prefers_the_largest_image():
    pin = {
        "media": {
            "images": {
                "150x150": {"url": "https://x/small.jpg"},
                "1200x": {"url": "https://x/big.jpg"},
            }
        }
    }
    assert pinterest.pick_image_url(pin) == "https://x/big.jpg"


def test_idea_pin_cover_is_found():
    """Idea and video pins carry media.items, not media.images. Without this
    every idea pin on a board is skipped."""
    pin = {
        "media": {
            "media_type": "video",
            "items": [{"images": {"1200x": {"url": "https://x/cover.jpg"}}}],
        }
    }
    assert pinterest.pick_image_url(pin) == "https://x/cover.jpg"


def test_idea_pin_items_as_a_mapping():
    pin = {"media": {"items": {"0": {"cover_image_url": "https://x/c.jpg"}}}}
    assert pinterest.pick_image_url(pin) == "https://x/c.jpg"


def test_pin_with_no_image_returns_none():
    assert pinterest.pick_image_url({"media": {}}) is None
    assert pinterest.pick_image_url({}) is None


# ---------------------------------------------------------------- sections


def _fake_pages(monkeypatch, routes: dict[str, list[dict]]):
    """Stub _get so each path returns its items in one page."""

    def fake_get(path, params=None, **_):
        for prefix, items in routes.items():
            if path == prefix:
                return {"items": items, "bookmark": None}
        return {"items": [], "bookmark": None}

    monkeypatch.setattr(pinterest, "_get", fake_get)


def _pin(pid):
    return {"id": pid, "title": pid, "media": {"images": {"1200x": {"url": f"https://x/{pid}"}}}}


def test_pins_inside_sections_are_collected(monkeypatch):
    """The board-pins endpoint does not reliably include sectioned pins."""
    _fake_pages(
        monkeypatch,
        {
            "/boards/B/pins": [_pin("loose")],
            "/boards/B/sections": [{"id": "S1", "name": "Kitchen"}],
            "/boards/B/sections/S1/pins": [_pin("in-section")],
        },
    )
    result = pinterest.list_pins("B")
    ids = {p["external_id"] for p in result["pins"]}
    assert ids == {"loose", "in-section"}
    assert result["sections"] == ["Kitchen"]


def test_a_pin_in_both_listings_is_not_duplicated(monkeypatch):
    _fake_pages(
        monkeypatch,
        {
            "/boards/B/pins": [_pin("p1")],
            "/boards/B/sections": [{"id": "S1", "name": "Kitchen"}],
            "/boards/B/sections/S1/pins": [_pin("p1")],
        },
    )
    result = pinterest.list_pins("B")
    assert len(result["pins"]) == 1
    # ...and it keeps the section it was filed under.
    assert result["pins"][0]["section"] == "Kitchen"


def test_pins_without_an_image_are_counted_not_dropped_silently(monkeypatch):
    _fake_pages(
        monkeypatch,
        {
            "/boards/B/pins": [_pin("ok"), {"id": "bad", "media": {}}],
            "/boards/B/sections": [],
        },
    )
    result = pinterest.list_pins("B")
    assert len(result["pins"]) == 1
    assert result["skipped_no_image"] == 1


# ---------------------------------------------------------------- pagination


def test_truncation_is_reported_rather_than_silent(monkeypatch):
    """Hitting the page cap must be visible, or a board looks complete when
    it is not."""

    def endless(path, params=None, **_):
        return {"items": [_pin("p")], "bookmark": "more"}

    monkeypatch.setattr(pinterest, "_get", endless)
    items, truncated = pinterest._paginate("/boards/B/pins", max_pages=3)
    assert truncated is True
    assert len(items) == 3


def test_pagination_follows_bookmarks_to_the_end(monkeypatch):
    pages = [
        {"items": [_pin("a")], "bookmark": "b2"},
        {"items": [_pin("b")], "bookmark": None},
    ]
    calls = []

    def paged(path, params=None, **_):
        calls.append(params or {})
        return pages[len(calls) - 1]

    monkeypatch.setattr(pinterest, "_get", paged)
    items, truncated = pinterest._paginate("/boards/B/pins")
    assert [i["id"] for i in items] == ["a", "b"]
    assert truncated is False
    assert calls[1]["bookmark"] == "b2"


# ---------------------------------------------------------------- tokens


def test_token_near_expiry_counts_as_expired():
    soon = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    assert pinterest._expired({"expires_at": soon}) is True


def test_token_with_plenty_of_life_is_not_expired():
    later = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    assert pinterest._expired({"expires_at": later}) is False


def test_missing_or_unparseable_expiry_is_not_treated_as_expired():
    assert pinterest._expired({}) is False
    assert pinterest._expired({"expires_at": "not a date"}) is False


def test_save_token_records_an_absolute_expiry():
    pinterest.save_token({"access_token": "a", "expires_in": 3600})
    stored = pinterest.load_token()
    assert "expires_at" in stored
    assert pinterest._expired(stored) is False


def test_stored_token_is_not_world_readable():
    pinterest.save_token({"access_token": "secret", "expires_in": 60})
    mode = pinterest._token_path().stat().st_mode & 0o077
    assert mode == 0, "the access token file is readable by other users"


def test_disconnect_removes_the_token():
    pinterest.save_token({"access_token": "a"})
    assert pinterest.is_connected()
    pinterest.disconnect()
    assert not pinterest.is_connected()


# ---------------------------------------------------------------- rate limits


class FakeResponse:
    def __init__(self, headers):
        self.headers = headers


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ({"retry-after": "30"}, 30),
        # A pathological value must not hang the request for an hour.
        ({"retry-after": "99999"}, 120),
        ({"retry-after": "soon"}, None),
        ({}, None),
    ],
)
def test_retry_after_header_is_respected_and_capped(header, expected):
    assert pinterest._retry_after_seconds(FakeResponse(header)) == expected


def test_login_url_refuses_without_credentials():
    with pytest.raises(pinterest.PinterestError, match="not configured"):
        pinterest.login_url()


def test_calls_without_a_token_say_so_clearly():
    with pytest.raises(pinterest.PinterestNotConnected):
        pinterest._access_token()
