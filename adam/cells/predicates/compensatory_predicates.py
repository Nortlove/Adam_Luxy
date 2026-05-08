"""Compensatory-consumption cohort-keyed cell predicates.

References:
    Mead, N. L., Baumeister, R. F., Stillman, T. F., Rawn, C. D.,
        & Vohs, K. D. (2010). Social exclusion causes people to
        spend and consume strategically in the service of
        affiliation. JCR 37(5), 902-919.
    Loh, H. C. et al. (2021). Compensatory consumption: A
        systematic review. JCB 20(5), 1144-1156.
"""
from typing import Optional

from adam.cells.evaluator import CreativeModulation, cell_predicate
from adam.cells.features import CellFeatureSet


@cell_predicate(name="compensatory_cohort_social_consumption")
def compensatory_cohort_social_consumption(
    features: CellFeatureSet,
) -> Optional[CreativeModulation]:
    """Cell condition: F.2 cohort flag is True with confidence > 0.65
    AND posture is SOCIAL_CONSUMPTION.

    Bias: boost liking + unity (affiliative mechanisms that match the
    compensatory-consumption motive Mead 2010 identified — consumption
    as social-substitute / in-group signaling). Dampen anchoring +
    loss_aversion which read as transactional/utilitarian frames the
    compensatory motive doesn't respond to.

    HEURISTIC SUBSTRATE (per F.2 caveat): the Cialdini-mechanism →
    compensatory-consumption mapping is theoretically motivated but
    not empirically validated on this platform's data. Pilot data
    will tighten thresholds + may revise mechanism selection.
    """
    if (
        features.compensatory_consumption_pattern
        and features.compensatory_detection_confidence > 0.65
        and features.posture == "SOCIAL_CONSUMPTION"
    ):
        return CreativeModulation(
            predicate_name="compensatory_cohort_social_consumption",
            cell_id=features.cell_id,
            creative_class_boosts={"liking": 1.4, "unity": 1.4},
            creative_class_dampens={"anchoring": 0.85, "loss_aversion": 0.85},
            reason=(
                f"compensatory cohort (conf={features.compensatory_detection_confidence:.2f}) "
                f"+ social consumption → affiliative framing"
            ),
        )
    return None
