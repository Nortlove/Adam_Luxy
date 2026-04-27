#!/usr/bin/env python3
"""Pre-populate the page-intelligence cache with the LUXY pilot URL set.

Reads campaigns/ridelux_v6/domain_archetype_mapping.json (73 hand-curated
domain×archetype entries across 6 LUXY-specific archetypes, tier 1/2/3)
and writes domain-level PagePsychologicalProfile entries to Redis under
the schema PageIntelligenceCache.lookup() reads.

Provenance: the mapping was hand-curated via "manual_research_3_passes_
article_level_verification" — the most accurate signal available for
those publishers. Without this populator, the cascade falls through to
url_intelligence's heuristics for those domains, losing the curated edge.

Usage:
    # Dry run (default — no Redis writes)
    python scripts/populate_luxy_page_cache.py

    # Actually write to Redis
    python scripts/populate_luxy_page_cache.py --write

    # Use a custom mapping file
    python scripts/populate_luxy_page_cache.py --mapping path/to/mapping.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapping", type=Path, default=None,
        help="Path to domain_archetype_mapping.json (defaults to "
             "campaigns/ridelux_v6/domain_archetype_mapping.json)",
    )
    parser.add_argument(
        "--write", action="store_true",
        help="Actually write to Redis (default is dry-run)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Log per-entry results",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    from adam.intelligence.luxy_page_populator import populate_luxy_pages

    result = populate_luxy_pages(
        mapping_path=args.mapping,
        dry_run=not args.write,
    )

    print(f"\n=== LUXY page-cache populator ===")
    print(f"  mode:    {'WRITE' if args.write else 'DRY-RUN'}")
    print(f"  written: {result.written}")
    print(f"  skipped: {result.skipped}")
    print(f"  errors:  {len(result.errors)}")
    if result.errors:
        print(f"\n  Error samples (first 5):")
        for err in result.errors[:5]:
            print(f"    - {err}")

    if args.verbose and result.written_keys:
        print(f"\n  Written keys (first 10):")
        for key in result.written_keys[:10]:
            print(f"    - {key}")

    if result.errors and not result.written:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
