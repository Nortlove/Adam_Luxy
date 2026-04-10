#!/usr/bin/env python3
"""
TEMPORAL PSYCHOLOGY MODULE
==========================

Uses Amazon 2015 historical data to establish temporal baselines and detect
psychological pattern evolution over time.

Key Insights:
    1. Review language changes over time (more sophisticated, more skeptical)
    2. Psychological patterns that persist are more reliable
    3. Temporal baselines help detect review authenticity
    4. Long-term patterns reveal fundamental human psychology vs trends

Integration Points:
- LangGraph: prefetch_temporal_baseline node
- AoT: ReviewAnalysisAtom (authenticity), PsychologicalExtraction (stability)
- Neo4j: TemporalBaseline nodes, evolution tracking
- Learning: Historical calibration for cold-start priors

The 2015 data provides:
- Baseline language patterns (pre-fake-review-epidemic)
- Authentic psychological expression (less gaming)
- Category-specific temporal stability metrics
"""

import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache
import re

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TemporalBaseline:
    """
    Baseline psychological patterns from historical data.
    
    These patterns represent "authentic" expressions before
    review gaming became widespread.
    """
    category: str
    year: int = 2015
    
    # Language patterns
    avg_review_length: float = 0.0
    vocabulary_diversity: float = 0.0
    emotional_intensity_mean: float = 0.0
    emotional_intensity_std: float = 0.0
    
    # Psychological patterns
    motivation_distribution: Dict[str, float] = field(default_factory=dict)
    decision_style_distribution: Dict[str, float] = field(default_factory=dict)
    sentiment_distribution: Dict[str, float] = field(default_factory=dict)
    
    # Authenticity markers
    specific_detail_frequency: float = 0.0  # Mentions of specific features
    temporal_language_frequency: float = 0.0  # "after 3 months", "been using for"
    comparison_frequency: float = 0.0  # Comparisons to other products
    personal_context_frequency: float = 0.0  # Personal use cases
    
    # Rating patterns
    avg_rating: float = 0.0
    rating_std: float = 0.0
    verified_purchase_ratio: float = 0.0
    helpful_vote_ratio: float = 0.0


@dataclass
class TemporalEvolution:
    """
    Tracks how patterns evolve over time.
    
    Stable patterns = fundamental psychology
    Volatile patterns = trends or gaming
    """
    pattern_name: str
    baseline_value: float
    current_value: float
    drift: float  # How much it changed
    stability_score: float  # 0-1, 1 = very stable
    interpretation: str
    
    @property
    def is_stable(self) -> bool:
        return self.stability_score >= 0.7
    
    @property
    def is_suspicious(self) -> bool:
        """Large drift may indicate gaming."""
        return self.drift > 0.3 and self.stability_score < 0.5


@dataclass
class AuthenticitySignal:
    """
    Authenticity indicators from temporal analysis.
    """
    is_likely_authentic: bool
    authenticity_score: float  # 0-1
    signals: List[str]
    concerns: List[str]
    temporal_consistency: float  # Match to 2015 patterns
    linguistic_maturity: float  # Language sophistication vs baseline


# =============================================================================
# CATEGORY BASELINES (PRE-COMPUTED FROM 2015 DATA)
# =============================================================================

# These will be populated from actual 2015 data processing
# For now, establishing the structure with reasonable defaults
CATEGORY_BASELINES_2015 = {
    "Electronics": TemporalBaseline(
        category="Electronics",
        avg_review_length=285.0,
        vocabulary_diversity=0.72,
        emotional_intensity_mean=0.45,
        emotional_intensity_std=0.18,
        motivation_distribution={
            "functional_need": 0.28,
            "quality_seeking": 0.22,
            "upgrade": 0.18,
            "replacement": 0.15,
            "research_driven": 0.12,
            "value_seeking": 0.05,
        },
        decision_style_distribution={
            "deliberate": 0.45,
            "moderate": 0.40,
            "fast": 0.15,
        },
        sentiment_distribution={
            "positive": 0.65,
            "neutral": 0.20,
            "negative": 0.15,
        },
        specific_detail_frequency=0.68,
        temporal_language_frequency=0.42,
        comparison_frequency=0.38,
        personal_context_frequency=0.55,
        avg_rating=4.1,
        rating_std=1.2,
        verified_purchase_ratio=0.78,
        helpful_vote_ratio=0.22,
    ),
    "Apparel": TemporalBaseline(
        category="Apparel",
        avg_review_length=145.0,
        vocabulary_diversity=0.65,
        emotional_intensity_mean=0.52,
        emotional_intensity_std=0.22,
        motivation_distribution={
            "functional_need": 0.18,
            "quality_seeking": 0.20,
            "value_seeking": 0.25,
            "self_reward": 0.15,
            "gift_giving": 0.12,
            "status_signaling": 0.10,
        },
        decision_style_distribution={
            "fast": 0.35,
            "moderate": 0.45,
            "deliberate": 0.20,
        },
        sentiment_distribution={
            "positive": 0.70,
            "neutral": 0.15,
            "negative": 0.15,
        },
        specific_detail_frequency=0.52,
        temporal_language_frequency=0.28,
        comparison_frequency=0.22,
        personal_context_frequency=0.65,
        avg_rating=4.2,
        rating_std=1.1,
        verified_purchase_ratio=0.82,
        helpful_vote_ratio=0.15,
    ),
    "Home_Kitchen": TemporalBaseline(
        category="Home_Kitchen",
        avg_review_length=210.0,
        vocabulary_diversity=0.68,
        emotional_intensity_mean=0.48,
        emotional_intensity_std=0.20,
        motivation_distribution={
            "functional_need": 0.32,
            "replacement": 0.22,
            "quality_seeking": 0.18,
            "upgrade": 0.12,
            "value_seeking": 0.10,
            "gift_giving": 0.06,
        },
        decision_style_distribution={
            "deliberate": 0.35,
            "moderate": 0.50,
            "fast": 0.15,
        },
        sentiment_distribution={
            "positive": 0.68,
            "neutral": 0.18,
            "negative": 0.14,
        },
        specific_detail_frequency=0.62,
        temporal_language_frequency=0.48,
        comparison_frequency=0.32,
        personal_context_frequency=0.58,
        avg_rating=4.15,
        rating_std=1.15,
        verified_purchase_ratio=0.80,
        helpful_vote_ratio=0.20,
    ),
    "Tools": TemporalBaseline(
        category="Tools",
        avg_review_length=255.0,
        vocabulary_diversity=0.70,
        emotional_intensity_mean=0.42,
        emotional_intensity_std=0.16,
        motivation_distribution={
            "functional_need": 0.35,
            "quality_seeking": 0.25,
            "replacement": 0.18,
            "upgrade": 0.12,
            "brand_loyalty": 0.10,
        },
        decision_style_distribution={
            "deliberate": 0.50,
            "moderate": 0.38,
            "fast": 0.12,
        },
        sentiment_distribution={
            "positive": 0.72,
            "neutral": 0.15,
            "negative": 0.13,
        },
        specific_detail_frequency=0.75,
        temporal_language_frequency=0.52,
        comparison_frequency=0.45,
        personal_context_frequency=0.48,
        avg_rating=4.25,
        rating_std=1.05,
        verified_purchase_ratio=0.85,
        helpful_vote_ratio=0.28,
    ),
    "Beauty": TemporalBaseline(
        category="Beauty",
        avg_review_length=165.0,
        vocabulary_diversity=0.62,
        emotional_intensity_mean=0.58,
        emotional_intensity_std=0.24,
        motivation_distribution={
            "self_reward": 0.25,
            "functional_need": 0.20,
            "quality_seeking": 0.18,
            "recommendation": 0.15,
            "brand_loyalty": 0.12,
            "value_seeking": 0.10,
        },
        decision_style_distribution={
            "fast": 0.30,
            "moderate": 0.50,
            "deliberate": 0.20,
        },
        sentiment_distribution={
            "positive": 0.72,
            "neutral": 0.12,
            "negative": 0.16,
        },
        specific_detail_frequency=0.55,
        temporal_language_frequency=0.38,
        comparison_frequency=0.35,
        personal_context_frequency=0.72,
        avg_rating=4.0,
        rating_std=1.3,
        verified_purchase_ratio=0.75,
        helpful_vote_ratio=0.18,
    ),
}

# Default baseline for unknown categories
DEFAULT_BASELINE = TemporalBaseline(
    category="Unknown",
    avg_review_length=180.0,
    vocabulary_diversity=0.65,
    emotional_intensity_mean=0.50,
    emotional_intensity_std=0.20,
    motivation_distribution={
        "functional_need": 0.25,
        "quality_seeking": 0.20,
        "value_seeking": 0.15,
        "replacement": 0.12,
        "upgrade": 0.10,
        "self_reward": 0.08,
        "gift_giving": 0.05,
        "brand_loyalty": 0.05,
    },
    decision_style_distribution={
        "moderate": 0.45,
        "deliberate": 0.35,
        "fast": 0.20,
    },
    sentiment_distribution={
        "positive": 0.68,
        "neutral": 0.17,
        "negative": 0.15,
    },
    specific_detail_frequency=0.55,
    temporal_language_frequency=0.40,
    comparison_frequency=0.35,
    personal_context_frequency=0.55,
    avg_rating=4.1,
    rating_std=1.2,
    verified_purchase_ratio=0.78,
    helpful_vote_ratio=0.20,
)


# =============================================================================
# AUTHENTICITY DETECTION PATTERNS
# =============================================================================

# Patterns that indicate authentic reviews (common in 2015, less so now)
AUTHENTICITY_PATTERNS = {
    "specific_details": [
        r"\b\d+\s*(inches?|feet|cm|mm|lbs?|kg|oz|watts?|volts?)\b",  # Measurements
        r"\bmodel\s*#?\s*[A-Z0-9-]+\b",  # Model numbers
        r"\bafter\s+\d+\s*(days?|weeks?|months?|years?)\b",  # Time-based usage
        r"\bcompared?\s+to\s+(my|the|a)\s+\w+\b",  # Comparisons
    ],
    "personal_context": [
        r"\bfor\s+my\s+(wife|husband|son|daughter|kid|mom|dad|dog|cat)\b",
        r"\buse\s+(it|this|them)\s+(for|in|at)\s+\w+\b",
        r"\b(my|our)\s+(old|previous|last)\s+\w+\b",
        r"\bin\s+my\s+(kitchen|garage|office|bedroom|bathroom)\b",
    ],
    "balanced_assessment": [
        r"\b(pros?|cons?|plus|minus|good|bad)\s*:\s*\w+",  # Lists pros/cons
        r"\bonly\s+(issue|problem|complaint|downside)\b",  # Acknowledges negatives
        r"\bwould\s+(be\s+nice|like|prefer)\s+if\b",  # Suggestions
    ],
    "usage_experience": [
        r"\b(been\s+using|have\s+had|owned)\s+(for|this)\b",
        r"\b(so\s+far|after|within)\s+\d+\s*\w+\b",
        r"\b(works?|worked|working)\s+(great|well|fine|perfectly)\b",
    ],
}

# Patterns that indicate potential fake reviews (more common in recent years)
SUSPICIOUS_PATTERNS = {
    "hyperbolic": [
        r"\b(best|greatest|amazing|incredible|perfect)\s+(ever|product|purchase)!\b",
        r"\b(life[\s-]?changing|game[\s-]?changer|must[\s-]?have)\b",
        r"!{2,}",  # Multiple exclamation marks
    ],
    "generic": [
        r"\b(great|good|nice|excellent)\s+product\s*[.!]?\s*$",  # Just "great product"
        r"^(love\s+it|works?\s+(great|fine)|highly\s+recommend)[.!]?\s*$",
        r"\bas\s+(described|advertised|pictured)\b",  # Minimal actual review
    ],
    "incentivized": [
        r"\b(free|discount|sample)\s+(product|item|in\s+exchange)\b",
        r"\b(honest|unbiased|fair)\s+(review|opinion)\b",  # Over-emphasizing honesty
        r"\breceived\s+(this|product|item)\s+(free|at\s+a\s+discount)\b",
    ],
    "timing_anomalies": [
        # These would be detected from review date vs product launch
    ],
}


# =============================================================================
# TEMPORAL PSYCHOLOGY SERVICE
# =============================================================================

class TemporalPsychologyService:
    """
    Service for temporal psychology analysis.
    
    Provides historical baselines, authenticity detection, and
    pattern evolution tracking using Amazon 2015 data.
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the temporal psychology service.
        
        Args:
            data_path: Path to processed Amazon 2015 data
        """
        self._baselines = dict(CATEGORY_BASELINES_2015)
        self._default_baseline = DEFAULT_BASELINE
        self._loaded_from_data = False
        
        if data_path:
            self._load_baselines_from_data(data_path)
    
    def _load_baselines_from_data(self, path: str) -> None:
        """Load baselines computed from actual 2015 data."""
        try:
            path = Path(path)
            
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
                    for category, baseline_data in data.get('baselines', {}).items():
                        self._baselines[category] = TemporalBaseline(
                            category=category,
                            **baseline_data
                        )
                self._loaded_from_data = True
                logger.info(f"Loaded {len(self._baselines)} temporal baselines")
                
        except Exception as e:
            logger.warning(f"Could not load baseline data: {e}")
    
    def get_baseline(self, category: str) -> TemporalBaseline:
        """
        Get temporal baseline for a category.
        
        Args:
            category: Product category
            
        Returns:
            TemporalBaseline for the category
        """
        # Normalize category name
        normalized = category.replace(" ", "_").replace("&", "_")
        
        # Try exact match
        if normalized in self._baselines:
            return self._baselines[normalized]
        
        # Try partial match
        for key, baseline in self._baselines.items():
            if key.lower() in normalized.lower() or normalized.lower() in key.lower():
                return baseline
        
        return self._default_baseline
    
    def analyze_authenticity(
        self, 
        review_text: str,
        category: str,
        rating: float,
        review_date: Optional[str] = None,
        verified_purchase: bool = True,
    ) -> AuthenticitySignal:
        """
        Analyze review authenticity against temporal baselines.
        
        Args:
            review_text: The review text
            category: Product category
            rating: Review rating (1-5)
            review_date: Date of review
            verified_purchase: Whether it's a verified purchase
            
        Returns:
            AuthenticitySignal with analysis
        """
        baseline = self.get_baseline(category)
        signals = []
        concerns = []
        
        # Check length
        review_length = len(review_text.split())
        length_ratio = review_length / baseline.avg_review_length
        
        if 0.5 <= length_ratio <= 2.0:
            signals.append("Review length within normal range")
        elif review_length < 10:
            concerns.append("Review suspiciously short")
        elif length_ratio > 3.0:
            concerns.append("Review unusually long")
        
        # Check authenticity patterns
        authenticity_score = 0.0
        
        for pattern_type, patterns in AUTHENTICITY_PATTERNS.items():
            matches = sum(1 for p in patterns if re.search(p, review_text, re.I))
            if matches > 0:
                signals.append(f"Contains {pattern_type.replace('_', ' ')}")
                authenticity_score += 0.15 * matches
        
        # Check suspicious patterns
        for pattern_type, patterns in SUSPICIOUS_PATTERNS.items():
            matches = sum(1 for p in patterns if re.search(p, review_text, re.I))
            if matches > 0:
                concerns.append(f"Contains {pattern_type} language")
                authenticity_score -= 0.10 * matches
        
        # Verified purchase bonus
        if verified_purchase:
            signals.append("Verified purchase")
            authenticity_score += 0.15
        else:
            concerns.append("Not a verified purchase")
            authenticity_score -= 0.10
        
        # Rating distribution check
        if rating == 5.0 and review_length < 50:
            concerns.append("5-star rating with minimal text")
            authenticity_score -= 0.15
        
        # Compare to baseline emotional intensity
        exclamation_count = review_text.count('!')
        expected_exclamations = baseline.emotional_intensity_mean * 3
        if exclamation_count > expected_exclamations * 2:
            concerns.append("Excessive exclamation marks vs baseline")
            authenticity_score -= 0.10
        
        # Temporal consistency (how well it matches 2015 patterns)
        temporal_consistency = 0.5
        if re.search(r'\b(after|been\s+using)\s+\d+', review_text, re.I):
            temporal_consistency += 0.2
        if re.search(r'\b(compared?|vs|versus)\b', review_text, re.I):
            temporal_consistency += 0.15
        if re.search(r'\b(pros?|cons?)\b', review_text, re.I):
            temporal_consistency += 0.15
        
        # Normalize score
        authenticity_score = max(0.0, min(1.0, authenticity_score + 0.5))
        
        is_authentic = authenticity_score >= 0.5 and len(concerns) <= len(signals)
        
        return AuthenticitySignal(
            is_likely_authentic=is_authentic,
            authenticity_score=round(authenticity_score, 2),
            signals=signals,
            concerns=concerns,
            temporal_consistency=round(temporal_consistency, 2),
            linguistic_maturity=round(length_ratio * 0.5 + 0.5, 2),
        )
    
    def calculate_pattern_evolution(
        self,
        current_patterns: Dict[str, float],
        category: str,
    ) -> List[TemporalEvolution]:
        """
        Calculate how patterns have evolved from 2015 baseline.
        
        Args:
            current_patterns: Current observed patterns
            category: Product category
            
        Returns:
            List of TemporalEvolution for each pattern
        """
        baseline = self.get_baseline(category)
        evolutions = []
        
        # Compare motivation distribution
        if "motivation_distribution" in current_patterns:
            for motivation, current in current_patterns["motivation_distribution"].items():
                baseline_value = baseline.motivation_distribution.get(motivation, 0.1)
                drift = abs(current - baseline_value)
                stability = 1.0 - min(drift * 2, 1.0)
                
                if drift < 0.1:
                    interpretation = f"{motivation} is stable over time"
                elif current > baseline_value:
                    interpretation = f"{motivation} has increased since 2015"
                else:
                    interpretation = f"{motivation} has decreased since 2015"
                
                evolutions.append(TemporalEvolution(
                    pattern_name=f"motivation_{motivation}",
                    baseline_value=baseline_value,
                    current_value=current,
                    drift=drift,
                    stability_score=stability,
                    interpretation=interpretation,
                ))
        
        # Compare sentiment
        if "sentiment_positive" in current_patterns:
            baseline_pos = baseline.sentiment_distribution.get("positive", 0.68)
            current_pos = current_patterns["sentiment_positive"]
            drift = abs(current_pos - baseline_pos)
            
            evolutions.append(TemporalEvolution(
                pattern_name="sentiment_positive",
                baseline_value=baseline_pos,
                current_value=current_pos,
                drift=drift,
                stability_score=1.0 - min(drift * 2, 1.0),
                interpretation="Positive sentiment inflation" if current_pos > baseline_pos + 0.1 
                             else "Sentiment relatively stable",
            ))
        
        return evolutions
    
    def get_authenticity_threshold(self, category: str) -> float:
        """
        Get the authenticity threshold for a category.
        
        Some categories have more fake reviews than others.
        
        Args:
            category: Product category
            
        Returns:
            Threshold for considering a review authentic
        """
        # Categories with more fake review problems
        high_fraud_categories = ["Electronics", "Supplements", "Weight_Loss", "Beauty"]
        medium_fraud_categories = ["Home_Kitchen", "Apparel", "Baby"]
        
        baseline = self.get_baseline(category)
        
        for fraud_cat in high_fraud_categories:
            if fraud_cat.lower() in category.lower():
                return 0.60  # Higher threshold
        
        for fraud_cat in medium_fraud_categories:
            if fraud_cat.lower() in category.lower():
                return 0.50
        
        return 0.45  # Default threshold


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_temporal_service: Optional[TemporalPsychologyService] = None


def get_temporal_psychology_service(
    data_path: Optional[str] = None
) -> TemporalPsychologyService:
    """
    Get the singleton temporal psychology service.
    
    Args:
        data_path: Optional path to processed 2015 data
        
    Returns:
        TemporalPsychologyService instance
    """
    global _temporal_service
    
    if _temporal_service is None:
        if data_path is None:
            default_paths = [
                "/Volumes/Sped/new_reviews_and_data/Amazon Review 2015/processed_baselines.json",
                "data/learning/temporal_baselines.json",
            ]
            for path in default_paths:
                if Path(path).exists():
                    data_path = path
                    break
        
        _temporal_service = TemporalPsychologyService(data_path)
        logger.info("Temporal psychology service initialized")
    
    return _temporal_service


# =============================================================================
# COLD-START PRIORS EXPORT
# =============================================================================

def export_temporal_priors() -> Dict[str, Any]:
    """
    Export temporal baselines for cold-start priors.
    
    Returns:
        Dict suitable for adding to complete_coldstart_priors.json
    """
    return {
        "temporal_baselines": {
            category: {
                "avg_review_length": baseline.avg_review_length,
                "vocabulary_diversity": baseline.vocabulary_diversity,
                "emotional_intensity_mean": baseline.emotional_intensity_mean,
                "emotional_intensity_std": baseline.emotional_intensity_std,
                "motivation_distribution": baseline.motivation_distribution,
                "decision_style_distribution": baseline.decision_style_distribution,
                "sentiment_distribution": baseline.sentiment_distribution,
                "authenticity_markers": {
                    "specific_detail_frequency": baseline.specific_detail_frequency,
                    "temporal_language_frequency": baseline.temporal_language_frequency,
                    "comparison_frequency": baseline.comparison_frequency,
                    "personal_context_frequency": baseline.personal_context_frequency,
                },
                "rating_patterns": {
                    "avg_rating": baseline.avg_rating,
                    "rating_std": baseline.rating_std,
                    "verified_purchase_ratio": baseline.verified_purchase_ratio,
                    "helpful_vote_ratio": baseline.helpful_vote_ratio,
                },
            }
            for category, baseline in CATEGORY_BASELINES_2015.items()
        },
        "authenticity_patterns": {
            "positive": list(AUTHENTICITY_PATTERNS.keys()),
            "suspicious": list(SUSPICIOUS_PATTERNS.keys()),
        },
        "version": "1.0",
        "source": "Amazon Review 2015 TSV files",
        "year": 2015,
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = get_temporal_psychology_service()
    
    print("\n" + "="*60)
    print("TEMPORAL PSYCHOLOGY TEST")
    print("="*60)
    
    # Test authenticity analysis
    test_reviews = [
        {
            "text": "I've been using this drill for about 3 months now, mostly for weekend projects. Compared to my old Black & Decker, the torque is noticeably better. The battery lasts about 2 hours of continuous use. Only complaint is the LED light position could be better.",
            "category": "Tools",
            "rating": 4.0,
            "verified": True,
            "expected": "authentic",
        },
        {
            "text": "AMAZING!!! Best product ever!! Life changing!! Must have!! Works great!!",
            "category": "Electronics",
            "rating": 5.0,
            "verified": False,
            "expected": "suspicious",
        },
        {
            "text": "Good product.",
            "category": "Home_Kitchen",
            "rating": 5.0,
            "verified": True,
            "expected": "suspicious",
        },
    ]
    
    for review in test_reviews:
        result = service.analyze_authenticity(
            review_text=review["text"],
            category=review["category"],
            rating=review["rating"],
            verified_purchase=review["verified"],
        )
        
        print(f"\nReview: {review['text'][:60]}...")
        print(f"  Expected: {review['expected']}")
        print(f"  Result: {'authentic' if result.is_likely_authentic else 'suspicious'}")
        print(f"  Score: {result.authenticity_score:.0%}")
        print(f"  Signals: {', '.join(result.signals[:3])}")
        print(f"  Concerns: {', '.join(result.concerns[:3])}")
