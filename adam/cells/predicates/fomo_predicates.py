"""FOMO-keyed cell predicates.

References:
    Cialdini, R. (1984/2016). Influence: Science and Practice
        (scarcity / urgency mechanisms).
    Pham, M. T., & Higgins, E. T. (2005). Promotion and prevention
        in consumer decision making. JCR 32(2), 180-189.
    Przybylski, A. K. et al. (2013). Motivational, emotional, and
        behavioral correlates of fear of missing out. CHB 29(4),
        1841-1848.
"""
from typing import Optional

from adam.cells.evaluator import CreativeModulation, cell_predicate
from adam.cells.features import CellFeatureSet
from adam.cells.taxonomy import RegulatoryFocus


@cell_predicate(name="high_fomo_promotion")
def high_fomo_promotion(features: CellFeatureSet) -> Optional[CreativeModulation]:
    """Cell condition: FOMO score > 0.7 + promotion regulatory focus.

    Bias: boost scarcity + loss_aversion mechanisms; dampen reciprocity
    (which is reflective/relationship-oriented and competes with
    urgency framing).

    Pham-Higgins regulatory-fit: promotion-oriented users in high-
    arousal-with-scarcity states respond to urgency-signaling
    creative; prevention-oriented users in the same state respond
    differently (see high_fomo_prevention sibling).
    """
    if (
        features.fomo_score > 0.7
        and features.regulatory_focus == RegulatoryFocus.PROMOTION
    ):
        return CreativeModulation(
            predicate_name="high_fomo_promotion",
            cell_id=features.cell_id,
            creative_class_boosts={"scarcity": 1.5, "loss_aversion": 1.3},
            creative_class_dampens={"reciprocity": 0.7},
            reason=(
                f"high FOMO ({features.fomo_score:.2f}) + promotion focus → "
                f"urgency framing"
            ),
        )
    return None


@cell_predicate(name="high_fomo_prevention")
def high_fomo_prevention(features: CellFeatureSet) -> Optional[CreativeModulation]:
    """Cell condition: FOMO score > 0.7 + prevention regulatory focus.

    Different modulation than promotion: prevention-oriented users in
    FOMO state respond to safety/loss-aversion framing rather than
    pure urgency. Loss aversion still applies but scarcity is dampened
    (it reads as pressure, not protection, to prevention-focused
    users).
    """
    if (
        features.fomo_score > 0.7
        and features.regulatory_focus == RegulatoryFocus.PREVENTION
    ):
        return CreativeModulation(
            predicate_name="high_fomo_prevention",
            cell_id=features.cell_id,
            creative_class_boosts={"loss_aversion": 1.4},
            creative_class_dampens={"scarcity": 0.8},
            reason=(
                f"high FOMO ({features.fomo_score:.2f}) + prevention focus → "
                f"loss-aversion framing"
            ),
        )
    return None
