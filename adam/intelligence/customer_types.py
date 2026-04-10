# =============================================================================
# ADAM Purchase-Predictive Customer Type System
# Location: adam/intelligence/customer_types.py
# =============================================================================

"""
PURCHASE-PREDICTIVE CUSTOMER TYPE SYSTEM

This system segments customers based on dimensions that MOST PREDICT purchase behavior
and persuasion susceptibility, as extracted from review analysis:

TIER 1 - Highest Predictive Value:
- Purchase Motivation (15 types) - WHY they buy
- Decision Style (3 types) - HOW they decide (System 1 vs 2)
- Persuasion Profile (6 primary mechanisms) - WHAT persuades them

TIER 2 - Strong Predictive Value:
- Regulatory Focus (2 types) - Promotion vs Prevention orientation
- Emotional Intensity (3 levels) - HOW strongly they respond
- Price Sensitivity (4 tiers) - WHERE on the price spectrum

TIER 3 - Contextual Modifiers:
- Archetype (8 types) - Personality-based behavioral patterns
- Trust Level (3 levels) - HOW easily they convert

Total Base Types: 15 × 3 × 2 × 3 × 4 = 1,080 primary purchase profiles
With archetypes: 1,080 × 8 = 8,640 detailed customer types

This is grounded in what the deep review analysis ACTUALLY EXTRACTS and what
research shows PREDICTS who will buy.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# TIER 1: HIGHEST PREDICTIVE VALUE (from review analysis)
# =============================================================================

class PurchaseMotivation(str, Enum):
    """
    WHY they buy - 15 motivations detected from review language.
    This is one of the strongest predictors of purchase behavior.
    """
    FUNCTIONAL_NEED = "functional_need"      # "needed it for...", "required"
    QUALITY_SEEKING = "quality_seeking"      # "wanted the best", "premium"
    VALUE_SEEKING = "value_seeking"          # "great deal", "worth the price"
    STATUS_SIGNALING = "status_signaling"    # "impressed", "compliments"
    SELF_REWARD = "self_reward"              # "treat myself", "deserved"
    GIFT_GIVING = "gift_giving"              # "bought for", "as a gift"
    REPLACEMENT = "replacement"              # "old one broke", "needed new"
    UPGRADE = "upgrade"                      # "better than my old", "upgraded"
    IMPULSE = "impulse"                      # "couldn't resist", "spontaneous"
    RESEARCH_DRIVEN = "research_driven"      # "after much research", "compared"
    RECOMMENDATION = "recommendation"        # "friend recommended", "was told"
    BRAND_LOYALTY = "brand_loyalty"          # "always buy this brand"
    SOCIAL_PROOF = "social_proof"            # "everyone has", "popular"
    FOMO = "fomo"                            # "limited time", "before it sold out"
    PROBLEM_SOLVING = "problem_solving"      # "to solve", "fixed my issue"


class DecisionStyle(str, Enum):
    """
    HOW they decide - System 1 (fast/intuitive) vs System 2 (slow/deliberate).
    Strongly predicts which persuasion approaches work.
    """
    SYSTEM1_INTUITIVE = "system1"    # Fast, gut feeling, emotional
    SYSTEM2_DELIBERATE = "system2"   # Slow, analytical, research-heavy
    MIXED = "mixed"                  # Context-dependent


class PersuasionProfile(str, Enum):
    """
    WHAT persuades them most - primary mechanism susceptibility.
    Based on Cialdini principles + additional mechanisms.
    """
    AUTHORITY_DRIVEN = "authority"         # Responds to expertise, credentials
    SOCIAL_PROOF_DRIVEN = "social_proof"   # Responds to what others do
    SCARCITY_DRIVEN = "scarcity"           # Responds to limited availability
    RECIPROCITY_DRIVEN = "reciprocity"     # Responds to favors, gifts
    COMMITMENT_DRIVEN = "commitment"       # Responds to consistency
    LIKING_DRIVEN = "liking"               # Responds to connection, similarity


# =============================================================================
# TIER 2: STRONG PREDICTIVE VALUE
# =============================================================================

class RegulatoryFocus(str, Enum):
    """
    Promotion vs Prevention - affects message framing effectiveness.
    """
    PROMOTION = "promotion"    # Gains, achievement, positive outcomes
    PREVENTION = "prevention"  # Security, safety, avoiding losses


class EmotionalIntensity(str, Enum):
    """
    HOW strongly they respond emotionally.
    High intensity correlates with faster decisions and stronger loyalty.
    """
    HIGH = "high"      # Exclamation marks, intensifiers, superlatives
    MEDIUM = "medium"  # Balanced emotional expression
    LOW = "low"        # Reserved, factual, minimal emotion


class PriceSensitivity(str, Enum):
    """
    WHERE on the price spectrum they operate.
    Affects which value propositions work.
    """
    PREMIUM_SEEKER = "premium"   # Positive correlation between price and satisfaction
    VALUE_HUNTER = "value"       # Negative correlation, price-conscious
    PRICE_NEUTRAL = "neutral"    # No strong price preference
    BUDGET_FOCUSED = "budget"    # Strongly price-constrained


# =============================================================================
# TIER 3: CONTEXTUAL MODIFIERS
# =============================================================================

class Archetype(str, Enum):
    """
    8 archetypes based on Big Five personality profiles.
    Provides behavioral context for the purchase profile.
    """
    ACHIEVER = "achiever"      # Goal-oriented, quality-focused
    EXPLORER = "explorer"      # Novelty-seeking, adventurous
    CONNECTOR = "connector"    # Social, relationship-focused
    GUARDIAN = "guardian"      # Security-focused, cautious
    ANALYST = "analyst"        # Data-driven, thorough
    CREATOR = "creator"        # Original, expressive
    NURTURER = "nurturer"      # Care-oriented, community-focused
    PRAGMATIST = "pragmatist"  # Practical, efficient


class TrustLevel(str, Enum):
    """
    HOW easily they convert - affects conversion likelihood.
    """
    HIGH_TRUST = "high"       # Quick to trust, low skepticism
    MODERATE_TRUST = "moderate"
    SKEPTICAL = "skeptical"   # Requires proof, verification


# =============================================================================
# MECHANISM EFFECTIVENESS BY DIMENSION
# =============================================================================

# Mechanism effectiveness by purchase motivation (most predictive)
MECHANISM_BY_MOTIVATION = {
    PurchaseMotivation.FUNCTIONAL_NEED: {
        "authority": 0.7, "social_proof": 0.5, "scarcity": 0.3,
        "reciprocity": 0.4, "commitment": 0.6, "liking": 0.3,
    },
    PurchaseMotivation.QUALITY_SEEKING: {
        "authority": 0.9, "social_proof": 0.6, "scarcity": 0.5,
        "reciprocity": 0.3, "commitment": 0.7, "liking": 0.4,
    },
    PurchaseMotivation.VALUE_SEEKING: {
        "authority": 0.4, "social_proof": 0.7, "scarcity": 0.8,
        "reciprocity": 0.7, "commitment": 0.5, "liking": 0.4,
    },
    PurchaseMotivation.STATUS_SIGNALING: {
        "authority": 0.8, "social_proof": 0.9, "scarcity": 0.9,
        "reciprocity": 0.3, "commitment": 0.6, "liking": 0.7,
    },
    PurchaseMotivation.SELF_REWARD: {
        "authority": 0.4, "social_proof": 0.5, "scarcity": 0.6,
        "reciprocity": 0.5, "commitment": 0.3, "liking": 0.8,
    },
    PurchaseMotivation.GIFT_GIVING: {
        "authority": 0.5, "social_proof": 0.8, "scarcity": 0.4,
        "reciprocity": 0.9, "commitment": 0.4, "liking": 0.7,
    },
    PurchaseMotivation.REPLACEMENT: {
        "authority": 0.6, "social_proof": 0.5, "scarcity": 0.3,
        "reciprocity": 0.4, "commitment": 0.8, "liking": 0.3,
    },
    PurchaseMotivation.UPGRADE: {
        "authority": 0.7, "social_proof": 0.6, "scarcity": 0.5,
        "reciprocity": 0.3, "commitment": 0.5, "liking": 0.5,
    },
    PurchaseMotivation.IMPULSE: {
        "authority": 0.3, "social_proof": 0.6, "scarcity": 0.95,
        "reciprocity": 0.4, "commitment": 0.2, "liking": 0.8,
    },
    PurchaseMotivation.RESEARCH_DRIVEN: {
        "authority": 0.9, "social_proof": 0.4, "scarcity": 0.2,
        "reciprocity": 0.3, "commitment": 0.7, "liking": 0.3,
    },
    PurchaseMotivation.RECOMMENDATION: {
        "authority": 0.8, "social_proof": 0.9, "scarcity": 0.3,
        "reciprocity": 0.6, "commitment": 0.5, "liking": 0.8,
    },
    PurchaseMotivation.BRAND_LOYALTY: {
        "authority": 0.6, "social_proof": 0.4, "scarcity": 0.4,
        "reciprocity": 0.5, "commitment": 0.95, "liking": 0.7,
    },
    PurchaseMotivation.SOCIAL_PROOF: {
        "authority": 0.5, "social_proof": 0.95, "scarcity": 0.6,
        "reciprocity": 0.4, "commitment": 0.4, "liking": 0.7,
    },
    PurchaseMotivation.FOMO: {
        "authority": 0.4, "social_proof": 0.8, "scarcity": 0.98,
        "reciprocity": 0.3, "commitment": 0.3, "liking": 0.5,
    },
    PurchaseMotivation.PROBLEM_SOLVING: {
        "authority": 0.8, "social_proof": 0.6, "scarcity": 0.3,
        "reciprocity": 0.4, "commitment": 0.6, "liking": 0.3,
    },
}

# Decision style modifiers
MECHANISM_BY_DECISION_STYLE = {
    DecisionStyle.SYSTEM1_INTUITIVE: {
        "authority": 0.4, "social_proof": 0.7, "scarcity": 0.9,
        "reciprocity": 0.5, "commitment": 0.3, "liking": 0.9,
    },
    DecisionStyle.SYSTEM2_DELIBERATE: {
        "authority": 0.9, "social_proof": 0.4, "scarcity": 0.2,
        "reciprocity": 0.4, "commitment": 0.8, "liking": 0.3,
    },
    DecisionStyle.MIXED: {
        "authority": 0.6, "social_proof": 0.6, "scarcity": 0.5,
        "reciprocity": 0.5, "commitment": 0.5, "liking": 0.6,
    },
}

# Regulatory focus modifiers
MECHANISM_BY_REGULATORY = {
    RegulatoryFocus.PROMOTION: {
        "authority": 0.5, "social_proof": 0.6, "scarcity": 0.8,
        "reciprocity": 0.5, "commitment": 0.5, "liking": 0.7,
    },
    RegulatoryFocus.PREVENTION: {
        "authority": 0.8, "social_proof": 0.6, "scarcity": 0.3,
        "reciprocity": 0.6, "commitment": 0.8, "liking": 0.4,
    },
}

# Emotional intensity modifiers
MECHANISM_BY_EMOTIONAL = {
    EmotionalIntensity.HIGH: {
        "authority": 0.4, "social_proof": 0.7, "scarcity": 0.8,
        "reciprocity": 0.6, "commitment": 0.4, "liking": 0.9,
    },
    EmotionalIntensity.MEDIUM: {
        "authority": 0.6, "social_proof": 0.6, "scarcity": 0.5,
        "reciprocity": 0.5, "commitment": 0.6, "liking": 0.6,
    },
    EmotionalIntensity.LOW: {
        "authority": 0.8, "social_proof": 0.4, "scarcity": 0.3,
        "reciprocity": 0.4, "commitment": 0.7, "liking": 0.3,
    },
}


# =============================================================================
# CUSTOMER TYPE DATA CLASS
# =============================================================================

@dataclass
class CustomerType:
    """
    A purchase-predictive customer type.
    
    Each type represents a unique combination of:
    - Purchase Motivation (WHY they buy)
    - Decision Style (HOW they decide)
    - Persuasion Profile (WHAT persuades them)
    - Regulatory Focus (promotion vs prevention)
    - Emotional Intensity (HOW strongly they respond)
    - Price Sensitivity (WHERE on price spectrum)
    - Archetype (behavioral context)
    - Trust Level (conversion likelihood)
    """
    
    type_id: str
    
    # Tier 1 - Highest predictive value
    purchase_motivation: PurchaseMotivation
    decision_style: DecisionStyle
    primary_persuasion: PersuasionProfile
    
    # Tier 2 - Strong predictive value
    regulatory_focus: RegulatoryFocus
    emotional_intensity: EmotionalIntensity
    price_sensitivity: PriceSensitivity
    
    # Tier 3 - Contextual
    archetype: Optional[Archetype] = None
    trust_level: TrustLevel = TrustLevel.MODERATE_TRUST
    
    # Calculated effectiveness
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Conversion probability modifier
    conversion_modifier: float = 1.0
    
    def __post_init__(self):
        """Calculate mechanism effectiveness after initialization."""
        if not self.mechanism_effectiveness:
            self.mechanism_effectiveness = self._calculate_mechanism_effectiveness()
        self.conversion_modifier = self._calculate_conversion_modifier()
    
    def _calculate_mechanism_effectiveness(self) -> Dict[str, float]:
        """
        Calculate mechanism effectiveness by blending all predictive dimensions.
        
        Weights based on predictive value:
        - Purchase Motivation: 35% (highest predictor)
        - Decision Style: 25%
        - Regulatory Focus: 20%
        - Emotional Intensity: 15%
        - Primary Persuasion: 5% (boost to declared preference)
        """
        mechanisms = ["authority", "social_proof", "scarcity", "reciprocity", "commitment", "liking"]
        result = {}
        
        for mech in mechanisms:
            score = 0.0
            
            # Purchase motivation influence (35%)
            motivation_score = MECHANISM_BY_MOTIVATION.get(
                self.purchase_motivation, {}
            ).get(mech, 0.5)
            score += motivation_score * 0.35
            
            # Decision style influence (25%)
            style_score = MECHANISM_BY_DECISION_STYLE.get(
                self.decision_style, {}
            ).get(mech, 0.5)
            score += style_score * 0.25
            
            # Regulatory focus influence (20%)
            regulatory_score = MECHANISM_BY_REGULATORY.get(
                self.regulatory_focus, {}
            ).get(mech, 0.5)
            score += regulatory_score * 0.20
            
            # Emotional intensity influence (15%)
            emotional_score = MECHANISM_BY_EMOTIONAL.get(
                self.emotional_intensity, {}
            ).get(mech, 0.5)
            score += emotional_score * 0.15
            
            # Primary persuasion boost (5%)
            if self.primary_persuasion.value == mech:
                score += 0.05  # Boost for declared primary mechanism
            
            result[mech] = min(1.0, max(0.0, score))
        
        return result
    
    def _calculate_conversion_modifier(self) -> float:
        """Calculate conversion probability modifier based on trust and decision style."""
        modifier = 1.0
        
        # Trust level affects conversion
        if self.trust_level == TrustLevel.HIGH_TRUST:
            modifier *= 1.3
        elif self.trust_level == TrustLevel.SKEPTICAL:
            modifier *= 0.7
        
        # Emotional intensity affects conversion speed
        if self.emotional_intensity == EmotionalIntensity.HIGH:
            modifier *= 1.2
        elif self.emotional_intensity == EmotionalIntensity.LOW:
            modifier *= 0.8
        
        # System 1 thinkers convert faster
        if self.decision_style == DecisionStyle.SYSTEM1_INTUITIVE:
            modifier *= 1.15
        
        return modifier
    
    def get_top_mechanisms(self, n: int = 3) -> List[Tuple[str, float]]:
        """Get top N most effective mechanisms for this type."""
        return sorted(
            self.mechanism_effectiveness.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
    
    def get_optimal_approach(self) -> Dict[str, Any]:
        """Get the optimal persuasion approach for this customer type."""
        top_mechs = self.get_top_mechanisms(2)
        
        # Message framing based on regulatory focus
        if self.regulatory_focus == RegulatoryFocus.PROMOTION:
            framing = "gain-focused"
            message_style = "emphasize benefits, achievements, positive outcomes"
        else:
            framing = "loss-focused"
            message_style = "emphasize security, risk avoidance, protection"
        
        # Urgency based on decision style
        if self.decision_style == DecisionStyle.SYSTEM1_INTUITIVE:
            urgency = "high"
            content_style = "emotional, immediate, simple"
        elif self.decision_style == DecisionStyle.SYSTEM2_DELIBERATE:
            urgency = "low"
            content_style = "detailed, evidence-based, comparative"
        else:
            urgency = "moderate"
            content_style = "balanced"
        
        # Price approach
        if self.price_sensitivity == PriceSensitivity.PREMIUM_SEEKER:
            price_approach = "emphasize quality and exclusivity"
        elif self.price_sensitivity == PriceSensitivity.VALUE_HUNTER:
            price_approach = "emphasize value proposition and savings"
        elif self.price_sensitivity == PriceSensitivity.BUDGET_FOCUSED:
            price_approach = "emphasize affordability and deals"
        else:
            price_approach = "balanced value-quality messaging"
        
        return {
            "primary_mechanism": top_mechs[0][0],
            "secondary_mechanism": top_mechs[1][0] if len(top_mechs) > 1 else None,
            "mechanism_effectiveness": dict(top_mechs),
            "message_framing": framing,
            "message_style": message_style,
            "urgency_level": urgency,
            "content_style": content_style,
            "price_approach": price_approach,
            "conversion_modifier": self.conversion_modifier,
            "motivation_appeal": self.purchase_motivation.value,
        }
    
    def get_description(self) -> str:
        """Get human-readable description."""
        return (
            f"{self.purchase_motivation.value.replace('_', ' ').title()} buyer, "
            f"{self.decision_style.value.replace('_', ' ')} decision-maker, "
            f"{self.regulatory_focus.value}-focused, "
            f"{self.emotional_intensity.value} emotional intensity, "
            f"{self.price_sensitivity.value.replace('_', ' ')} price orientation"
        )
    
    @classmethod
    def from_profile(
        cls,
        purchase_motivation: PurchaseMotivation,
        decision_style: DecisionStyle,
        primary_persuasion: PersuasionProfile,
        regulatory_focus: RegulatoryFocus,
        emotional_intensity: EmotionalIntensity,
        price_sensitivity: PriceSensitivity,
        archetype: Optional[Archetype] = None,
        trust_level: TrustLevel = TrustLevel.MODERATE_TRUST,
    ) -> "CustomerType":
        """Create customer type from profile values."""
        type_id = f"{purchase_motivation.value}_{decision_style.value}_{regulatory_focus.value}_{emotional_intensity.value}_{price_sensitivity.value}"
        if archetype:
            type_id += f"_{archetype.value}"
        
        return cls(
            type_id=type_id,
            purchase_motivation=purchase_motivation,
            decision_style=decision_style,
            primary_persuasion=primary_persuasion,
            regulatory_focus=regulatory_focus,
            emotional_intensity=emotional_intensity,
            price_sensitivity=price_sensitivity,
            archetype=archetype,
            trust_level=trust_level,
        )


# =============================================================================
# CUSTOMER TYPE GENERATOR
# =============================================================================

class CustomerTypeGenerator:
    """
    Generates customer types from purchase-predictive dimension combinations.
    
    Primary Types (without archetype): 15 × 3 × 2 × 3 × 4 = 1,080
    With Archetypes: 1,080 × 8 = 8,640
    """
    
    def __init__(self):
        self._primary_types: Dict[str, CustomerType] = {}
        self._full_types: Dict[str, CustomerType] = {}
        
        self._generate_types()
    
    def _generate_types(self) -> None:
        """Generate all customer type combinations."""
        from itertools import product
        
        # Primary types (most predictive dimensions only)
        for combo in product(
            PurchaseMotivation,
            DecisionStyle,
            RegulatoryFocus,
            EmotionalIntensity,
            PriceSensitivity,
        ):
            motivation, style, regulatory, emotional, price = combo
            
            # Determine primary persuasion based on motivation + style
            primary_persuasion = self._infer_primary_persuasion(motivation, style)
            
            ct = CustomerType.from_profile(
                purchase_motivation=motivation,
                decision_style=style,
                primary_persuasion=primary_persuasion,
                regulatory_focus=regulatory,
                emotional_intensity=emotional,
                price_sensitivity=price,
            )
            
            self._primary_types[ct.type_id] = ct
            
            # Also generate with each archetype
            for archetype in Archetype:
                ct_with_arch = CustomerType.from_profile(
                    purchase_motivation=motivation,
                    decision_style=style,
                    primary_persuasion=primary_persuasion,
                    regulatory_focus=regulatory,
                    emotional_intensity=emotional,
                    price_sensitivity=price,
                    archetype=archetype,
                )
                self._full_types[ct_with_arch.type_id] = ct_with_arch
        
        logger.info(f"Generated {len(self._primary_types)} primary types, "
                    f"{len(self._full_types)} full types")
    
    def _infer_primary_persuasion(
        self,
        motivation: PurchaseMotivation,
        style: DecisionStyle,
    ) -> PersuasionProfile:
        """Infer primary persuasion profile from motivation and decision style."""
        # Motivation-based inference
        motivation_persuasion = {
            PurchaseMotivation.QUALITY_SEEKING: PersuasionProfile.AUTHORITY_DRIVEN,
            PurchaseMotivation.RESEARCH_DRIVEN: PersuasionProfile.AUTHORITY_DRIVEN,
            PurchaseMotivation.PROBLEM_SOLVING: PersuasionProfile.AUTHORITY_DRIVEN,
            PurchaseMotivation.SOCIAL_PROOF: PersuasionProfile.SOCIAL_PROOF_DRIVEN,
            PurchaseMotivation.RECOMMENDATION: PersuasionProfile.SOCIAL_PROOF_DRIVEN,
            PurchaseMotivation.STATUS_SIGNALING: PersuasionProfile.SOCIAL_PROOF_DRIVEN,
            PurchaseMotivation.FOMO: PersuasionProfile.SCARCITY_DRIVEN,
            PurchaseMotivation.IMPULSE: PersuasionProfile.SCARCITY_DRIVEN,
            PurchaseMotivation.VALUE_SEEKING: PersuasionProfile.SCARCITY_DRIVEN,
            PurchaseMotivation.GIFT_GIVING: PersuasionProfile.RECIPROCITY_DRIVEN,
            PurchaseMotivation.BRAND_LOYALTY: PersuasionProfile.COMMITMENT_DRIVEN,
            PurchaseMotivation.REPLACEMENT: PersuasionProfile.COMMITMENT_DRIVEN,
            PurchaseMotivation.SELF_REWARD: PersuasionProfile.LIKING_DRIVEN,
            PurchaseMotivation.FUNCTIONAL_NEED: PersuasionProfile.AUTHORITY_DRIVEN,
            PurchaseMotivation.UPGRADE: PersuasionProfile.COMMITMENT_DRIVEN,
        }
        
        return motivation_persuasion.get(motivation, PersuasionProfile.SOCIAL_PROOF_DRIVEN)
    
    def get_primary_type_count(self) -> int:
        """Get count of primary customer types (without archetype)."""
        return len(self._primary_types)
    
    def get_full_type_count(self) -> int:
        """Get count of all customer types (with archetypes)."""
        return len(self._full_types)
    
    def get_type(
        self,
        motivation: str,
        style: str,
        regulatory: str,
        emotional: str,
        price: str,
        archetype: Optional[str] = None,
    ) -> Optional[CustomerType]:
        """Get a customer type by dimension values."""
        try:
            motivation_enum = PurchaseMotivation(motivation.lower().replace(" ", "_"))
            style_enum = DecisionStyle(style.lower().replace(" ", "_"))
            regulatory_enum = RegulatoryFocus(regulatory.lower())
            emotional_enum = EmotionalIntensity(emotional.lower())
            price_enum = PriceSensitivity(price.lower().replace(" ", "_"))
            
            type_id = f"{motivation_enum.value}_{style_enum.value}_{regulatory_enum.value}_{emotional_enum.value}_{price_enum.value}"
            
            if archetype:
                arch_enum = Archetype(archetype.lower())
                type_id += f"_{arch_enum.value}"
                return self._full_types.get(type_id)
            
            return self._primary_types.get(type_id)
        except (ValueError, KeyError):
            return None
    
    def find_types_by_motivation(self, motivation: str) -> List[CustomerType]:
        """Find all types with a given purchase motivation."""
        try:
            mot = PurchaseMotivation(motivation.lower().replace(" ", "_"))
            return [ct for ct in self._primary_types.values() if ct.purchase_motivation == mot]
        except ValueError:
            return []
    
    def get_types_for_review_profile(
        self,
        archetype_distribution: Dict[str, float],
        decision_style: Optional[str] = None,
        purchase_motivation: Optional[str] = None,
        regulatory_focus: Optional[str] = None,
        emotional_intensity: Optional[str] = None,
        price_sensitivity: Optional[str] = None,
    ) -> List[CustomerType]:
        """
        Get customer types matching a review-extracted profile.
        
        Uses defaults when values not detected:
        - decision_style: mixed
        - purchase_motivation: inferred from archetype
        - regulatory_focus: inferred from archetype
        - emotional_intensity: medium
        - price_sensitivity: neutral
        """
        results = []
        
        # Get dominant archetype
        sorted_archetypes = sorted(
            archetype_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Default inferences
        default_motivation = PurchaseMotivation.FUNCTIONAL_NEED
        default_style = DecisionStyle(decision_style) if decision_style else DecisionStyle.MIXED
        default_emotional = EmotionalIntensity(emotional_intensity) if emotional_intensity else EmotionalIntensity.MEDIUM
        default_price = PriceSensitivity(price_sensitivity) if price_sensitivity else PriceSensitivity.PRICE_NEUTRAL
        
        for arch_name, prob in sorted_archetypes:
            if prob < 0.05:
                continue
            
            try:
                archetype = Archetype(arch_name.lower())
            except ValueError:
                continue
            
            # Infer regulatory focus from archetype
            if regulatory_focus:
                regulatory = RegulatoryFocus(regulatory_focus)
            elif archetype in [Archetype.GUARDIAN, Archetype.PRAGMATIST, Archetype.ANALYST]:
                regulatory = RegulatoryFocus.PREVENTION
            else:
                regulatory = RegulatoryFocus.PROMOTION
            
            # Infer motivation from archetype
            if purchase_motivation:
                motivation = PurchaseMotivation(purchase_motivation.lower().replace(" ", "_"))
            else:
                archetype_motivation = {
                    Archetype.ACHIEVER: PurchaseMotivation.QUALITY_SEEKING,
                    Archetype.EXPLORER: PurchaseMotivation.IMPULSE,
                    Archetype.CONNECTOR: PurchaseMotivation.SOCIAL_PROOF,
                    Archetype.GUARDIAN: PurchaseMotivation.RESEARCH_DRIVEN,
                    Archetype.ANALYST: PurchaseMotivation.RESEARCH_DRIVEN,
                    Archetype.CREATOR: PurchaseMotivation.SELF_REWARD,
                    Archetype.NURTURER: PurchaseMotivation.GIFT_GIVING,
                    Archetype.PRAGMATIST: PurchaseMotivation.VALUE_SEEKING,
                }
                motivation = archetype_motivation.get(archetype, default_motivation)
            
            # Generate type
            primary_persuasion = self._infer_primary_persuasion(motivation, default_style)
            
            ct = CustomerType.from_profile(
                purchase_motivation=motivation,
                decision_style=default_style,
                primary_persuasion=primary_persuasion,
                regulatory_focus=regulatory,
                emotional_intensity=default_emotional,
                price_sensitivity=default_price,
                archetype=archetype,
            )
            ct.population_share = prob
            results.append(ct)
        
        return results
    
    def get_all_primary_types(self) -> List[CustomerType]:
        """Get all primary customer types."""
        return list(self._primary_types.values())
    
    def get_all_full_types(self) -> List[CustomerType]:
        """Get all customer types with archetypes."""
        return list(self._full_types.values())


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_generator: Optional[CustomerTypeGenerator] = None


def get_customer_type_generator() -> CustomerTypeGenerator:
    """Get singleton CustomerTypeGenerator instance."""
    global _generator
    if _generator is None:
        _generator = CustomerTypeGenerator()
    return _generator


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_primary_type_count() -> int:
    """Get count of primary customer types."""
    return get_customer_type_generator().get_primary_type_count()


def get_full_type_count() -> int:
    """Get count of all customer types."""
    return get_customer_type_generator().get_full_type_count()


def get_customer_type(
    motivation: str,
    style: str,
    regulatory: str,
    emotional: str,
    price: str,
    archetype: Optional[str] = None,
) -> Optional[CustomerType]:
    """Get a customer type by dimension values."""
    return get_customer_type_generator().get_type(
        motivation=motivation,
        style=style,
        regulatory=regulatory,
        emotional=emotional,
        price=price,
        archetype=archetype,
    )


def get_types_for_category(
    archetype_distribution: Dict[str, float],
    **kwargs,
) -> List[CustomerType]:
    """Get customer types for a category based on its profile."""
    return get_customer_type_generator().get_types_for_review_profile(
        archetype_distribution=archetype_distribution,
        **kwargs,
    )


def get_system_summary() -> Dict[str, Any]:
    """Get summary of the customer type system."""
    gen = get_customer_type_generator()
    
    return {
        "grounded_in": "Purchase behavior prediction from review analysis",
        "tier_1_dimensions": {
            "purchase_motivations": len(PurchaseMotivation),
            "decision_styles": len(DecisionStyle),
            "persuasion_profiles": len(PersuasionProfile),
        },
        "tier_2_dimensions": {
            "regulatory_focus": len(RegulatoryFocus),
            "emotional_intensity": len(EmotionalIntensity),
            "price_sensitivity": len(PriceSensitivity),
        },
        "tier_3_dimensions": {
            "archetypes": len(Archetype),
            "trust_levels": len(TrustLevel),
        },
        "formula": f"{len(PurchaseMotivation)} × {len(DecisionStyle)} × {len(RegulatoryFocus)} × {len(EmotionalIntensity)} × {len(PriceSensitivity)}",
        "primary_types": gen.get_primary_type_count(),
        "full_types_with_archetypes": gen.get_full_type_count(),
        "predictive_value": {
            "purchase_motivation": "35% - WHY they buy",
            "decision_style": "25% - HOW they decide",
            "regulatory_focus": "20% - WHAT appeals to them",
            "emotional_intensity": "15% - HOW strongly they respond",
            "primary_persuasion": "5% - WHAT mechanism works best",
        },
    }


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PURCHASE-PREDICTIVE CUSTOMER TYPE SYSTEM")
    print("=" * 80)
    
    summary = get_system_summary()
    
    print(f"\n=== DIMENSIONS (ranked by predictive value) ===")
    print("\nTIER 1 - Highest Predictive Value:")
    for dim, count in summary["tier_1_dimensions"].items():
        print(f"  {dim}: {count}")
    
    print("\nTIER 2 - Strong Predictive Value:")
    for dim, count in summary["tier_2_dimensions"].items():
        print(f"  {dim}: {count}")
    
    print("\nTIER 3 - Contextual Modifiers:")
    for dim, count in summary["tier_3_dimensions"].items():
        print(f"  {dim}: {count}")
    
    print(f"\n=== TYPE COUNTS ===")
    print(f"Formula: {summary['formula']}")
    print(f"Primary Types (without archetype): {summary['primary_types']:,}")
    print(f"Full Types (with archetypes): {summary['full_types_with_archetypes']:,}")
    
    print(f"\n=== SAMPLE CUSTOMER TYPES ===")
    gen = get_customer_type_generator()
    
    samples = [
        ("quality_seeking", "system2", "promotion", "high", "premium"),
        ("impulse", "system1", "promotion", "high", "value"),
        ("gift_giving", "mixed", "prevention", "medium", "neutral"),
        ("research_driven", "system2", "prevention", "low", "neutral"),
        ("fomo", "system1", "promotion", "high", "budget"),
    ]
    
    for sample in samples:
        ct = gen.get_type(*sample)
        if ct:
            print(f"\n{ct.type_id}:")
            print(f"  Description: {ct.get_description()}")
            approach = ct.get_optimal_approach()
            print(f"  Primary mechanism: {approach['primary_mechanism']} (eff: {ct.mechanism_effectiveness[approach['primary_mechanism']]:.2f})")
            print(f"  Message framing: {approach['message_framing']}")
            print(f"  Urgency level: {approach['urgency_level']}")
            print(f"  Conversion modifier: {ct.conversion_modifier:.2f}x")
