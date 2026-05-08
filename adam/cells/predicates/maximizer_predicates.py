"""Maximizer-trait keyed cell predicates.

References:
    Schwartz, B., Ward, A., Monterosso, J., Lyubomirsky, S.,
        White, K., & Lehman, D. R. (2002). Maximizing versus
        satisficing: Happiness is a matter of choice. JPSP 83(5),
        1178-1197.
"""
from typing import Optional

from adam.cells.evaluator import CreativeModulation, cell_predicate
from adam.cells.features import CellFeatureSet


@cell_predicate(name="high_maximizer_comparison")
def high_maximizer_comparison(features: CellFeatureSet) -> Optional[CreativeModulation]:
    """Cell condition: maximizer posterior mean > 0.65 + transactional
    comparison posture.

    Bias: boost authority + anchoring mechanisms (which present
    comparison-information substrates that satisfy maximizer's
    information-seeking pattern). Maximizers in comparison posture
    actively seek evidence; trying to short-circuit with social_proof
    backfires.

    Schwartz et al. 2002: maximizers seek to optimize across the full
    choice set; comparison posture is the explicit behavioral
    signature of that motive.
    """
    if (
        features.maximizer_tendency_posterior_mean > 0.65
        and features.posture == "TRANSACTIONAL_COMPARISON"
    ):
        return CreativeModulation(
            predicate_name="high_maximizer_comparison",
            cell_id=features.cell_id,
            creative_class_boosts={"authority": 1.4, "anchoring": 1.3},
            creative_class_dampens={"social_proof": 0.85},
            reason=(
                f"maximizer trait ({features.maximizer_tendency_posterior_mean:.2f}) "
                f"+ comparison posture → evidence/comparison framing"
            ),
        )
    return None
