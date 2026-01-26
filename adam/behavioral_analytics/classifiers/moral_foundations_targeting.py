# =============================================================================
# ADAM Behavioral Analytics: Moral Foundations Targeting
# Location: adam/behavioral_analytics/classifiers/moral_foundations_targeting.py
# =============================================================================

"""
MORAL FOUNDATIONS TARGETING

Values are UPSTREAM of preferences. Knowing moral foundations
predicts response to brand positioning better than demographics.

The 6 Moral Foundations (Haidt & Graham):
1. Care/Harm - Protecting others from harm
2. Fairness/Cheating - Justice, equality, reciprocity
3. Loyalty/Betrayal - Group membership, patriotism
4. Authority/Subversion - Respect for hierarchy, tradition
5. Sanctity/Degradation - Purity, contamination avoidance
6. Liberty/Oppression - Freedom from constraint

Effect sizes: d = 0.3-0.5 for consumer behavior predictions

Reference: Haidt & Graham; Moral Foundations Theory
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.advertising_psychology import (
    MoralFoundationsProfile,
    MoralFoundation,
    SignalConfidence,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MORAL FOUNDATION WORD DICTIONARIES
# =============================================================================

# Words indicating Care/Harm sensitivity
CARE_HARM_WORDS = [
    # Care
    'care', 'caring', 'protect', 'help', 'helping', 'compassion', 'compassionate',
    'empathy', 'nurture', 'nurturing', 'kindness', 'kind', 'gentle', 'tender',
    'vulnerable', 'children', 'baby', 'animals', 'welfare', 'support', 'safe',
    
    # Harm (negative markers)
    'hurt', 'harm', 'suffer', 'suffering', 'cruel', 'cruelty', 'abuse', 'violence',
    'pain', 'destroy', 'damage',
]

# Words indicating Fairness/Cheating sensitivity
FAIRNESS_WORDS = [
    'fair', 'fairness', 'equal', 'equality', 'justice', 'just', 'rights',
    'reciprocity', 'honest', 'honesty', 'transparent', 'transparency',
    'deserve', 'earned', 'merit', 'balanced', 'equitable',
    
    # Cheating (negative markers)
    'cheat', 'cheating', 'unfair', 'unjust', 'fraud', 'dishonest', 'corrupt',
]

# Words indicating Loyalty/Betrayal sensitivity
LOYALTY_WORDS = [
    'loyal', 'loyalty', 'team', 'family', 'community', 'together', 'united',
    'patriot', 'patriotic', 'country', 'nation', 'heritage', 'tradition',
    'belong', 'belonging', 'member', 'group', 'tribe', 'us', 'we',
    
    # Betrayal (negative markers)
    'betray', 'traitor', 'disloyal', 'abandon',
]

# Words indicating Authority/Subversion sensitivity
AUTHORITY_WORDS = [
    'authority', 'respect', 'obey', 'obedience', 'order', 'law', 'tradition',
    'traditional', 'expert', 'expertise', 'leader', 'leadership', 'senior',
    'experience', 'experienced', 'established', 'institution', 'hierarchy',
    
    # Subversion (negative markers)
    'rebel', 'disobey', 'disrespect', 'undermine',
]

# Words indicating Sanctity/Degradation sensitivity
SANCTITY_WORDS = [
    'pure', 'purity', 'clean', 'natural', 'organic', 'wholesome', 'sacred',
    'holy', 'divine', 'pristine', 'untouched', 'virgin', 'innocent',
    'healthy', 'fresh', 'authentic', 'real', 'genuine',
    
    # Degradation (negative markers)
    'dirty', 'contaminate', 'pollute', 'toxic', 'artificial', 'fake',
    'disgusting', 'gross', 'impure',
]

# Words indicating Liberty/Oppression sensitivity
LIBERTY_WORDS = [
    'free', 'freedom', 'liberty', 'choice', 'choose', 'independent', 'independence',
    'autonomous', 'autonomy', 'self', 'personal', 'individual', 'rights',
    'optional', 'flexible', 'open', 'unrestricted',
    
    # Oppression (negative markers)
    'control', 'controlling', 'force', 'forced', 'mandatory', 'required',
    'restrict', 'restricted', 'limit', 'limited', 'trap', 'trapped',
]


# =============================================================================
# FOUNDATION-SPECIFIC AD APPEALS
# =============================================================================

FOUNDATION_APPEALS = {
    MoralFoundation.CARE_HARM: {
        "sensitivity": "Protecting others from harm",
        "appeals": ["helping", "nurturing", "protection of vulnerable", "caring for family"],
        "imagery": ["children", "animals", "caring interactions", "safe environments"],
        "products": ["health", "safety", "insurance", "charitable", "baby products"],
        "copy_examples": [
            "Protect what matters most",
            "Because they depend on you",
            "Care for your loved ones",
        ],
    },
    MoralFoundation.FAIRNESS_CHEATING: {
        "sensitivity": "Justice, equality, reciprocity",
        "appeals": ["fair pricing", "equal treatment", "transparency", "earned rewards"],
        "imagery": ["balanced scales", "handshakes", "equal portions"],
        "products": ["ethical brands", "fair trade", "transparent pricing"],
        "copy_examples": [
            "Honest pricing, no hidden fees",
            "You deserve better",
            "Fair value for your money",
        ],
        "avoid": "Dynamic pricing visibility (triggers outrage)",
    },
    MoralFoundation.LOYALTY_BETRAYAL: {
        "sensitivity": "Group membership, patriotism",
        "appeals": ["heritage", "tradition", "brand community", "family legacy"],
        "imagery": ["flags", "teams", "families", "generations together"],
        "products": ["domestic brands", "legacy brands", "sports teams", "local businesses"],
        "copy_examples": [
            "Part of our family for generations",
            "Join millions who trust us",
            "Made in America, by Americans",
        ],
    },
    MoralFoundation.AUTHORITY_SUBVERSION: {
        "sensitivity": "Respect for hierarchy, tradition",
        "appeals": ["expertise", "established brands", "endorsements", "tradition"],
        "imagery": ["professionals", "certificates", "institutions", "suits"],
        "products": ["premium brands", "professional services", "traditional categories"],
        "copy_examples": [
            "Trusted by experts",
            "The industry standard since 1950",
            "Recommended by professionals",
        ],
    },
    MoralFoundation.SANCTITY_DEGRADATION: {
        "sensitivity": "Purity, contamination avoidance",
        "appeals": ["natural", "clean", "pure", "organic", "wholesome"],
        "imagery": ["nature", "white space", "cleanliness", "fresh ingredients"],
        "products": ["food", "beauty", "cleaning", "health", "baby"],
        "copy_examples": [
            "Pure and natural",
            "No artificial ingredients",
            "Clean beauty for clean living",
        ],
        "avoid": "Any contamination associations, artificial ingredients prominent",
    },
    MoralFoundation.LIBERTY_OPPRESSION: {
        "sensitivity": "Freedom from constraint",
        "appeals": ["choice", "freedom", "no obligations", "customization"],
        "imagery": ["open spaces", "options", "paths", "keys"],
        "products": ["experiences", "travel", "customizable products", "flexible services"],
        "copy_examples": [
            "Your choice, your way",
            "No contracts, no commitments",
            "Freedom to choose",
        ],
        "avoid": "Controlling language, forced bundling, 'must' or 'need' language",
    },
}


# =============================================================================
# DETECTION RESULT
# =============================================================================

class MoralFoundationsDetection(BaseModel):
    """
    Result of moral foundations detection.
    
    Provides foundation scores and ad targeting recommendations.
    """
    
    # Foundation scores (0-1)
    care_harm: float = Field(default=0.5, ge=0.0, le=1.0)
    fairness_cheating: float = Field(default=0.5, ge=0.0, le=1.0)
    loyalty_betrayal: float = Field(default=0.5, ge=0.0, le=1.0)
    authority_subversion: float = Field(default=0.5, ge=0.0, le=1.0)
    sanctity_degradation: float = Field(default=0.5, ge=0.0, le=1.0)
    liberty_oppression: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Dominant foundations
    dominant_foundations: List[str] = Field(default_factory=list)
    
    # Evidence
    foundation_words_found: Dict[str, List[str]] = Field(default_factory=dict)
    total_foundation_words: int = Field(default=0)
    
    # Recommendations
    recommended_appeals: Dict[str, List[str]] = Field(default_factory=dict)
    recommended_imagery: Dict[str, List[str]] = Field(default_factory=dict)
    recommended_products: Dict[str, List[str]] = Field(default_factory=dict)
    copy_examples: List[str] = Field(default_factory=list)
    avoid_elements: List[str] = Field(default_factory=list)
    
    # Confidence
    confidence: SignalConfidence = Field(default=SignalConfidence.LOW)
    
    # Timestamp
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_profile(self) -> MoralFoundationsProfile:
        """Convert to MoralFoundationsProfile model."""
        return MoralFoundationsProfile(
            care_harm=self.care_harm,
            fairness_cheating=self.fairness_cheating,
            loyalty_betrayal=self.loyalty_betrayal,
            authority_subversion=self.authority_subversion,
            sanctity_degradation=self.sanctity_degradation,
            liberty_oppression=self.liberty_oppression,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "care_harm": self.care_harm,
            "fairness_cheating": self.fairness_cheating,
            "loyalty_betrayal": self.loyalty_betrayal,
            "authority_subversion": self.authority_subversion,
            "sanctity_degradation": self.sanctity_degradation,
            "liberty_oppression": self.liberty_oppression,
            "dominant_foundations": self.dominant_foundations,
            "foundation_words_found": self.foundation_words_found,
            "recommended_appeals": self.recommended_appeals,
            "copy_examples": self.copy_examples,
            "confidence": self.confidence.value,
            "detected_at": self.detected_at.isoformat(),
        }


# =============================================================================
# MORAL FOUNDATIONS DETECTOR
# =============================================================================

class MoralFoundationsDetector:
    """
    Detects moral foundation sensitivities from text.
    
    Values are UPSTREAM of preferences - knowing moral foundations
    predicts response to brand positioning better than demographics.
    
    Effect sizes: d = 0.3-0.5 for consumer behavior predictions
    
    Usage:
        detector = MoralFoundationsDetector()
        detection = detector.detect_from_text(
            "I care about my family and want to protect them"
        )
        # detection.dominant_foundations = ["care_harm"]
    """
    
    def __init__(self):
        self._word_lists = {
            MoralFoundation.CARE_HARM: set(CARE_HARM_WORDS),
            MoralFoundation.FAIRNESS_CHEATING: set(FAIRNESS_WORDS),
            MoralFoundation.LOYALTY_BETRAYAL: set(LOYALTY_WORDS),
            MoralFoundation.AUTHORITY_SUBVERSION: set(AUTHORITY_WORDS),
            MoralFoundation.SANCTITY_DEGRADATION: set(SANCTITY_WORDS),
            MoralFoundation.LIBERTY_OPPRESSION: set(LIBERTY_WORDS),
        }
        self._detection_count = 0
    
    def detect_from_text(
        self,
        text: str,
        min_words_for_confidence: int = 10,
    ) -> MoralFoundationsDetection:
        """
        Detect moral foundations from text content.
        
        Args:
            text: Text to analyze
            min_words_for_confidence: Minimum foundation words for HIGH confidence
            
        Returns:
            MoralFoundationsDetection with scores and recommendations
        """
        if not text:
            return MoralFoundationsDetection()
        
        # Tokenize
        import re
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Count words by foundation
        foundation_words = {}
        foundation_counts = {}
        
        for foundation, word_set in self._word_lists.items():
            found = [w for w in words if w in word_set]
            foundation_words[foundation.value] = found
            foundation_counts[foundation] = len(found)
        
        total_foundation_words = sum(foundation_counts.values())
        
        if total_foundation_words == 0:
            return MoralFoundationsDetection()
        
        # Calculate scores using research-validated approach
        # Reference: Graham et al. (2011) MFQ validation studies
        # Effect sizes for moral foundations → consumer behavior: d = 0.3-0.5
        scores = {}
        for foundation, count in foundation_counts.items():
            # Use proportion of words in this foundation relative to all foundation words
            # This provides fair comparison across foundations
            if total_foundation_words > 0:
                relative_freq = count / total_foundation_words
                # Transform to score with symmetric scaling around 0.5
                # Use 0.8 multiplier for conservative effect size estimation
                scores[foundation] = 0.5 + (relative_freq - (1.0/6.0)) * 0.8 * 6.0
                scores[foundation] = max(0.0, min(1.0, scores[foundation]))
            else:
                scores[foundation] = 0.5
        
        # Find dominant foundations (above threshold)
        threshold = 0.6
        dominant = [f.value for f, s in scores.items() if s > threshold]
        dominant.sort(key=lambda x: scores[MoralFoundation(x)], reverse=True)
        
        # Get recommendations for dominant foundations
        recommendations = self._get_recommendations(dominant[:2])  # Top 2
        
        # Determine confidence
        confidence = SignalConfidence.HIGH if total_foundation_words >= min_words_for_confidence else (
            SignalConfidence.MODERATE if total_foundation_words >= 5 else SignalConfidence.LOW
        )
        
        detection = MoralFoundationsDetection(
            care_harm=scores[MoralFoundation.CARE_HARM],
            fairness_cheating=scores[MoralFoundation.FAIRNESS_CHEATING],
            loyalty_betrayal=scores[MoralFoundation.LOYALTY_BETRAYAL],
            authority_subversion=scores[MoralFoundation.AUTHORITY_SUBVERSION],
            sanctity_degradation=scores[MoralFoundation.SANCTITY_DEGRADATION],
            liberty_oppression=scores[MoralFoundation.LIBERTY_OPPRESSION],
            dominant_foundations=dominant,
            foundation_words_found=foundation_words,
            total_foundation_words=total_foundation_words,
            confidence=confidence,
            **recommendations,
        )
        
        self._detection_count += 1
        
        logger.debug(
            f"Moral foundations detection: dominant={dominant}, "
            f"total_words={total_foundation_words}"
        )
        
        return detection
    
    def detect_from_aggregated_texts(
        self,
        texts: List[str],
        weights: Optional[List[float]] = None,
    ) -> MoralFoundationsDetection:
        """
        Detect moral foundations from multiple texts.
        
        More reliable than single text - aggregate multiple reviews/posts.
        
        Args:
            texts: List of text samples
            weights: Optional weights for each text
            
        Returns:
            Aggregated MoralFoundationsDetection
        """
        if not texts:
            return MoralFoundationsDetection()
        
        # Combine all texts
        combined = " ".join(texts)
        return self.detect_from_text(combined)
    
    def get_appeals_for_foundation(
        self,
        foundation: str,
    ) -> Dict[str, Any]:
        """
        Get advertising appeals for a specific foundation.
        
        Args:
            foundation: Foundation name
            
        Returns:
            Dict with appeals, imagery, products, copy examples
        """
        try:
            f = MoralFoundation(foundation)
            return FOUNDATION_APPEALS.get(f, {})
        except ValueError:
            return {}
    
    def match_product_to_foundations(
        self,
        product_category: str,
    ) -> List[MoralFoundation]:
        """
        Match a product category to relevant moral foundations.
        
        Args:
            product_category: Product category name
            
        Returns:
            List of relevant MoralFoundations
        """
        category_lower = product_category.lower()
        matches = []
        
        for foundation, appeals in FOUNDATION_APPEALS.items():
            products = appeals.get("products", [])
            if any(p in category_lower for p in products):
                matches.append(foundation)
        
        return matches
    
    def _get_recommendations(
        self,
        dominant_foundations: List[str],
    ) -> Dict[str, Any]:
        """Get recommendations for dominant foundations."""
        appeals = {}
        imagery = {}
        products = {}
        copy_examples = []
        avoid_elements = []
        
        for f_name in dominant_foundations:
            try:
                foundation = MoralFoundation(f_name)
                f_appeals = FOUNDATION_APPEALS.get(foundation, {})
                
                appeals[f_name] = f_appeals.get("appeals", [])
                imagery[f_name] = f_appeals.get("imagery", [])
                products[f_name] = f_appeals.get("products", [])
                copy_examples.extend(f_appeals.get("copy_examples", []))
                
                if "avoid" in f_appeals:
                    avoid_elements.append(f_appeals["avoid"])
            except ValueError:
                continue
        
        return {
            "recommended_appeals": appeals,
            "recommended_imagery": imagery,
            "recommended_products": products,
            "copy_examples": copy_examples[:6],  # Limit to 6
            "avoid_elements": avoid_elements,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "detections_performed": self._detection_count,
            "foundations_tracked": len(self._word_lists),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_detector: Optional[MoralFoundationsDetector] = None


def get_moral_foundations_detector() -> MoralFoundationsDetector:
    """Get singleton moral foundations detector."""
    global _detector
    if _detector is None:
        _detector = MoralFoundationsDetector()
    return _detector
