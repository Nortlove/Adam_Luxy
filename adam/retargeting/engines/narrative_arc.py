# =============================================================================
# Therapeutic Retargeting Engine — Narrative Arc Builder
# Location: adam/retargeting/engines/narrative_arc.py
# Spec: Enhancement #33, Section B.4 + Session 33-7
# =============================================================================

"""
Narrative Arc Builder — Structures retargeting sequences as episodic stories.

From Van Laer et al. (2014), k=132: transportation→affective responses r=.57,
transportation→reduced critical thoughts r=-.20. Effects STRONGER for
commercial stories and user-generated content.

Sequential retargeting should be structured as an unfolding story, not
discrete ad impressions. Each touch advances the narrative.

Three arc types per archetype:
- RESOLUTION: Problem→Solution (Careful Truster, Corporate Executive)
- DISCOVERY: Curiosity→Reward (Status Seeker, Explorer)
- TRANSFORMATION: Before→After (Easy Decider, Achiever)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Narrative chapters (5-chapter Freytag-derived arc)
# ---------------------------------------------------------------------------
NARRATIVE_CHAPTERS = {
    1: {
        "name": "introduction",
        "function": "introduce_character",
        "description": "Establish the character the prospect can identify with",
        "construal": "abstract",
        "processing": "peripheral",
        "testimonial_type": "coping",  # Braaksma: weak learners → coping models
    },
    2: {
        "name": "complication",
        "function": "present_conflict",
        "description": "Present the problem the user shares with the character",
        "construal": "abstract",
        "processing": "peripheral",
        "testimonial_type": "coping",
    },
    3: {
        "name": "rising_action",
        "function": "show_consideration",
        "description": "Show the character's consideration and evaluation process",
        "construal": "concrete",
        "processing": "central",
        "testimonial_type": "coping",
    },
    4: {
        "name": "resolution",
        "function": "show_resolution",
        "description": "Show the character's positive outcome with the product",
        "construal": "concrete",
        "processing": "central",
        "testimonial_type": "mastery",  # Braaksma: later → mastery models
    },
    5: {
        "name": "epilogue",
        "function": "confirm_outcome",
        "description": "Social proof / outcome confirmation / call to action",
        "construal": "concrete",
        "processing": "peripheral",
        "testimonial_type": "mastery",
    },
}

# Arc type per archetype
ARCHETYPE_ARC_TYPES = {
    "careful_truster": "resolution",
    "corporate_executive": "resolution",
    "status_seeker": "discovery",
    "explorer": "discovery",
    "easy_decider": "transformation",
    "achiever": "transformation",
    "guardian": "resolution",
    "analyst": "resolution",
    "connector": "transformation",
    "creator": "discovery",
    # Defaults
    "_default": "resolution",
}

# Arc-specific chapter emphasis adjustments
ARC_CHAPTER_WEIGHTS = {
    "resolution": {
        1: 0.15, 2: 0.25, 3: 0.25, 4: 0.25, 5: 0.10,
    },
    "discovery": {
        1: 0.25, 2: 0.15, 3: 0.20, 4: 0.25, 5: 0.15,
    },
    "transformation": {
        1: 0.20, 2: 0.15, 3: 0.15, 4: 0.30, 5: 0.20,
    },
}


@dataclass
class NarrativePosition:
    """Current position in the narrative arc."""

    chapter: int  # 1-5
    chapter_name: str
    function: str
    construal_level: str  # abstract or concrete
    processing_route: str  # central or peripheral
    testimonial_type: str  # coping or mastery
    arc_type: str
    chapter_weight: float  # How much emphasis this chapter gets in this arc


class NarrativeArcBuilder:
    """Structures retargeting sequences as episodic narratives.

    Maps touch position → narrative chapter, accounting for:
    - Archetype-matched arc type
    - Current conversion stage (skip early chapters for advanced stages)
    - Rupture events (may reset arc position)
    - Touch count vs chapter count (may condense or expand)
    """

    def get_arc_type(self, archetype_id: str) -> str:
        """Get the narrative arc type for an archetype."""
        return ARCHETYPE_ARC_TYPES.get(archetype_id, ARCHETYPE_ARC_TYPES["_default"])

    def get_narrative_position(
        self,
        touch_position: int,
        archetype_id: str,
        stage: ConversionStage = ConversionStage.CURIOUS,
        max_touches: int = 7,
        arc_reset: bool = False,
    ) -> NarrativePosition:
        """Determine narrative position for a given touch.

        Maps touch position to chapter, with adjustments:
        - If stage is INTENDING/STALLED, skip to chapter 3+ (they don't need intro)
        - If arc_reset (after rupture), restart from chapter 1
        - If max_touches < 5, condense (skip chapters 2 or 5)
        - If max_touches > 5, stretch (repeat chapter 3 with variations)
        """
        arc_type = self.get_arc_type(archetype_id)

        if arc_reset:
            chapter = 1
        else:
            chapter = self._map_touch_to_chapter(
                touch_position, stage, max_touches
            )

        chapter_info = NARRATIVE_CHAPTERS[chapter]
        weights = ARC_CHAPTER_WEIGHTS.get(arc_type, ARC_CHAPTER_WEIGHTS["resolution"])

        return NarrativePosition(
            chapter=chapter,
            chapter_name=chapter_info["name"],
            function=chapter_info["function"],
            construal_level=chapter_info["construal"],
            processing_route=chapter_info["processing"],
            testimonial_type=chapter_info["testimonial_type"],
            arc_type=arc_type,
            chapter_weight=weights.get(chapter, 0.20),
        )

    def _map_touch_to_chapter(
        self,
        touch_position: int,
        stage: ConversionStage,
        max_touches: int,
    ) -> int:
        """Map touch position to narrative chapter (1-5)."""

        # Stage-based fast-forward: advanced stages skip intro chapters
        min_chapter = 1
        if stage in (ConversionStage.INTENDING, ConversionStage.STALLED):
            min_chapter = 3  # Skip intro + complication
        elif stage == ConversionStage.EVALUATING:
            min_chapter = 2  # Skip intro

        # Linear mapping: spread max_touches across chapters min..5
        available_chapters = 5 - min_chapter + 1
        if max_touches <= 0:
            max_touches = 5

        # Which chapter does this touch fall in?
        progress = (touch_position - 1) / max(max_touches - 1, 1)
        chapter = min_chapter + int(progress * (available_chapters - 1))
        chapter = max(min_chapter, min(5, chapter))

        return chapter

    def build_creative_context(
        self,
        position: NarrativePosition,
        barrier: BarrierCategory,
        mechanism: TherapeuticMechanism,
        brand_name: str = "",
    ) -> Dict:
        """Build creative context dict for copy generation.

        This becomes the creative_strategy field on TherapeuticTouch.
        """
        return {
            "narrative_chapter": position.chapter,
            "narrative_function": position.function,
            "arc_type": position.arc_type,
            "construal_level": position.construal_level,
            "processing_route": position.processing_route,
            "testimonial_model_type": position.testimonial_type,
            "barrier_targeted": barrier.value,
            "mechanism": mechanism.value,
            "brand_name": brand_name,
            "creative_direction": self._chapter_creative_direction(
                position, barrier, mechanism
            ),
        }

    def _chapter_creative_direction(
        self,
        position: NarrativePosition,
        barrier: BarrierCategory,
        mechanism: TherapeuticMechanism,
    ) -> str:
        """Generate human-readable creative direction for this chapter."""
        directions = {
            1: (
                f"Chapter 1 (Introduction): Establish character the prospect "
                f"identifies with. Use {position.testimonial_type} model. "
                f"Abstract framing — focus on WHY, not HOW. "
                f"Target barrier: {barrier.value} via {mechanism.value}."
            ),
            2: (
                f"Chapter 2 (Complication): Present the problem. The character "
                f"faces the same {barrier.value} the prospect experiences. "
                f"Build tension without resolution yet."
            ),
            3: (
                f"Chapter 3 (Rising Action): Show the character evaluating options. "
                f"Deploy {mechanism.value} as the turning point. "
                f"Shift to concrete framing — specific features, evidence."
            ),
            4: (
                f"Chapter 4 (Resolution): The character's positive outcome. "
                f"Use mastery model (confident, successful). "
                f"Concrete proof that {barrier.value} was resolved."
            ),
            5: (
                f"Chapter 5 (Epilogue): Social proof confirmation. Numbers, "
                f"ratings, volume. Simplified CTA. The narrative is complete — "
                f"the prospect should feel the story is about THEM."
            ),
        }
        return directions.get(position.chapter, "")
