"""Pin Slice 5 wire — outcome handler calls write_outcome_trace_closure.

Audit Tier 1 #4 (closure loop): outcomes never linked back to their
originating DecisionTrace. The wire MUST live inside
``OutcomeHandler.process_outcome`` so every resolved outcome
attempts the closure write.

Source-text contract pin — guards against silent removal of the
wire in a refactor that drops the import without realizing the
closure depends on it.
"""

from __future__ import annotations

from pathlib import Path


def test_outcome_handler_imports_closure_writer():
    """OutcomeHandler module must reference the closure writer."""
    src = Path("adam/core/learning/outcome_handler.py").read_text()
    assert (
        "from adam.intelligence.outcome_trace_closure import"
        in src
    ), (
        "OutcomeHandler lost its import of write_outcome_trace_closure. "
        "Slice 5 closure loop is broken — outcomes will not link back "
        "to their originating DecisionTrace; OPE post-outcome update + "
        "DR provenance layer both depend on this wire."
    )
    assert "write_outcome_trace_closure" in src, (
        "OutcomeHandler no longer calls write_outcome_trace_closure. "
        "The (:ConversionEdge)-[:RESOLVED]->(:DecisionTrace) edge is "
        "no longer being written."
    )


def test_closure_wire_passes_signed_reward():
    """Wire must thread signed_reward (Foundation rule 11 magnitude)."""
    src = Path("adam/core/learning/outcome_handler.py").read_text()
    # The wire block should pass signed_reward=signed_reward
    assert "signed_reward=signed_reward" in src, (
        "Closure wire dropped signed_reward — Foundation rule 11 "
        "magnitude information lost from the ConversionEdge node."
    )


def test_closure_wire_in_soft_fail_block():
    """Wire must be in a try/except — outcome processing cannot block on logging."""
    src = Path("adam/core/learning/outcome_handler.py").read_text()
    # Find the closure-call region
    closure_idx = src.find("write_outcome_trace_closure(")
    assert closure_idx > 0
    # The 200 chars BEFORE the call should include a try: opening,
    # and the 300 chars AFTER should include an except clause.
    pre = src[max(0, closure_idx - 400):closure_idx]
    post = src[closure_idx:closure_idx + 600]
    assert "try:" in pre, (
        "Closure wire is not inside a try block — a Neo4j failure "
        "would crash outcome processing. Restore the soft-fail wrapper."
    )
    assert "except" in post, (
        "Closure wire missing the except clause for soft-fail."
    )
