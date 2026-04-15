"""
AtomDAG Simulation — TEST-ONLY Fabrication of Atom Results
============================================================

This module contains the former `_simulate_atom_dag` function from the
campaign orchestrator. It was removed from the production decision path
because it was silently substituting fabricated construct values for real
atom runs, contaminating the learning loop with outcomes that could not be
cleanly credited.

The function is preserved here for legitimate uses — load testing the
orchestrator plumbing without a running Neo4j, developer iteration on
downstream consumers (mechanism selection, copy generation) when the full
stack is not available, and integration tests that need a predictable
AtomDAG response.

**It must never be imported from production code.** The module enforces
this by asserting at import time that `ADAM_ENV != "production"`. If a
production process somehow reaches this module, it will crash at import
rather than silently producing fabrications.

If you find yourself wanting to import this module from `adam.orchestrator`
or anywhere else in the live decision path, stop. The whole point of this
module's existence as a separate file is that the decision path must not
have access to it. If you need graceful-degradation behavior on the
decision path, produce an `INCOMPLETE` or `REFUSED` AtomDAGResult with
explicit grounding evidence instead. See `adam/core/decision_mode.py`.
"""

from __future__ import annotations

import os
import time
from typing import Any

# Production guard. The only way to disable this is to set ADAM_ENV to
# something other than "production" in the environment — which should only
# happen in development, CI, and load-test contexts.
_ADAM_ENV = os.environ.get("ADAM_ENV", "").lower()
if _ADAM_ENV == "production":
    raise ImportError(
        "adam.testing.simulation must not be imported in production. "
        "This module fabricates atom results for testing and its outputs "
        "are not grounded in any user or context. If you reached this "
        "error from a production code path, that code path has a bug: "
        "production code must produce typed INCOMPLETE or REFUSED "
        "AtomDAGResult responses on failure, not fabrications. "
        "See adam/core/decision_mode.py for the correct pattern."
    )

from adam.orchestrator.models import (
    AtomDAGResult,
    AtomExecutionResult,
    EvidenceItem,
    ReasoningTrace,
)


async def simulate_atom_dag(
    brand: str,
    product: str,
    description: str,
    customer_intelligence: Any,
    archetype: str,
    trace: ReasoningTrace,
    start_time: float,
) -> AtomDAGResult:
    """Produce a fabricated AtomDAGResult for test / load-test / dev use.

    This function's outputs have no epistemic grounding. The `mode` field
    on the returned result is deliberately set to `incomplete` so that even
    if the result leaks into a learning-loop consumer (through a bug), the
    consumer's decision-mode gate refuses to update posteriors from it.
    That is a second line of defense; the first line is that this module
    cannot be imported in production at all.
    """
    atom_result = AtomDAGResult(
        execution_order=[
            "UserStateAtom",
            "RegulatoryFocusAtom",
            "ConstrualLevelAtom",
            "ReviewIntelligenceAtom",
            "PersonalityExpressionAtom",
            "MechanismActivationAtom",
        ],
        # Defense-in-depth: simulation results are NEVER grounded, even if
        # a test harness populates real-looking atom_results into them.
        mode="incomplete",
        grounding_evidence={
            "bilateral_edge_evidence_present": False,
            "atom_run_real": False,
            "theoretical_link_traversed": False,
            "failure_reasons": [
                "adam.testing.simulation: fabricated result, not grounded in any user or context",
            ],
        },
        missing_links=[
            "bilateral_edge_evidence_present",
            "atom_run_real",
            "theoretical_link_traversed",
        ],
        refusal_reason=None,
    )

    atom_result.atom_results["UserStateAtom"] = AtomExecutionResult(
        atom_name="UserStateAtom",
        atom_type="inference",
        execution_time_ms=5.0,
        primary_output={"archetype": archetype},
        confidence=0.7,
        reasoning="[SIMULATED] Determined user archetype from product analysis",
    )

    reg_focus = "promotion"
    if archetype in ("Guardian",):
        reg_focus = "prevention"

    atom_result.atom_results["RegulatoryFocusAtom"] = AtomExecutionResult(
        atom_name="RegulatoryFocusAtom",
        atom_type="inference",
        execution_time_ms=3.0,
        primary_output={"regulatory_focus": reg_focus, "strength": 0.65},
        confidence=0.7,
        reasoning=f"[SIMULATED] Archetype {archetype} typically has {reg_focus} focus",
    )

    if customer_intelligence:
        atom_result.atom_results["ReviewIntelligenceAtom"] = AtomExecutionResult(
            atom_name="ReviewIntelligenceAtom",
            atom_type="empirical",
            execution_time_ms=2.0,
            primary_output={
                "reviews_analyzed": customer_intelligence.reviews_analyzed,
                "dominant_archetype": customer_intelligence.dominant_archetype,
                "mechanism_predictions": customer_intelligence.mechanism_predictions,
            },
            confidence=customer_intelligence.overall_confidence or 0.5,
            evidence_items=[
                EvidenceItem(
                    source="product_reviews",
                    construct="buyer_archetype",
                    value=customer_intelligence.archetype_confidence or 0.5,
                    confidence=customer_intelligence.overall_confidence or 0.5,
                ),
            ],
            reasoning=f"[SIMULATED] Analyzed {customer_intelligence.reviews_analyzed} customer reviews",
        )

    atom_result.total_execution_time_ms = (time.time() - start_time) * 1000

    atom_result.final_psychological_profile = {
        "archetype": archetype,
        "regulatory_focus": reg_focus,
        "construal_level": "high" if archetype in ("Achiever", "Explorer") else "low",
    }

    trace.atom_dag_result = atom_result

    return atom_result
