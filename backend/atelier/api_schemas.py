"""Response/request shapes for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceOut(ORMModel):
    id: int
    tier: str
    retailer: str
    url: str
    kind: str
    ships: str = "local"
    region: str | None = None
    product_name: str | None = None
    price: str | None = None
    note: str | None = None


class ItemOut(ORMModel):
    id: int
    pin_id: int
    pin_image_file: str = ""
    board_id: int = 0
    domain: str
    category: str
    name: str
    description: str
    attributes: dict
    search_terms: list
    est_tier: str | None = None
    confidence: float
    bbox: list | None = None
    is_hero: bool
    sources: list[SourceOut] = []


class PinOut(ORMModel):
    id: int
    board_id: int
    title: str | None = None
    note: str | None = None
    link: str | None = None
    image_file: str
    scene_summary: str | None = None
    analyzed_at: datetime | None = None
    items: list[ItemOut] = []


class BoardOut(ORMModel):
    id: int
    name: str
    domain: str
    source: str
    external_id: str | None = None
    description: str | None = None
    synced_at: datetime | None = None
    pin_count: int = 0
    analyzed_count: int = 0
    item_count: int = 0


class StyleProfileOut(ORMModel):
    id: int
    board_id: int
    domain: str
    summary: str
    palette: list
    materials: list
    keywords: list
    axes: dict
    tensions: list
    pin_count: int
    created_at: datetime


class FloorPlanOut(ORMModel):
    id: int
    space_id: int
    image_file: str
    kind: str
    label: str | None = None
    analysis: dict | None = None
    analyzed_at: datetime | None = None


class SpaceOut(ORMModel):
    id: int
    name: str
    domain: str
    kind: str | None = None
    notes: str | None = None
    plans: list[FloorPlanOut] = []


class PlanOut(ORMModel):
    id: int
    space_id: int
    board_id: int | None = None
    title: str
    narrative: str
    zones: list
    shopping_list: list
    cautions: list
    created_at: datetime


# ---- requests ----


class ImportFolderIn(BaseModel):
    path: str = Field(description="Absolute path to a folder of images")
    domain: str = "interior"
    board_name: str | None = None
    is_pinterest_export: bool = False


class SyncBoardIn(BaseModel):
    external_id: str
    domain: str = "interior"
    name: str | None = None


class SpaceIn(BaseModel):
    name: str
    domain: str = "interior"
    kind: str | None = None
    notes: str | None = None


class BuildPlanIn(BaseModel):
    board_id: int | None = None
    brief: str = ""


class SourceItemIn(BaseModel):
    use_web_search: bool | None = None
    region: str | None = None


class StatusOut(BaseModel):
    claude_configured: bool
    model: str
    effort: str
    region: str
    include_international: bool
    web_search_enabled: bool
    pinterest_configured: bool
    pinterest_connected: bool
    board_count: int
    item_count: int
