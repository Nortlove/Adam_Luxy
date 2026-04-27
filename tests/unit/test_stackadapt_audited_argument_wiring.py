"""Pin the audited-argument wiring in the StackAdapt creative-intelligence path.

Discipline anchors:
    - The StackAdapt /creative-intelligence endpoint is the LUXY production
      gate. Without this wiring, ClaudeArgumentEngine output never reaches
      the LUXY DSP — the literal 'most powerful mechanism' (handoff §6.1)
      is dark on production traffic.
    - Cache hit must be SYNC and must NOT block the <120ms cascade SLA.
      A misbehaving cache lookup that raises must NOT crash the cascade.
    - Cache miss must fall through to the existing mechanism templates
      cleanly — no behavior change for cells M6 hasn't populated yet.
    - The audited_argument shape is part of the response contract going
      forward; downstream integrations route on it. This test pins the
      shape so a refactor doesn't silently strip fields.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
from adam.api.stackadapt.service import CreativeIntelligenceService
from adam.intelligence.argument_cache import CachedArgument


def _make_ci(primary_mechanism: str = "social_proof") -> CreativeIntelligence:
    return CreativeIntelligence(
        primary_mechanism=primary_mechanism,
        secondary_mechanism="authority",
        framing="gain",
        cascade_level=3,
    )


def _service() -> CreativeIntelligenceService:
    """Build a service WITHOUT triggering Neo4j / Redis / pipeline init.
    The default __init__ leaves _graph_cache=None until lazily initialized;
    _build_copy_guidance does not touch it, so a bare instance is safe."""
    return CreativeIntelligenceService()


# -----------------------------------------------------------------------------
# Cache hit — audited argument flows into copy_guidance
# -----------------------------------------------------------------------------


def test_cache_hit_prepends_headline_and_surfaces_audited_argument():
    """When the audited cache returns a cached argument for this cell,
    the returned copy_guidance must:
      1. Have the cached headline as the FIRST entry in headline_templates
         (so the existing StackAdapt adapter that picks [0] gets it)
      2. Have audited_argument populated with the structured argument
      3. Carry audited_argument_source='cached' for routing visibility
    """
    cached = CachedArgument(
        headline="Quietly arrived. Already where you wanted to be.",
        body="Bespoke chauffeur service for those who don't need to explain.",
        cta="Open your private profile",
        barrier_addressed="status_signaling_anxiety",
        archetype_fit_score=0.91,
        factscore=0.97,
        iterations_to_converge=2,
        mechanism_audited="social_proof",
        archetype_audited="status_seeker",
    )

    svc = _service()
    with patch(
        "adam.intelligence.argument_cache.get_cached_argument",
        return_value=cached,
    ):
        result = svc._build_copy_guidance(
            _make_ci("social_proof"),
            brand_name="LUXY Ride",
            brand_id="lux_luxy_ride",
            archetype="status_seeker",
            barrier="status_signaling_anxiety",
        )

    # Cached headline is FIRST — StackAdapt adapter does headline_templates[0]
    assert result["headline_templates"][0] == cached.headline

    # audited_argument is populated with the full structured shape
    aa = result.get("audited_argument")
    assert aa is not None
    assert aa["headline"] == cached.headline
    assert aa["body"] == cached.body
    assert aa["cta"] == cached.cta
    assert aa["archetype_fit_score"] == 0.91
    assert aa["factscore"] == 0.97

    assert result.get("audited_argument_source") == "cached"


# -----------------------------------------------------------------------------
# Cache miss — falls through to mechanism templates cleanly
# -----------------------------------------------------------------------------


def test_cache_miss_falls_through_to_templates():
    """When the cache returns None (M6 hasn't populated this cell yet),
    the existing mechanism-template path runs unchanged. No
    audited_argument key in the response."""
    svc = _service()
    with patch(
        "adam.intelligence.argument_cache.get_cached_argument",
        return_value=None,
    ):
        result = svc._build_copy_guidance(
            _make_ci("social_proof"),
            brand_name="LUXY Ride",
            brand_id="lux_luxy_ride",
            archetype="status_seeker",
            barrier="trust_deficit",
        )

    # Mechanism template path ran — at least one headline present
    assert len(result["headline_templates"]) >= 1
    # No audited argument flag
    assert "audited_argument" not in result
    assert "audited_argument_source" not in result


def test_cache_unavailable_does_not_crash_cascade():
    """A misbehaving cache lookup that raises must NOT crash the
    cascade — fallback is the template path."""
    svc = _service()
    with patch(
        "adam.intelligence.argument_cache.get_cached_argument",
        side_effect=ConnectionError("redis unreachable"),
    ):
        result = svc._build_copy_guidance(
            _make_ci("social_proof"),
            brand_name="LUXY Ride",
            brand_id="lux_luxy_ride",
            archetype="status_seeker",
            barrier="trust_deficit",
        )

    # Cascade survived; templates rendered
    assert len(result["headline_templates"]) >= 1
    assert "audited_argument" not in result


# -----------------------------------------------------------------------------
# Skip lookup when brand_id / archetype missing
# -----------------------------------------------------------------------------


def test_skip_lookup_when_brand_id_missing():
    """If the cascade resolves a category but no asin/brand_id, the
    cache key would be malformed — skip lookup entirely rather than
    poll a key that can never hit."""
    svc = _service()
    with patch(
        "adam.intelligence.argument_cache.get_cached_argument",
    ) as mock_get:
        svc._build_copy_guidance(
            _make_ci("social_proof"),
            brand_name="LUXY Ride",
            brand_id="",        # ← empty
            archetype="status_seeker",
            barrier="trust_deficit",
        )
    mock_get.assert_not_called()


def test_skip_lookup_when_archetype_missing():
    svc = _service()
    with patch(
        "adam.intelligence.argument_cache.get_cached_argument",
    ) as mock_get:
        svc._build_copy_guidance(
            _make_ci("social_proof"),
            brand_name="LUXY Ride",
            brand_id="lux_luxy_ride",
            archetype="",       # ← empty
            barrier="trust_deficit",
        )
    mock_get.assert_not_called()


# -----------------------------------------------------------------------------
# Backward compatibility — old call signature still works
# -----------------------------------------------------------------------------


def test_old_two_arg_call_signature_still_works():
    """Existing callers that pass only (ci, brand_name) without the new
    brand_id/archetype/barrier kwargs must still receive valid template
    output. New params default to '' so cache lookup is skipped."""
    svc = _service()
    result = svc._build_copy_guidance(
        _make_ci("social_proof"),
        "LUXY Ride",
    )
    assert "headline_templates" in result
    assert len(result["headline_templates"]) >= 1
    assert "audited_argument" not in result
