"""Pin the argument cache layer — sync read on cascade hot path, soft-fail
on Redis unavailable, mechanism + archetype round-trip discipline.

Discipline anchors:
    - The cascade hot path runs in <120ms (handoff §reference architecture).
      get_cached_argument MUST be sync (no asyncio bridge), MUST never
      raise, MUST return None on every error path. A cache read that
      raises on the bid path would cascade-fail the entire StackAdapt
      response.
    - Cache key includes CONSTITUTION_VERSION. A bump invalidates every
      key from the prior version. This test pins that the version is
      part of the key so a future refactor can't silently strip it.
    - Mechanism / archetype mismatch returns miss rather than serving
      a wrong-mechanism creative. The mechanism_faithful principle in
      the constitution is meaningless if a cached argument audited under
      mechanism A can be served for mechanism B.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from adam.intelligence.argument_constitution import CONSTITUTION_VERSION
from adam.intelligence.argument_cache import (
    CachedArgument,
    assemble_primary_text,
    barrier_hash,
    cache_key,
    get_cached_argument,
    invalidate_cached_argument,
    put_cached_argument,
)


# -----------------------------------------------------------------------------
# Key derivation — stability and version inclusion
# -----------------------------------------------------------------------------


def test_cache_key_includes_constitution_version():
    """A constitution bump must invalidate caches; the version dimension
    is part of the key."""
    key = cache_key("luxy", "status_seeker", "social_proof", "trust_deficit")
    assert CONSTITUTION_VERSION in key


def test_cache_key_is_case_insensitive_on_archetype_and_mechanism():
    """Cascade may pass mixed casing; cache must not fragment."""
    a = cache_key("luxy", "STATUS_SEEKER", "Social_Proof", "trust_deficit")
    b = cache_key("luxy", "status_seeker", "social_proof", "trust_deficit")
    assert a == b


def test_cache_key_preserves_brand_id_case():
    """Brand ids carry case meaningfully in StackAdapt's namespace."""
    a = cache_key("LUXY", "status_seeker", "social_proof", "trust_deficit")
    b = cache_key("luxy", "status_seeker", "social_proof", "trust_deficit")
    assert a != b


def test_cache_key_distinguishes_barriers():
    """Same (brand × archetype × mechanism) carries different arguments
    per diagnosed barrier — the barrier_hash dimension keeps them
    distinct in cache."""
    a = cache_key("luxy", "status_seeker", "social_proof", "trust_deficit")
    b = cache_key("luxy", "status_seeker", "social_proof", "price_objection")
    assert a != b


def test_barrier_hash_is_stable():
    """Hash must be deterministic across calls so cache lookups land on
    the same key the writer used."""
    assert barrier_hash("trust_deficit") == barrier_hash("trust_deficit")
    assert barrier_hash("trust_deficit") != barrier_hash("price_objection")


def test_barrier_hash_handles_empty_string():
    """Empty barrier must not raise — the cascade may not always have
    a diagnosed barrier."""
    h = barrier_hash("")
    assert isinstance(h, str)
    assert len(h) == 8


# -----------------------------------------------------------------------------
# Read path — sync, soft-fails on every error
# -----------------------------------------------------------------------------


def test_get_returns_none_when_redis_unavailable():
    """Cascade hot path must not crash when Redis is down."""
    with patch("adam.infrastructure.redis_client.get_redis", return_value=None):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


def test_get_returns_none_on_cache_miss():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


def test_get_returns_argument_on_cache_hit():
    arg = CachedArgument(
        headline="Discreet luxury for those who already know",
        body="Bespoke chauffeur service used by the people you used to read about",
        cta="Reserve your private rider profile",
        barrier_addressed="trust_deficit",
        archetype_fit_score=0.91,
        factscore=0.97,
        iterations_to_converge=2,
        mechanism_audited="social_proof",
        archetype_audited="status_seeker",
    )
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps({
        "headline": arg.headline, "body": arg.body, "cta": arg.cta,
        "barrier_addressed": arg.barrier_addressed,
        "archetype_fit_score": arg.archetype_fit_score,
        "factscore": arg.factscore,
        "iterations_to_converge": arg.iterations_to_converge,
        "constitution_version": CONSTITUTION_VERSION,
        "mechanism_audited": arg.mechanism_audited,
        "archetype_audited": arg.archetype_audited,
        "provenance": {},
    }))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is not None
    assert result.headline == arg.headline
    assert result.factscore == 0.97


def test_get_handles_redis_exception_silently():
    """Redis client raises mid-read → cache treated as miss, cascade
    continues."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(side_effect=ConnectionError("network blip"))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


def test_get_handles_malformed_json_silently():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value="not json {{{ ")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


def test_get_handles_schema_drift_silently():
    """Cached payload was written under an older shape — no required
    fields. Must return None, not crash."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps({
        "totally_unknown_field": "drift",
    }))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


def test_get_handles_bytes_payload():
    """Some redis clients return bytes; must decode."""
    payload_dict = {
        "headline": "test", "body": "", "cta": "",
        "barrier_addressed": "", "archetype_fit_score": 0.9,
        "factscore": 0.96, "iterations_to_converge": 1,
        "constitution_version": CONSTITUTION_VERSION,
        "mechanism_audited": "social_proof",
        "archetype_audited": "status_seeker",
        "provenance": {},
    }
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps(payload_dict).encode("utf-8"))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is not None
    assert result.headline == "test"


# -----------------------------------------------------------------------------
# Mechanism / archetype round-trip discipline
# -----------------------------------------------------------------------------


def test_get_returns_none_on_mechanism_mismatch():
    """A cached argument audited against authority must NEVER be served
    for a cascade decision that resolved social_proof. The
    mechanism_faithful principle is the architectural commitment to the
    construct vocabulary — silently substituting mechanisms severs the
    decision-to-creative attribution chain."""
    payload_dict = {
        "headline": "test", "body": "", "cta": "",
        "barrier_addressed": "", "archetype_fit_score": 0.9,
        "factscore": 0.96, "iterations_to_converge": 1,
        "constitution_version": CONSTITUTION_VERSION,
        "mechanism_audited": "authority",         # cached against authority
        "archetype_audited": "status_seeker",
        "provenance": {},
    }
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps(payload_dict))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        # Cascade asks for social_proof — must miss
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


def test_get_returns_none_on_archetype_mismatch():
    payload_dict = {
        "headline": "test", "body": "", "cta": "",
        "barrier_addressed": "", "archetype_fit_score": 0.9,
        "factscore": 0.96, "iterations_to_converge": 1,
        "constitution_version": CONSTITUTION_VERSION,
        "mechanism_audited": "social_proof",
        "archetype_audited": "skeptical_analyst",  # cached against different archetype
        "provenance": {},
    }
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps(payload_dict))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert result is None


# -----------------------------------------------------------------------------
# Write path — stamps round-trip metadata, soft-fails
# -----------------------------------------------------------------------------


def test_put_writes_under_canonical_key():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    arg = CachedArgument(headline="h", body="b", cta="c")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = put_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit", arg,
        )
    assert ok is True
    redis_mock.set.assert_called_once()
    key = redis_mock.set.call_args.args[0]
    expected = cache_key("luxy", "status_seeker", "social_proof", "trust_deficit")
    assert key == expected


def test_put_stamps_round_trip_metadata():
    """Writer must stamp mechanism_audited + archetype_audited +
    constitution_version onto the argument so reader-side mismatch
    detection has something to compare against. A writer that forgets
    to stamp would cache arguments that always pass the round-trip
    check (because mismatch would never trigger), defeating the
    discipline."""
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    # Pass an argument with all stamps absent
    arg = CachedArgument(headline="h", body="b", cta="c")
    assert arg.mechanism_audited == ""
    assert arg.archetype_audited == ""
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        put_cached_argument("luxy", "status_seeker", "social_proof", "trust_deficit", arg)

    payload = redis_mock.set.call_args.args[1]
    parsed = json.loads(payload)
    assert parsed["mechanism_audited"] == "social_proof"
    assert parsed["archetype_audited"] == "status_seeker"
    assert parsed["constitution_version"] == CONSTITUTION_VERSION


def test_put_passes_ttl_to_redis():
    """7-day TTL per handoff §6.5. Must be propagated to Redis SET."""
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    arg = CachedArgument(headline="h", body="b", cta="c")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        put_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit", arg,
        )
    kwargs = redis_mock.set.call_args.kwargs
    assert kwargs.get("ex") == 7 * 24 * 3600


def test_put_soft_fails_when_redis_unavailable():
    arg = CachedArgument(headline="h", body="b", cta="c")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=None):
        ok = put_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit", arg,
        )
    assert ok is False


def test_put_soft_fails_when_redis_raises():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock(side_effect=ConnectionError("net"))
    arg = CachedArgument(headline="h", body="b", cta="c")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = put_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit", arg,
        )
    assert ok is False


# -----------------------------------------------------------------------------
# Invalidate
# -----------------------------------------------------------------------------


def test_invalidate_deletes_key():
    redis_mock = MagicMock()
    redis_mock.delete = MagicMock(return_value=1)
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = invalidate_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert ok is True
    redis_mock.delete.assert_called_once()


def test_invalidate_soft_fails_when_unavailable():
    with patch("adam.infrastructure.redis_client.get_redis", return_value=None):
        ok = invalidate_cached_argument(
            "luxy", "status_seeker", "social_proof", "trust_deficit",
        )
    assert ok is False


# -----------------------------------------------------------------------------
# Round-trip — write then read returns same payload
# -----------------------------------------------------------------------------


def test_round_trip_write_then_read():
    """End-to-end: M6 writes, cascade reads, no drift."""
    storage = {}
    redis_mock = MagicMock()
    redis_mock.set = MagicMock(side_effect=lambda k, v, ex=None: storage.update({k: v}))
    redis_mock.get = MagicMock(side_effect=lambda k: storage.get(k))

    arg = CachedArgument(
        headline="Quietly arrived. Already where you wanted to be.",
        body="The chauffeur service of people who don't need to explain themselves",
        cta="Open your private profile",
        barrier_addressed="status_signaling_anxiety",
        archetype_fit_score=0.93,
        factscore=0.97,
        iterations_to_converge=2,
    )
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        put_cached_argument(
            "luxy", "status_seeker", "social_proof", "status_signaling_anxiety", arg,
        )
        result = get_cached_argument(
            "luxy", "status_seeker", "social_proof", "status_signaling_anxiety",
        )

    assert result is not None
    assert result.headline == arg.headline
    assert result.body == arg.body
    assert result.cta == arg.cta
    assert result.archetype_audited == "status_seeker"
    assert result.mechanism_audited == "social_proof"


# -----------------------------------------------------------------------------
# assemble_primary_text — concatenation matches legacy template path shape
# -----------------------------------------------------------------------------


def test_assemble_concatenates_headline_body_cta():
    arg = CachedArgument(headline="H", body="B", cta="C")
    assert assemble_primary_text(arg) == "H B C"


def test_assemble_skips_empty_parts():
    arg = CachedArgument(headline="H", body="", cta="C")
    assert assemble_primary_text(arg) == "H C"


def test_assemble_strips_whitespace():
    arg = CachedArgument(headline="  H  ", body=" B ", cta=" C ")
    assert assemble_primary_text(arg) == "H B C"
