"""Pin the G5 recommendation_class cascade wire — every decision upserts a class.

Discipline anchors:
    - The recommendation_class package (12 modules) shipped with no
      external invokers. G5 closes that dark-code surface by hooking
      RecommendationClassGraph.upsert_class_sync into the cascade's
      _persist_decision. Every LUXY decision now creates/updates the
      corresponding RecommendationClass node — the durable target
      that future adjudication will read.
    - The wire is FIRE-AND-FORGET. The bid path must NEVER block on
      RecommendationClass writes. Failures are swallowed in the package
      itself (graph.py's shadow-write safety) plus in the cascade's
      try/except.
    - Plant-model projection + ProjectedImpactClaim recording is
      EXPLICITLY out of scope for this commit. Wiring those without
      proper PublicationBiasCorrectedEffect / AudienceSummary inputs
      would invent the projections — exactly the drift this discipline
      exists to prevent.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
from adam.api.stackadapt.service import CreativeIntelligenceService


def _ci_with_mech(mech: str = "social_proof") -> CreativeIntelligence:
    return CreativeIntelligence(
        primary_mechanism=mech,
        secondary_mechanism="authority",
        framing="gain",
        cascade_level=3,
    )


def _service() -> CreativeIntelligenceService:
    return CreativeIntelligenceService()


# -----------------------------------------------------------------------------
# Cascade wire calls upsert_class_sync per decision
# -----------------------------------------------------------------------------


def test_persist_decision_calls_upsert_class_sync():
    """Every cascade _persist_decision call should upsert the
    corresponding RecommendationClass node fire-and-forget."""
    svc = _service()

    captured = {"called": False, "identity": None}

    class FakeGraph:
        def upsert_class_sync(self, identity):
            captured["called"] = True
            captured["identity"] = identity

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        return_value=FakeGraph(),
    ):
        mock_cache.return_value = MagicMock()
        svc._persist_decision(
            decision_id="d1",
            cascade_result=_ci_with_mech("social_proof"),
            segment_id="informativ_status_seeker_luxury_transportation_t1",
            asin="lux_luxy_ride",
            buyer_id="b1",
            content_category="luxury_transportation",
            product_category="luxury_transportation",
        )

    assert captured["called"] is True
    assert captured["identity"] is not None
    assert captured["identity"].advertiser_id == "lux_luxy_ride"
    assert captured["identity"].mechanism == "social_proof"


def test_identity_uses_neutral_posture_when_context_missing():
    """When ci.context_intelligence is None, the cascade hasn't yet
    derived an attentional posture. Default to 'neutral' — the honest
    fallback, NOT an invented value."""
    svc = _service()

    captured = {"identity": None}

    class FakeGraph:
        def upsert_class_sync(self, identity):
            captured["identity"] = identity

    ci = _ci_with_mech()
    ci.context_intelligence = None  # no derived posture

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        return_value=FakeGraph(),
    ):
        mock_cache.return_value = MagicMock()
        svc._persist_decision(
            decision_id="d1", cascade_result=ci,
            segment_id="informativ_status_seeker_t1",
            asin="lux_luxy_ride", buyer_id="b1",
            content_category="luxury_transportation",
            product_category="luxury_transportation",
        )

    assert captured["identity"].context_posture_band == "neutral"


def test_identity_uses_attentional_posture_band_when_present():
    """When ci.context_intelligence carries a posture band, use it."""
    svc = _service()
    captured = {"identity": None}

    class FakeGraph:
        def upsert_class_sync(self, identity):
            captured["identity"] = identity

    ci = _ci_with_mech()
    ci.context_intelligence = {
        "attentional_posture_band": "vigilance_high",
        "mindset": "informed",
    }

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        return_value=FakeGraph(),
    ):
        mock_cache.return_value = MagicMock()
        svc._persist_decision(
            decision_id="d1", cascade_result=ci,
            segment_id="informativ_status_seeker_t1",
            asin="lux_luxy_ride", buyer_id="b1",
            content_category="luxury_transportation",
            product_category="luxury_transportation",
        )

    assert captured["identity"].context_posture_band == "vigilance_high"


# -----------------------------------------------------------------------------
# Cascade NEVER breaks on recommendation_class failures (fire-and-forget)
# -----------------------------------------------------------------------------


def test_cascade_survives_recommendation_class_import_error():
    """If recommendation_class imports somehow fail (sandbox, missing
    deps, etc.), the cascade _persist_decision must still complete.
    The try/except is the discipline anchor."""
    svc = _service()

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        side_effect=ImportError("simulated package import failure"),
    ):
        mock_cache.return_value = MagicMock()
        # Must NOT raise
        svc._persist_decision(
            decision_id="d1", cascade_result=_ci_with_mech(),
            segment_id="informativ_status_seeker_t1",
            asin="lux_luxy_ride", buyer_id="b1",
            content_category="luxury_transportation",
            product_category="luxury_transportation",
        )


def test_cascade_survives_upsert_exception():
    """RecommendationClassGraph itself is shadow-write-safe (catches
    Neo4j errors internally) but if for any reason upsert_class_sync
    raises, the cascade must survive."""
    svc = _service()

    class BrokenGraph:
        def upsert_class_sync(self, identity):
            raise ConnectionError("Neo4j down")

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        return_value=BrokenGraph(),
    ):
        mock_cache.return_value = MagicMock()
        # Must NOT raise
        svc._persist_decision(
            decision_id="d1", cascade_result=_ci_with_mech(),
            segment_id="informativ_status_seeker_t1",
            asin="lux_luxy_ride", buyer_id="b1",
            content_category="luxury_transportation",
            product_category="luxury_transportation",
        )


def test_cascade_survives_invalid_identity():
    """If the identity tuple has empty fields (e.g., asin missing,
    buyer_id missing, mechanism unset), the upsert validation will
    reject. Cascade must survive."""
    svc = _service()
    ci = CreativeIntelligence(
        primary_mechanism="",  # empty mechanism — invalid identity
        cascade_level=1,
    )

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache:
        mock_cache.return_value = MagicMock()
        # Must NOT raise even if upsert validation fails
        svc._persist_decision(
            decision_id="d1", cascade_result=ci,
            segment_id="informativ_status_seeker_t1",
            asin="", buyer_id="",
            content_category="", product_category="",
        )


# -----------------------------------------------------------------------------
# Identity tuple shape is correct
# -----------------------------------------------------------------------------


def test_identity_carries_all_five_components():
    """The RecommendationClassIdentity must populate all five tuple
    fields (advertiser, archetype, mechanism, posture, horizon). A
    missing field would cause upsert validation to reject silently."""
    svc = _service()
    captured = {"identity": None}

    class FakeGraph:
        def upsert_class_sync(self, identity):
            captured["identity"] = identity

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        return_value=FakeGraph(),
    ):
        mock_cache.return_value = MagicMock()
        svc._persist_decision(
            decision_id="d1", cascade_result=_ci_with_mech("authority"),
            segment_id="informativ_status_seeker_luxury_transportation_t1",
            asin="lux_luxy_ride", buyer_id="b1",
            content_category="luxury_transportation",
            product_category="luxury_transportation",
        )

    identity = captured["identity"]
    assert identity.advertiser_id == "lux_luxy_ride"
    assert identity.archetype_id  # non-empty
    assert identity.mechanism == "authority"
    assert identity.context_posture_band  # non-empty (defaults to neutral)
    assert identity.horizon_band == "30d"


def test_identity_id_is_deterministic():
    """Same inputs → same id. The recommendation_class_id() function
    is deterministic per its docstring; two upserts with the same
    cascade output should target the same node."""
    svc = _service()
    captured = []

    class FakeGraph:
        def upsert_class_sync(self, identity):
            captured.append(identity.id)

    with patch(
        "adam.api.stackadapt.service.get_decision_cache",
    ) as mock_cache, patch(
        "adam.intelligence.recommendation_class.get_recommendation_class_graph",
        return_value=FakeGraph(),
    ):
        mock_cache.return_value = MagicMock()
        for _ in range(3):
            svc._persist_decision(
                decision_id=f"d{_}", cascade_result=_ci_with_mech("social_proof"),
                segment_id="informativ_status_seeker_t1",
                asin="lux_luxy_ride", buyer_id="b1",
                content_category="luxury_transportation",
                product_category="luxury_transportation",
            )

    # All three upserts target the same node id (same identity tuple)
    assert len(set(captured)) == 1
