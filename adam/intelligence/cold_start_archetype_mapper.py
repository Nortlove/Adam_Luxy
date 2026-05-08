"""Bid-stream-signal cold-start archetype mapper.

Per Q25=(β) adjudication: when a buyer_id has no stored archetype
on BuyerUncertaintyProfile (cold-start), assign one of the 8
archetypes via heuristic voting rules over bid-stream signals
(geo, device, time-of-day, IAB content category).

This is HEURISTIC SUBSTRATE informed by platform research on user-
context-to-archetype correlations. NOT load-bearing academic
citation. Pilot data through per_user_posterior_modulation will
tighten the rules. Rules are module-level constants for tunability;
S5.5 nightly retrain will revise them post-pilot.

Bid-time latency target: <100μs per call (dict lookups + Counter).

The mapper output is the cold-start prior assignment. Once
assigned, per_user_posterior_modulation updates per-user Beta
posteriors from bid evidence within the assigned archetype's
prior. Q27=(ε) policy permits exactly one reassignment after
N=20 bids if a different archetype fits the accumulated posterior
notably better.
"""
from collections import Counter
from typing import Dict, FrozenSet, List, Optional, Tuple

from adam.cold_start.models.enums import ArchetypeID


# ============================================================================
# Tunable mapping rules (module-level for pilot calibration)
# ============================================================================

URBAN_GEO_INDICATORS: FrozenSet[str] = frozenset({
    # Top-tier urban DMAs (heuristic seed; pilot data expands)
    "NYC", "SF", "LA", "CHI", "BOS", "SEA", "DC", "MIA",
    "PHL", "ATL", "DAL", "HOU", "DEN", "MSP", "PDX",
})
"""Urban geo indicators (DMAs / city codes). Tilts toward
EXPLORER / CONNECTOR / CREATOR archetypes per population research
on urban-context openness/extraversion correlates."""

RURAL_GEO_INDICATORS: FrozenSet[str] = frozenset({
    # Heuristic rural-tier seed; pilot data expands
    "RURAL", "RURAL_NE", "RURAL_SE", "RURAL_MW", "RURAL_SW",
    "RURAL_W",
})
"""Rural geo indicators. Tilts toward GUARDIAN / NURTURER /
PRAGMATIST per population research on rural-context conscientious-
ness/agreeableness correlates."""

DEVICE_ARCHETYPE_HINTS: Dict[str, List[ArchetypeID]] = {
    "desktop": [ArchetypeID.ANALYST, ArchetypeID.GUARDIAN],
    "mobile": [ArchetypeID.EXPLORER, ArchetypeID.CONNECTOR],
    "tablet": [ArchetypeID.CREATOR, ArchetypeID.NURTURER],
    "ctv": [ArchetypeID.ACHIEVER, ArchetypeID.PRAGMATIST],
}
"""Device-archetype affinity heuristic. Pilot data tightens."""

HOUR_BUCKET_ARCHETYPE_HINTS: Dict[str, List[ArchetypeID]] = {
    "morning_commute": [ArchetypeID.ACHIEVER, ArchetypeID.GUARDIAN],
    "workday": [ArchetypeID.ANALYST, ArchetypeID.PRAGMATIST],
    "evening_leisure": [ArchetypeID.CONNECTOR, ArchetypeID.NURTURER],
    "late_night": [ArchetypeID.EXPLORER, ArchetypeID.CREATOR],
}
"""Time-of-day archetype affinity buckets."""

IAB_CATEGORY_ARCHETYPE_HINTS: Dict[str, List[ArchetypeID]] = {
    # IAB Content Taxonomy 3.0 tier-1 categories. Heuristic seed;
    # extend per pilot's IAB coverage.
    "Business and Finance": [ArchetypeID.ANALYST, ArchetypeID.GUARDIAN],
    "Technology and Computing": [
        ArchetypeID.ANALYST, ArchetypeID.EXPLORER,
    ],
    "Health and Wellness": [
        ArchetypeID.NURTURER, ArchetypeID.GUARDIAN,
    ],
    "Travel": [ArchetypeID.EXPLORER, ArchetypeID.CONNECTOR],
    "Style and Fashion": [
        ArchetypeID.CREATOR, ArchetypeID.CONNECTOR,
    ],
    "Food and Drink": [ArchetypeID.NURTURER, ArchetypeID.CREATOR],
    "Home and Garden": [
        ArchetypeID.NURTURER, ArchetypeID.PRAGMATIST,
    ],
    "Sports": [ArchetypeID.ACHIEVER, ArchetypeID.EXPLORER],
    "Entertainment": [ArchetypeID.CREATOR, ArchetypeID.CONNECTOR],
    "News": [ArchetypeID.ANALYST, ArchetypeID.GUARDIAN],
    "Education": [ArchetypeID.ANALYST, ArchetypeID.NURTURER],
    "Automotive": [ArchetypeID.ACHIEVER, ArchetypeID.PRAGMATIST],
}

COLD_START_DEFAULT_ARCHETYPE: ArchetypeID = ArchetypeID.PRAGMATIST
"""When no signals provide hints, default to PRAGMATIST per A.2's
balanced-profile derivation; least-bad default when no better
signal available."""


# ============================================================================
# Public API
# ============================================================================

def map_cold_start_archetype(
    *,
    geo: Optional[str] = None,
    device: Optional[str] = None,
    hour_of_day: Optional[int] = None,
    iab_category: Optional[str] = None,
) -> ArchetypeID:
    """Map bid-stream signals to a cold-start archetype.

    Voting across 4 signal sources (geo, device, hour-of-day, IAB).
    Each signal source contributes 1-2 archetype candidates per
    its hints dict. Most-voted archetype is selected. Ties broken
    deterministically by lexicographic order of archetype value.
    PRAGMATIST default if no signals provide hints.

    Args:
        geo: DMA / city code (case-insensitive); optional.
        device: device type (desktop / mobile / tablet / ctv);
            case-insensitive; optional.
        hour_of_day: 0-23; optional.
        iab_category: IAB tier-1 category name (case-sensitive
            per IAB Tech Lab convention); optional.

    Returns:
        ArchetypeID — one of 8 archetypes per A.2.

    Bid-time latency: <100μs (dict lookups + Counter).
    """
    candidates: List[ArchetypeID] = []

    # Device hints (most reliable single signal)
    if device:
        device_normalized = device.lower()
        if device_normalized in DEVICE_ARCHETYPE_HINTS:
            candidates.extend(DEVICE_ARCHETYPE_HINTS[device_normalized])

    # Hour-of-day bucket hints
    if hour_of_day is not None:
        bucket = _hour_to_bucket(hour_of_day)
        if bucket in HOUR_BUCKET_ARCHETYPE_HINTS:
            candidates.extend(HOUR_BUCKET_ARCHETYPE_HINTS[bucket])

    # IAB category hints
    if iab_category and iab_category in IAB_CATEGORY_ARCHETYPE_HINTS:
        candidates.extend(IAB_CATEGORY_ARCHETYPE_HINTS[iab_category])

    # Geo-tier modifier (boosts existing tilts rather than adding
    # entirely new candidates)
    if geo:
        geo_upper = geo.upper()
        if geo_upper in URBAN_GEO_INDICATORS:
            candidates.extend([
                ArchetypeID.EXPLORER,
                ArchetypeID.CONNECTOR,
            ])
        elif geo_upper in RURAL_GEO_INDICATORS:
            candidates.extend([
                ArchetypeID.GUARDIAN,
                ArchetypeID.NURTURER,
            ])

    if not candidates:
        return COLD_START_DEFAULT_ARCHETYPE

    counter = Counter(candidates)
    max_count = max(counter.values())
    top = sorted(
        [a for a, c in counter.items() if c == max_count],
        key=lambda a: a.value,
    )
    return top[0]


def _hour_to_bucket(hour: int) -> str:
    """Map 0-23 hour to canonical bucket name."""
    if 6 <= hour < 10:
        return "morning_commute"
    if 10 <= hour < 17:
        return "workday"
    if 17 <= hour < 22:
        return "evening_leisure"
    return "late_night"
