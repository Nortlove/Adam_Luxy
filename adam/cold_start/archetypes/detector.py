# =============================================================================
# ADAM Enhancement #13: Archetype Detector
# Location: adam/cold_start/archetypes/detector.py
# =============================================================================

"""
Archetype detection engine.

Matches users to psychological archetypes based on:
- Inferred trait values (from behavior)
- Demographic signals
- Contextual signals
- Behavioral patterns
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from adam.cold_start.models.enums import (
    ArchetypeID, PersonalityTrait
)
from adam.cold_start.models.archetypes import (
    ArchetypeMatchResult, ArchetypeDefinition
)
from .definitions import ARCHETYPE_DEFINITIONS, get_archetype

logger = logging.getLogger(__name__)


class ArchetypeDetector:
    """
    Matches users to psychological archetypes.
    
    Uses multiple signals:
    1. Trait similarity (Big Five distance)
    2. Behavioral patterns (if available)
    3. Demographic priors (age/gender associations)
    4. Contextual signals (content preferences)
    """
    
    def __init__(
        self,
        min_confidence_threshold: float = 0.3,
        demographic_weight: float = 0.2,
        behavioral_weight: float = 0.3,
        trait_weight: float = 0.5,
    ):
        self.min_confidence = min_confidence_threshold
        self.demographic_weight = demographic_weight
        self.behavioral_weight = behavioral_weight
        self.trait_weight = trait_weight
        
        self.archetypes = ARCHETYPE_DEFINITIONS
        
        # Demographic associations (from research)
        self.age_archetype_priors = {
            "18-24": {ArchetypeID.EXPLORER: 1.3, ArchetypeID.CREATOR: 1.2},
            "25-34": {ArchetypeID.ACHIEVER: 1.2, ArchetypeID.CONNECTOR: 1.1},
            "35-44": {ArchetypeID.ACHIEVER: 1.3, ArchetypeID.PRAGMATIST: 1.2},
            "45-54": {ArchetypeID.GUARDIAN: 1.2, ArchetypeID.PRAGMATIST: 1.2},
            "55+": {ArchetypeID.GUARDIAN: 1.3, ArchetypeID.NURTURER: 1.2},
        }
        
        self.gender_archetype_priors = {
            "male": {ArchetypeID.ACHIEVER: 1.1, ArchetypeID.ANALYST: 1.1},
            "female": {ArchetypeID.CONNECTOR: 1.1, ArchetypeID.NURTURER: 1.2},
        }
    
    def detect_archetype(
        self,
        trait_estimates: Optional[Dict[PersonalityTrait, float]] = None,
        behavioral_signals: Optional[Dict[str, float]] = None,
        age_bracket: Optional[str] = None,
        gender: Optional[str] = None,
        content_types_consumed: Optional[List[str]] = None,
    ) -> ArchetypeMatchResult:
        """
        Detect the best-matching archetype for a user.
        
        Args:
            trait_estimates: Estimated Big Five values (0-1)
            behavioral_signals: Behavioral pattern scores
            age_bracket: Age bracket (e.g., "25-34")
            gender: Gender ("male", "female", other)
            content_types_consumed: List of content types consumed
            
        Returns:
            ArchetypeMatchResult with matched archetype and confidence
        """
        archetype_scores: Dict[ArchetypeID, float] = {}
        
        # Initialize with uniform prior
        for archetype_id in ArchetypeID:
            archetype_scores[archetype_id] = 1.0
        
        # Apply trait-based scoring
        if trait_estimates:
            trait_scores = self._score_by_traits(trait_estimates)
            for arch, score in trait_scores.items():
                archetype_scores[arch] *= (1 + score * self.trait_weight)
        
        # Apply demographic priors
        demo_scores = self._score_by_demographics(age_bracket, gender)
        for arch, multiplier in demo_scores.items():
            archetype_scores[arch] *= multiplier ** self.demographic_weight
        
        # Apply behavioral scoring
        if behavioral_signals:
            behavioral_scores = self._score_by_behavior(behavioral_signals)
            for arch, score in behavioral_scores.items():
                archetype_scores[arch] *= (1 + score * self.behavioral_weight)
        
        # Normalize scores
        total_score = sum(archetype_scores.values())
        if total_score > 0:
            for arch in archetype_scores:
                archetype_scores[arch] /= total_score
        
        # Find best match
        best_archetype = max(archetype_scores, key=archetype_scores.get)
        best_score = archetype_scores[best_archetype]
        
        # Calculate confidence
        scores_sorted = sorted(archetype_scores.values(), reverse=True)
        if len(scores_sorted) >= 2 and scores_sorted[1] > 0:
            clarity = 1.0 - (scores_sorted[1] / scores_sorted[0])
        else:
            clarity = 1.0
        
        confidence = min(1.0, best_score * 2 * clarity)
        
        # Build evidence lists
        trait_evidence = trait_estimates or {}
        behavioral_evidence = list(behavioral_signals.keys()) if behavioral_signals else []
        contextual_evidence = []
        if age_bracket:
            contextual_evidence.append(f"age:{age_bracket}")
        if gender:
            contextual_evidence.append(f"gender:{gender}")
        
        return ArchetypeMatchResult(
            matched_archetype=best_archetype,
            confidence=confidence,
            archetype_scores=archetype_scores,
            matching_method="multi_signal",
            trait_evidence=trait_evidence,
            behavioral_evidence=behavioral_evidence,
            contextual_evidence=contextual_evidence,
        )
    
    def _score_by_traits(
        self, 
        trait_estimates: Dict[PersonalityTrait, float]
    ) -> Dict[ArchetypeID, float]:
        """Score archetypes by trait similarity."""
        scores = {}
        
        for archetype_id, archetype in self.archetypes.items():
            similarity = archetype.trait_profile.similarity_to(trait_estimates)
            scores[archetype_id] = similarity
        
        return scores
    
    def _score_by_demographics(
        self,
        age_bracket: Optional[str],
        gender: Optional[str]
    ) -> Dict[ArchetypeID, float]:
        """Get demographic-based archetype multipliers."""
        multipliers = {arch: 1.0 for arch in ArchetypeID}
        
        if age_bracket and age_bracket in self.age_archetype_priors:
            for arch, mult in self.age_archetype_priors[age_bracket].items():
                multipliers[arch] *= mult
        
        if gender and gender.lower() in self.gender_archetype_priors:
            for arch, mult in self.gender_archetype_priors[gender.lower()].items():
                multipliers[arch] *= mult
        
        return multipliers
    
    def _score_by_behavior(
        self,
        behavioral_signals: Dict[str, float]
    ) -> Dict[ArchetypeID, float]:
        """Score archetypes by behavioral patterns."""
        scores = {arch: 0.0 for arch in ArchetypeID}
        
        # Map behavioral signals to archetype affinities
        signal_archetype_map = {
            "novelty_seeking": [ArchetypeID.EXPLORER, ArchetypeID.CREATOR],
            "goal_oriented": [ArchetypeID.ACHIEVER],
            "social_engagement": [ArchetypeID.CONNECTOR],
            "risk_averse": [ArchetypeID.GUARDIAN],
            "analytical": [ArchetypeID.ANALYST],
            "creative": [ArchetypeID.CREATOR],
            "caring": [ArchetypeID.NURTURER],
            "practical": [ArchetypeID.PRAGMATIST],
        }
        
        for signal, value in behavioral_signals.items():
            if signal in signal_archetype_map:
                for arch in signal_archetype_map[signal]:
                    scores[arch] += value
        
        # Normalize
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            for arch in scores:
                scores[arch] /= max_score
        
        return scores
    
    def detect_from_session_behavior(
        self,
        session_events: List[Dict],
        age_bracket: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> ArchetypeMatchResult:
        """
        Detect archetype from session behavior alone.
        
        Used for anonymous users with no profile.
        """
        # Extract behavioral signals from session events
        behavioral_signals = self._extract_behavioral_signals(session_events)
        
        return self.detect_archetype(
            behavioral_signals=behavioral_signals,
            age_bracket=age_bracket,
            gender=gender,
        )
    
    def _extract_behavioral_signals(
        self,
        session_events: List[Dict]
    ) -> Dict[str, float]:
        """Extract behavioral signals from session events."""
        signals = {
            "novelty_seeking": 0.0,
            "goal_oriented": 0.0,
            "social_engagement": 0.0,
            "risk_averse": 0.0,
            "analytical": 0.0,
            "creative": 0.0,
            "caring": 0.0,
            "practical": 0.0,
        }
        
        if not session_events:
            return signals
        
        # Count event types
        event_counts: Dict[str, int] = {}
        total_events = len(session_events)
        
        for event in session_events:
            event_type = event.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Map events to behavioral signals
        novelty_events = ["search", "explore", "discover", "new_category"]
        goal_events = ["add_to_cart", "purchase", "complete", "goal"]
        social_events = ["share", "comment", "like", "follow"]
        analytical_events = ["compare", "review_read", "specs_view", "filter"]
        
        for event_type, count in event_counts.items():
            weight = count / total_events
            
            if any(e in event_type for e in novelty_events):
                signals["novelty_seeking"] += weight
            if any(e in event_type for e in goal_events):
                signals["goal_oriented"] += weight
            if any(e in event_type for e in social_events):
                signals["social_engagement"] += weight
            if any(e in event_type for e in analytical_events):
                signals["analytical"] += weight
        
        return signals


# Singleton instance
_detector: Optional[ArchetypeDetector] = None


def get_archetype_detector() -> ArchetypeDetector:
    """Get singleton archetype detector."""
    global _detector
    if _detector is None:
        _detector = ArchetypeDetector()
    return _detector
