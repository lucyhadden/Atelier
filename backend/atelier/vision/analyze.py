"""Orchestration: turn stored images into stored analysis."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..config import get_settings
from ..domains import get_domain
from ..models import Board, FloorPlan, Item, Pin, Plan, Space, StyleProfile
from . import prompts
from .client import AnalysisError, parse_with_images
from .schemas import DesignPlan, FloorPlanRead, PinAnalysis, StyleRead

log = logging.getLogger(__name__)

# How many board images to send in one style read. More images give a better
# read; this is the point where cost stops buying much.
STYLE_SAMPLE_SIZE = 24


def _image_path(pin_or_plan) -> object:
    return get_settings().image_dir / pin_or_plan.image_file


def analyze_pin(db: Session, pin: Pin, *, force: bool = False) -> Pin:
    """Catalogue one pin into Items."""
    if pin.analyzed_at and not force:
        return pin

    domain = get_domain(pin.board.domain)
    path = _image_path(pin)
    if not path.exists():
        raise AnalysisError(f"Image missing on disk: {pin.image_file}")

    hint = ""
    if pin.title or pin.note:
        hint = (
            "\n\nThe person saved this with the caption: "
            f"{(pin.title or '') + ' ' + (pin.note or '')}".strip()
            + "\nUse it only as a hint; trust the image over the caption."
        )

    result: PinAnalysis = parse_with_images(
        system=prompts.pin_system(domain),
        prompt=f"Catalogue this image.{hint}",
        images=[path],
        output_format=PinAnalysis,
    )

    # Replace prior items for this pin so re-running is idempotent.
    for existing in list(pin.items):
        db.delete(existing)
    db.flush()

    pin.scene_summary = result.scene_summary
    valid = set(domain.categories)
    for detected in result.items:
        category = detected.category if detected.category in valid else "decor-object"
        db.add(
            Item(
                pin_id=pin.id,
                domain=domain.key,
                category=category,
                name=detected.name,
                description=detected.description,
                attributes={a.key: a.value for a in detected.attributes},
                search_terms=detected.search_terms,
                est_tier=detected.est_tier,
                confidence=detected.confidence,
                bbox=detected.bbox,
                is_hero=detected.is_hero,
            )
        )
    pin.analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(pin)
    return pin


def analyze_board(db: Session, board: Board, *, force: bool = False) -> dict:
    """Catalogue every unanalysed pin on a board. Returns a per-pin report."""
    done, skipped, failed = 0, 0, []
    for pin in board.pins:
        if pin.analyzed_at and not force:
            skipped += 1
            continue
        try:
            analyze_pin(db, pin, force=force)
            done += 1
        except AnalysisError as exc:
            log.warning("pin %s failed: %s", pin.id, exc)
            failed.append({"pin_id": pin.id, "error": str(exc)})
    return {"analyzed": done, "skipped": skipped, "failed": failed}


def read_style(db: Session, board: Board) -> StyleProfile:
    """Read the whole board at once to find its throughline."""
    domain = get_domain(board.domain)
    paths = []
    # Prefer pins that turned out to have hero items - they carry the most signal.
    ordered = sorted(board.pins, key=lambda p: (not any(i.is_hero for i in p.items), p.id))
    for pin in ordered[:STYLE_SAMPLE_SIZE]:
        p = _image_path(pin)
        if p.exists():
            paths.append(p)

    if not paths:
        raise AnalysisError("No images available on this board to read.")

    catalogued = [
        f"- {item.name} ({item.category})"
        for pin in board.pins
        for item in pin.items
        if item.is_hero
    ][:40]
    context = ""
    if catalogued:
        context = "\n\nAlready catalogued as standout pieces:\n" + "\n".join(catalogued)

    result: StyleRead = parse_with_images(
        system=prompts.style_system(domain),
        prompt=(
            f'Read this collection of {len(paths)} images saved to a board called '
            f'"{board.name}".{context}'
        ),
        images=paths,
        output_format=StyleRead,
        max_tokens=16000,
    )

    profile = StyleProfile(
        board_id=board.id,
        domain=domain.key,
        summary=result.summary,
        palette=[c.model_dump() for c in result.palette],
        materials=result.materials,
        keywords=result.keywords,
        axes=result.axes,
        tensions=result.tensions,
        pin_count=len(paths),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def read_floorplan(db: Session, plan: FloorPlan) -> FloorPlan:
    path = _image_path(plan)
    if not path.exists():
        raise AnalysisError(f"Image missing on disk: {plan.image_file}")

    result: FloorPlanRead = parse_with_images(
        system=prompts.floorplan_system(),
        prompt=(
            f"Read this {'floor plan' if plan.kind == 'floorplan' else 'room photograph'}"
            + (f' labelled "{plan.label}".' if plan.label else ".")
        ),
        images=[path],
        output_format=FloorPlanRead,
    )
    plan.analysis = result.model_dump()
    plan.analyzed_at = datetime.now(UTC)
    db.commit()
    db.refresh(plan)
    return plan


def build_plan(db: Session, space: Space, board: Board | None, brief: str = "") -> Plan:
    """The payoff: a board's style applied to a specific space."""
    domain = get_domain(space.domain)

    parts: list[str] = [f"The space: {space.name}" + (f" ({space.kind})" if space.kind else "")]
    if space.notes:
        parts.append(f"What they want from it: {space.notes}")
    if brief:
        parts.append(f"Additional brief: {brief}")

    for fp in space.plans:
        if fp.analysis:
            a = fp.analysis
            parts.append(
                f"\nFrom the uploaded {fp.kind} ({fp.label or 'unlabelled'}):\n"
                f"  Summary: {a.get('summary')}\n"
                f"  Scale legible: {a.get('scale_confidence')}\n"
                f"  Fixed features: {'; '.join(a.get('fixed_features') or []) or 'none noted'}\n"
                f"  Constraints: {'; '.join(a.get('constraints') or []) or 'none noted'}\n"
                f"  Circulation: {'; '.join(a.get('circulation') or []) or 'not noted'}"
            )

    images = []
    if board is not None:
        profile = (
            db.query(StyleProfile)
            .filter(StyleProfile.board_id == board.id)
            .order_by(StyleProfile.created_at.desc())
            .first()
        )
        if profile:
            parts.append(
                f'\nThe saved aesthetic, from the board "{board.name}":\n'
                f"  {profile.summary}\n"
                f"  Palette: {', '.join(c['name'] for c in profile.palette)}\n"
                f"  Materials: {', '.join(profile.materials)}\n"
                f"  Keywords: {', '.join(profile.keywords)}\n"
                f"  Known tensions: {'; '.join(profile.tensions) or 'none'}"
            )
        heroes = [
            f"- {i.name} ({i.category}): {i.description}"
            for p in board.pins
            for i in p.items
            if i.is_hero
        ][:25]
        if heroes:
            parts.append("\nStandout pieces they saved:\n" + "\n".join(heroes))
        # A few reference images ground the plan in the actual look.
        ordered = sorted(board.pins, key=lambda p: (not any(i.is_hero for i in p.items), p.id))
        for pin in ordered[:8]:
            path = _image_path(pin)
            if path.exists():
                images.append(path)

    if not images:
        # Fall back to the floor plan images so the call still has something to see.
        for fp in space.plans:
            path = _image_path(fp)
            if path.exists():
                images.append(path)
    if not images:
        raise AnalysisError("Nothing to look at - add a board or a floor plan first.")

    result: DesignPlan = parse_with_images(
        system=prompts.plan_system(domain),
        prompt="\n".join(parts) + "\n\nWrite the plan.",
        images=images,
        output_format=DesignPlan,
        max_tokens=16000,
    )

    plan = Plan(
        space_id=space.id,
        board_id=board.id if board else None,
        title=result.title,
        narrative=result.narrative,
        zones=[z.model_dump() for z in result.zones],
        shopping_list=[i.model_dump() for i in result.shopping_list],
        cautions=result.cautions,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
