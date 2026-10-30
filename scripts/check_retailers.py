#!/usr/bin/env python3
"""Check every retailer search template still resolves.

Shops change their URL schemes without warning, which silently turns a tier's
links into 404s. This fires one request per template and prints what broke, so
fixing it is a one-line edit in backend/atelier/shopping/retailers.py.

    make check-retailers
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx

from atelier.shopping.query import build_url
from atelier.shopping.retailers import ALL

SAMPLE = {"interior": "floor lamp", "wardrobe": "wool coat"}
# Plenty of retailers block an obvious bot outright; a browser UA gets an
# honest answer about whether the URL itself is valid.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


# Status codes that mean "a bot asked, so we said no" rather than "bad URL".
BOT_WALL = {401, 403, 418, 429, 503}


def main() -> int:
    ok, blocked, broken = [], [], []

    with httpx.Client(timeout=20.0, follow_redirects=True, headers=HEADERS) as client:
        for r in ALL:
            url = build_url(r.search, SAMPLE[r.domain])
            label = f"{r.domain:9s} {r.tier:11s} {r.name}"
            try:
                resp = client.get(url)
            except httpx.TimeoutException:
                # Several retailers tarpit non-browser clients. That says nothing
                # about whether the URL is right, so do not cry wolf.
                blocked.append((label, url, "timeout"))
                continue
            except httpx.HTTPError as exc:
                broken.append((label, url, f"{type(exc).__name__}: {exc}"))
                continue

            if resp.status_code == 200:
                ok.append(label)
            elif resp.status_code in BOT_WALL:
                blocked.append((label, url, resp.status_code))
            else:
                broken.append((label, url, f"HTTP {resp.status_code}"))

    print(f"\n{len(ok)} OK\n")
    for label in ok:
        print(f"  ok       {label}")

    if blocked:
        print(
            f"\n{len(blocked)} could not be verified from a script (anti-bot). "
            "The URL is probably fine - open one to be sure:\n"
        )
        for label, url, code in blocked:
            print(f"  [{code}]  {label}\n           {url}")

    if broken:
        print(f"\n{len(broken)} BROKEN - fix the template in retailers.py:\n")
        for label, url, why in broken:
            print(f"  FAIL     {label}  ({why})\n           {url}")

    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
