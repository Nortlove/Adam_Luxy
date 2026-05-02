#!/usr/bin/env python3
"""Operator CLI: persist one 5-class posture label to the
:PostureLabel manifest (Slice 22 substrate).

Usage (single label):
    python3 scripts/persist_posture_label.py \\
        --url "https://www.nytimes.com/wirecutter/reviews/best-electric-cars/" \\
        --label INFORMATION_FORAGING \\
        --notes "Wirecutter comparison page; classic research-mode posture"

Usage (verify corpus state):
    python3 scripts/persist_posture_label.py --list
    python3 scripts/persist_posture_label.py --count

Auth: requires NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD in .env
or environment. Loaded automatically from project-root .env when
present.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Self-locate the project root so the script runs from any cwd
# without requiring PYTHONPATH. Matches the existing pattern in
# scripts/annotate_seller_side.py + others.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load_env_from_dotenv() -> None:
    """Best-effort .env load."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(
            k.strip(), v.strip().strip('"').strip("'"),
        )


async def _build_driver() -> Optional[Any]:
    """Async Neo4j driver from env. None on failure."""
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USERNAME")
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not uri or not user or not pwd:
        print(
            "ERROR: NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD not set "
            "(check .env or environment).",
            file=sys.stderr,
        )
        return None
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(uri, auth=(user, pwd))
        await driver.verify_connectivity()
        return driver
    except Exception as exc:
        print(
            f"ERROR: Neo4j driver build failed: {exc}",
            file=sys.stderr,
        )
        return None


async def _persist(args: argparse.Namespace) -> int:
    from adam.intelligence.posture_five_class import (
        FIVE_CLASS_POSTURES,
        PageLabelEntry,
        count_labels_corpus,
        load_labeled_pages,
        persist_page_label,
    )

    driver = await _build_driver()
    if driver is None:
        return 2

    try:
        if args.list:
            entries = await load_labeled_pages(driver, limit=args.limit)
            print(f"Loaded {len(entries)} label(s):")
            for e in entries:
                print(
                    f"  url={e.url}\n"
                    f"    label={e.label}  "
                    f"labeler={e.labeler}  "
                    f"confidence={e.confidence:.2f}"
                )
                if e.notes:
                    print(f"    notes={e.notes}")
            return 0

        if args.count:
            counts = await count_labels_corpus(driver)
            print(
                f"n_labels={counts['n_labels']}  "
                f"n_classes_covered={counts['n_classes_covered']}"
            )
            return 0

        # Persist one label
        if not args.url or not args.label:
            print(
                "ERROR: --url and --label are required for persist mode "
                "(or use --list / --count).",
                file=sys.stderr,
            )
            return 1

        try:
            entry = PageLabelEntry(
                url=args.url,
                label=args.label,
                labeler=args.labeler,
                notes=args.notes,
                confidence=args.confidence,
            )
        except Exception as exc:
            print(
                f"ERROR: PageLabelEntry validation failed: {exc}\n\n"
                f"Allowed label values (case-insensitive): "
                f"{list(FIVE_CLASS_POSTURES)}",
                file=sys.stderr,
            )
            return 3

        ok = await persist_page_label(entry, driver=driver)
        if not ok:
            print(
                f"ERROR: persist_page_label returned False for "
                f"url={args.url}",
                file=sys.stderr,
            )
            return 4

        # Verify by reading back via load_labeled_pages.
        all_entries = await load_labeled_pages(driver, limit=10000)
        match = next(
            (e for e in all_entries if e.url == args.url), None,
        )
        if match is None:
            print(
                f"ERROR: persist returned True but read-back found no "
                f"record for url={args.url}",
                file=sys.stderr,
            )
            return 5

        counts = await count_labels_corpus(driver)
        print(
            f"OK  persisted  url={args.url}\n"
            f"    label={match.label}  labeler={match.labeler}  "
            f"confidence={match.confidence:.2f}"
        )
        if match.notes:
            print(f"    notes={match.notes}")
        print(
            f"\nCorpus state after persist: "
            f"n_labels={counts['n_labels']}  "
            f"n_classes_covered={counts['n_classes_covered']}"
        )
        return 0
    finally:
        try:
            await driver.close()
        except Exception:
            pass


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--url", type=str, default=None,
                   help="The page URL being labeled.")
    p.add_argument(
        "--label", type=str, default=None,
        help="One of: INFORMATION_FORAGING / TASK_COMPLETION / "
             "LEISURE_BROWSING / SOCIAL_CONSUMPTION / "
             "TRANSACTIONAL_COMPARISON (case-insensitive).",
    )
    p.add_argument(
        "--labeler", type=str, default="operator",
        help="Labeler identifier. Default 'operator'.",
    )
    p.add_argument(
        "--notes", type=str, default=None,
        help="Optional free-text notes (e.g., why this label).",
    )
    p.add_argument(
        "--confidence", type=float, default=1.0,
        help="Labeler confidence in [0, 1]. Default 1.0 = certain.",
    )
    p.add_argument(
        "--list", action="store_true",
        help="List all persisted labels (verification mode).",
    )
    p.add_argument(
        "--limit", type=int, default=200,
        help="Limit on --list output. Default 200.",
    )
    p.add_argument(
        "--count", action="store_true",
        help="Print n_labels + n_classes_covered (corpus state).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    _load_env_from_dotenv()
    return asyncio.run(_persist(args))


if __name__ == "__main__":
    sys.exit(main())
