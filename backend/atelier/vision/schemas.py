"""Pydantic models that Claude's structured output is validated against.

These are the contract for every vision call - the model is constrained to this
shape, so downstream code never parses prose.
"""

from pydantic import BaseModel, Field


class ItemAttribute(BaseModel):
    key: str = Field(description="One of the domain's attribute names")
    value: str


class DetectedItem(BaseModel):
    name: str = Field(description="Short specific name, e.g. 'ribbed opal glass table lamp'")
    category: str = Field(description="Exactly one category from the provided list")
    description: str = Field(
        description="Two sentences: what it is, and what makes it work in this image"
    )
    attributes: list[ItemAttribute]
    search_terms: list[str] = Field(
        description="2-4 phrases to type into a shop's search box, most specific first"
    )
    est_tier: str = Field(description="One of: splurge, mid, budget, secondhand, unclear")
    confidence: float = Field(ge=0.0, le=1.0)
    is_hero: bool = Field(description="True if this is the item the image is really about")
    bbox: list[float] | None = Field(
        default=None,
        description="Normalised [x, y, width, height] in 0-1 from the top-left, or null",
    )


class PinAnalysis(BaseModel):
    scene_summary: str = Field(description="What this image is and why it reads the way it does")
    items: list[DetectedItem]


class PaletteColour(BaseModel):
    name: str
    hex: str = Field(description="Approximate hex, e.g. '#C8B9A6'")
    role: str = Field(description="e.g. dominant, secondary, accent, grounding")


class StyleRead(BaseModel):
    summary: str = Field(description="3-5 sentences naming the throughline of this board")
    palette: list[PaletteColour]
    materials: list[str]
    keywords: list[str] = Field(description="6-12 terms useful for shopping and search")
    axes: dict[str, str] = Field(
        description="For each supplied aesthetic axis, where this board sits and why"
    )
    tensions: list[str] = Field(
        description="Genuine conflicts in the board - things that will not sit together. "
        "Empty list if the board is coherent."
    )


class PlanZone(BaseModel):
    zone: str
    intent: str
    pieces: list[str]
    notes: str


class PlanItem(BaseModel):
    category: str
    what: str
    why: str
    priority: str = Field(description="One of: first, then, later")
    budget_band: str = Field(description="Where to spend vs save: splurge, mid, budget")


class DesignPlan(BaseModel):
    title: str
    narrative: str = Field(description="How the board's style lands in this specific space")
    zones: list[PlanZone]
    shopping_list: list[PlanItem]
    cautions: list[str] = Field(
        description="Where the board's look will fight this space's constraints"
    )


class FloorPlanRead(BaseModel):
    summary: str
    rooms: list[dict] = Field(
        description="[{name, approx_dimensions, approx_area, notes}] - say 'unclear' "
        "for anything not legible rather than estimating"
    )
    fixed_features: list[str] = Field(
        description="Windows, doors, radiators, chimney breasts, built-ins, awkward angles"
    )
    circulation: list[str] = Field(description="How people will move through the space")
    opportunities: list[str]
    constraints: list[str]
    scale_confidence: str = Field(
        description="high / medium / low / none - whether dimensions were actually legible"
    )


class ProductFind(BaseModel):
    retailer: str
    product_name: str
    url: str
    price: str = Field(description="As shown, with currency. 'unknown' if not visible.")
    tier: str = Field(description="splurge, mid, budget or secondhand")
    note: str = Field(description="How close this is to the original, and where it differs")
    ships_to_region: str = Field(
        description="Does this seller ship to the shopper's region? 'yes' if the site "
        "says so or it is a local seller, 'no' if it says it does not, 'unknown' if you "
        "could not tell. Never guess 'yes'."
    )


class ProductFindings(BaseModel):
    findings: list[ProductFind]
    caveat: str = Field(
        description="What you could not verify - stock, exact price, or whether it is the "
        "same product. Empty string if everything was confirmed on the page."
    )
