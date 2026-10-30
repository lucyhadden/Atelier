"""The retailer registry: who sells what, at which price tier.

The `search` template is a deep link into that shop's own search results. These
are hand-maintained and shops do change their URL schemes, so treat this file as
editable data, not as settled truth - run `make check-retailers` to find any
template that has stopped resolving, then fix the one line.

`category_hints` narrows which item categories a retailer is worth searching.
An empty list means "anything in this domain".
"""

from dataclasses import dataclass, field

TIERS = ("splurge", "mid", "budget", "secondhand")

TIER_LABELS = {
    "splurge": "Splurge",
    "mid": "Middle",
    "budget": "Budget",
    "secondhand": "Secondhand",
}


@dataclass(frozen=True)
class Retailer:
    name: str
    tier: str
    domain: str
    search: str  # must contain {q}
    regions: tuple[str, ...] = ("US", "UK")
    category_hints: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


INTERIOR: tuple[Retailer, ...] = (
    # ---- splurge ----
    Retailer("1stDibs", "splurge", "interior", "https://www.1stdibs.com/search/?q={q}",
             note="Vintage and collectible design; the real thing, at auction prices."),
    Retailer("Design Within Reach", "splurge", "interior",
             "https://www.dwr.com/search?q={q}", regions=("US",),
             note="Licensed modern classics."),
    Retailer("The Conran Shop", "splurge", "interior",
             "https://www.conranshop.co.uk/catalogsearch/result/?q={q}", regions=("UK",)),
    Retailer("Soho Home", "splurge", "interior", "https://www.sohohome.com/search?q={q}"),
    Retailer("Lumens", "splurge", "interior", "https://www.lumens.com/search/?q={q}",
             regions=("US",), category_hints=("lighting-ceiling", "lighting-floor",
                                              "lighting-table", "lighting-wall")),
    Retailer("Schoolhouse", "splurge", "interior", "https://schoolhouse.com/search?q={q}",
             regions=("US",), category_hints=("lighting-ceiling", "lighting-wall",
                                              "hardware-fixture")),

    # ---- mid ----
    Retailer("West Elm", "mid", "interior",
             "https://www.westelm.com/search/results.html?words={q}"),
    Retailer("CB2", "mid", "interior", "https://www.cb2.com/search?query={q}", regions=("US",)),
    Retailer("Crate & Barrel", "mid", "interior",
             "https://www.crateandbarrel.com/search?query={q}", regions=("US",)),
    Retailer("Anthropologie", "mid", "interior", "https://www.anthropologie.com/search?q={q}"),
    Retailer("Article", "mid", "interior", "https://www.article.com/search?q={q}",
             regions=("US",), category_hints=("seating-sofa", "seating-chair", "table-dining",
                                              "table-coffee", "table-side", "bed")),
    Retailer("John Lewis", "mid", "interior",
             "https://www.johnlewis.com/search?search-term={q}", regions=("UK",)),
    Retailer("Heal's", "mid", "interior", "https://www.heals.com/search?q={q}",
             regions=("UK",)),
    Retailer("Wayfair", "mid", "interior", "https://www.wayfair.com/keyword.php?keyword={q}",
             note="Huge range, uneven quality - read the dimensions."),
    Retailer("Farrow & Ball", "mid", "interior",
             "https://www.farrow-ball.com/search?q={q}",
             category_hints=("paint-colour", "wallpaper")),

    # ---- budget ----
    Retailer("IKEA", "budget", "interior", "https://www.ikea.com/us/en/search/?q={q}",
             regions=("US",)),
    Retailer("IKEA UK", "budget", "interior", "https://www.ikea.com/gb/en/search/?q={q}",
             regions=("UK",)),
    Retailer("H&M Home", "budget", "interior",
             "https://www2.hm.com/en_us/search-results.html?q={q}",
             category_hints=("textile-cushion", "textile-throw", "textile-bedding",
                             "ceramics-vessel", "decor-object", "mirror")),
    Retailer("Target", "budget", "interior", "https://www.target.com/s?searchTerm={q}",
             regions=("US",)),
    Retailer("Dunelm", "budget", "interior", "https://www.dunelm.com/search?q={q}",
             regions=("UK",)),
    Retailer("Amazon", "budget", "interior", "https://www.amazon.com/s?k={q}",
             note="Last resort - listings are often unbranded copies."),

    # ---- secondhand ----
    Retailer("eBay", "secondhand", "interior", "https://www.ebay.com/sch/i.html?_nkw={q}"),
    Retailer("Etsy", "secondhand", "interior", "https://www.etsy.com/search?q={q}",
             note="Good for handmade ceramics, textiles and small-batch lighting."),
    Retailer("Chairish", "secondhand", "interior", "https://www.chairish.com/search?q={q}",
             regions=("US",)),
    Retailer("Vinterior", "secondhand", "interior", "https://www.vinterior.co/search?q={q}",
             regions=("UK",)),
    Retailer("Facebook Marketplace", "secondhand", "interior",
             "https://www.facebook.com/marketplace/search/?query={q}",
             note="Cheapest route for large furniture, if you can collect it. "
                  "The link only works while you are logged into Facebook."),
)

WARDROBE: tuple[Retailer, ...] = (
    # ---- splurge ----
    Retailer("Net-a-Porter", "splurge", "wardrobe",
             "https://www.net-a-porter.com/en-us/shop/search/{q}"),
    Retailer("SSENSE", "splurge", "wardrobe", "https://www.ssense.com/en-us/women?q={q}"),
    Retailer("Mytheresa", "splurge", "wardrobe", "https://www.mytheresa.com/en-us/search?q={q}"),
    Retailer("Farfetch", "splurge", "wardrobe",
             "https://www.farfetch.com/shopping/search/items.aspx?q={q}"),

    # ---- mid ----
    Retailer("COS", "mid", "wardrobe", "https://www.cos.com/en_usd/search.html?q={q}"),
    Retailer("Arket", "mid", "wardrobe", "https://www.arket.com/en/search.html?q={q}"),
    Retailer("& Other Stories", "mid", "wardrobe",
             "https://www.stories.com/en_usd/search.html?q={q}"),
    Retailer("Everlane", "mid", "wardrobe", "https://www.everlane.com/search?q={q}",
             regions=("US",)),
    Retailer("Reformation", "mid", "wardrobe", "https://www.thereformation.com/search?q={q}"),
    Retailer("Sézane", "mid", "wardrobe", "https://www.sezane.com/us/search?q={q}"),
    Retailer("Nordstrom", "mid", "wardrobe", "https://www.nordstrom.com/sr?keyword={q}",
             regions=("US",)),

    # ---- budget ----
    Retailer("Uniqlo", "budget", "wardrobe", "https://www.uniqlo.com/us/en/search?q={q}",
             note="Best-in-class basics; fabric quality beats the price."),
    Retailer("Zara", "budget", "wardrobe", "https://www.zara.com/us/en/search?searchTerm={q}"),
    Retailer("Mango", "budget", "wardrobe", "https://shop.mango.com/us/search?q={q}"),
    Retailer("H&M", "budget", "wardrobe", "https://www2.hm.com/en_us/search-results.html?q={q}"),
    Retailer("ASOS", "budget", "wardrobe", "https://www.asos.com/search/?q={q}"),

    # ---- secondhand ----
    Retailer("Vinted", "secondhand", "wardrobe", "https://www.vinted.com/catalog?search_text={q}"),
    Retailer("Depop", "secondhand", "wardrobe", "https://www.depop.com/search/?q={q}"),
    Retailer("Vestiaire Collective", "secondhand", "wardrobe",
             "https://www.vestiairecollective.com/search/?q={q}",
             note="Authenticated designer resale."),
    Retailer("The RealReal", "secondhand", "wardrobe",
             "https://www.therealreal.com/search?keywords={q}", regions=("US",)),
    Retailer("eBay", "secondhand", "wardrobe", "https://www.ebay.com/sch/i.html?_nkw={q}"),
)

ALL: tuple[Retailer, ...] = INTERIOR + WARDROBE


def for_domain(domain: str, *, region: str = "US", category: str | None = None) -> list[Retailer]:
    out = []
    for r in ALL:
        if r.domain != domain or region not in r.regions:
            continue
        if category and r.category_hints and category not in r.category_hints:
            continue
        out.append(r)
    return out


def by_tier(
    domain: str, *, region: str = "US", category: str | None = None, per_tier: int = 3
) -> dict[str, list[Retailer]]:
    """The shape the UI wants: tier -> a handful of retailers."""
    grouped: dict[str, list[Retailer]] = {t: [] for t in TIERS}
    for r in for_domain(domain, region=region, category=category):
        if len(grouped[r.tier]) < per_tier:
            grouped[r.tier].append(r)
    # If a category hint filtered a tier down to nothing, fall back to the
    # domain's generalists so no tier is left empty.
    for tier, items in grouped.items():
        if not items:
            grouped[tier] = [
                r for r in for_domain(domain, region=region) if r.tier == tier
            ][:per_tier]
    return grouped
