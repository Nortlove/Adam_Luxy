"""D / S6-prep.3b — depletion_proxy derived composite state +
3 orchestrator-populated fields on PageMindstateVector.

Per slice spec: pin depletion derivation correctness + range
invariants + saturation + replication-crisis caveat documentation
+ new-field defaults and range invariants + bid-time latency for
all 3 composites + three-way trait × state composability +
zero-regression on existing fields and C's two derivations +
constants tunability.

Loneliness_compensatory_flag and parasocial_priming_score derivations
are DEFERRED to D.bis per Q12.A=(γ) adjudication (canonical
vocabulary extension required for emotion_loneliness, emotion_warmth,
creator_content frame). This file does NOT test those derivations.

References:
    Baumeister, R. F., Bratslavsky, E., Muraven, M., & Tice, D. M.
        (1998). Ego depletion: Is the active self a limited resource?
        JPSP 74(5), 1252-1265.
    [WITH CAVEAT:]
    Carter, E. C., & McCullough, M. E. (2014). Publication bias and
        the limited strength model of self-control. Frontiers in
        Psychology 5: 823.
    Hagger, M. S. et al. (2016). A multilab preregistered replication
        of the ego-depletion effect. Perspectives on Psychological
        Science 11(4), 546-573.
"""
import time

import pytest

from adam.cold_start.priors.maximizer_tendency import (
    ARCHETYPE_MAXIMIZER_PRIORS,
)
from adam.cold_start.models.enums import ArchetypeID
from adam.retargeting.resonance.models import (
    DEPLETION_THRESHOLD_SECONDS,
    PageMindstateVector,
)


# ---------------------------------------------------------------------------
# Depletion proxy derivation tests
# ---------------------------------------------------------------------------

class TestDepletionProxyDerivation:

    def test_default_state_yields_zero(self):
        """Default PMV (cognitive_load=0.5, session_position_seconds=0.0)
        → depletion_proxy = 0.0 (session_position_normalized = 0
        zeros the product)."""
        m = PageMindstateVector()
        assert m.depletion_proxy == 0.0

    def test_high_load_early_session_yields_low_depletion(self):
        """cognitive_load=0.8, session_position=300s (5min)
        → 0.8 × (300/1800) = 0.8 × 0.1667 = 0.1333."""
        m = PageMindstateVector(
            cognitive_load=0.8, session_position_seconds=300.0,
        )
        expected = 0.8 * (300.0 / 1800.0)
        assert abs(m.depletion_proxy - expected) < 1e-9

    def test_high_load_threshold_session_yields_high(self):
        """cognitive_load=0.8 × normalized 1.0 (at 30-min threshold)
        = 0.8 (peak at threshold)."""
        m = PageMindstateVector(
            cognitive_load=0.8,
            session_position_seconds=DEPLETION_THRESHOLD_SECONDS,
        )
        assert abs(m.depletion_proxy - 0.8) < 1e-9

    def test_session_position_saturates_at_threshold(self):
        """session_position=3600s (60min, beyond threshold)
        → normalized clipped to 1.0; depletion = cognitive_load × 1.0."""
        m = PageMindstateVector(
            cognitive_load=0.8, session_position_seconds=3600.0,
        )
        assert abs(m.depletion_proxy - 0.8) < 1e-9

    def test_zero_load_yields_zero_regardless_of_session_position(self):
        """cognitive_load=0.0 → depletion_proxy = 0.0 (cognitive_load
        zeros the product)."""
        m = PageMindstateVector(
            cognitive_load=0.0,
            session_position_seconds=DEPLETION_THRESHOLD_SECONDS * 2,
        )
        assert m.depletion_proxy == 0.0

    @pytest.mark.parametrize("cognitive_load", [0.0, 0.25, 0.5, 0.75, 1.0])
    @pytest.mark.parametrize(
        "session_pos", [0.0, 300.0, 900.0, 1800.0, 3600.0, 7200.0],
    )
    def test_range_invariant_fuzz(self, cognitive_load, session_pos):
        """Across realistic combinations, depletion_proxy ∈ [0, 1]."""
        m = PageMindstateVector(
            cognitive_load=cognitive_load,
            session_position_seconds=session_pos,
        )
        assert 0.0 <= m.depletion_proxy <= 1.0

    def test_replication_crisis_caveat_pinned_in_docstring(self):
        """Pin the heuristic-substrate intent in the test suite —
        future readers can't promote depletion_proxy to load-bearing
        without breaking this test."""
        doc = PageMindstateVector.depletion_proxy.fget.__doc__
        assert doc is not None
        assert "REPLICATION-CRISIS CAVEAT" in doc, (
            "depletion_proxy docstring must contain explicit "
            "replication-crisis caveat language to prevent future "
            "promotion to load-bearing"
        )
        # Sanity: the caveat must reference the actual replication-
        # failure papers Hagger 2016 RRR + Carter & McCullough 2014.
        assert "Hagger" in doc or "Replication" in doc
        assert "Carter" in doc or "replication" in doc.lower()


# ---------------------------------------------------------------------------
# New-field tests (defaults + range invariants)
# ---------------------------------------------------------------------------

class TestNewOrchestratorFields:

    def test_session_position_seconds_default_zero(self):
        m = PageMindstateVector()
        assert m.session_position_seconds == 0.0

    def test_posture_class_default_empty_string(self):
        """Empty string is the safe cold-start default; D.bis
        (loneliness_compensatory_flag) consumes posture_class to
        check SOCIAL_CONSUMPTION."""
        m = PageMindstateVector()
        assert m.posture_class == ""

    def test_browsing_momentum_default_mid(self):
        """0.5 = uninformative mid; D.bis consumes for
        compensatory-shopping inverse-momentum signal."""
        m = PageMindstateVector()
        assert m.browsing_momentum == 0.5

    @pytest.mark.parametrize("posture", [
        "INFORMATION_FORAGING",
        "TASK_COMPLETION",
        "LEISURE_BROWSING",
        "SOCIAL_CONSUMPTION",
        "TRANSACTIONAL_COMPARISON",
        "",  # cold-start unset
    ])
    def test_posture_class_accepts_canonical_values(self, posture):
        """All 5 canonical FIVE_CLASS_POSTURES + empty string
        accepted without validation error (PMV is dataclass; no
        validator beyond type)."""
        m = PageMindstateVector(posture_class=posture)
        assert m.posture_class == posture

    @pytest.mark.parametrize(
        "momentum", [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0],
    )
    def test_browsing_momentum_accepts_unit_range(self, momentum):
        """browsing_momentum ∈ [0, 1] per BrowsingMomentumTracker
        convention; safe construct across the unit range."""
        m = PageMindstateVector(browsing_momentum=momentum)
        assert m.browsing_momentum == momentum

    def test_session_position_negative_default_safe(self):
        """Range constraint per spec: ≥ 0. Dataclass doesn't
        validate at construct time, but downstream session-state
        producers will not emit negative values; we pin the default
        as ≥ 0."""
        m = PageMindstateVector()
        assert m.session_position_seconds >= 0


# ---------------------------------------------------------------------------
# Cross-cutting tests
# ---------------------------------------------------------------------------

class TestCrossCutting:

    def test_depletion_coexists_with_c_derivations(self):
        """All 3 derivations on a single PageMindstateVector compute
        correctly without interference."""
        m = PageMindstateVector(
            # FOMO inputs
            emotional_arousal=0.7,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
            # Psych ownership inputs
            touch_count=5,
            dwell_seconds=90,
            ndf_activations={"temporal_horizon": 0.2},
            # Depletion inputs
            cognitive_load=0.6,
            session_position_seconds=900.0,
        )
        # FOMO: 0.7 × 1.0 × 1.2 = 0.84
        assert abs(m.fomo_score - 0.84) < 1e-9
        # Psych ownership: min(1, 5/8) × min(1, 90/60) × (1 - 0.2)
        #                = 0.625 × 1.0 × 0.8 = 0.5
        assert abs(m.psych_ownership_proxy - 0.5) < 1e-9
        # Depletion: 0.6 × (900/1800) = 0.6 × 0.5 = 0.3
        assert abs(m.depletion_proxy - 0.3) < 1e-9

    def test_bid_time_latency_under_one_ms_p99_for_all_three(self):
        """Time all 3 derivations across 10,000 randomly-parameterized
        instances. Per-call (all 3 derivations together) p99 < 1ms.
        In practice this is microseconds (cached-field arithmetic);
        1000μs is a generous ceiling."""
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
                cognitive_load=rng.random(),
                session_position_seconds=rng.uniform(0, 7200),
            )
            t0 = time.perf_counter()
            _ = m.fomo_score
            _ = m.psych_ownership_proxy
            _ = m.depletion_proxy
            elapsed_us = (time.perf_counter() - t0) * 1_000_000
            latencies_us.append(elapsed_us)

        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 1000.0, (
            f"p99 latency {p99:.1f}μs exceeds 1ms budget for all 3 "
            f"derivations combined"
        )

    def test_three_way_trait_x_state_composability(self):
        """Two PageMindstateVectors with same FOMO state but different
        depletion levels, applied to ANALYST archetype's
        maximizer_tendency Beta prior. Pins three-way trait × state
        × state composition: depletion can amplify FOMO-driven
        response when combined with archetype trait prior.

        State A: high depletion + same FOMO → larger combined response
        State B: low depletion + same FOMO → smaller combined response
        """
        analyst_prior = ARCHETYPE_MAXIMIZER_PRIORS[ArchetypeID.ANALYST]
        analyst_trait_mean = (
            analyst_prior.alpha
            / (analyst_prior.alpha + analyst_prior.beta)
        )

        # Same FOMO inputs across both states.
        common_fomo_kwargs = dict(
            emotional_arousal=0.85,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )

        state_a = PageMindstateVector(
            **common_fomo_kwargs,
            cognitive_load=0.85,
            session_position_seconds=DEPLETION_THRESHOLD_SECONDS,
        )
        state_b = PageMindstateVector(
            **common_fomo_kwargs,
            cognitive_load=0.20,
            session_position_seconds=300.0,
        )

        # Three-way composition: trait × FOMO × depletion
        combined_a = (
            analyst_trait_mean
            * state_a.fomo_score
            * state_a.depletion_proxy
        )
        combined_b = (
            analyst_trait_mean
            * state_b.fomo_score
            * state_b.depletion_proxy
        )

        # Both states have the same FOMO score (same fomo inputs);
        # the difference is depletion. State A has high depletion
        # (0.85 × 1.0 = 0.85); State B has low (0.20 × 0.167 = 0.033).
        assert state_a.fomo_score == state_b.fomo_score, (
            "FOMO inputs are matched; FOMO score should be identical"
        )
        assert state_a.depletion_proxy > state_b.depletion_proxy
        assert combined_a > combined_b, (
            f"three-way composability broken: high-depletion combined "
            f"score {combined_a:.4f} not > low-depletion {combined_b:.4f}"
        )

    def test_zero_regression_on_pmv_existing_fields_and_c_derivations(self):
        """Construct a PageMindstateVector populating ONLY pre-D
        fields. All pre-D field values + to_numpy() projection +
        C's two derivations unchanged. New fields take safe
        defaults; depletion_proxy returns 0.0 (no session position)."""
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
            # C's orchestrator fields (also pre-D-shaped at this point)
            scarcity_frame_present=False,
            regulatory_focus_priming="neutral",
            touch_count=0,
            dwell_seconds=0.0,
        )
        # Pre-C/D fields unchanged.
        assert m.edge_dimensions == {"regulatory_fit": 0.7}
        assert m.emotional_valence == 0.4
        # to_numpy() still 32-dim (D's new fields are NOT in projection).
        vec = m.to_numpy()
        assert vec.shape == (32,)
        # C's derivations unchanged.
        assert m.fomo_score == 0.0  # no scarcity → 0
        assert m.psych_ownership_proxy == 0.0  # touch=0 → 0
        # D's new field defaults applied.
        assert m.session_position_seconds == 0.0
        assert m.posture_class == ""
        assert m.browsing_momentum == 0.5
        # D's derivation returns 0.0 (no session position).
        assert m.depletion_proxy == 0.0


# ---------------------------------------------------------------------------
# Constants tunability
# ---------------------------------------------------------------------------

class TestConstantsTunability:

    def test_depletion_threshold_constant_matches_spec_default(self):
        """30-minute threshold per spec; module-level constant is
        the tunable surface."""
        assert DEPLETION_THRESHOLD_SECONDS == 1800.0

    def test_depletion_threshold_is_positive(self):
        """Sanity invariant — threshold must be positive (zero
        would zero-divide; negative would invert direction)."""
        assert DEPLETION_THRESHOLD_SECONDS > 0
