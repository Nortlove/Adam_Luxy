#!/usr/bin/env python3
"""
ADAM FINANCIAL PSYCHOLOGY INTELLIGENCE
=======================================

The Financial Trust Layer - Specialized psychological intelligence for financial decisions.

UNIQUE VALUE:
- Trust psychology (existential, not preferential)
- Financial anxiety detection (unique psychological state)
- Service interaction patterns (institutional, not product)
- Credit rebuilding journey (transformation narrative)
- Long-term relationship dynamics (years, not transactions)

Based on 19,271 bank reviews across 47 US banks.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class FinancialAnxietyLevel(Enum):
    """Financial anxiety state levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # Requires ethical safeguards


class CreditJourneyStage(Enum):
    """Credit rebuilding journey stages."""
    NOT_APPLICABLE = "not_applicable"
    SHAME = "shame"              # Initial awareness of credit issues
    SEEKING = "seeking"          # Looking for solutions
    REBUILDING = "rebuilding"    # Actively working on credit
    RECOVERED = "recovered"      # Credit restored
    ADVOCATE = "advocate"        # Helping others rebuild


class ChannelPreference(Enum):
    """Digital vs traditional banking preference."""
    DIGITAL = "digital"
    TRADITIONAL = "traditional"
    HYBRID = "hybrid"


class BankingRelationshipTenure(Enum):
    """Length of banking relationship."""
    NEW = "new"              # < 1 year
    ESTABLISHED = "established"  # 1-5 years
    LOYAL = "loyal"          # 5-10 years
    LEGACY = "legacy"        # 10+ years


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

# Financial anxiety markers
FINANCIAL_ANXIETY_MARKERS = {
    "high": [
        r"\b(bankrupt|bankruptcy|foreclosure|collections|garnish)\b",
        r"\b(cant afford|cant pay|behind on|late payment|missed payment)\b",
        r"\b(struggling|desperate|drowning in debt|underwater)\b",
        r"\b(scared|terrified|anxious|worried sick) about (money|finances|bills)\b",
    ],
    "medium": [
        r"\b(worried|concerned|nervous) about (credit|score|finances)\b",
        r"\b(bad credit|poor credit|low score|credit issues)\b",
        r"\b(rebuild|improve|fix) (my |our )?(credit|score)\b",
        r"\b(debt|bills|payments) (stress|worry|concern)\b",
    ],
    "low": [
        r"\b(checking|monitoring) (my |our )?(credit|score)\b",
        r"\b(budget|saving|financial goal)\b",
        r"\b(interest rate|apr|fees)\b",
    ],
}

# Credit journey markers
CREDIT_JOURNEY_MARKERS = {
    "shame": [
        r"\b(embarrassed|ashamed|humiliated) (by|about) (credit|score|finances)\b",
        r"\b(my fault|made mistakes|bad decisions)\b",
        r"\b(never thought|didn't realize|wish i had)\b",
    ],
    "seeking": [
        r"\b(looking for|searching for|need) (help|solution|options)\b",
        r"\b(how (do|can) i|what can i do|where do i start)\b",
        r"\b(second chance|fresh start|new beginning)\b",
    ],
    "rebuilding": [
        r"\b(working on|building|improving) (my |our )?(credit|score)\b",
        r"\b(secured card|credit builder|starter card)\b",
        r"\b(making progress|getting better|moving up)\b",
        r"\b(on time|every month|consistent)\b",
    ],
    "recovered": [
        r"\b(finally|achieved|reached) (good|excellent|great) (credit|score)\b",
        r"\b(approved|qualified|accepted) for\b",
        r"\b(hard work paid off|worth it|so happy)\b",
    ],
    "advocate": [
        r"\b(tell everyone|recommend to|helped (my |a )?friend)\b",
        r"\b(if (i|you) can do it|anyone can|you can too)\b",
        r"\b(share my story|my experience|what i learned)\b",
    ],
}

# Digital preference markers
DIGITAL_PREFERENCE_MARKERS = {
    "digital_positive": [
        r"\b(love|great|excellent|amazing) (app|website|online|mobile)\b",
        r"\b(easy to use|user friendly|convenient|quick)\b",
        r"\b(instant|immediate|real-?time|24/7)\b",
        r"\b(no need to|don't have to|without going to) (call|visit|branch)\b",
    ],
    "digital_negative": [
        r"\b(app (crashes|sucks|terrible|broken|glitchy))\b",
        r"\b(website (down|slow|confusing|outdated))\b",
        r"\b(can't (log in|login|access|use))\b",
    ],
    "traditional_positive": [
        r"\b(branch|in-?person|face-?to-?face|local)\b",
        r"\b(personal (service|touch|attention|relationship))\b",
        r"\b(talk to|speak with|met with) (someone|a person|representative)\b",
    ],
}

# Trust markers
TRUST_MARKERS = {
    "high_trust": [
        r"\b(trust|trustworthy|reliable|dependable|honest)\b",
        r"\b(peace of mind|feel (safe|secure)|confidence)\b",
        r"\b(always|never (let me down|disappointed|failed))\b",
        r"\b(recommend|refer|tell (everyone|friends|family))\b",
    ],
    "low_trust": [
        r"\b(don't trust|can't trust|lost trust|betrayed)\b",
        r"\b(scam|fraud|rip-?off|shady|sketchy)\b",
        r"\b(hidden|surprise|unexpected) (fee|charge|cost)\b",
        r"\b(lied|deceived|misled|tricked)\b",
    ],
}

# Relationship duration markers
RELATIONSHIP_MARKERS = {
    "long_term": [
        r"\b(years|decades|long time|since \d{4})\b",
        r"\b(loyal|faithful|dedicated) customer\b",
        r"\b(never (left|switched|changed)|always been)\b",
    ],
    "new": [
        r"\b(just (opened|started|joined|signed up))\b",
        r"\b(new (customer|account|member))\b",
        r"\b(first (time|experience|month))\b",
    ],
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FinancialPsychologyProfile:
    """Complete financial psychology profile for a user/context."""
    
    # Anxiety state
    anxiety_level: FinancialAnxietyLevel = FinancialAnxietyLevel.NONE
    anxiety_confidence: float = 0.0
    anxiety_markers_found: List[str] = field(default_factory=list)
    
    # Credit journey
    credit_journey_stage: CreditJourneyStage = CreditJourneyStage.NOT_APPLICABLE
    journey_confidence: float = 0.0
    journey_markers_found: List[str] = field(default_factory=list)
    
    # Channel preference
    channel_preference: ChannelPreference = ChannelPreference.HYBRID
    digital_score: float = 0.5
    traditional_score: float = 0.5
    
    # Trust state
    trust_level: float = 0.5  # 0-1
    trust_markers_found: List[str] = field(default_factory=list)
    
    # Relationship
    relationship_tenure: BankingRelationshipTenure = BankingRelationshipTenure.NEW
    
    # Mechanism adjustments (based on financial psychology)
    mechanism_adjustments: Dict[str, float] = field(default_factory=dict)
    
    # Ethical flags
    requires_safeguards: bool = False
    safeguard_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for atom injection."""
        return {
            "anxiety_level": self.anxiety_level.value,
            "anxiety_confidence": self.anxiety_confidence,
            "credit_journey_stage": self.credit_journey_stage.value,
            "journey_confidence": self.journey_confidence,
            "channel_preference": self.channel_preference.value,
            "digital_score": self.digital_score,
            "trust_level": self.trust_level,
            "relationship_tenure": self.relationship_tenure.value,
            "mechanism_adjustments": self.mechanism_adjustments,
            "requires_safeguards": self.requires_safeguards,
            "safeguard_reason": self.safeguard_reason,
        }


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def detect_financial_anxiety(
    text: str,
    behavioral_signals: Optional[Dict[str, float]] = None,
) -> Tuple[FinancialAnxietyLevel, float, List[str]]:
    """
    Detect financial anxiety level from text and behavioral signals.
    
    Returns:
        Tuple of (anxiety_level, confidence, markers_found)
    """
    if not text:
        return FinancialAnxietyLevel.NONE, 0.0, []
    
    text_lower = text.lower()
    markers_found = []
    
    # Check high anxiety markers first
    high_count = 0
    for pattern in FINANCIAL_ANXIETY_MARKERS["high"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            high_count += 1
            markers_found.append(f"high:{pattern[:30]}")
    
    if high_count >= 2:
        return FinancialAnxietyLevel.CRITICAL, 0.9, markers_found
    elif high_count >= 1:
        return FinancialAnxietyLevel.HIGH, 0.8, markers_found
    
    # Check medium markers
    medium_count = 0
    for pattern in FINANCIAL_ANXIETY_MARKERS["medium"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            medium_count += 1
            markers_found.append(f"medium:{pattern[:30]}")
    
    if medium_count >= 2:
        return FinancialAnxietyLevel.MEDIUM, 0.7, markers_found
    
    # Check low markers
    low_count = 0
    for pattern in FINANCIAL_ANXIETY_MARKERS["low"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            low_count += 1
            markers_found.append(f"low:{pattern[:30]}")
    
    if low_count >= 2 or medium_count >= 1:
        return FinancialAnxietyLevel.LOW, 0.6, markers_found
    
    return FinancialAnxietyLevel.NONE, 0.5, markers_found


def detect_credit_journey_stage(
    text: str,
) -> Tuple[CreditJourneyStage, float, List[str]]:
    """
    Detect credit rebuilding journey stage from text.
    
    Returns:
        Tuple of (stage, confidence, markers_found)
    """
    if not text:
        return CreditJourneyStage.NOT_APPLICABLE, 0.0, []
    
    text_lower = text.lower()
    markers_found = []
    stage_scores = {stage: 0 for stage in CreditJourneyStage}
    
    for stage_name, patterns in CREDIT_JOURNEY_MARKERS.items():
        stage = CreditJourneyStage[stage_name.upper()]
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                stage_scores[stage] += 1
                markers_found.append(f"{stage_name}:{pattern[:30]}")
    
    # Find highest scoring stage
    max_stage = max(stage_scores, key=stage_scores.get)
    max_score = stage_scores[max_stage]
    
    if max_score == 0:
        return CreditJourneyStage.NOT_APPLICABLE, 0.0, markers_found
    
    # Confidence based on score
    confidence = min(0.5 + (max_score * 0.15), 0.95)
    
    return max_stage, confidence, markers_found


def detect_channel_preference(
    text: str,
) -> Tuple[ChannelPreference, float, float]:
    """
    Detect digital vs traditional channel preference.
    
    Returns:
        Tuple of (preference, digital_score, traditional_score)
    """
    if not text:
        return ChannelPreference.HYBRID, 0.5, 0.5
    
    text_lower = text.lower()
    
    digital_positive = sum(
        1 for p in DIGITAL_PREFERENCE_MARKERS["digital_positive"]
        if re.search(p, text_lower, re.IGNORECASE)
    )
    digital_negative = sum(
        1 for p in DIGITAL_PREFERENCE_MARKERS["digital_negative"]
        if re.search(p, text_lower, re.IGNORECASE)
    )
    traditional_positive = sum(
        1 for p in DIGITAL_PREFERENCE_MARKERS["traditional_positive"]
        if re.search(p, text_lower, re.IGNORECASE)
    )
    
    digital_score = (digital_positive - digital_negative * 0.5) / max(digital_positive + 1, 1)
    digital_score = max(0, min(1, 0.5 + digital_score * 0.5))
    
    traditional_score = traditional_positive / max(traditional_positive + 1, 1)
    traditional_score = max(0, min(1, 0.5 + traditional_score * 0.5))
    
    if digital_score > 0.65 and traditional_score < 0.4:
        return ChannelPreference.DIGITAL, digital_score, traditional_score
    elif traditional_score > 0.65 and digital_score < 0.4:
        return ChannelPreference.TRADITIONAL, digital_score, traditional_score
    else:
        return ChannelPreference.HYBRID, digital_score, traditional_score


def detect_trust_level(text: str) -> Tuple[float, List[str]]:
    """
    Detect trust level from text.
    
    Returns:
        Tuple of (trust_level 0-1, markers_found)
    """
    if not text:
        return 0.5, []
    
    text_lower = text.lower()
    markers_found = []
    
    high_trust_count = 0
    for pattern in TRUST_MARKERS["high_trust"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            high_trust_count += 1
            markers_found.append(f"high_trust:{pattern[:30]}")
    
    low_trust_count = 0
    for pattern in TRUST_MARKERS["low_trust"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            low_trust_count += 1
            markers_found.append(f"low_trust:{pattern[:30]}")
    
    # Calculate trust score
    trust_score = 0.5 + (high_trust_count * 0.15) - (low_trust_count * 0.2)
    trust_score = max(0, min(1, trust_score))
    
    return trust_score, markers_found


def detect_relationship_tenure(text: str) -> BankingRelationshipTenure:
    """Detect banking relationship duration from text."""
    if not text:
        return BankingRelationshipTenure.NEW
    
    text_lower = text.lower()
    
    # Check for long-term indicators
    for pattern in RELATIONSHIP_MARKERS["long_term"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            # Try to extract years
            year_match = re.search(r"(\d+)\s*years?", text_lower)
            if year_match:
                years = int(year_match.group(1))
                if years >= 10:
                    return BankingRelationshipTenure.LEGACY
                elif years >= 5:
                    return BankingRelationshipTenure.LOYAL
                elif years >= 1:
                    return BankingRelationshipTenure.ESTABLISHED
            return BankingRelationshipTenure.LOYAL  # Default if "years" mentioned
    
    # Check for new indicators
    for pattern in RELATIONSHIP_MARKERS["new"]:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return BankingRelationshipTenure.NEW
    
    return BankingRelationshipTenure.ESTABLISHED  # Default


# =============================================================================
# MECHANISM ADJUSTMENTS
# =============================================================================

def calculate_mechanism_adjustments(
    profile: FinancialPsychologyProfile,
) -> Dict[str, float]:
    """
    Calculate mechanism effectiveness adjustments based on financial psychology.
    
    Returns multipliers for each mechanism (1.0 = no change).
    """
    adjustments = {
        "authority": 1.0,
        "commitment": 1.0,
        "social_proof": 1.0,
        "reciprocity": 1.0,
        "liking": 1.0,
        "scarcity": 1.0,
        "unity": 1.0,
        "fear_appeal": 1.0,
    }
    
    # Financial products always favor authority + commitment
    adjustments["authority"] *= 1.3
    adjustments["commitment"] *= 1.3
    
    # Anxiety-based adjustments
    if profile.anxiety_level in [FinancialAnxietyLevel.HIGH, FinancialAnxietyLevel.CRITICAL]:
        # ETHICAL: Reduce fear-based mechanisms
        adjustments["fear_appeal"] = 0.0  # COMPLETELY DISABLED
        adjustments["scarcity"] *= 0.3    # Heavily reduced
        
        # Boost supportive mechanisms
        adjustments["liking"] *= 1.5
        adjustments["social_proof"] *= 1.3
        
    elif profile.anxiety_level == FinancialAnxietyLevel.MEDIUM:
        adjustments["fear_appeal"] *= 0.3
        adjustments["scarcity"] *= 0.5
        adjustments["liking"] *= 1.3
    
    # Credit journey stage adjustments
    stage_adjustments = {
        CreditJourneyStage.SHAME: {
            "liking": 1.5, "social_proof": 1.4, "fear_appeal": 0.0,
        },
        CreditJourneyStage.SEEKING: {
            "authority": 1.5, "commitment": 1.4,
        },
        CreditJourneyStage.REBUILDING: {
            "commitment": 1.6, "reciprocity": 1.4,
        },
        CreditJourneyStage.RECOVERED: {
            "social_proof": 1.5, "unity": 1.4,
        },
        CreditJourneyStage.ADVOCATE: {
            "unity": 1.6, "social_proof": 1.3,
        },
    }
    
    if profile.credit_journey_stage in stage_adjustments:
        for mech, mult in stage_adjustments[profile.credit_journey_stage].items():
            adjustments[mech] *= mult
    
    # Trust level adjustments
    if profile.trust_level < 0.3:
        # Low trust - need authority and social proof
        adjustments["authority"] *= 1.4
        adjustments["social_proof"] *= 1.3
    elif profile.trust_level > 0.7:
        # High trust - commitment and reciprocity work well
        adjustments["commitment"] *= 1.3
        adjustments["reciprocity"] *= 1.3
    
    # Relationship tenure adjustments
    tenure_adjustments = {
        BankingRelationshipTenure.NEW: {
            "authority": 1.3, "social_proof": 1.3,
        },
        BankingRelationshipTenure.ESTABLISHED: {
            "commitment": 1.2, "reciprocity": 1.2,
        },
        BankingRelationshipTenure.LOYAL: {
            "commitment": 1.4, "unity": 1.3,
        },
        BankingRelationshipTenure.LEGACY: {
            "unity": 1.5, "commitment": 1.3,
        },
    }
    
    if profile.relationship_tenure in tenure_adjustments:
        for mech, mult in tenure_adjustments[profile.relationship_tenure].items():
            adjustments[mech] *= mult
    
    return adjustments


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_financial_psychology(
    text: str,
    category: Optional[str] = None,
    behavioral_signals: Optional[Dict[str, float]] = None,
) -> FinancialPsychologyProfile:
    """
    Complete financial psychology analysis.
    
    Args:
        text: User text (review, query, etc.)
        category: Product category (if known)
        behavioral_signals: Additional behavioral data
        
    Returns:
        Complete FinancialPsychologyProfile
    """
    profile = FinancialPsychologyProfile()
    
    # Detect anxiety
    anxiety_level, anxiety_conf, anxiety_markers = detect_financial_anxiety(
        text, behavioral_signals
    )
    profile.anxiety_level = anxiety_level
    profile.anxiety_confidence = anxiety_conf
    profile.anxiety_markers_found = anxiety_markers
    
    # Detect credit journey
    journey_stage, journey_conf, journey_markers = detect_credit_journey_stage(text)
    profile.credit_journey_stage = journey_stage
    profile.journey_confidence = journey_conf
    profile.journey_markers_found = journey_markers
    
    # Detect channel preference
    channel_pref, digital_score, trad_score = detect_channel_preference(text)
    profile.channel_preference = channel_pref
    profile.digital_score = digital_score
    profile.traditional_score = trad_score
    
    # Detect trust level
    trust_level, trust_markers = detect_trust_level(text)
    profile.trust_level = trust_level
    profile.trust_markers_found = trust_markers
    
    # Detect relationship tenure
    profile.relationship_tenure = detect_relationship_tenure(text)
    
    # Calculate mechanism adjustments
    profile.mechanism_adjustments = calculate_mechanism_adjustments(profile)
    
    # Set ethical safeguards
    if profile.anxiety_level in [FinancialAnxietyLevel.HIGH, FinancialAnxietyLevel.CRITICAL]:
        profile.requires_safeguards = True
        profile.safeguard_reason = f"High financial anxiety detected ({profile.anxiety_level.value})"
    
    return profile


# =============================================================================
# BANK PROFILE LOADER
# =============================================================================

_BANK_PROFILES_CACHE: Optional[Dict] = None


def load_bank_profiles() -> Dict[str, Dict]:
    """Load bank psychological profiles from checkpoint."""
    global _BANK_PROFILES_CACHE
    
    if _BANK_PROFILES_CACHE is not None:
        return _BANK_PROFILES_CACHE
    
    checkpoint_path = Path(__file__).parent.parent.parent / "data" / "learning" / "multi_domain" / "checkpoint_bank_reviews.json"
    
    if not checkpoint_path.exists():
        logger.warning("Bank checkpoint not found")
        _BANK_PROFILES_CACHE = {}
        return _BANK_PROFILES_CACHE
    
    try:
        with open(checkpoint_path) as f:
            data = json.load(f)
        
        _BANK_PROFILES_CACHE = data.get("profiles", {})
        logger.info(f"Loaded {len(_BANK_PROFILES_CACHE)} bank profiles")
        
    except Exception as e:
        logger.error(f"Failed to load bank profiles: {e}")
        _BANK_PROFILES_CACHE = {}
    
    return _BANK_PROFILES_CACHE


def get_bank_profile(bank_name: str) -> Optional[Dict]:
    """Get psychological profile for a specific bank."""
    profiles = load_bank_profiles()
    
    # Try exact match
    if bank_name in profiles:
        return profiles[bank_name]
    
    # Try normalized match
    normalized = bank_name.lower().replace(" ", "_").replace("'", "")
    for key, profile in profiles.items():
        if normalized in key.lower() or key.lower() in normalized:
            return profile
    
    return None


# =============================================================================
# SINGLETON SERVICE
# =============================================================================

class FinancialPsychologyService:
    """Singleton service for financial psychology intelligence."""
    
    _instance = None
    
    def __init__(self):
        self._bank_profiles = None
        self._global_psychology = None
    
    @classmethod
    def get_instance(cls) -> "FinancialPsychologyService":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """Load all financial psychology data."""
        self._bank_profiles = load_bank_profiles()
        
        # Load global psychology
        checkpoint_path = Path(__file__).parent.parent.parent / "data" / "learning" / "multi_domain" / "checkpoint_bank_reviews.json"
        
        if checkpoint_path.exists():
            with open(checkpoint_path) as f:
                data = json.load(f)
            
            self._global_psychology = {
                "banking_psychology": data.get("banking_psychology_global", {}),
                "cialdini_principles": data.get("cialdini_principles_global", {}),
                "archetype_distribution": data.get("archetype_totals", {}),
            }
    
    def analyze(
        self,
        text: str,
        category: Optional[str] = None,
        bank_name: Optional[str] = None,
    ) -> FinancialPsychologyProfile:
        """Analyze financial psychology for text."""
        return analyze_financial_psychology(text, category)
    
    def get_bank_effectiveness(self, bank_name: str) -> Optional[Dict]:
        """Get mechanism effectiveness for a bank."""
        profile = get_bank_profile(bank_name)
        if profile:
            return profile.get("cialdini_principles", {})
        return None
    
    @property
    def global_psychology(self) -> Dict:
        """Get global banking psychology."""
        return self._global_psychology or {}


def get_financial_psychology_service() -> FinancialPsychologyService:
    """Get the financial psychology service singleton."""
    return FinancialPsychologyService.get_instance()


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    # Test the financial psychology detection
    test_texts = [
        "I'm really worried about my credit score and struggling to pay bills",
        "I've been with Chase for 15 years and they've always been great",
        "The mobile app is amazing, I never need to go to a branch anymore",
        "After rebuilding my credit from 450 to 720, I finally got approved!",
        "I'm looking for a secured card to help build my credit back up",
    ]
    
    service = get_financial_psychology_service()
    
    print("=" * 70)
    print("FINANCIAL PSYCHOLOGY DETECTION TEST")
    print("=" * 70)
    
    for text in test_texts:
        print(f"\nText: {text[:60]}...")
        profile = service.analyze(text)
        print(f"  Anxiety: {profile.anxiety_level.value} ({profile.anxiety_confidence:.2f})")
        print(f"  Journey: {profile.credit_journey_stage.value} ({profile.journey_confidence:.2f})")
        print(f"  Channel: {profile.channel_preference.value}")
        print(f"  Trust: {profile.trust_level:.2f}")
        print(f"  Tenure: {profile.relationship_tenure.value}")
        print(f"  Safeguards: {profile.requires_safeguards}")
        if profile.mechanism_adjustments:
            top_mechs = sorted(profile.mechanism_adjustments.items(), key=lambda x: -x[1])[:3]
            print(f"  Top Mechs: {', '.join([f'{m}:{v:.2f}' for m, v in top_mechs])}")
