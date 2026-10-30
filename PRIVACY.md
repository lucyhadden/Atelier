# Privacy Policy — Atelier

_Last updated: 30 October 2026_

Atelier is a personal, open-source tool that a single person runs on their own
computer. It is not a hosted service. There is no Atelier server, no account to
create, and no operator who can see your data.

This policy describes what the software does with information, so you can verify
it against the source code in this repository.

## Who this covers

The person who installs and runs Atelier on their own machine. Atelier has no
other users and collects nothing from anyone else.

## What Atelier stores, and where

Everything Atelier keeps is written to a `data/` directory inside the folder where
you installed it, on your own computer:

| What | Where | Notes |
|---|---|---|
| Images you import or sync | `data/images/` | Copies of your own saved images, downscaled |
| Boards, pins, identified items, shopping links, design plans | `data/atelier.db` (SQLite) | A local file |
| Your Pinterest access token, if you connect Pinterest | `data/pinterest_token.json` | Written with owner-only permissions (`0600`) |
| Your API keys | `.env` | Never committed; excluded by `.gitignore` |

None of this is transmitted to the author of Atelier or to any analytics service.
There is no telemetry, no usage tracking, no crash reporting, and no "phone home"
of any kind.

## What Atelier sends elsewhere, and when

Atelier makes outbound network requests only in these cases:

**1. Pinterest (only if you connect it).** Atelier uses the official Pinterest API
v5 with OAuth. It requests read-only scopes (`boards:read`, `pins:read`,
`user_accounts:read`) and reads **only the authenticated account's own boards and
pins**. It never posts, creates, edits or deletes anything on Pinterest, and never
accesses any other person's data. Your access token stays on your machine; it is
sent only to Pinterest.

**2. Anthropic (only when you ask for an analysis).** When you choose to read a
board, read a floor plan, or source an item, the relevant images and text are sent
to Anthropic's API to be analysed, and the result comes back. This is the only
third party that ever receives your images. Anthropic's handling of that data is
governed by their own privacy policy and commercial terms:
<https://www.anthropic.com/legal/privacy>. If you never trigger an analysis, no
image ever leaves your machine.

**3. Web search (only if enabled, and only when you source an item).** With
`ATELIER_WEB_SEARCH=true`, sourcing a piece sends a description of that item (for
example "ribbed opal glass table lamp, brushed brass") as a search query, via
Anthropic's server-side web search tool, to find real products and prices. The
search text describes the object, not you. Set `ATELIER_WEB_SEARCH=false` to
disable this entirely.

**4. Image downloads.** When syncing a Pinterest board, Atelier downloads the pin
images from Pinterest's content servers so it can store them locally.

Atelier does not contact retailers on your behalf. Shopping links are constructed
locally and only opened when **you** click them, in your own browser.

## What Atelier never does

- It never sells, rents, shares or discloses your data to anyone.
- It never shows you advertising and contains no advertising or tracking SDKs.
- It never reads any Pinterest account other than the one you authenticate.
- It never writes to, posts on, or modifies your Pinterest account.
- It never collects names, addresses, payment details or government identifiers.
  There is no payment flow in the software at all.

## Cookies

Atelier sets no cookies and uses no browser storage for tracking. The local
interface runs at `localhost` and keeps its state in the URL.

## Children

Atelier is not directed at children and collects no information from anyone,
including children.

## Deleting your data

Delete the `data/` directory. That removes every image, every analysis, and the
stored Pinterest token. To revoke Atelier's access to your Pinterest account
independently, remove it from your Pinterest account's connected apps, or use the
**Disconnect** button in Atelier, which deletes the stored token.

Uninstalling Atelier is deleting its folder. Nothing is left behind elsewhere on
your system and nothing persists on any server.

## Changes to this policy

Any change is a commit in this repository, so the full history of this document is
public and auditable.

## Contact

Raise an issue on this repository:
<https://github.com/lucyhadden/Atelier/issues>
