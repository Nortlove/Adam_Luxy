"""Pin the publication_bias_correction response block.

Discipline anchors:
    - Doc 3 §I.8 directs that every mechanism MUST carry the corrected-
      effect annotation alongside any lift claim. Surfacing the
      annotation in the cascade response makes that claim operational
      end-to-end: the consumer reading expected_lift cannot now read it
      without seeing the correction provenance.
    - The block must NOT be silently empty for known mechanisms —
      "publication_bias_correction": {} would be indistinguishable from
      a regression to inflated published values.
    - Empty block IS correct when no mechanism is resolved (very low
      cascade level), and the test pins that boundary.
"""

from __future__ import annotations

from adam.api.stackadapt.service import _build_correction_block


def test_returns_block_for_primary_only():
    block = _build_correction_block(primary="loss_aversion", secondary=None)
    assert "primary" in block
    assert block["primary"]["mechanism"] == "loss_aversion_framing"
    assert "secondary" not in block


def test_returns_block_for_primary_and_secondary():
    block = _build_correction_block(primary="loss_aversion", secondary="authority")
    assert "primary" in block
    assert "secondary" in block
    assert block["primary"]["mechanism"] == "loss_aversion_framing"
    assert block["secondary"]["mechanism"] == "authority"


def test_skips_secondary_when_same_as_primary():
    """Avoid redundant secondary block when primary == secondary."""
    block = _build_correction_block(primary="liking", secondary="liking")
    assert "primary" in block
    assert "secondary" not in block


def test_empty_block_when_no_primary():
    """No primary mechanism → empty block. Honest empty (request lacks
    a mechanism), not silent default."""
    block = _build_correction_block(primary=None, secondary=None)
    assert block == {}


def test_unknown_mechanism_carries_not_registered_status():
    """Unknown mechanism MUST surface as NOT_REGISTERED in the response
    block, not silently degrade. Failing this means a mechanism added
    to the cascade but not yet to the registry would ship without
    provenance — exactly the failure mode Doc 3 §I.8 warns against."""
    block = _build_correction_block(
        primary="not_a_real_mechanism", secondary=None
    )
    assert block["primary"]["correction_status"] == "NOT_REGISTERED"


def test_block_carries_pending_review_flag():
    """The pending_review flag MUST be visible to consumers so they can
    interpret claims with the right caveat."""
    block_pending = _build_correction_block(primary="authority", secondary=None)
    assert block_pending["primary"]["pending_review"] is True

    block_corrected = _build_correction_block(
        primary="construal_level_matching", secondary=None
    )
    assert block_corrected["primary"]["pending_review"] is False


def test_block_carries_citations():
    """Citations are provenance — the auditor needs them to trace a
    lift claim back to its meta-analytic source."""
    block = _build_correction_block(primary="loss_aversion", secondary=None)
    citations = block["primary"]["citations"]
    assert isinstance(citations, list) and len(citations) >= 1
    # Loss aversion citation must reference Kenworthy or Izuma-Murayama
    citation_text = " ".join(citations).lower()
    assert "kenworthy" in citation_text or "izuma" in citation_text


# -----------------------------------------------------------------------------
# Router-wiring regression — the bug I just fixed was that the router
# explicitly constructs CreativeIntelligenceResponse(...) and silently
# dropped publication_bias_correction (defaulting to {}). These tests
# pin the wiring at both ends so the same regression cannot recur.
# -----------------------------------------------------------------------------


def test_response_model_declares_publication_bias_correction_field():
    """The Pydantic response model MUST declare the field. Without it,
    even if the service writes it, FastAPI strips it."""
    from adam.api.stackadapt.models import CreativeIntelligenceResponse

    fields = CreativeIntelligenceResponse.model_fields
    assert "publication_bias_correction" in fields, (
        "CreativeIntelligenceResponse missing publication_bias_correction "
        "field. Doc 3 §I.8 mandates this provenance block on every cascade "
        "response."
    )


def test_router_response_constructor_passes_publication_bias_correction():
    """The router builds CreativeIntelligenceResponse(...) explicitly.
    If the constructor call doesn't include publication_bias_correction,
    the field defaults to {} regardless of what the service writes.
    This test reads the router source for the explicit kwarg — the
    only way to pin the regression without mocking FastAPI deeply."""
    from pathlib import Path

    router_src = Path(__file__).resolve().parent.parent.parent / "adam" / "api" / "stackadapt" / "router.py"
    text = router_src.read_text()
    assert "publication_bias_correction=result" in text, (
        "router.py must pass publication_bias_correction from the result "
        "dict into CreativeIntelligenceResponse(...). Without this kwarg, "
        "the service's _format_response writes are silently dropped."
    )
