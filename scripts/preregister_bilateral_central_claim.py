"""Pre-register the bilateral central claim test box (Q.B/Q.3 Sketch C+).

Run ONCE at deployment time (or as part of Q.1 deploy). Builds the
sealed BlindAnalysisBox specifying:
  * Parameter grid: 8 archetypes × 21 dimensions × 9 mechanisms = 1,512 cells
  * Decision statistic: MODERATES_edge_count_per_archetype
  * Decision threshold: alpha = 0.05 (with BH FDR + LEE correction)
  * Signal region: cells where lift > 1.1 with significance after corrections
  * Control region: complementary cells (no significant lift)
  * Post-pilot composition methods (sealed at deploy time):
      - causal_decomposition output → causal_forest CATE features
      - causal_forest CATE → causal_conformal interval wrap
      - DoWhy refutation gating on causal_dag_ensemble edges
      - causal_decomposition recipes → causal_adjudicator integration

Persists the sealed box as a (:BlindAnalysisBox) Neo4j node keyed on
its deterministic SHA-256 pre_registration_hash. Discovery paths read
the box state before persisting MODERATES edges; every persisted edge
carries box_hash linking to this pre-registration.

Sketch C+ discipline anchor: post-pilot composition methods are
sealed AT DEPLOY TIME, not designed after the pilot data is unblinded.
Post-hoc test design is what blind_analysis exists to prevent. The
sealed box is the contract between pre-pilot (substrate ships,
discovery accumulates, MODERATES edges NOT persisted) and post-pilot
(box transitions to UNBLINDED, MODERATES edges materialize, post-
pilot composition methods execute).

USAGE
-----

  python scripts/preregister_bilateral_central_claim.py
  # Output: SHA-256 hash of the sealed box.
  # The hash is the canonical reference for all MODERATES edges
  # discovered during this deployment cycle.

Re-running the script with identical parameters produces the same
hash (deterministic SHA-256 + idempotent Neo4j MERGE). Re-running
with DIFFERENT parameters produces a DIFFERENT hash → a new box
node, preserving the original. Auditability across box revisions.
"""

import asyncio
import json
import sys

from adam.blind_analysis.box import BoxParameter, sealed_box
from adam.blind_analysis.box_neo4j import write_box_to_neo4j
from adam.intelligence.causal_learning import (
    CANONICAL_CIALDINI_9,
    EDGE_DIMENSIONS,
)


# 8 archetypes per adam.cold_start.unified_learning.Archetype
ARCHETYPE_VALUES = (
    "explorer",
    "achiever",
    "connector",
    "guardian",
    "seeker",
    "pragmatist",
    "influencer",
    "analyst",
)


# Sketch C+ post-pilot composition methods. Sealed at deploy time;
# executed post-pilot when the box is UNBLINDED. Each method
# documented with parameters fully resolved so post-pilot integration
# is execution of pre-registered analysis, not post-hoc design.
POST_PILOT_COMPOSITION_METHODS = {
    "causal_decomposition_to_causal_forest": {
        "description": (
            "causal_decomposition.CausalRecipe.ingredients are projected "
            "into causal_forest LoggedDecisionRow.context_features. "
            "Each ingredient's combined_strength becomes a numeric "
            "feature; the active_chain steps become categorical "
            "features. CATE estimation then operates on the joint "
            "(buyer_archetype × page_dim × decomposition_ingredients) "
            "feature space."
        ),
        "causal_forest_params": {
            "n_estimators": 2000,
            "min_samples_leaf": 15,
            "max_samples": 0.45,
            "max_depth": 10,
            "honest": True,
            "cv": 5,
            "random_state": 42,
        },
        "deferred_until": "post_pilot_unblinding",
    },
    "causal_forest_to_causal_conformal": {
        "description": (
            "causal_forest.CATEResult.tau_hat is wrapped by "
            "causal_conformal.ConformalLiftWrap for distribution-free "
            "marginal-coverage CIs. Calibration set bootstrapped "
            "from synthetic_ab_simulation pre-pilot; replaced with "
            "real holdout pairs post-pilot."
        ),
        "conformal_params": {
            "alpha": 0.05,
            "min_calibration_size": 20,
        },
        "deferred_until": "post_pilot_unblinding",
    },
    "dowhy_refutation_on_causal_dag_ensemble": {
        "description": (
            "Apply DoWhy placebo + random-common-cause + unobserved-"
            "confounder tests to the M7 ensemble's high-vote edges "
            "(votes >= 2/4 methods). Edges that fail any refutation "
            "are demoted to candidate status; only refutation-survivors "
            "are persisted as (:PsychDim)-[:CAUSES]->(:PsychDim) edges."
        ),
        "refutation_methods": [
            "placebo_treatment_refuter",
            "random_common_cause",
            "data_subset_refuter",
        ],
        "deferred_until": "post_pilot_unblinding_AND_dowhy_install",
    },
    "causal_decomposition_to_causal_adjudicator": {
        "description": (
            "When adjudicating a Deviation, fetch causal_decomposition "
            "recipes for impressions in the campaign window and check "
            "whether the recipe's primary ingredients were active "
            "in the deviation period. Recipes whose ingredients align "
            "with the system's preferred action become positive "
            "evidence for system_right; misaligned recipes are "
            "evidence for user_right or indeterminate."
        ),
        "deferred_until": "post_pilot_unblinding",
    },
}


def build_bilateral_central_claim_box():
    """Build + seal the bilateral central claim box.

    Returns the sealed BlindAnalysisBox. Idempotent — same parameters
    produce same SHA-256 hash.
    """
    archetype_param = BoxParameter(
        name="archetype",
        values=ARCHETYPE_VALUES,
        description=(
            "8 archetypes per adam.cold_start.unified_learning.Archetype "
            "enum: explorer, achiever, connector, guardian, seeker, "
            "pragmatist, influencer, analyst."
        ),
    )
    dimension_param = BoxParameter(
        name="page_dimension",
        values=tuple(EDGE_DIMENSIONS),
        description=(
            "21 page-side edge dimensions per "
            "adam.intelligence.causal_learning.EDGE_DIMENSIONS "
            "(post-Q.X cleanup; includes maximizer_tendency)."
        ),
    )
    mechanism_param = BoxParameter(
        name="mechanism",
        values=CANONICAL_CIALDINI_9,
        description=(
            "9 canonical Cialdini mechanisms per "
            "adam.intelligence.causal_learning.CANONICAL_CIALDINI_9 "
            "(post-Q.W reconciliation; includes anchoring)."
        ),
    )

    parameters = (archetype_param, dimension_param, mechanism_param)

    # The signal region is conceptually "all cells with significant
    # lift" — but signal/control membership of any specific cell is
    # NOT decided at sealing time; it's discovered. Pre-registration
    # commits to the parameter grid + threshold + statistical
    # discipline; the signal/control assignment per cell happens
    # at discovery time. To satisfy sealed_box's invariant
    # (signal_region + control_region disjoint subsets of grid) we
    # seal with empty signal_region + full grid as control_region.
    # Discovery transitions cells from control → signal as evidence
    # accumulates and clears thresholds.
    full_grid = []
    for arch in ARCHETYPE_VALUES:
        for dim in EDGE_DIMENSIONS:
            for mech in CANONICAL_CIALDINI_9:
                full_grid.append((arch, dim, mech))

    box = sealed_box(
        name="bilateral_central_claim_v1",
        parameters=parameters,
        signal_region=[],
        control_region=full_grid,
        decision_statistic="MODERATES_edge_count_per_archetype",
        decision_threshold=0.05,
        notes=(
            "Q.B/Q.3 Sketch C+ pre-registered box for bilateral central "
            "claim test. Discovery happens via "
            "causal_learning.CausalTestEngine."
            "test_archetype_moderates_dimension_amplifies_mechanism over "
            "the (archetype × dimension × mechanism) grid. "
            "BH FDR correction applied across the grid; LEE correction "
            "via gross_vitells_global_p_value applied to local "
            "p-values before edge persistence. Post-pilot composition "
            "methods sealed in post_pilot_methods_json — see Sketch C+ "
            "discipline. Discovery accumulates pre-pilot (box state: "
            "SEALED → AUTHORIZED at pilot launch); MODERATES edges "
            "persist only post-unblinding. Grid size: 8 × 21 × 9 = "
            "1,512 cells."
        ),
    )
    return box


async def persist_box(box) -> bool:
    """Write the sealed box to Neo4j as a (:BlindAnalysisBox) node."""
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        if not infra._neo4j_driver:
            try:
                await infra.initialize()
            except Exception as exc:
                print(
                    f"WARNING: could not initialize infrastructure: {exc}",
                    file=sys.stderr,
                )
                return False
        if not infra._neo4j_driver:
            print(
                "WARNING: Neo4j driver unavailable; box hash printed but "
                "not persisted to Neo4j.",
                file=sys.stderr,
            )
            return False

        ok = await write_box_to_neo4j(
            box,
            infra._neo4j_driver,
            post_pilot_methods=POST_PILOT_COMPOSITION_METHODS,
        )
        return ok
    except Exception as exc:
        print(f"WARNING: box persistence failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    box = build_bilateral_central_claim_box()
    print(f"name: {box.name}")
    print(f"hash: {box.pre_registration_hash}")
    print(f"decision_statistic: {box.decision_statistic}")
    print(f"decision_threshold: {box.decision_threshold}")
    print(
        f"parameter_grid: 8 archetypes × {len(EDGE_DIMENSIONS)} dimensions "
        f"× {len(CANONICAL_CIALDINI_9)} mechanisms = "
        f"{8 * len(EDGE_DIMENSIONS) * len(CANONICAL_CIALDINI_9)} cells"
    )
    print(f"state: {box.state.value}")
    print(
        "post_pilot_methods: "
        f"{json.dumps(list(POST_PILOT_COMPOSITION_METHODS.keys()))}"
    )

    print("\nPersisting to Neo4j...")
    persisted = asyncio.run(persist_box(box))
    if persisted:
        print(f"✓ Persisted (:BlindAnalysisBox {{hash: '{box.pre_registration_hash}'}})")
        return 0
    else:
        print(
            "✗ Persistence skipped (Neo4j unavailable). Box hash above is "
            "still valid; re-run after Neo4j is reachable."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
