"""Turn an Item into search strings a shop will actually match."""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ..models import Item

# Words that read well in a description but return nothing in a search box.
NOISE = {
    "beautiful", "gorgeous", "stunning", "lovely", "perfect", "elegant",
    "timeless", "effortless", "curated", "elevated", "statement", "chic",
    "cosy", "cozy", "warm", "inviting", "serene", "moody", "vibe", "aesthetic",
    "ish", "very", "quite", "slightly", "subtle", "understated",
}

CATEGORY_NOUNS = {
    "lighting-ceiling": "pendant light",
    "lighting-floor": "floor lamp",
    "lighting-table": "table lamp",
    "lighting-wall": "wall sconce",
    "seating-sofa": "sofa",
    "seating-chair": "armchair",
    "seating-stool": "stool",
    "table-dining": "dining table",
    "table-coffee": "coffee table",
    "table-side": "side table",
    "storage-shelving": "shelving",
    "storage-cabinet": "cabinet",
    "bed": "bed frame",
    "rug": "rug",
    "wallpaper": "wallpaper",
    "paint-colour": "paint",
    "window-treatment": "curtains",
    "textile-cushion": "cushion cover",
    "textile-throw": "throw blanket",
    "textile-bedding": "bedding",
    "mirror": "mirror",
    "artwork": "art print",
    "ceramics-vessel": "vase",
    "tile": "tile",
    "hardware-fixture": "hardware",
    "plant": "plant pot",
    "decor-object": "decorative object",
    "outerwear-coat": "coat",
    "outerwear-jacket": "jacket",
    "knitwear": "knit jumper",
    "top-shirt": "shirt",
    "top-tee": "t-shirt",
    "top-blouse": "blouse",
    "dress": "dress",
    "skirt": "skirt",
    "trousers": "trousers",
    "jeans": "jeans",
    "shorts": "shorts",
    "suiting": "blazer",
    "shoes-flat": "flat shoes",
    "shoes-heel": "heels",
    "shoes-boot": "boots",
    "shoes-trainer": "trainers",
    "bag": "bag",
    "belt": "belt",
    "jewellery": "jewellery",
    "scarf": "scarf",
    "hat": "hat",
    "eyewear": "sunglasses",
}

# Attributes worth putting in a search box, in priority order.
USEFUL_ATTRS = (
    "material", "fabric", "colour", "finish", "silhouette", "cut_or_fit",
    "length", "era_or_style",
)


def _clean(text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9-]+", text.lower())
    return " ".join(w for w in words if w not in NOISE and len(w) > 1)


def search_queries(item: Item, *, limit: int = 3) -> list[str]:
    """Best-effort search strings, most specific first."""
    queries: list[str] = []

    # The model's own suggestions come first - they are written for this purpose.
    for term in item.search_terms or []:
        cleaned = _clean(term)
        if cleaned and cleaned not in queries:
            queries.append(cleaned)

    # Then a constructed fallback: attributes + the category's plain noun.
    noun = CATEGORY_NOUNS.get(item.category, item.category.split("-")[-1])
    attrs = [
        _clean(str(item.attributes.get(k)))
        for k in USEFUL_ATTRS
        if item.attributes.get(k)
    ]
    constructed = " ".join([a for a in attrs[:2] if a] + [noun]).strip()
    if constructed and constructed not in queries:
        queries.append(constructed)

    # And the bare noun, which always returns something.
    if noun not in queries:
        queries.append(noun)

    return queries[:limit]


def build_url(template: str, query: str) -> str:
    # Some shops take the query as a path segment rather than a parameter.
    if template.endswith("{q}") and "?" not in template.rsplit("/", 1)[-1]:
        return template.replace("{q}", quote_plus(query).replace("+", "-"))
    return template.replace("{q}", quote_plus(query))
