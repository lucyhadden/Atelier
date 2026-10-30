"""Command-line access to the same operations the API exposes.

    atelier import ~/Pictures/future-home --domain interior
    atelier boards
    atelier analyze 1
    atelier style 1
    atelier source 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .db import SessionLocal, init_db
from .ingest import local, pinterest, sync
from .models import Board, Item, Space
from .shopping import sourcing
from .vision import analyze
from .vision.client import AnalysisError


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atelier", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Import a folder of images as a board")
    p_import.add_argument("path")
    p_import.add_argument("--domain", default="interior", choices=["interior", "wardrobe"])
    p_import.add_argument("--name")
    p_import.add_argument("--export", action="store_true", help="Treat as a Pinterest export")

    sub.add_parser("boards", help="List local boards")
    sub.add_parser("pinterest-boards", help="List boards on your Pinterest account")

    p_sync = sub.add_parser("sync", help="Sync a Pinterest board by its id")
    p_sync.add_argument("external_id")
    p_sync.add_argument("--domain", default="interior", choices=["interior", "wardrobe"])

    p_an = sub.add_parser("analyze", help="Catalogue every pin on a board")
    p_an.add_argument("board_id", type=int)
    p_an.add_argument("--force", action="store_true")

    p_st = sub.add_parser("style", help="Read a board's style profile")
    p_st.add_argument("board_id", type=int)

    p_src = sub.add_parser("source", help="Find places to buy an item")
    p_src.add_argument("item_id", type=int)
    p_src.add_argument("--no-web", action="store_true", help="Search links only, no Claude")

    p_plan = sub.add_parser("design", help="Build a plan for a space")
    p_plan.add_argument("space_id", type=int)
    p_plan.add_argument("--board", type=int)
    p_plan.add_argument("--brief", default="")

    args = parser.parse_args(argv)
    init_db()
    db = SessionLocal()

    try:
        if args.command == "import":
            path = Path(args.path)
            if args.export:
                _print(local.import_pinterest_export(db, path, domain=args.domain))
            else:
                _print(
                    local.import_folder(db, path, domain=args.domain, board_name=args.name)
                )

        elif args.command == "boards":
            _print(
                [
                    {
                        "id": b.id,
                        "name": b.name,
                        "domain": b.domain,
                        "source": b.source,
                        "pins": len(b.pins),
                        "analyzed": sum(1 for p in b.pins if p.analyzed_at),
                        "items": sum(len(p.items) for p in b.pins),
                    }
                    for b in db.query(Board).all()
                ]
            )

        elif args.command == "pinterest-boards":
            _print(pinterest.list_boards())

        elif args.command == "sync":
            _print(sync.sync_board(db, args.external_id, domain=args.domain))

        elif args.command == "analyze":
            board = db.get(Board, args.board_id)
            if board is None:
                print(f"No board {args.board_id}", file=sys.stderr)
                return 1
            _print(analyze.analyze_board(db, board, force=args.force))

        elif args.command == "style":
            board = db.get(Board, args.board_id)
            if board is None:
                print(f"No board {args.board_id}", file=sys.stderr)
                return 1
            profile = analyze.read_style(db, board)
            _print(
                {
                    "summary": profile.summary,
                    "palette": profile.palette,
                    "materials": profile.materials,
                    "keywords": profile.keywords,
                    "axes": profile.axes,
                    "tensions": profile.tensions,
                }
            )

        elif args.command == "source":
            item = db.get(Item, args.item_id)
            if item is None:
                print(f"No item {args.item_id}", file=sys.stderr)
                return 1
            result = sourcing.source_item(db, item, use_web_search=not args.no_web)
            _print(
                {
                    **result,
                    "sources": [
                        {
                            "tier": s.tier,
                            "retailer": s.retailer,
                            "kind": s.kind,
                            "product": s.product_name,
                            "price": s.price,
                            "url": s.url,
                        }
                        for s in item.sources
                    ],
                }
            )

        elif args.command == "design":
            space = db.get(Space, args.space_id)
            if space is None:
                print(f"No space {args.space_id}", file=sys.stderr)
                return 1
            board = db.get(Board, args.board) if args.board else None
            plan = analyze.build_plan(db, space, board, args.brief)
            _print(
                {
                    "title": plan.title,
                    "narrative": plan.narrative,
                    "zones": plan.zones,
                    "shopping_list": plan.shopping_list,
                    "cautions": plan.cautions,
                }
            )

    except (AnalysisError, pinterest.PinterestError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
