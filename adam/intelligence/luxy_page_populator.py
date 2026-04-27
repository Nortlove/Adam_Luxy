"""LUXY pilot page-intelligence cache populator.

The LUXY pilot has a hand-curated mapping of 73 URL patterns across 6
pilot-specific archetypes (tier 1/2/3) at:
    campaigns/ridelux_v6/domain_archetype_mapping.json

That file's provenance: 'manual_research_3_passes_article_level_verification'
— the most accurate signal we have for these specific publishers. Without
this populator, the cascade falls through to url_intelligence's generic
heuristics for those domains, losing the curated signal.

This module reads the mapping, derives edge_dimensions for each domain
via the existing url_intelligence resolver (no invented coefficients),
stamps pilot metadata (audience, tier, pilot archetype label) onto
PagePsychologicalProfile, and writes to Redis under the schema the
PageIntelligenceCache.lookup() reader already expects.

Discipline:
    - We do NOT invent edge_dimensions per domain. They come from the
      existing url_intelligence.resolve_url_intelligence — the same
      resolver the cascade uses at request time when the cache misses.
      The populator's job is to RUN THE RESOLVER ONCE OFFLINE, write
      the result to cache, and add the curated pilot metadata. Cache
      hits at request time then deliver the same edge_dimensions plus
      the pilot context.
    - Confidence per tier follows the curation provenance: tier 1
      (article-level verified) > tier 2 (verified) > tier 3 (audience-
      adjacent). We bump confidence by tier; we do not invent
      edge_dimension values.
    - Pilot archetype labels (careful_truster, dependable_loyalist,
      home_market, prevention_planner, reliable_cooperator,
      trusting_loyalist) are LUXY-specific. They are stamped onto the
      profile as DESCRIPTIVE METADATA (mindset / profile_source). They
      do NOT participate in the cascade's canonical archetype routing —
      that resolves separately from segment_id.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Tier → confidence floor. Curated mappings carry higher confidence than
# url_intelligence's heuristic floor of 0.15 — but we still do not push
# above the urls_intelligence heuristic ceiling for unscored URLs (~0.55).
# Provenance: campaigns/ridelux_v6/domain_archetype_mapping.json says
# "manual_research_3_passes_article_level_verification".
_TIER_CONFIDENCE: Dict[int, float] = {
    1: 0.55,  # Article-level verified
    2: 0.45,  # Verified, audience-adjacent
    3: 0.35,  # Adjacent fit
}
_DEFAULT_TIER_CONFIDENCE = 0.30


_DEFAULT_MAPPING_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "campaigns" / "ridelux_v6" / "domain_archetype_mapping.json"
)


@dataclass
class PopulationResult:
    """Outcome of a populator run."""

    written: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    written_keys: List[str] = field(default_factory=list)
    dry_run: bool = False


def load_luxy_mapping(
    mapping_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Load the LUXY domain×archetype mapping into a flat list of entries.

    Each entry: {"domain", "audience", "tier", "pilot_archetype"}.
    """
    path = mapping_path or _DEFAULT_MAPPING_PATH
    if not path.exists():
        raise FileNotFoundError(f"LUXY mapping not found at {path}")

    with open(path, "r") as f:
        data = json.load(f)

    archetype_lists = data.get("archetype_domain_lists", {})
    if not isinstance(archetype_lists, dict):
        raise ValueError(
            "LUXY mapping malformed: archetype_domain_lists is not a dict"
        )

    entries: List[Dict[str, Any]] = []
    for pilot_archetype, domain_list in archetype_lists.items():
        if not isinstance(domain_list, list):
            continue
        for entry in domain_list:
            if not isinstance(entry, dict):
                continue
            domain = entry.get("domain")
            if not domain:
                continue
            entries.append({
                "domain": domain,
                "audience": entry.get("audience", ""),
                "tier": int(entry.get("tier", 0) or 0),
                "pilot_archetype": pilot_archetype,
            })
    return entries


def populate_one_entry(
    entry: Dict[str, Any],
    dry_run: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Populate one (domain, audience, tier, archetype) entry.

    Returns (success, redis_key_written_or_None, error_or_None).

    Discipline: edge_dimensions come from the existing resolver — the
    same one the cascade falls through to at request time when the
    cache misses. We are NOT inventing per-domain values.
    """
    domain = entry["domain"]
    pilot_archetype = entry.get("pilot_archetype", "")
    audience = entry.get("audience", "")
    tier = entry.get("tier", 0)

    # Use a representative URL for resolver input — the homepage. The
    # resolver normalizes to a URL pattern internally.
    url = f"https://{domain}/"

    try:
        from adam.intelligence.url_intelligence import resolve_url_intelligence
        from adam.intelligence.page_intelligence import (
            PagePsychologicalProfile,
            _url_to_pattern,
            _extract_domain,
        )
    except Exception as exc:
        return False, None, f"import failed: {exc}"

    try:
        resolved = resolve_url_intelligence(url)
    except Exception as exc:
        return False, None, f"resolver failed for {domain}: {exc}"

    edge_dims = resolved.get("edge_dimensions", {}) if resolved else {}
    if not edge_dims:
        # Resolver returned nothing usable — skip rather than write an
        # empty profile that would shadow the cascade's own request-time
        # resolution.
        return False, None, f"resolver produced no edge_dimensions for {domain}"

    confidence = _TIER_CONFIDENCE.get(tier, _DEFAULT_TIER_CONFIDENCE)

    # Build profile. Pilot metadata lives on existing fields:
    #   - profile_source carries "luxy_pilot_curated_tier_{N}" as the
    #     debugging-visible provenance string
    #   - mindset carries the pilot archetype label as descriptive text
    #   - primary_topic carries the audience label
    # No new schema fields; no shadowing of the cascade's canonical
    # archetype routing.
    pattern = _url_to_pattern(url)
    domain_extracted = _extract_domain(url) or domain

    profile = PagePsychologicalProfile(
        url_pattern=pattern,
        domain=domain_extracted,
        last_crawled=time.time(),
        edge_dimensions=edge_dims,
        construct_activations=edge_dims,
        confidence=confidence,
        profile_source=f"luxy_pilot_curated_tier_{tier}",
        edge_scoring_tier=f"luxy_pilot_curated_tier_{tier}",
        mindset=pilot_archetype or "unknown",
        primary_topic=audience or "",
    )
    # Set emotional / cognitive fields from edge_dimensions (matches the
    # taxonomy-fallback path in PageIntelligenceCache.lookup).
    profile.emotional_valence = edge_dims.get("regulatory_fit", 0.5) * 2 - 1
    profile.emotional_arousal = edge_dims.get("emotional_resonance", 0.5)
    profile.cognitive_load = 1.0 - edge_dims.get("cognitive_load_tolerance", 0.5)

    if dry_run:
        return True, f"DRY_RUN:{domain_extracted}", None

    try:
        from adam.intelligence.page_intelligence import get_page_intelligence_cache
        cache = get_page_intelligence_cache()
        ok = cache.store(profile)
    except Exception as exc:
        return False, None, f"store failed for {domain}: {exc}"

    if not ok:
        return False, None, f"store returned False for {domain} (Redis unavailable?)"

    return True, f"informativ:page:{pattern}", None


def populate_luxy_pages(
    mapping_path: Optional[Path] = None,
    dry_run: bool = False,
) -> PopulationResult:
    """End-to-end populator. Reads the LUXY mapping, writes profiles.

    On dry_run=True: walks the entries, runs the resolver, but does NOT
    write to Redis. Returns the summary so the run is auditable before
    committing.
    """
    result = PopulationResult(dry_run=dry_run)

    try:
        entries = load_luxy_mapping(mapping_path)
    except (FileNotFoundError, ValueError) as exc:
        result.errors.append(f"mapping load failed: {exc}")
        return result

    for entry in entries:
        ok, key, err = populate_one_entry(entry, dry_run=dry_run)
        if ok:
            result.written += 1
            if key:
                result.written_keys.append(key)
        else:
            result.skipped += 1
            if err:
                result.errors.append(err)

    logger.info(
        "LUXY page populator: written=%d skipped=%d errors=%d dry_run=%s",
        result.written, result.skipped, len(result.errors), dry_run,
    )
    return result
