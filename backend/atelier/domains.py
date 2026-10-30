"""The two domains Atelier knows about, and the vocabulary each one uses.

Everything downstream (vision prompts, retailer tiers, UI labels) keys off this
module, so adding a third domain (garden, say) means adding one entry here plus
a retailer block in shopping/retailers.py.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Domain:
    key: str
    label: str
    # What a single buyable thing is called in this domain.
    unit: str
    # Categories the vision model is asked to sort items into. Keeping this list
    # explicit stops the model inventing a new taxonomy on every call, which is
    # what makes grouping across boards possible.
    categories: list[str]
    # The attributes worth pulling out per item - these become the search query
    # and the "why this matches" explanation.
    attributes: list[str]
    # Extra guidance folded into the vision system prompt.
    notes: str = ""
    aesthetic_axes: list[str] = field(default_factory=list)


INTERIOR = Domain(
    key="interior",
    label="Interiors",
    unit="piece",
    categories=[
        "lighting-ceiling",
        "lighting-floor",
        "lighting-table",
        "lighting-wall",
        "seating-sofa",
        "seating-chair",
        "seating-stool",
        "table-dining",
        "table-coffee",
        "table-side",
        "storage-shelving",
        "storage-cabinet",
        "bed",
        "rug",
        "wallpaper",
        "paint-colour",
        "window-treatment",
        "textile-cushion",
        "textile-throw",
        "textile-bedding",
        "mirror",
        "artwork",
        "ceramics-vessel",
        "tile",
        "hardware-fixture",
        "plant",
        "decor-object",
        "architectural-detail",
    ],
    attributes=[
        "material",
        "finish",
        "colour",
        "silhouette",
        "era_or_style",
        "scale",
    ],
    notes=(
        "Distinguish a buyable product from an architectural feature: cornicing, a "
        "bay window or a plaster finish is architectural-detail, not something to "
        "shop for. For paint-colour, name the colour precisely enough to be matched "
        "(hue, value, undertone) rather than guessing a brand's swatch name."
    ),
    aesthetic_axes=[
        "warm vs cool",
        "minimal vs layered",
        "soft vs structured",
        "period vs contemporary",
        "matte vs reflective",
    ],
)

WARDROBE = Domain(
    key="wardrobe",
    label="Wardrobe",
    unit="garment",
    categories=[
        "outerwear-coat",
        "outerwear-jacket",
        "knitwear",
        "top-shirt",
        "top-tee",
        "top-blouse",
        "dress",
        "skirt",
        "trousers",
        "jeans",
        "shorts",
        "suiting",
        "shoes-flat",
        "shoes-heel",
        "shoes-boot",
        "shoes-trainer",
        "bag",
        "belt",
        "jewellery",
        "scarf",
        "hat",
        "eyewear",
        "swimwear",
        "loungewear",
    ],
    attributes=[
        "fabric",
        "colour",
        "cut_or_fit",
        "length",
        "detailing",
        "formality",
    ],
    notes=(
        "Describe cut and proportion precisely - that is what makes a garment "
        "findable and what makes a cheaper version either work or fail. Note when a "
        "look depends on fabric weight or drape rather than on the design itself."
    ),
    aesthetic_axes=[
        "tailored vs relaxed",
        "neutral vs saturated",
        "classic vs directional",
        "covered vs exposed",
        "matte vs lustrous",
    ],
)

DOMAINS = {d.key: d for d in (INTERIOR, WARDROBE)}


def get_domain(key: str) -> Domain:
    try:
        return DOMAINS[key]
    except KeyError:
        raise ValueError(f"Unknown domain {key!r}; expected one of {sorted(DOMAINS)}") from None
