"""Psychological ownership-keyed cell predicates.

References:
    Pierce, J. L., Kostova, T., & Dirks, K. T. (2001). Toward a
        theory of psychological ownership in organizations.
        Academy of Management Review 26(2), 298-310.
    Kahneman, D., Knetsch, J. L., & Thaler, R. H. (1990).
        Experimental tests of the endowment effect and the Coase
        theorem. JPE 98(6), 1325-1348.
"""
from typing import Optional

from adam.cells.evaluator import CreativeModulation, cell_predicate
from adam.cells.features import CellFeatureSet


@cell_predicate(name="high_psych_ownership_endowment_reinforce")
def high_psych_ownership(features: CellFeatureSet) -> Optional[CreativeModulation]:
    """Cell condition: psychological ownership proxy > 0.55.

    Bias: boost commitment_consistency mechanism (already-mine
    framing, completion appeals) per Pierce-Kostova-Dirks ownership
    + Kahneman-Knetsch-Thaler endowment effect. Dampen scarcity —
    scarcity competes with the reassurance the user already has the
    relationship with the product.
    """
    if features.psych_ownership_proxy > 0.55:
        return CreativeModulation(
            predicate_name="high_psych_ownership_endowment_reinforce",
            cell_id=features.cell_id,
            creative_class_boosts={"commitment_consistency": 1.4},
            creative_class_dampens={"scarcity": 0.85},
            reason=(
                f"psych ownership ({features.psych_ownership_proxy:.2f}) → "
                f"endowment / completion framing"
            ),
        )
    return None
