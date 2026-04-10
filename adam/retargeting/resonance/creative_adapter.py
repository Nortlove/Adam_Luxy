# =============================================================================
# Resonance Engineering — Layer 4: ADAPT
# Location: adam/retargeting/resonance/creative_adapter.py
# =============================================================================

"""
Real-Time Creative Adaptation to Page Context.

When an ad impression lands on a specific page, adapt the creative
parameters to resonate with the actual page psychological field.

Same mechanism, different execution:
  evidence_proof on analytical page → data, statistics, comparisons
  evidence_proof on emotional page  → testimonial, personal story
  social_proof on authority page    → expert endorsement
  social_proof on community page    → peer reviews, user counts

Implementation: Pre-computed adaptation lookup per (mechanism, page_cluster).
At bid time (<5ms), page is mapped to nearest cluster and adaptation applied.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from adam.retargeting.resonance.models import PageMindstateVector

logger = logging.getLogger(__name__)


@dataclass
class CreativeAdaptation:
    """How to adapt the creative for a given page context."""

    # Original parameters (from mechanism selection)
    mechanism: str
    original_tone: str
    original_construal: str

    # Adapted parameters (for this page context)
    adapted_tone: str            # warm, authoritative, urgent, balanced
    adapted_construal: str       # abstract, concrete, mixed
    adapted_evidence_type: str   # data, testimonial, comparison, narrative, authority
    adapted_cta_style: str       # soft, direct, urgent, social
    adapted_headline_approach: str  # question, statement, number, story

    # Page context used
    page_cluster: str
    page_dominant_trait: str      # analytical, emotional, social, transactional
    resonance_multiplier: float
    adaptation_confidence: float


# ─────────────────────────────────────────────────────────────────────
# Page clusters — common psychological environments for ad placement
# ─────────────────────────────────────────────────────────────────────

PAGE_CLUSTERS = {
    "analytical": {
        "description": "High cognitive engagement, data-driven, central processing",
        "indicators": {"cognitive_engagement": 0.7, "information_seeking": 0.7, "emotional_arousal": 0.3},
        "tone": "authoritative",
        "evidence": "data",
        "cta": "direct",
        "headline": "number",
        "construal": "concrete",
    },
    "emotional": {
        "description": "High emotional resonance, narrative-driven, peripheral processing",
        "indicators": {"emotional_arousal": 0.7, "emotional_valence": 0.5, "narrative_transport": 0.6},
        "tone": "warm",
        "evidence": "testimonial",
        "cta": "soft",
        "headline": "story",
        "construal": "abstract",
    },
    "social": {
        "description": "Community-oriented, social proof dominant, peer influence",
        "indicators": {"social_calibration": 0.7, "social_proof_sensitivity": 0.6, "mimetic_desire": 0.5},
        "tone": "warm",
        "evidence": "social",
        "cta": "social",
        "headline": "question",
        "construal": "mixed",
    },
    "transactional": {
        "description": "Purchase-oriented, comparison-heavy, concrete processing",
        "indicators": {"loss_aversion_intensity": 0.5, "temporal_discounting": 0.6, "information_seeking": 0.6},
        "tone": "urgent",
        "evidence": "comparison",
        "cta": "urgent",
        "headline": "number",
        "construal": "concrete",
    },
    "aspirational": {
        "description": "Status-oriented, luxury positioning, identity signaling",
        "indicators": {"status_sensitivity": 0.7, "emotional_valence": 0.6, "approach_avoidance": 0.6},
        "tone": "warm",
        "evidence": "narrative",
        "cta": "soft",
        "headline": "statement",
        "construal": "abstract",
    },
    "neutral": {
        "description": "Default — no strong psychological orientation",
        "indicators": {},
        "tone": "balanced",
        "evidence": "testimonial",
        "cta": "direct",
        "headline": "statement",
        "construal": "mixed",
    },
}

# Mechanism-specific overrides per cluster
# When a specific mechanism lands on a specific cluster, override defaults
MECHANISM_CLUSTER_OVERRIDES = {
    ("evidence_proof", "emotional"): {
        "evidence": "testimonial",  # Evidence on emotional page = story, not stats
        "tone": "warm",
    },
    ("evidence_proof", "social"): {
        "evidence": "authority",  # Evidence on social page = expert endorsement
    },
    ("narrative_transportation", "analytical"): {
        "evidence": "narrative",  # Keep narrative even on analytical (the contrast works)
        "tone": "balanced",
    },
    ("social_proof_matched", "analytical"): {
        "evidence": "data",  # Social proof on analytical = numbers ("3,247 rides")
    },
    ("loss_framing", "aspirational"): {
        "tone": "balanced",  # Don't use urgent on aspirational (kills the vibe)
        "cta": "soft",
    },
    ("claude_argument", "emotional"): {
        "evidence": "narrative",  # Claude argument on emotional = story-form argument
    },
    ("anxiety_resolution", "aspirational"): {
        "tone": "warm",  # Anxiety resolution on aspirational = gentle reassurance
        "evidence": "testimonial",
    },
}


class CreativeAdapter:
    """Adapts creative execution to the page's psychological field."""

    def classify_page_cluster(
        self, mindstate: PageMindstateVector
    ) -> str:
        """Classify a page into one of the predefined clusters.

        Uses cosine similarity between the page's NDF/environment dimensions
        and each cluster's indicator profile.
        """
        best_cluster = "neutral"
        best_score = -1.0

        page_vec = mindstate.to_numpy()
        ndf = mindstate.ndf_activations
        env = {
            "emotional_valence": mindstate.emotional_valence,
            "emotional_arousal": mindstate.emotional_arousal,
            "cognitive_load": mindstate.cognitive_load,
            "publisher_authority": mindstate.publisher_authority,
        }
        page_features = {**mindstate.edge_dimensions, **ndf, **env}

        for cluster_name, cluster_info in PAGE_CLUSTERS.items():
            indicators = cluster_info.get("indicators", {})
            if not indicators:
                continue

            # Score = average match across indicator dimensions
            match_sum = 0.0
            match_count = 0
            for dim, target in indicators.items():
                actual = page_features.get(dim, 0.5)
                match_sum += 1.0 - abs(actual - target)
                match_count += 1

            if match_count > 0:
                score = match_sum / match_count
                if score > best_score:
                    best_score = score
                    best_cluster = cluster_name

        return best_cluster

    def adapt(
        self,
        mechanism: str,
        page_mindstate: PageMindstateVector,
        original_tone: str = "balanced",
        original_construal: str = "mixed",
        resonance_multiplier: float = 1.0,
    ) -> CreativeAdaptation:
        """Adapt creative parameters to the page context.

        Args:
            mechanism: The therapeutic mechanism being deployed
            page_mindstate: The page's psychological field
            original_tone: Tone from the mechanism selector
            original_construal: Construal from the narrative arc
            resonance_multiplier: From the resonance model

        Returns:
            CreativeAdaptation with adapted parameters
        """
        cluster = self.classify_page_cluster(page_mindstate)
        cluster_info = PAGE_CLUSTERS.get(cluster, PAGE_CLUSTERS["neutral"])

        # Start with cluster defaults
        tone = cluster_info["tone"]
        evidence = cluster_info["evidence"]
        cta = cluster_info["cta"]
        headline = cluster_info["headline"]
        construal = cluster_info["construal"]

        # Apply mechanism × cluster overrides
        override_key = (mechanism, cluster)
        if override_key in MECHANISM_CLUSTER_OVERRIDES:
            overrides = MECHANISM_CLUSTER_OVERRIDES[override_key]
            tone = overrides.get("tone", tone)
            evidence = overrides.get("evidence", evidence)
            cta = overrides.get("cta", cta)
            headline = overrides.get("headline", headline)

        # Dominant trait for interpretation
        dominant_trait = cluster

        return CreativeAdaptation(
            mechanism=mechanism,
            original_tone=original_tone,
            original_construal=original_construal,
            adapted_tone=tone,
            adapted_construal=construal,
            adapted_evidence_type=evidence,
            adapted_cta_style=cta,
            adapted_headline_approach=headline,
            page_cluster=cluster,
            page_dominant_trait=dominant_trait,
            resonance_multiplier=resonance_multiplier,
            adaptation_confidence=page_mindstate.confidence,
        )
