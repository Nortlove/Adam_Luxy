# =============================================================================
# ADAM Effectiveness Fast Lookup
# Location: adam/infrastructure/effectiveness_lookup.py
# =============================================================================

"""
FAST LOOKUP FOR MECHANISM EFFECTIVENESS

Reads the pre-computed fast_lookup_tables.json from build_aggregated_effectiveness_index.
Used at runtime when Neo4j is unavailable or when sub-5ms lookup is preferred.

Output shape matches HelpfulVoteIntelligence.get_mechanism_priors() so prefetch
and atoms can use this as a fallback without code changes.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Project root: adam/infrastructure -> adam -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_INDEX_PATH = _PROJECT_ROOT / "data" / "effectiveness_index" / "fast_lookup_tables.json"

_lookup_cache: Optional[Dict[str, Any]] = None


def _load_lookup_tables() -> Optional[Dict[str, Any]]:
    """Load fast lookup tables once; return None if missing or invalid."""
    global _lookup_cache
    if _lookup_cache is not None:
        return _lookup_cache
    if not _INDEX_PATH.exists():
        logger.debug(f"Effectiveness fast lookup not found: {_INDEX_PATH}")
        return None
    try:
        with open(_INDEX_PATH) as f:
            _lookup_cache = json.load(f)
        return _lookup_cache
    except Exception as e:
        logger.warning(f"Failed to load effectiveness fast lookup: {e}")
        return None


def get_mechanism_priors(archetype: str) -> Dict[str, Dict[str, float]]:
    """
    Get mechanism priors for an archetype (same shape as HelpfulVoteIntelligence).

    Returns:
        mechanism -> { success_rate, confidence, sample_size }
    """
    tables = _load_lookup_tables()
    if not tables:
        return {}
    top = tables.get("archetype_top_mechanisms") or {}
    entries = top.get(archetype)
    if not entries:
        return {}
    global_eff = tables.get("global_mechanism_effectiveness") or {}
    priors = {}
    for i, e in enumerate(entries):
        mech = e.get("mechanism")
        if not mech:
            continue
        score = float(e.get("score", 0))
        rate = float(global_eff.get(mech, score))
        # confidence from rank (top = 0.9, then decay)
        confidence = max(0.5, 0.9 - i * 0.1)
        priors[mech] = {
            "success_rate": rate,
            "confidence": confidence,
            "sample_size": 0,
        }
    return priors


def get_top_mechanisms(archetype: str, k: int = 5) -> List[str]:
    """Return top k mechanism names for an archetype."""
    priors = get_mechanism_priors(archetype)
    ordered = sorted(
        priors.items(),
        key=lambda x: x[1].get("success_rate", 0) * x[1].get("confidence", 0),
        reverse=True,
    )
    return [m for m, _ in ordered[:k]]


def is_available() -> bool:
    """Return True if fast lookup data is loaded and usable."""
    return _load_lookup_tables() is not None


def reset_cache() -> None:
    """Clear cached tables (for tests)."""
    global _lookup_cache
    _lookup_cache = None
