"""Thin wrapper over the Anthropic SDK.

Two entry points: `parse_with_images` for anything that must come back as a
validated object, and `research` for the one call that needs live web search.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from ..config import get_settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# Web search with dynamic filtering. Requires Opus 4.6+ / Sonnet 4.6+.
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 6}


class AnalysisError(RuntimeError):
    pass


def _client() -> anthropic.Anthropic:
    settings = get_settings()
    # Passing api_key=None lets the SDK resolve ANTHROPIC_API_KEY, an auth token,
    # or an `ant auth login` profile on its own.
    return anthropic.Anthropic(api_key=settings.anthropic_api_key or None, timeout=600.0)


def _image_block(path: Path) -> dict:
    media_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    if media_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        media_type = "image/jpeg"
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _check_refusal(response) -> None:
    # Always check stop_reason before reading content. Server-side `fallbacks`
    # would auto-retry a decline on another model, but that parameter lives on
    # the beta namespace and cannot be combined with the messages.parse helper,
    # so a refusal surfaces as an error here instead.
    if getattr(response, "stop_reason", None) == "refusal":
        detail = getattr(response, "stop_details", None)
        category = getattr(detail, "category", None) if detail else None
        raise AnalysisError(
            f"Claude declined this request (category: {category or 'unspecified'}). "
            "If this was one odd image, skip it and re-run the board."
        )


def parse_with_images(
    *,
    system: str,
    prompt: str,
    images: list[Path],
    output_format: type[T],
    max_tokens: int = 16000,
    effort: str | None = None,
) -> T:
    """One structured call over one or more images."""
    settings = get_settings()
    content: list[dict] = [_image_block(p) for p in images]
    content.append({"type": "text", "text": prompt})

    kwargs: dict = {
        "model": settings.atelier_model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content}],
        "output_format": output_format,
    }
    chosen_effort = effort or settings.atelier_effort
    if chosen_effort:
        kwargs["output_config"] = {"effort": chosen_effort}

    try:
        response = _client().messages.parse(**kwargs)
    except anthropic.NotFoundError as exc:
        raise AnalysisError(f"Model {settings.atelier_model!r} not available: {exc}") from exc
    except anthropic.RateLimitError as exc:
        raise AnalysisError("Rate limited by the Anthropic API - retry in a moment.") from exc
    except anthropic.AuthenticationError as exc:
        raise AnalysisError(
            "Anthropic rejected the credentials. Check ANTHROPIC_API_KEY in .env."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise AnalysisError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise AnalysisError(f"Could not reach the Anthropic API: {exc}") from exc

    _check_refusal(response)
    parsed = response.parsed_output
    if parsed is None:
        raise AnalysisError("Model returned no structured output.")
    return parsed


def research(*, system: str, prompt: str, max_tokens: int = 16000) -> str:
    """A web-search-backed call. Returns prose; structure it with a second pass.

    Structured output and server tools are kept in separate calls on purpose -
    searching and then shaping the result is more reliable than asking for both
    at once.
    """
    settings = get_settings()
    try:
        response = _client().messages.create(
            model=settings.atelier_model,
            max_tokens=max_tokens,
            system=system,
            tools=[WEB_SEARCH_TOOL],
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": settings.atelier_effort or "high"},
        )
    except anthropic.APIStatusError as exc:
        raise AnalysisError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise AnalysisError(f"Could not reach the Anthropic API: {exc}") from exc

    _check_refusal(response)

    parts: list[str] = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
        # A successful search result's content is a list; an error's is an object.
        elif block.type == "web_search_tool_result" and not isinstance(block.content, list):
            code = getattr(block.content, "error_code", "unknown")
            log.warning("web search failed: %s", code)
    return "\n".join(parts).strip()


def structure(*, system: str, prompt: str, output_format: type[T], max_tokens: int = 16000) -> T:
    """Text-only structured call - used to shape research output."""
    settings = get_settings()
    try:
        response = _client().messages.parse(
            model=settings.atelier_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=output_format,
        )
    except anthropic.APIStatusError as exc:
        raise AnalysisError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise AnalysisError(f"Could not reach the Anthropic API: {exc}") from exc

    _check_refusal(response)
    parsed = response.parsed_output
    if parsed is None:
        raise AnalysisError("Model returned no structured output.")
    return parsed
