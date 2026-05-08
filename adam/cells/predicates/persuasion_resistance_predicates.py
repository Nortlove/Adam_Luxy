"""Persuasion-knowledge / skepticism-keyed cell predicates.

References:
    Friestad, M., & Wright, P. (1994). The Persuasion Knowledge
        Model: How people cope with persuasion attempts. JCR 21(1),
        1-31.
"""
from typing import Optional

from adam.cells.evaluator import CreativeModulation, cell_predicate
from adam.cells.features import CellFeatureSet


@cell_predicate(name="high_persuasion_knowledge_skepticism_dampener")
def high_persuasion_knowledge(features: CellFeatureSet) -> Optional[CreativeModulation]:
    """Cell condition: persuasion knowledge activation > 0.50 with
    confidence > 0.65.

    Bias: dampen scarcity (which reads as overt sales pressure to
    high-PK consumers); boost authority + social_proof (which
    present credibility evidence rather than persuasion attempts).

    Friestad-Wright PKM: high-PK consumers cope with persuasion
    attempts by activating coping responses; explicit-persuasion
    creative triggers reactance, while evidence-based / authority-
    based creative bypasses the coping response.
    """
    if (
        features.persuasion_knowledge_activation > 0.50
        and features.confidence_persuasion_knowledge > 0.65
    ):
        return CreativeModulation(
            predicate_name="high_persuasion_knowledge_skepticism_dampener",
            cell_id=features.cell_id,
            creative_class_boosts={"authority": 1.4, "social_proof": 1.3},
            creative_class_dampens={"scarcity": 0.7, "loss_aversion": 0.85},
            reason=(
                f"PK activation ({features.persuasion_knowledge_activation:.2f}) → "
                f"evidence/authority framing (avoid sales-pressure cues)"
            ),
        )
    return None
