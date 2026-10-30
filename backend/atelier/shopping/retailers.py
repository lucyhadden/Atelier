"""The retailer registry: who sells what, at which price tier.

The `search` template is a deep link into that shop's own search results. These
are hand-maintained and shops do change their URL schemes, so treat this file as
editable data, not as settled truth - run `make check-retailers` to find any
template that has stopped resolving, then fix the one line.

`category_hints` narrows which item categories a retailer is worth searching.
An empty list means "anything in this domain".

`regions` is where a retailer is a *local* option - it ships domestically there.
`international=True` marks a retailer worth showing even when you are outside its
region, because it ships worldwide. Region is therefore a preference, not a
filter: local retailers come first, overseas ones follow, labelled as such.
"""

from dataclasses import dataclass, field

TIERS = ("splurge", "mid", "budget", "secondhand")

# Regions the retailer registry knows about.
REGIONS = ("AU", "NZ", "UK", "US")

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
    # Ships worldwide, so worth offering from outside `regions`.
    international: bool = False
    # The search URL only resolves for a signed-in visitor, so an automated
    # check cannot confirm it. Correct, but unverifiable from a script.
    login_required: bool = False


INTERIOR: tuple[Retailer, ...] = (
    # ---- splurge ----
    Retailer("1stDibs", "splurge", "interior", "https://www.1stdibs.com/search/?q={q}",
             international=True, note="Vintage and collectible design; the real thing, at auction prices."),
    Retailer("Design Within Reach", "splurge", "interior",
             "https://www.dwr.com/search?q={q}", regions=("US",),
             note="Licensed modern classics."),
    Retailer("The Conran Shop", "splurge", "interior",
             "https://www.conranshop.co.uk/catalogsearch/result/?q={q}", regions=("UK",)),
    Retailer("Soho Home", "splurge", "interior", "https://www.sohohome.com/search?q={q}",
             international=True),
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
    Retailer("Anthropologie", "mid", "interior", "https://www.anthropologie.com/search?q={q}",
             international=True),
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
             international=True, note="Good for handmade ceramics, textiles and small-batch lighting."),
    Retailer("Chairish", "secondhand", "interior", "https://www.chairish.com/search?q={q}",
             regions=("US",)),
    Retailer("Vinterior", "secondhand", "interior", "https://www.vinterior.co/search?q={q}",
             regions=("UK",)),
    Retailer("Facebook Marketplace", "secondhand", "interior",
             "https://www.facebook.com/marketplace/search/?query={q}",
             login_required=True,
             note="Cheapest route for large furniture, if you can collect it. "
                  "The link only works while you are logged into Facebook."),
)

WARDROBE: tuple[Retailer, ...] = (
    # ---- splurge ----
    Retailer("Net-a-Porter", "splurge", "wardrobe",
             "https://www.net-a-porter.com/en-us/shop/search/{q}", international=True),
    Retailer("SSENSE", "splurge", "wardrobe", "https://www.ssense.com/en-us/women?q={q}",
             international=True),
    Retailer("Mytheresa", "splurge", "wardrobe", "https://www.mytheresa.com/en-us/search?q={q}",
             international=True),
    Retailer("Farfetch", "splurge", "wardrobe",
             "https://www.farfetch.com/shopping/search/items.aspx?q={q}", international=True),

    # ---- mid ----
    Retailer("COS", "mid", "wardrobe", "https://www.cos.com/en_usd/search.html?q={q}",
             international=True),
    Retailer("Arket", "mid", "wardrobe", "https://www.arket.com/en/search.html?q={q}",
             international=True),
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
    Retailer("Depop", "secondhand", "wardrobe", "https://www.depop.com/search/?q={q}",
             international=True),
    Retailer("Vestiaire Collective", "secondhand", "wardrobe",
             "https://www.vestiairecollective.com/search/?q={q}",
             international=True, note="Authenticated designer resale."),
    Retailer("The RealReal", "secondhand", "wardrobe",
             "https://www.therealreal.com/search?keywords={q}", regions=("US",)),
    Retailer("eBay", "secondhand", "wardrobe", "https://www.ebay.com/sch/i.html?_nkw={q}"),
)

AU_INTERIOR: tuple[Retailer, ...] = (
    # ---- splurge ----
    Retailer("Coco Republic", "splurge", "interior",
             "https://www.cocorepublic.com.au/search.php?search_query={q}", regions=("AU",)),
    Retailer("Jardan", "splurge", "interior", "https://jardan.com.au/search?q={q}",
             regions=("AU",), note="Australian-made, built to order; long lead times."),
    Retailer("Space Furniture", "splurge", "interior",
             "https://www.spacefurniture.com.au/search?q={q}", regions=("AU",),
             note="Licensed European design."),
    Retailer("Cult", "splurge", "interior", "https://cultdesign.com.au/search?q={q}",
             regions=("AU", "NZ")),

    # ---- mid ----
    Retailer("Freedom", "mid", "interior", "https://www.freedom.com.au/search?q={q}",
             regions=("AU",)),
    Retailer("Temple & Webster", "mid", "interior",
             "https://www.templeandwebster.com.au/search?q={q}", regions=("AU",),
             note="Huge range, uneven quality - read the dimensions."),
    Retailer("Myer", "mid", "interior", "https://www.myer.com.au/search?query={q}",
             regions=("AU",)),
    Retailer("David Jones", "mid", "interior", "https://www.davidjones.com/search?q={q}",
             regions=("AU",)),
    Retailer("West Elm AU", "mid", "interior",
             "https://www.westelm.com.au/search/results.html?words={q}", regions=("AU",)),
    Retailer("Country Road", "mid", "interior",
             "https://www.countryroad.com.au/search?q={q}", regions=("AU", "NZ")),

    # ---- budget ----
    Retailer("IKEA AU", "budget", "interior", "https://www.ikea.com/au/en/search/?q={q}",
             regions=("AU",)),
    Retailer("Kmart", "budget", "interior", "https://www.kmart.com.au/search/?q={q}",
             regions=("AU",)),
    Retailer("Adairs", "budget", "interior", "https://www.adairs.com.au/search-results/?q={q}",
             regions=("AU", "NZ"),
             category_hints=("textile-cushion", "textile-throw", "textile-bedding",
                             "rug", "window-treatment")),
    Retailer("Fantastic Furniture", "budget", "interior",
             "https://www.fantasticfurniture.com.au/search?q={q}", regions=("AU",)),
    Retailer("Big W", "budget", "interior", "https://www.bigw.com.au/search?text={q}",
             regions=("AU",)),

    # ---- secondhand ----
    Retailer("eBay AU", "secondhand", "interior",
             "https://www.ebay.com.au/sch/i.html?_nkw={q}", regions=("AU",)),
    Retailer("Gumtree", "secondhand", "interior",
             "https://www.gumtree.com.au/s-search.html?q={q}", regions=("AU",),
             note="Cheapest route for large furniture, if you can collect it."),
    Retailer("Facebook Marketplace AU", "secondhand", "interior",
             "https://www.facebook.com/marketplace/search/?query={q}", regions=("AU", "NZ"),
             login_required=True,
             note="Only works while you are logged into Facebook."),
    Retailer("Trade Me", "secondhand", "interior",
             "https://www.trademe.co.nz/a/marketplace/search?search_string={q}",
             regions=("NZ",), note="The main NZ marketplace."),
)

AU_WARDROBE: tuple[Retailer, ...] = (
    # ---- splurge ----
    Retailer("Zimmermann", "splurge", "wardrobe",
             "https://www.zimmermann.com/catalogsearch/result/?q={q}", regions=("AU", "NZ"),
             international=True),
    Retailer("Camilla and Marc", "splurge", "wardrobe",
             "https://www.camillaandmarc.com/search?q={q}", regions=("AU", "NZ")),
    Retailer("Scanlan Theodore", "splurge", "wardrobe",
             "https://www.scanlantheodore.com/search?q={q}", regions=("AU",)),
    Retailer("David Jones", "splurge", "wardrobe",
             "https://www.davidjones.com/search?q={q}", regions=("AU",),
             note="Carries most of the Australian designer labels under one roof."),

    # ---- mid ----
    Retailer("The Iconic", "mid", "wardrobe",
             "https://www.theiconic.com.au/catalogsearch/result/?q={q}", regions=("AU", "NZ"),
             note="Broadest AU stock; fast delivery and free returns."),
    Retailer("Country Road", "mid", "wardrobe",
             "https://www.countryroad.com.au/search?q={q}", regions=("AU", "NZ")),
    Retailer("Witchery", "mid", "wardrobe", "https://www.witchery.com.au/search?q={q}",
             regions=("AU", "NZ")),
    Retailer("Seed Heritage", "mid", "wardrobe",
             "https://www.seedheritage.com/search?q={q}", regions=("AU", "NZ")),
    Retailer("Myer", "mid", "wardrobe", "https://www.myer.com.au/search?query={q}",
             regions=("AU",)),

    # ---- budget ----
    Retailer("Uniqlo AU", "budget", "wardrobe",
             "https://www.uniqlo.com/au/en/search?q={q}", regions=("AU",),
             note="Best-in-class basics; fabric quality beats the price."),
    Retailer("Cotton On", "budget", "wardrobe", "https://cottonon.com/AU/search?q={q}",
             regions=("AU", "NZ")),
    Retailer("Glassons", "budget", "wardrobe", "https://www.glassons.com/search?q={q}",
             regions=("AU", "NZ")),
    Retailer("Kmart", "budget", "wardrobe", "https://www.kmart.com.au/search/?q={q}",
             regions=("AU",)),

    # ---- secondhand ----
    Retailer("eBay AU", "secondhand", "wardrobe",
             "https://www.ebay.com.au/sch/i.html?_nkw={q}", regions=("AU",)),
    Retailer("Gumtree", "secondhand", "wardrobe",
             "https://www.gumtree.com.au/s-search.html?q={q}", regions=("AU",)),
    Retailer("Trade Me", "secondhand", "wardrobe",
             "https://www.trademe.co.nz/a/marketplace/search?search_string={q}",
             regions=("NZ",)),
)


ALL: tuple[Retailer, ...] = INTERIOR + WARDROBE + AU_INTERIOR + AU_WARDROBE


def for_domain(
    domain: str,
    *,
    region: str = "US",
    category: str | None = None,
    include_international: bool = True,
) -> list[Retailer]:
    """Retailers for this domain: local to `region` first, then overseas ones
    that ship there. Region is a preference - it never hides a good option, it
    just ranks domestic shipping above international."""
    local: list[Retailer] = []
    overseas: list[Retailer] = []
    for r in ALL:
        if r.domain != domain:
            continue
        if category and r.category_hints and category not in r.category_hints:
            continue
        if region in r.regions:
            local.append(r)
        elif include_international and r.international:
            overseas.append(r)
    return local + overseas


def is_local(retailer: Retailer, region: str) -> bool:
    return region in retailer.regions


def by_tier(
    domain: str,
    *,
    region: str = "US",
    category: str | None = None,
    per_tier: int = 3,
    include_international: bool = True,
) -> dict[str, list[Retailer]]:
    """The shape the UI wants: tier -> a handful of retailers, local first.

    `per_tier` counts local retailers. Overseas ones are added on top of that
    allowance rather than competing with it, so turning international on never
    pushes a domestic option off the list."""
    grouped: dict[str, list[Retailer]] = {t: [] for t in TIERS}
    overseas: dict[str, list[Retailer]] = {t: [] for t in TIERS}

    for r in for_domain(
        domain, region=region, category=category, include_international=include_international
    ):
        bucket = grouped if is_local(r, region) else overseas
        cap = per_tier if bucket is grouped else max(1, per_tier - 1)
        if len(bucket[r.tier]) < cap:
            bucket[r.tier].append(r)

    for tier in TIERS:
        # A category hint can empty a tier; fall back to the domain's generalists.
        if not grouped[tier] and not overseas[tier]:
            grouped[tier] = [
                r
                for r in for_domain(
                    domain, region=region, include_international=include_international
                )
                if r.tier == tier
            ][:per_tier]
        grouped[tier] = grouped[tier] + overseas[tier]
    return grouped
