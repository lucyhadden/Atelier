# Atelier

Turn the images you save into a design brief and a shopping list with prices.

Point it at a Pinterest board (or a folder of saved images), and it reads every
image one at a time: what's in it, what the piece is made of, and what makes it
work. Then it reads the whole board at once to find the throughline — the palette,
the materials, and the places where two directions in your board quietly disagree.

Pick any piece and it finds places to buy it at four price tiers: the real thing,
a good mid-range version, the cheapest thing that still gets the look, and
secondhand.

Two modes, same machinery: **Interiors** and **Wardrobe**.

---

## What it does

| | |
|---|---|
| **Boards** | Sync a Pinterest board over the official API, or import a folder of images. Each image is catalogued into individual buyable pieces. |
| **The read** | One pass over the whole board: palette with hex values, materials, where it sits on five aesthetic axes, and an honest list of its internal conflicts. |
| **Pieces** | Everything found across every board, grouped by category. The "what do I actually keep saving" view. |
| **Sourcing** | Per piece: splurge / middle / budget / secondhand. Either instant deep links into each shop's search, or a live web search that returns named products with real prices. |
| **Spaces** | Upload a floor plan or a room photo. Atelier reads the fixed features and constraints, then applies a board's aesthetic to that specific room — sequenced, with a spend-here/save-there call, and a list of where the look will fight the space. |

---

## Setup

```bash
make install
```

That creates the virtualenv, installs both halves, and copies `.env.example` to
`.env`. Then put an Anthropic API key in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get one at [console.anthropic.com](https://console.anthropic.com/settings/keys).
Nothing that reads an image works without it.

Run the two halves in separate terminals:

```bash
make backend
```

```bash
make frontend
```

Then open **http://localhost:5173**.

---

## Getting images in

### A folder (works immediately)

Drag whatever you've saved into a folder and give Atelier the path. The folder
name becomes the board name. Nothing is uploaded anywhere: files are copied into
`data/images/`, downscaled to 1600px, and that's the only copy Atelier touches.

### Pinterest, properly

Atelier uses the **official Pinterest API v5**. It does not automate a login or
scrape the site — that breaks Pinterest's terms and stops working without warning.

1. Create an app at [developers.pinterest.com/apps](https://developers.pinterest.com/apps/).
   Answer **"Yes, mine"** to *Reads Pins and/or Boards Data* — "Yes, for general
   users" triggers a separate approval you do not need.
2. Add `http://localhost:8787/api/pinterest/callback` as a redirect URI
3. Put the client id and secret in `.env`, restart the backend
4. Click **Connect Pinterest** on the Boards page

New Pinterest apps start in trial mode, which can only read *your own* account.
That is exactly what this needs, so you do not have to apply for anything.

**What the sync actually handles**

- **Secret boards.** Atelier asks for `boards:read_secret` and `pins:read_secret`.
  Without those a board you have marked secret — which a half-finished house plan
  very often is — simply does not appear. Scopes are fixed when you authorise, so
  this has to be right up front.
- **Board sections.** The board-pins endpoint does not reliably return pins filed
  inside a section, so sections are walked separately and merged, deduplicated by
  pin id. The section name is carried onto the pin, so the grouping you made on
  Pinterest survives the import.
- **Idea and video pins.** These carry their cover image under `media.items`
  rather than `media.images`. Without handling that, every idea pin on a board is
  silently skipped.
- **Rate limits.** Trial access allows roughly 1,000 calls a day. A 429 is waited
  out using Pinterest's own `Retry-After` and retried; if it persists the sync
  stops with a message saying so, and already-downloaded pins are kept, so running
  it again continues rather than restarting.
- **Long boards.** Paging stops at 5,000 pins per board and *tells you* it
  stopped, rather than returning a partial board that looks complete.
- **Pins deleted on Pinterest.** Reported, never deleted locally. Losing a
  catalogued piece because a pin was tidied away would be worse than keeping a
  stale one.
- **Token expiry.** The access token is refreshed just before it expires, so a
  long sync does not die halfway through.

### A Pinterest data export (no app needed)

Request your data from Pinterest settings, unzip it, tick **"This is an unzipped
Pinterest data export"** and give Atelier the folder. Each subfolder becomes a board.

---

## Two honest notes

**On shopping links.** Rows marked `found` are products Atelier actually located
through a live web search, with the price as listed at the time. Unmarked rows are
searches of that shop — a place to look, not a promise they stock it. Atelier will
not invent a product URL; findings without a usable absolute link are dropped
rather than shown.

Shops change their URL schemes, which silently turns search links into 404s:

```bash
make check-retailers
```

That fires one request per template and sorts the results into three buckets:
fine, bot-blocked (almost always still correct — the shop refused a script, not a
bad URL), and genuinely broken. Fixing one is a one-line edit in
`backend/atelier/shopping/retailers.py`. Pass a region to narrow it:

```bash
.venv/bin/python scripts/check_retailers.py AU
```

Every template in the registry was verified this way when added; it is how the
Heal'''s, Myer, Coco Republic, Adairs and Zimmermann URLs got corrected.

**On floor plans.** Atelier only reports a dimension if it is actually written on
the plan or readable from a scale bar. Otherwise it says "unclear" and tells you
its confidence was low. It will not estimate square footage from the proportions
of a photograph. Type the real dimensions into the brief and the plan will use them.

---

## Cost

Every image is one Claude call. Roughly:

| | |
|---|---|
| Reading a board | one call per image |
| The style read | one call for up to 24 images |
| Sourcing one piece, with web search | two calls plus the searches |
| Sourcing one piece, links only | free, no model call |
| A design plan | one call |

Defaults are `claude-opus-5` at `high` effort. To spend less, drop effort in `.env`:

```
ATELIER_EFFORT=medium
ATELIER_WEB_SEARCH=false
```

`ATELIER_WEB_SEARCH=false` makes sourcing instant and free — you still get all four
tiers, just as search links rather than named products.

## Where you shop

```
ATELIER_REGION=AU                  # AU, NZ, UK or US
ATELIER_INCLUDE_INTERNATIONAL=true
```

Region is a **preference, not a filter**. Set it to `AU` and every tier leads with
Australian sellers — Coco Republic and Jardan at the top, Freedom and Myer and
David Jones in the middle, IKEA AU and Kmart at the bottom, Gumtree and eBay AU
for secondhand — and then lists overseas sellers that ship to you underneath,
labelled `ships from US`. Nothing good is hidden because of where you live.

Set `ATELIER_INCLUDE_INTERNATIONAL=false` if you only want things that ship
domestically.

When live web search finds a shop that isn't in the registry, Atelier asks whether
it ships to your region and reports the answer. If that can't be established it
says **shipping unchecked** rather than guessing — an unverified shop is never
presented as local.

---

## Layout

```
backend/atelier/
  domains.py          the two domains and their vocabularies — add a third here
  models.py           SQLAlchemy models (one schema serves both domains)
  vision/
    prompts.py        system prompts (kept stable: they're the cached prefix)
    schemas.py        Pydantic shapes Claude's output is validated against
    client.py         the only module that talks to Anthropic
    analyze.py        orchestration: images in, rows out
  shopping/
    retailers.py      the tiered retailer registry — editable data, not truth
    query.py          turning a piece into something a search box will match
    sourcing.py       search links, plus optional live product research
  ingest/
    pinterest.py      official API v5 client + OAuth
    local.py          folder and data-export import
    images.py         download, downscale, store
frontend/src/         React + Vite UI, built to the Hallmark design floor
tests/                20 tests, no API key required
```

## Command line

Everything the UI does, scriptable:

```bash
.venv/bin/atelier import ~/Pictures/future-home --domain interior
.venv/bin/atelier boards
.venv/bin/atelier analyze 1
.venv/bin/atelier style 1
.venv/bin/atelier source 42
.venv/bin/atelier design 1 --board 1 --brief "4.2m x 3.1m, budget £3k"
```

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

They stub the model's responses, so they run without an API key and cost nothing.
They cover the parts worth protecting: that re-reading a board replaces rather than
duplicates, that a hallucinated category can't enter the taxonomy, that a failed web
search still leaves you your search links, and that a product without a real URL is
never stored.

## The UI

Built against [Hallmark](https://github.com/Nutlope/hallmark)'s design floor
(theme: Atelier — limewash paper, umber ink, Sentient over Hanken Grotesk). The
stamp and the one waiver are at the top of `frontend/src/app.css`. To re-check it:

```bash
node ~/.agents/skills/hallmark/scripts/sloplint.mjs frontend/src --genre editorial --scope app
```
