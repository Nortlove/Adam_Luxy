"""S3.2 — offline page-priming pipeline tests.

Per directive §S3.2: pipeline runs offline; output is
PagePrimingSignature persisted to Feature Store. Tests pin:
  - URL-to-hash determinism
  - ContentProfiler-output → PagePrimingSignature mapper invariants
  - Pipeline orchestration (fetch → profile → map → persist)
  - Failure paths (fetch exception, HTTP error, profile exception)
  - Batched concurrency
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.priming import PagePrimingSignature
from adam.priming.pipeline import (
    FetchedPage,
    PipelineResult,
    batch_process_urls,
    map_profile_to_signature,
    profile_url_to_signature,
    url_to_hash,
)


# ----------------------------------------------------------------------------
# url_to_hash determinism
# ----------------------------------------------------------------------------

class TestUrlToHash:
    def test_deterministic(self):
        h1 = url_to_hash("https://example.com/x")
        h2 = url_to_hash("https://example.com/x")
        assert h1 == h2

    def test_strip_whitespace(self):
        assert url_to_hash("  https://e.com/x  ") == url_to_hash("https://e.com/x")

    def test_different_urls_different_hash(self):
        assert url_to_hash("https://e.com/a") != url_to_hash("https://e.com/b")

    def test_hash_is_64_char_hex(self):
        h = url_to_hash("https://e.com")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ----------------------------------------------------------------------------
# Mapper: ContentProfiler output → PagePrimingSignature
# ----------------------------------------------------------------------------

def _profile_with(**overrides):
    """Helper to build a ContentProfiler-shaped profile dict."""
    base = {
        "ndf_profile": {
            "approach_avoidance": 0.5, "temporal_horizon": 0.5,
            "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
            "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
            "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
        },
        "mechanisms": [],
        "emotions": {},
        "confidence": 0.5,
        "segments": [], "constructs": {}, "mechanism_scores": [],
    }
    base.update(overrides)
    return base


class TestMapperValence:
    def test_neutral_profile_yields_zero_valence(self):
        sig = map_profile_to_signature("https://e.com", _profile_with())
        assert abs(sig.valence) < 0.01

    def test_positive_emotions_drive_valence_up(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            emotions={"joy": 1.0, "trust": 0.5},
        ))
        assert sig.valence > 0.3

    def test_fear_drives_valence_down(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            emotions={"fear": 1.0},
        ))
        assert sig.valence < -0.3

    def test_approach_avoidance_high_pushes_valence_positive(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.9, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
        ))
        assert sig.valence > 0.3

    def test_valence_clipped_to_minus_one_one(self):
        # Extreme emotion ratios should not exceed bounds
        sig = map_profile_to_signature("https://e.com", _profile_with(
            emotions={"joy": 100.0, "trust": 100.0, "excitement": 100.0},
            ndf_profile={
                "approach_avoidance": 1.0, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
        ))
        assert -1.0 <= sig.valence <= 1.0


class TestMapperArousal:
    def test_arousal_in_range(self):
        sig = map_profile_to_signature("https://e.com", _profile_with())
        assert 0.0 <= sig.arousal <= 1.0

    def test_emotions_increase_arousal(self):
        base = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.5, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
            emotions={},
        ))
        with_emo = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.5, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
            emotions={"excitement": 1.0, "joy": 1.0},
        ))
        assert with_emo.arousal > base.arousal


class TestMapperRegulatoryFocus:
    def test_high_approach_avoidance_promotion(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.8, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
        ))
        assert sig.regulatory_focus_priming == "promotion"

    def test_low_approach_avoidance_prevention(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.2, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
        ))
        assert sig.regulatory_focus_priming == "prevention"

    def test_loss_aversion_mechanism_prevention(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            mechanisms=["loss_aversion"],
        ))
        assert sig.regulatory_focus_priming == "prevention"

    def test_reciprocity_mechanism_promotion(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            mechanisms=["reciprocity"],
        ))
        assert sig.regulatory_focus_priming == "promotion"

    def test_neutral_default(self):
        sig = map_profile_to_signature("https://e.com", _profile_with())
        assert sig.regulatory_focus_priming == "neutral"

    def test_promotion_and_prevention_signals_collide_to_neutral(self):
        # Both signals fire → neutral by design (ambiguity)
        sig = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.8, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.5,
            },
            mechanisms=["loss_aversion"],
        ))
        assert sig.regulatory_focus_priming == "neutral"


class TestMapperCognitiveLoad:
    def test_high_velocity_low_load(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.5, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.9,
            },
        ))
        assert sig.cognitive_load_estimate < 0.2

    def test_low_velocity_high_load(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            ndf_profile={
                "approach_avoidance": 0.5, "temporal_horizon": 0.5,
                "social_calibration": 0.5, "uncertainty_tolerance": 0.5,
                "status_sensitivity": 0.5, "cognitive_engagement": 0.5,
                "arousal_seeking": 0.5, "cognitive_velocity": 0.1,
            },
        ))
        assert sig.cognitive_load_estimate > 0.8


class TestMapperFrames:
    def test_top_5_mechanisms_become_frames(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            mechanisms=["social_proof", "scarcity", "authority",
                        "reciprocity", "liking", "anchoring"],
        ))
        assert sig.activated_frames == (
            "social_proof", "scarcity", "authority",
            "reciprocity", "liking",
        )
        assert len(sig.activated_frames) == 5

    def test_empty_mechanisms_yield_empty_tuple(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            mechanisms=[],
        ))
        assert sig.activated_frames == tuple()


class TestMapperConfidence:
    def test_overall_confidence_distributes_to_dims(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            confidence=0.8, emotions={"joy": 1.0},
        ))
        assert all(0.0 <= v <= 1.0
                   for v in sig.confidence_per_dimension.values())
        # Emotion-derived dims should get the higher emo_factor (0.7)
        assert sig.confidence_per_dimension["valence"] > 0.4

    def test_no_emotions_lowers_emotion_dim_confidence(self):
        sig = map_profile_to_signature("https://e.com", _profile_with(
            confidence=0.8, emotions={},
        ))
        # emo_factor = 0.3 → 0.8 * 0.3 = 0.24
        assert sig.confidence_per_dimension["valence"] < 0.4


# ----------------------------------------------------------------------------
# profile_url_to_signature — orchestration
# ----------------------------------------------------------------------------

def _ok_page(url="https://e.com/x"):
    return FetchedPage(
        url=url, title="Title", body="Body text content with discover learn explore",
        fetched_at=datetime.now(tz=timezone.utc), http_status=200,
    )


class TestProfileUrlToSignature:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        async def fetcher(u): return _ok_page(u)
        profiler = MagicMock()
        profiler.profile = AsyncMock(return_value=_profile_with(
            confidence=0.7, mechanisms=["social_proof"],
            emotions={"trust": 0.5},
        ))
        result = await profile_url_to_signature(
            "https://e.com/x", fetcher, profiler,
        )
        assert result.succeeded
        assert result.signature is not None
        assert result.signature.activated_frames == ("social_proof",)

    @pytest.mark.asyncio
    async def test_fetch_exception_falls_back_to_neutral(self):
        async def fetcher(u): raise ConnectionError("dns_fail")
        profiler = MagicMock()
        profiler.profile = AsyncMock()
        result = await profile_url_to_signature(
            "https://e.com/x", fetcher, profiler,
            fallback_to_neutral_on_failure=True,
        )
        assert result.signature is not None
        assert "fetch_exception" in result.fetch_failure
        # Profiler not called on fetch failure
        profiler.profile.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_exception_no_fallback_returns_none(self):
        async def fetcher(u): raise ConnectionError("dns_fail")
        profiler = MagicMock()
        profiler.profile = AsyncMock()
        result = await profile_url_to_signature(
            "https://e.com/x", fetcher, profiler,
            fallback_to_neutral_on_failure=False,
        )
        assert result.signature is None
        assert result.fetch_failure is not None

    @pytest.mark.asyncio
    async def test_http_error_falls_back_to_neutral(self):
        page = FetchedPage(
            url="https://e.com/x", title="", body="",
            fetched_at=datetime.now(tz=timezone.utc),
            http_status=404,
        )
        async def fetcher(u): return page
        profiler = MagicMock()
        profiler.profile = AsyncMock()
        result = await profile_url_to_signature(
            "https://e.com/x", fetcher, profiler,
        )
        assert result.signature is not None
        assert "http_404" in result.fetch_failure

    @pytest.mark.asyncio
    async def test_profile_exception_falls_back(self):
        async def fetcher(u): return _ok_page(u)
        profiler = MagicMock()
        profiler.profile = AsyncMock(side_effect=ValueError("profile bug"))
        result = await profile_url_to_signature(
            "https://e.com/x", fetcher, profiler,
        )
        assert result.signature is not None
        assert "profile_exception" in result.profile_failure


# ----------------------------------------------------------------------------
# batch_process_urls
# ----------------------------------------------------------------------------

class TestBatchPipeline:
    @pytest.mark.asyncio
    async def test_processes_all_urls(self):
        async def fetcher(u): return _ok_page(u)
        profiler = MagicMock()
        profiler.profile = AsyncMock(return_value=_profile_with())
        urls = [f"https://e.com/p{i}" for i in range(10)]
        results = await batch_process_urls(urls, fetcher, profiler)
        assert len(results) == 10
        assert all(r.succeeded for r in results)

    @pytest.mark.asyncio
    async def test_persist_fn_called_per_signature(self):
        async def fetcher(u): return _ok_page(u)
        profiler = MagicMock()
        profiler.profile = AsyncMock(return_value=_profile_with())
        persist_calls = []
        async def persist(sig: PagePrimingSignature) -> bool:
            persist_calls.append(sig.url_hash)
            return True
        urls = ["https://e.com/a", "https://e.com/b"]
        await batch_process_urls(urls, fetcher, profiler, persist_fn=persist)
        assert len(persist_calls) == 2

    @pytest.mark.asyncio
    async def test_partial_failures_persist_fallback_signatures(self):
        async def fetcher(u):
            if "fail" in u:
                raise ConnectionError("x")
            return _ok_page(u)
        profiler = MagicMock()
        profiler.profile = AsyncMock(return_value=_profile_with())
        persist_calls = []
        async def persist(sig: PagePrimingSignature) -> bool:
            persist_calls.append(sig.url_hash)
            return True
        urls = ["https://e.com/ok", "https://e.com/fail"]
        results = await batch_process_urls(
            urls, fetcher, profiler, persist_fn=persist,
            fallback_to_neutral_on_failure=True,
        )
        # Both persisted (one OK, one neutral fallback)
        assert len(persist_calls) == 2
        assert results[0].succeeded
        assert results[1].fetch_failure is not None
        # But neutral signature still persisted
        assert results[1].signature is not None

    @pytest.mark.asyncio
    async def test_results_in_input_order(self):
        async def fetcher(u): return _ok_page(u)
        profiler = MagicMock()
        profiler.profile = AsyncMock(return_value=_profile_with())
        urls = [f"https://e.com/p{i}" for i in range(5)]
        results = await batch_process_urls(urls, fetcher, profiler)
        assert [r.url for r in results] == urls
