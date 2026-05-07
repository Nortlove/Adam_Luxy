"""C / S6-prep.3a — fomo_score + psych_ownership_proxy derived
composite states on PageMindstateVector.

Per slice spec: pin derivation correctness + range invariants +
bid-time latency + trait × state composability + zero-regression
on existing PageMindstateVector behavior + constants tunability.

References:
    Cialdini, R. (2009/2016). Influence: Science and Practice.
    Higgins, E. T. (1997). Beyond pleasure and pain.
    Pham, M. T., & Higgins, E. T. (2005). Promotion and prevention
        in consumer decision making.
    Pierce, J. L., Kostova, T., & Dirks, K. T. (2001). Toward a
        theory of psychological ownership in organizations.
        Academy of Management Review, 26(2), 298-310.
    Kahneman, D., Knetsch, J. L., & Thaler, R. H. (1990).
        Experimental tests of the endowment effect and the Coase
        theorem. JPE 98(6), 1325-1348.
    Przybylski, A. K. et al. (2013). Motivational, emotional, and
        behavioral correlates of fear of missing out. Computers in
        Human Behavior, 29(4), 1841-1848.
"""
import time

import pytest

from adam.cold_start.priors.maximizer_tendency import (
    ARCHETYPE_MAXIMIZER_PRIORS,
)
from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.resonance.models import (
    FOMO_REGULATORY_NEUTRAL_MODIFIER,
    FOMO_REGULATORY_PREVENTION_MODIFIER,
    FOMO_REGULATORY_PROMOTION_MODIFIER,
    FOMO_SCARCITY_FRAME_NAME,
    PSYCH_OWNERSHIP_DECAY_WINDOW_DAYS,
    PSYCH_OWNERSHIP_TARGET_DWELL_SECONDS,
    PageMindstateVector,
)


# ---------------------------------------------------------------------------
# FOMO derivation tests
# ---------------------------------------------------------------------------

class TestFomoScoreDerivation:

    def test_default_mindstate_yields_zero(self):
        """Default PageMindstateVector → fomo_score = 0.0
        (arousal=0.5 default; no scarcity frame; neutral focus —
        scarcity_indicator=0 zeros the product)."""
        m = PageMindstateVector()
        assert m.fomo_score == 0.0

    def test_pure_scarcity_frame_without_arousal_yields_zero(self):
        """Scarcity frame present but arousal=0.0 → 0.0."""
        m = PageMindstateVector(
            emotional_arousal=0.0,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )
        assert m.fomo_score == 0.0

    def test_promotion_scarcity_high_arousal_yields_high_fomo(self):
        """arousal=0.8 × scarcity × promotion (1.2 modifier)
        = 0.96."""
        m = PageMindstateVector(
            emotional_arousal=0.8,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )
        assert abs(m.fomo_score - 0.96) < 1e-9

    def test_prevention_yields_lower_fomo_than_promotion(self):
        """Same arousal+scarcity but prevention focus
        (0.8 modifier) → 0.64; strictly less than promotion case."""
        m_prev = PageMindstateVector(
            emotional_arousal=0.8,
            scarcity_frame_present=True,
            regulatory_focus_priming="prevention",
        )
        m_prom = PageMindstateVector(
            emotional_arousal=0.8,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )
        assert abs(m_prev.fomo_score - 0.64) < 1e-9
        assert m_prev.fomo_score < m_prom.fomo_score

    def test_neutral_focus_uses_unit_modifier(self):
        """Neutral focus modifier = 1.0; arousal × 1.0 × 1.0
        = arousal directly."""
        m = PageMindstateVector(
            emotional_arousal=0.5,
            scarcity_frame_present=True,
            regulatory_focus_priming="neutral",
        )
        assert abs(m.fomo_score - 0.5) < 1e-9

    @pytest.mark.parametrize("arousal", [0.0, 0.25, 0.5, 0.75, 1.0])
    @pytest.mark.parametrize("scarcity", [True, False])
    @pytest.mark.parametrize(
        "focus", ["promotion", "prevention", "neutral"],
    )
    def test_range_invariant_fuzz(self, arousal, scarcity, focus):
        """Across all combinations of arousal × scarcity × focus,
        fomo_score ∈ [0, 1]."""
        m = PageMindstateVector(
            emotional_arousal=arousal,
            scarcity_frame_present=scarcity,
            regulatory_focus_priming=focus,
        )
        assert 0.0 <= m.fomo_score <= 1.0

    def test_clipping_at_one(self):
        """arousal=0.95 × scarcity × promotion → raw 1.14 → 1.0."""
        m = PageMindstateVector(
            emotional_arousal=0.95,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )
        assert m.fomo_score == 1.0


# ---------------------------------------------------------------------------
# Psychological ownership derivation tests
# ---------------------------------------------------------------------------

class TestPsychOwnershipProxyDerivation:

    def test_cold_start_user_yields_zero(self):
        """touch_count=0, dwell=0 → psych_ownership_proxy = 0.0
        (touch_density = 0 zeros the product)."""
        m = PageMindstateVector(
            touch_count=0,
            dwell_seconds=0,
            ndf_activations={"temporal_horizon": 0.5},
        )
        assert m.psych_ownership_proxy == 0.0

    def test_heavy_touch_present_focus_yields_high(self):
        """touch_count=8 (= 1+decay_window=8 → density saturates at 1.0)
        × dwell 120s (= 2× target → saturates at 1.0)
        × presentness 1.0 (temporal_horizon=0.0)
        = 1.0."""
        m = PageMindstateVector(
            touch_count=8,
            dwell_seconds=120,
            ndf_activations={"temporal_horizon": 0.0},
        )
        assert m.psych_ownership_proxy == 1.0

    def test_heavy_touch_future_focused_yields_lower(self):
        """Same touch+dwell but future-focused (temporal_horizon=0.8)
        → 1.0 × 1.0 × 0.2 = 0.2; strictly less than present-focus
        case."""
        m_future = PageMindstateVector(
            touch_count=8,
            dwell_seconds=120,
            ndf_activations={"temporal_horizon": 0.8},
        )
        m_present = PageMindstateVector(
            touch_count=8,
            dwell_seconds=120,
            ndf_activations={"temporal_horizon": 0.0},
        )
        assert abs(m_future.psych_ownership_proxy - 0.2) < 1e-9
        assert m_future.psych_ownership_proxy < m_present.psych_ownership_proxy

    def test_dwell_saturates_at_target(self):
        """dwell=300s (5× target) → dwell_normalized saturated at 1.0,
        not 5.0. Combined with touch=5 (5/8=0.625) and present-focus
        (1.0): 0.625 × 1.0 × 1.0 = 0.625."""
        m = PageMindstateVector(
            touch_count=5,
            dwell_seconds=300,
            ndf_activations={"temporal_horizon": 0.0},
        )
        assert abs(m.psych_ownership_proxy - 0.625) < 1e-9

    @pytest.mark.parametrize("touch_count", [0, 1, 5, 10, 20])
    @pytest.mark.parametrize("dwell", [0, 30, 60, 200, 600])
    @pytest.mark.parametrize("temporal_horizon", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_range_invariant_fuzz(self, touch_count, dwell, temporal_horizon):
        """Across realistic combinations, psych_ownership_proxy
        ∈ [0, 1]."""
        m = PageMindstateVector(
            touch_count=touch_count,
            dwell_seconds=dwell,
            ndf_activations={"temporal_horizon": temporal_horizon},
        )
        assert 0.0 <= m.psych_ownership_proxy <= 1.0


# ---------------------------------------------------------------------------
# Cross-cutting tests
# ---------------------------------------------------------------------------

class TestCrossCutting:

    def test_both_composites_coexist_on_same_vector(self):
        """A single PageMindstateVector exposes both .fomo_score and
        .psych_ownership_proxy without interference."""
        m = PageMindstateVector(
            emotional_arousal=0.7,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
            touch_count=5,
            dwell_seconds=90,
            ndf_activations={"temporal_horizon": 0.2},
        )
        # FOMO: 0.7 × 1.0 × 1.2 = 0.84
        assert abs(m.fomo_score - 0.84) < 1e-9
        # Ownership: min(1, 5/8) × min(1, 90/60) × (1 - 0.2)
        #          = 0.625 × 1.0 × 0.8 = 0.5
        assert abs(m.psych_ownership_proxy - 0.5) < 1e-9

    def test_bid_time_latency_under_one_ms_p99(self):
        """Time both derivations across 10,000 randomly-parameterized
        instances. Both must fit a per-derivation budget; the
        per-derivation p99 should be well under 1ms (microseconds-
        scale arithmetic). We measure the per-call elapsed and
        assert the 99th percentile is < 1ms (1000μs)."""
        import random

        rng = random.Random(2026)
        latencies_us = []
        for _ in range(10000):
            m = PageMindstateVector(
                emotional_arousal=rng.random(),
                scarcity_frame_present=rng.choice([True, False]),
                regulatory_focus_priming=rng.choice(
                    ["promotion", "prevention", "neutral"],
                ),
                touch_count=rng.randint(0, 20),
                dwell_seconds=rng.uniform(0, 600),
                ndf_activations={"temporal_horizon": rng.random()},
            )
            t0 = time.perf_counter()
            _ = m.fomo_score
            _ = m.psych_ownership_proxy
            elapsed_us = (time.perf_counter() - t0) * 1_000_000
            latencies_us.append(elapsed_us)

        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        # Per-call (BOTH derivations together) p99 < 1ms = 1000μs is
        # the slice's stated budget. In practice this is microseconds
        # (cached-field arithmetic), so a 1000μs ceiling is generous.
        assert p99 < 1000.0, (
            f"p99 latency {p99:.1f}μs exceeds 1ms budget for both "
            f"derivations combined"
        )

    def test_trait_x_state_composability_with_archetype_priors(self):
        """Two PageMindstateVectors with different FOMO states
        applied to the same ANALYST archetype's maximizer_tendency
        Beta prior. Pins the multiplicative trait × state pattern:
        same trait, different state → different combined response.

        State A (high-FOMO, promotion-amplified) > State B (neutral
        focus) when combined with the same trait posterior mean.
        """
        analyst_prior = ARCHETYPE_MAXIMIZER_PRIORS[ArchetypeID.ANALYST]
        analyst_trait_mean = (
            analyst_prior.alpha
            / (analyst_prior.alpha + analyst_prior.beta)
        )

        state_a = PageMindstateVector(
            emotional_arousal=0.85,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )
        state_b = PageMindstateVector(
            emotional_arousal=0.85,
            scarcity_frame_present=True,
            regulatory_focus_priming="neutral",
        )

        combined_a = analyst_trait_mean * state_a.fomo_score
        combined_b = analyst_trait_mean * state_b.fomo_score

        assert combined_a > combined_b, (
            f"trait × state composability broken: "
            f"promotion-amplified={combined_a:.4f} not > "
            f"neutral={combined_b:.4f}"
        )

    def test_zero_regression_on_existing_pmv_behavior(self):
        """Construct a PageMindstateVector populating ONLY the
        pre-C fields. All pre-C field values + to_numpy() projection
        unchanged. New fields take safe defaults; new derivations
        return 0.0 (no scarcity, no touch)."""
        m = PageMindstateVector(
            edge_dimensions={"regulatory_fit": 0.7},
            ndf_activations={"approach_avoidance": 0.6},
            mechanism_susceptibility={"social_proof": 0.5},
            emotional_valence=0.4,
            emotional_arousal=0.3,
            cognitive_load=0.5,
            publisher_authority=0.7,
            remaining_bandwidth=0.5,
            url_pattern="https://example.com/x",
            domain="example.com",
            confidence=0.6,
            scoring_tier="full_extraction",
        )
        # Pre-C fields unchanged.
        assert m.edge_dimensions == {"regulatory_fit": 0.7}
        assert m.emotional_valence == 0.4
        assert m.emotional_arousal == 0.3
        assert m.publisher_authority == 0.7
        # to_numpy() still produces a 32-dim vector (NEW fields are
        # NOT in the projection — they're side-channel derivation
        # inputs only).
        vec = m.to_numpy()
        assert vec.shape == (32,)
        # New defaults applied.
        assert m.scarcity_frame_present is False
        assert m.regulatory_focus_priming == "neutral"
        assert m.touch_count == 0
        assert m.dwell_seconds == 0.0
        # New derivations return 0.0 (no scarcity, no touch).
        assert m.fomo_score == 0.0
        assert m.psych_ownership_proxy == 0.0


# ---------------------------------------------------------------------------
# Constants tunability
# ---------------------------------------------------------------------------

class TestConstantsTunability:

    def test_fomo_modifier_constants_match_spec_defaults(self):
        """Module-level constants are the tunable surface."""
        assert FOMO_REGULATORY_PROMOTION_MODIFIER == 1.2
        assert FOMO_REGULATORY_PREVENTION_MODIFIER == 0.8
        assert FOMO_REGULATORY_NEUTRAL_MODIFIER == 1.0

    def test_fomo_promotion_strictly_greater_than_prevention(self):
        """Pham-Higgins regulatory-fit asymmetry: promotion > prevention
        must hold for FOMO amplification direction to remain correct."""
        assert (
            FOMO_REGULATORY_PROMOTION_MODIFIER
            > FOMO_REGULATORY_NEUTRAL_MODIFIER
            > FOMO_REGULATORY_PREVENTION_MODIFIER
        )

    def test_scarcity_frame_name_matches_mechanism_keywords(self):
        """The constant must match the canonical mechanism name in
        ContentProfiler.MECHANISM_KEYWORDS so 'scarcity' detected on
        a page properly populates activated_frames + flips
        scarcity_frame_present at orchestrator input time."""
        assert FOMO_SCARCITY_FRAME_NAME == "scarcity"

    def test_psych_ownership_constants_match_spec_defaults(self):
        assert PSYCH_OWNERSHIP_DECAY_WINDOW_DAYS == 7.0
        assert PSYCH_OWNERSHIP_TARGET_DWELL_SECONDS == 60.0
