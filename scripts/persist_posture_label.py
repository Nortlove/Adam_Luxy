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

Held-out fixture isolation (binding rule:
feedback_heldout_fixture_isolation.md): every persist invocation
checks the URL's registrable domain against the held-out fixture
in scripts/heldout_eval_posture_classifier.py. If a collision is
detected, the persist is REFUSED with exit code 6 and an error
message naming the colliding fixture URL plus two resolution paths
(pick a different candidate, preferred; or rotate the fixture-side
URL with a HELDOUT_ROTATION_MANIFEST entry, fallback). This
protects against accidental fixture re-contamination at the
keystroke. --list and --count modes do not run the check.

Exit codes:
  0 — persist succeeded (or list/count succeeded)
  1 — invalid args (missing --url or --label)
  2 — Neo4j env vars missing or driver build failed
  3 — PageLabelEntry validation failed
  4 — persist_page_label returned False
  5 — persist returned True but read-back found no record
  6 — held-out fixture isolation violation (NEW; refuse-to-persist)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

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


def _load_heldout_fixture_urls() -> List[str]:
    """Load the held-out fixture URLs for the persist-time isolation
    check. Imported lazily so that --list / --count modes don't pay
    the import cost. Returns [] if the fixture script is missing or
    malformed (which itself is a soft failure — the operator gets a
    warning rather than a refusal, since the gate script's absence
    already breaks the gate)."""
    try:
        from scripts.heldout_eval_posture_classifier import HELDOUT_URLS
    except Exception as exc:
        print(
            f"WARNING: could not import held-out fixture for "
            f"isolation check ({exc}). Persist will proceed WITHOUT "
            f"the fixture-isolation rule enforced — verify the "
            f"colliding-domain audit by hand "
            f"(/tmp/domain_overlap_audit.py).",
            file=sys.stderr,
        )
        return []
    return [u for u, _, _ in HELDOUT_URLS]


async def _persist(args: argparse.Namespace) -> int:
    from adam.intelligence.posture_five_class import (
        FIVE_CLASS_POSTURES,
        PageLabelEntry,
        count_labels_corpus,
        find_url_fixture_collision,
        load_labeled_pages,
        persist_page_label,
        registrable_domain,
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

        # Held-out fixture isolation check (binding rule:
        # feedback_heldout_fixture_isolation.md). Refuse to persist
        # any URL whose registrable domain matches a held-out fixture
        # domain, naming the colliding fixture URL. Resolution
        # preference: pick a different candidate (preferred — fixture
        # authority preserved) or rotate the fixture-side URL
        # (fallback — append HELDOUT_ROTATION_MANIFEST entry).
        fixture_urls = _load_heldout_fixture_urls()
        collision = find_url_fixture_collision(args.url, fixture_urls)
        if collision is not None:
            collision_domain, fixture_url = collision
            print(
                f"ERROR: URL violates the held-out fixture isolation "
                f"rule.\n"
                f"\n"
                f"  url being persisted    : {args.url}\n"
                f"  registrable_domain     : {collision_domain}\n"
                f"  collides with fixture  : {fixture_url}\n"
                f"\n"
                f"The held-out fixture in "
                f"scripts/heldout_eval_posture_classifier.py uses "
                f"{collision_domain}; persisting any URL on that "
                f"domain into :PostureLabel would contaminate the "
                f"criterion-(ii) gate.\n"
                f"\n"
                f"Resolution preference:\n"
                f"  (a) [PREFERRED] Choose a different labeling "
                f"candidate from a domain not in the held-out "
                f"fixture. This preserves the fixture's authority.\n"
                f"  (b) [FALLBACK] Rotate the fixture-side URL by "
                f"editing scripts/heldout_eval_posture_classifier.py "
                f"— swap the colliding HELDOUT_URLS entry to a "
                f"fresh same-class URL on a never-trained domain, "
                f"then append a HELDOUT_ROTATION_MANIFEST entry "
                f"recording the swap.\n"
                f"\n"
                f"Binding rule: feedback_heldout_fixture_isolation.md\n"
                f"Audit memo:   docs/CRITERION_II_STATUS_CORRECTION_2026_05_02.md",
                file=sys.stderr,
            )
            return 6

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
