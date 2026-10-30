"""ORM models.

One schema serves both domains; `domain` ("interior" | "wardrobe") is carried on
boards and items so a single database can hold a future-home board and an
autumn-wardrobe board without them bleeding into each other.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Board(Base):
    """A Pinterest board, or a local folder of images treated as one."""

    __tablename__ = "boards"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_board_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    domain: Mapped[str] = mapped_column(String(32), default="interior", index=True)
    source: Mapped[str] = mapped_column(String(32))  # pinterest | local
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pins: Mapped[list[Pin]] = relationship(
        back_populates="board", cascade="all, delete-orphan", lazy="selectin"
    )
    profiles: Mapped[list[StyleProfile]] = relationship(
        back_populates="board", cascade="all, delete-orphan"
    )


class Pin(Base):
    """One saved image."""

    __tablename__ = "pins"

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Where the pin pointed (often the original product page - a useful hint).
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Path relative to the configured image dir.
    image_file: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Whole-image read: the scene, mood, and what makes it work.
    scene_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    board: Mapped[Board] = relationship(back_populates="pins")
    items: Mapped[list[Item]] = relationship(
        back_populates="pin", cascade="all, delete-orphan", lazy="selectin"
    )


class Item(Base):
    """A single buyable thing identified inside a pin."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id", ondelete="CASCADE"), index=True)
    domain: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    # Domain-specific attributes (material/finish/colour, or fabric/cut/length).
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    # What to type into a shop's search box.
    search_terms: Mapped[list] = mapped_column(JSON, default=list)
    # Rough price band the original looks like it sits in.
    est_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # Normalised [x, y, w, h] in 0-1 so the UI can box it on the image.
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_hero: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pin: Mapped[Pin] = relationship(back_populates="items")
    sources: Mapped[list[Source]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )

    # Convenience for the API: an item is always shown beside the image it came from.
    @property
    def pin_image_file(self) -> str:
        return self.pin.image_file

    @property
    def board_id(self) -> int:
        return self.pin.board_id


class Source(Base):
    """A place to buy an item, at a price tier."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    tier: Mapped[str] = mapped_column(String(32), index=True)  # splurge|mid|budget|secondhand
    retailer: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(Text)
    # kind="search" is a deep link into a shop's search results (always valid).
    # kind="product" is a specific product found via live web search.
    kind: Mapped[str] = mapped_column(String(16), default="search")
    # "local" = ships within your region; "overseas" = ships to you from abroad.
    ships: Mapped[str] = mapped_column(String(16), default="local")
    # The retailer's home region, for display ("AU", "US", ...).
    region: Mapped[str | None] = mapped_column(String(8), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    item: Mapped[Item] = relationship(back_populates="sources")


class StyleProfile(Base):
    """The read on a whole board: palette, materials, the throughline."""

    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), index=True)
    domain: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    # [{name, hex, role}]
    palette: Mapped[list] = mapped_column(JSON, default=list)
    materials: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    # Where the board sits on each of the domain's aesthetic axes.
    axes: Mapped[dict] = mapped_column(JSON, default=dict)
    # Honest friction: what in the board fights with the rest of it.
    tensions: Mapped[list] = mapped_column(JSON, default=list)
    pin_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    board: Mapped[Board] = relationship(back_populates="profiles")


class Space(Base):
    """A room (or a wardrobe brief) you are designing."""

    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(32), default="interior")
    kind: Mapped[str | None] = mapped_column(String(64), nullable=True)  # living room, bedroom...
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plans: Mapped[list[FloorPlan]] = relationship(
        back_populates="space", cascade="all, delete-orphan", lazy="selectin"
    )


class FloorPlan(Base):
    """An uploaded floor plan or room photo, plus what Claude read off it."""

    __tablename__ = "floor_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    image_file: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(32), default="floorplan")  # floorplan | photo
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    space: Mapped[Space] = relationship(back_populates="plans")


class Plan(Base):
    """A generated design plan: a board's style applied to a specific space."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    board_id: Mapped[int | None] = mapped_column(
        ForeignKey("boards.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300))
    narrative: Mapped[str] = mapped_column(Text)
    # [{zone, intent, pieces: [...], notes}]
    zones: Mapped[list] = mapped_column(JSON, default=list)
    # [{category, why, priority, budget_band}]
    shopping_list: Mapped[list] = mapped_column(JSON, default=list)
    cautions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
