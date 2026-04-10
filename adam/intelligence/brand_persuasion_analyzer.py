#!/usr/bin/env python3
"""
BRAND PERSUASION ANALYZER
=========================

Phase 6+ Enhancement: Full Brand Copy Utilization

Analyzes brand copy (product descriptions, titles, bullet points) for
persuasion techniques using Cialdini's 7 Principles of Influence.

Key Insight (from ADAM_CORE_PHILOSOPHY.md):
"On a site like Amazon... all of the brand's own copy about their product.
They don't own the store so this represents their chance to glow about
their product and SELL it and try to connect with the customer.
In this sense, the information they provide is much like an advertisement."

Brand copy IS advertising. This module extracts the persuasion DNA
from brand copy to:
1. Match brands to receptive customer types
2. Learn which persuasion styles work for which audiences
3. Identify brand positioning and messaging strategy
4. Create brand→customer type fit scores
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)


# =============================================================================
# CIALDINI'S 7 PRINCIPLES OF INFLUENCE
# =============================================================================

class CialdiniPrinciple(str, Enum):
    """
    Cialdini's 7 Principles of Persuasion.
    
    These are the core psychological triggers brands use (consciously or not)
    in their product copy.
    """
    
    RECIPROCITY = "reciprocity"       # Give first, receive later
    COMMITMENT = "commitment"          # Consistency with past behavior
    SOCIAL_PROOF = "social_proof"     # Others do it, so should you
    AUTHORITY = "authority"           # Expert endorsement
    LIKING = "liking"                 # Similarity, compliments, familiarity
    SCARCITY = "scarcity"             # Limited availability increases value
    UNITY = "unity"                   # Shared identity, belonging


# =============================================================================
# PERSUASION TECHNIQUE CATEGORIES
# =============================================================================

class PersuasionTechnique(str, Enum):
    """Specific persuasion techniques brands use in copy."""
    
    # Reciprocity Techniques
    FREE_VALUE = "free_value"           # "Includes free X", "Bonus Y"
    GUARANTEE = "guarantee"             # "Money back", "Risk free"
    GENEROUS_RETURN = "generous_return" # Extended return windows
    
    # Commitment/Consistency
    IDENTITY_APPEAL = "identity_appeal"   # "For runners", "Athletes choose"
    LIFESTYLE_FIT = "lifestyle_fit"       # "Perfect for active lifestyle"
    UPGRADE_PATH = "upgrade_path"         # "Step up from...", "Graduate to..."
    
    # Social Proof
    BESTSELLER = "bestseller"             # "#1 selling", "Most popular"
    CUSTOMER_COUNT = "customer_count"     # "10,000+ satisfied customers"
    RATING_MENTION = "rating_mention"     # "4.8 stars", "Top rated"
    CELEBRITY_USE = "celebrity_use"       # "As seen on", "Used by..."
    TRENDING = "trending"                 # "Viral", "Everyone's talking"
    
    # Authority
    EXPERT_DESIGN = "expert_design"       # "Designed by experts"
    CERTIFICATION = "certification"       # "FDA approved", "ISO certified"
    AWARDS = "awards"                     # "Award winning"
    PATENT = "patent"                     # "Patented technology"
    RESEARCH_BACKED = "research_backed"   # "Clinically proven"
    
    # Liking
    FRIENDLY_VOICE = "friendly_voice"     # Casual, conversational tone
    BRAND_STORY = "brand_story"           # Origin story, founder story
    VALUES_ALIGNMENT = "values_alignment" # Sustainability, ethics
    COMPLIMENT = "compliment"             # "You deserve...", "Treat yourself"
    
    # Scarcity
    LIMITED_EDITION = "limited_edition"   # "Limited", "Exclusive"
    TIME_PRESSURE = "time_pressure"       # "Limited time", "While supplies last"
    STOCK_WARNING = "stock_warning"       # "Only X left", "Selling fast"
    SEASONAL = "seasonal"                 # "Summer collection", seasonal urgency
    
    # Unity
    COMMUNITY = "community"               # "Join the family", "Part of..."
    SHARED_VALUES = "shared_values"       # "We believe...", "Our mission"
    INSIDER = "insider"                   # "Members only", "VIP"
    TRIBE_LANGUAGE = "tribe_language"     # In-group jargon


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

TECHNIQUE_PATTERNS: Dict[PersuasionTechnique, List[str]] = {
    # Reciprocity
    PersuasionTechnique.FREE_VALUE: [
        r"(?:free|bonus|included|complimentary|extra)\s+[\w\s]+(?:included|inside|with)",
        r"(?:get|receive)\s+(?:a\s+)?free\b",
    ],
    PersuasionTechnique.GUARANTEE: [
        r"(?:money.?back|satisfaction|happiness)\s*guarantee",
        r"(?:\d+.?day|\d+.?year|lifetime)\s+(?:guarantee|warranty)",
        r"risk.?free|no.?risk",
    ],
    PersuasionTechnique.GENEROUS_RETURN: [
        r"(?:\d+).?day\s+(?:return|refund)",
        r"easy\s+returns?|hassle.?free\s+return",
    ],
    
    # Commitment
    PersuasionTechnique.IDENTITY_APPEAL: [
        r"(?:for|designed for|made for)\s+(?:runners|athletes|professionals|experts|enthusiasts)",
        r"(?:the|a)\s+(?:runner's|athlete's|professional's|chef's)\s+choice",
    ],
    PersuasionTechnique.LIFESTYLE_FIT: [
        r"(?:perfect|ideal|great)\s+for\s+(?:your|an?)\s+(?:active|busy|modern)\s+lifestyle",
        r"(?:fits|complements|enhances)\s+your\s+(?:life|routine|style)",
    ],
    PersuasionTechnique.UPGRADE_PATH: [
        r"(?:upgrade|step up|level up|graduate)\s+(?:from|to)",
        r"(?:next|new)\s+(?:level|generation|evolution)",
    ],
    
    # Social Proof
    PersuasionTechnique.BESTSELLER: [
        r"(?:#1|number one|top|best)\s*sell(?:ing|er)",
        r"(?:most|highly)\s+(?:popular|loved|requested)",
    ],
    PersuasionTechnique.CUSTOMER_COUNT: [
        r"(?:\d+[,\d]*\+?|millions? of|thousands? of)\s+(?:happy|satisfied)?\s*customers",
        r"(?:trusted|loved|used)\s+by\s+(?:\d+|millions|thousands)",
    ],
    PersuasionTechnique.RATING_MENTION: [
        r"(?:\d+\.?\d*)\s*(?:star|out of \d)",
        r"(?:top|highest)\s+rated",
        r"(?:\d+)%\s+(?:recommend|positive|satisfaction)",
    ],
    PersuasionTechnique.CELEBRITY_USE: [
        r"(?:as seen|featured)\s+(?:on|in)\s+[\w\s]+",
        r"(?:celebrity|influencer|athlete)\s+(?:favorite|choice|pick)",
        r"(?:endorsed|recommended)\s+by",
    ],
    PersuasionTechnique.TRENDING: [
        r"(?:viral|trending|hot|buzzing)",
        r"everyone(?:'s| is)\s+(?:talking|raving)",
        r"(?:tiktok|instagram)\s+(?:famous|sensation)",
    ],
    
    # Authority
    PersuasionTechnique.EXPERT_DESIGN: [
        r"(?:designed|developed|created|crafted)\s+by\s+(?:experts?|professionals?|engineers?)",
        r"(?:expert|professional|precision)\s+(?:engineered|crafted|designed)",
    ],
    PersuasionTechnique.CERTIFICATION: [
        r"(?:fda|usda|iso|ce|ul)\s+(?:approved|certified|compliant)",
        r"(?:certified|approved)\s+by",
        r"(?:meets|exceeds)\s+(?:standards|requirements)",
    ],
    PersuasionTechnique.AWARDS: [
        r"(?:award|prize)\s*(?:-|\s)?(?:winning|winner)",
        r"(?:won|received|earned)\s+(?:the|a)?\s*[\w\s]*award",
    ],
    PersuasionTechnique.PATENT: [
        r"(?:patented|proprietary|exclusive)\s+(?:technology|formula|design)",
        r"patent(?:ed|s)?\s+(?:#|no\.?|number)?",
    ],
    PersuasionTechnique.RESEARCH_BACKED: [
        r"(?:clinically|scientifically|laboratory)\s+(?:proven|tested|verified)",
        r"(?:research|study|studies)\s+(?:shows?|proves?|supports?)",
    ],
    
    # Liking
    PersuasionTechnique.FRIENDLY_VOICE: [
        r"(?:we|we're|let's|you'll)\s+(?:love|think|know)",
        r"(?:trust us|believe us|here's the thing)",
    ],
    PersuasionTechnique.BRAND_STORY: [
        r"(?:founded|started|born)\s+in\s+\d{4}",
        r"(?:our|the)\s+(?:story|journey|mission)\s+(?:began|started)",
        r"(?:family|small)\s+(?:owned|business|company)",
    ],
    PersuasionTechnique.VALUES_ALIGNMENT: [
        r"(?:sustainable|eco.?friendly|organic|natural|ethical|fair.?trade)",
        r"(?:give back|donate|charity|cause)",
        r"(?:planet|environment|earth)\s+(?:friendly|conscious)",
    ],
    PersuasionTechnique.COMPLIMENT: [
        r"(?:you deserve|treat yourself|pamper yourself)",
        r"(?:because you're|for someone)\s+(?:worth it|special|amazing)",
    ],
    
    # Scarcity
    PersuasionTechnique.LIMITED_EDITION: [
        r"limited\s+(?:edition|release|run|quantity)",
        r"(?:exclusive|rare|special)\s+(?:edition|release|collection)",
    ],
    PersuasionTechnique.TIME_PRESSURE: [
        r"(?:limited|for a limited)\s+time\s+(?:only|offer)?",
        r"(?:ends|expires|available until)",
        r"(?:don't miss|act now|hurry)",
    ],
    PersuasionTechnique.STOCK_WARNING: [
        r"(?:only|just)\s+\d+\s+(?:left|remaining|in stock)",
        r"(?:selling|going)\s+fast",
        r"(?:low|limited)\s+stock",
    ],
    PersuasionTechnique.SEASONAL: [
        r"(?:spring|summer|fall|winter|holiday|christmas)\s+(?:collection|edition|special)",
        r"(?:new|this)\s+season",
    ],
    
    # Unity
    PersuasionTechnique.COMMUNITY: [
        r"(?:join|become part of|welcome to)\s+(?:the|our)\s+(?:family|community|tribe)",
        r"(?:fellow|our)\s+(?:members|community|family)",
    ],
    PersuasionTechnique.SHARED_VALUES: [
        r"(?:we|our team)\s+(?:believe|stand for|are committed)",
        r"(?:our|the)\s+mission\s+(?:is|to)",
    ],
    PersuasionTechnique.INSIDER: [
        r"(?:members?|vip|insider)\s+(?:only|exclusive|access)",
        r"(?:unlock|get)\s+(?:exclusive|special|vip)",
    ],
    PersuasionTechnique.TRIBE_LANGUAGE: [
        r"(?:gear|kit|setup|rig|loadout)",  # Enthusiast jargon
        r"(?:drop|cop|flex|drip)",          # Streetwear/sneaker jargon
    ],
}

# Map techniques to Cialdini principles
TECHNIQUE_TO_PRINCIPLE: Dict[PersuasionTechnique, CialdiniPrinciple] = {
    PersuasionTechnique.FREE_VALUE: CialdiniPrinciple.RECIPROCITY,
    PersuasionTechnique.GUARANTEE: CialdiniPrinciple.RECIPROCITY,
    PersuasionTechnique.GENEROUS_RETURN: CialdiniPrinciple.RECIPROCITY,
    
    PersuasionTechnique.IDENTITY_APPEAL: CialdiniPrinciple.COMMITMENT,
    PersuasionTechnique.LIFESTYLE_FIT: CialdiniPrinciple.COMMITMENT,
    PersuasionTechnique.UPGRADE_PATH: CialdiniPrinciple.COMMITMENT,
    
    PersuasionTechnique.BESTSELLER: CialdiniPrinciple.SOCIAL_PROOF,
    PersuasionTechnique.CUSTOMER_COUNT: CialdiniPrinciple.SOCIAL_PROOF,
    PersuasionTechnique.RATING_MENTION: CialdiniPrinciple.SOCIAL_PROOF,
    PersuasionTechnique.CELEBRITY_USE: CialdiniPrinciple.SOCIAL_PROOF,
    PersuasionTechnique.TRENDING: CialdiniPrinciple.SOCIAL_PROOF,
    
    PersuasionTechnique.EXPERT_DESIGN: CialdiniPrinciple.AUTHORITY,
    PersuasionTechnique.CERTIFICATION: CialdiniPrinciple.AUTHORITY,
    PersuasionTechnique.AWARDS: CialdiniPrinciple.AUTHORITY,
    PersuasionTechnique.PATENT: CialdiniPrinciple.AUTHORITY,
    PersuasionTechnique.RESEARCH_BACKED: CialdiniPrinciple.AUTHORITY,
    
    PersuasionTechnique.FRIENDLY_VOICE: CialdiniPrinciple.LIKING,
    PersuasionTechnique.BRAND_STORY: CialdiniPrinciple.LIKING,
    PersuasionTechnique.VALUES_ALIGNMENT: CialdiniPrinciple.LIKING,
    PersuasionTechnique.COMPLIMENT: CialdiniPrinciple.LIKING,
    
    PersuasionTechnique.LIMITED_EDITION: CialdiniPrinciple.SCARCITY,
    PersuasionTechnique.TIME_PRESSURE: CialdiniPrinciple.SCARCITY,
    PersuasionTechnique.STOCK_WARNING: CialdiniPrinciple.SCARCITY,
    PersuasionTechnique.SEASONAL: CialdiniPrinciple.SCARCITY,
    
    PersuasionTechnique.COMMUNITY: CialdiniPrinciple.UNITY,
    PersuasionTechnique.SHARED_VALUES: CialdiniPrinciple.UNITY,
    PersuasionTechnique.INSIDER: CialdiniPrinciple.UNITY,
    PersuasionTechnique.TRIBE_LANGUAGE: CialdiniPrinciple.UNITY,
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PersuasionMatch:
    """A detected persuasion technique in brand copy."""
    
    technique: PersuasionTechnique
    principle: CialdiniPrinciple
    matched_text: str
    confidence: float


@dataclass
class BrandPersuasionProfile:
    """
    Persuasion profile of a brand's copy.
    
    Captures the "persuasion DNA" of how a brand communicates.
    """
    
    brand_name: str = ""
    
    # Detected techniques
    matches: List[PersuasionMatch] = field(default_factory=list)
    
    # Cialdini principle scores (0-1)
    reciprocity_score: float = 0.0
    commitment_score: float = 0.0
    social_proof_score: float = 0.0
    authority_score: float = 0.0
    liking_score: float = 0.0
    scarcity_score: float = 0.0
    unity_score: float = 0.0
    
    # Dominant strategies
    primary_principle: Optional[CialdiniPrinciple] = None
    secondary_principle: Optional[CialdiniPrinciple] = None
    dominant_techniques: List[PersuasionTechnique] = field(default_factory=list)
    
    # Customer type fit scores
    analytical_fit: float = 0.0     # High authority, research-backed
    emotional_fit: float = 0.0      # High liking, community
    social_fit: float = 0.0         # High social proof, trending
    impulsive_fit: float = 0.0      # High scarcity, urgency
    value_conscious_fit: float = 0.0 # High reciprocity, guarantees
    
    # Overall profile
    persuasion_intensity: float = 0.0  # How "salesy" is the copy
    text_analyzed: int = 0             # Characters analyzed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "techniques_detected": len(self.matches),
            "primary_principle": self.primary_principle.value if self.primary_principle else None,
            "secondary_principle": self.secondary_principle.value if self.secondary_principle else None,
            "dominant_techniques": [t.value for t in self.dominant_techniques],
            "principle_scores": {
                "reciprocity": self.reciprocity_score,
                "commitment": self.commitment_score,
                "social_proof": self.social_proof_score,
                "authority": self.authority_score,
                "liking": self.liking_score,
                "scarcity": self.scarcity_score,
                "unity": self.unity_score,
            },
            "customer_fit": {
                "analytical": self.analytical_fit,
                "emotional": self.emotional_fit,
                "social": self.social_fit,
                "impulsive": self.impulsive_fit,
                "value_conscious": self.value_conscious_fit,
            },
            "persuasion_intensity": self.persuasion_intensity,
        }


# =============================================================================
# BRAND PERSUASION ANALYZER
# =============================================================================

class BrandPersuasionAnalyzer:
    """
    Analyzes brand copy for persuasion techniques.
    
    Treats brand descriptions as "pseudo-ads" and extracts
    the persuasion strategies embedded in them.
    """
    
    def __init__(self):
        self._compiled_patterns: Dict[PersuasionTechnique, List[re.Pattern]] = {}
        self._compile_patterns()
        
        # Stats
        self._brands_analyzed = 0
        self._techniques_detected = 0
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns."""
        for technique, patterns in TECHNIQUE_PATTERNS.items():
            self._compiled_patterns[technique] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def analyze(
        self,
        brand_name: str,
        copy: str,
        title: Optional[str] = None,
        bullet_points: Optional[List[str]] = None,
    ) -> BrandPersuasionProfile:
        """
        Analyze brand copy for persuasion techniques.
        
        Args:
            brand_name: Brand name
            copy: Main product description
            title: Product title
            bullet_points: Bullet point features
            
        Returns:
            BrandPersuasionProfile
        """
        self._brands_analyzed += 1
        
        # Combine all text
        all_text_parts = [copy]
        if title:
            all_text_parts.insert(0, title)
        if bullet_points:
            all_text_parts.extend(bullet_points)
        
        full_text = " ".join(filter(None, all_text_parts))
        
        if not full_text:
            return BrandPersuasionProfile(brand_name=brand_name)
        
        # Detect techniques
        matches = []
        for technique, compiled in self._compiled_patterns.items():
            for pattern in compiled:
                for match in pattern.finditer(full_text):
                    matches.append(PersuasionMatch(
                        technique=technique,
                        principle=TECHNIQUE_TO_PRINCIPLE[technique],
                        matched_text=match.group(),
                        confidence=0.8,
                    ))
        
        self._techniques_detected += len(matches)
        
        # Count by principle
        principle_counts: Counter[CialdiniPrinciple] = Counter()
        technique_counts: Counter[PersuasionTechnique] = Counter()
        
        for m in matches:
            principle_counts[m.principle] += 1
            technique_counts[m.technique] += 1
        
        # Calculate principle scores (normalized by text length)
        text_len = len(full_text)
        len_factor = min(1.0, text_len / 500)  # Normalize for text length
        
        profile = BrandPersuasionProfile(
            brand_name=brand_name,
            matches=matches,
            reciprocity_score=min(1.0, principle_counts[CialdiniPrinciple.RECIPROCITY] * 0.4 / len_factor),
            commitment_score=min(1.0, principle_counts[CialdiniPrinciple.COMMITMENT] * 0.4 / len_factor),
            social_proof_score=min(1.0, principle_counts[CialdiniPrinciple.SOCIAL_PROOF] * 0.25 / len_factor),
            authority_score=min(1.0, principle_counts[CialdiniPrinciple.AUTHORITY] * 0.3 / len_factor),
            liking_score=min(1.0, principle_counts[CialdiniPrinciple.LIKING] * 0.35 / len_factor),
            scarcity_score=min(1.0, principle_counts[CialdiniPrinciple.SCARCITY] * 0.5 / len_factor),
            unity_score=min(1.0, principle_counts[CialdiniPrinciple.UNITY] * 0.4 / len_factor),
            text_analyzed=text_len,
        )
        
        # Determine dominant principles
        if principle_counts:
            sorted_principles = principle_counts.most_common(2)
            profile.primary_principle = sorted_principles[0][0]
            if len(sorted_principles) > 1:
                profile.secondary_principle = sorted_principles[1][0]
        
        # Dominant techniques
        profile.dominant_techniques = [t for t, _ in technique_counts.most_common(3)]
        
        # Calculate customer type fits
        profile.analytical_fit = (
            profile.authority_score * 0.5 +
            profile.commitment_score * 0.3 +
            profile.reciprocity_score * 0.2
        )
        
        profile.emotional_fit = (
            profile.liking_score * 0.5 +
            profile.unity_score * 0.3 +
            profile.reciprocity_score * 0.2
        )
        
        profile.social_fit = (
            profile.social_proof_score * 0.6 +
            profile.unity_score * 0.25 +
            profile.liking_score * 0.15
        )
        
        profile.impulsive_fit = (
            profile.scarcity_score * 0.6 +
            profile.social_proof_score * 0.25 +
            profile.reciprocity_score * 0.15
        )
        
        profile.value_conscious_fit = (
            profile.reciprocity_score * 0.5 +
            profile.authority_score * 0.3 +
            profile.social_proof_score * 0.2
        )
        
        # Overall persuasion intensity
        profile.persuasion_intensity = min(1.0, len(matches) / max(1, text_len / 100))
        
        return profile
    
    def analyze_multiple(
        self,
        products: List[Dict[str, Any]],
        brand_key: str = "brand",
        description_key: str = "description",
        title_key: str = "title",
    ) -> Dict[str, BrandPersuasionProfile]:
        """
        Analyze multiple products and aggregate by brand.
        
        Args:
            products: List of product dicts
            brand_key: Key for brand name
            description_key: Key for description
            title_key: Key for title
            
        Returns:
            Dict mapping brand name to aggregated profile
        """
        brand_profiles: Dict[str, List[BrandPersuasionProfile]] = {}
        
        for product in products:
            brand = product.get(brand_key, "Unknown")
            desc = product.get(description_key, "")
            title = product.get(title_key, "")
            
            profile = self.analyze(brand, desc, title)
            
            if brand not in brand_profiles:
                brand_profiles[brand] = []
            brand_profiles[brand].append(profile)
        
        # Aggregate by brand
        aggregated = {}
        for brand, profiles in brand_profiles.items():
            if not profiles:
                continue
            
            # Average scores
            n = len(profiles)
            aggregated[brand] = BrandPersuasionProfile(
                brand_name=brand,
                matches=[m for p in profiles for m in p.matches[:5]],  # Sample matches
                reciprocity_score=sum(p.reciprocity_score for p in profiles) / n,
                commitment_score=sum(p.commitment_score for p in profiles) / n,
                social_proof_score=sum(p.social_proof_score for p in profiles) / n,
                authority_score=sum(p.authority_score for p in profiles) / n,
                liking_score=sum(p.liking_score for p in profiles) / n,
                scarcity_score=sum(p.scarcity_score for p in profiles) / n,
                unity_score=sum(p.unity_score for p in profiles) / n,
                primary_principle=profiles[0].primary_principle,  # Most common
                dominant_techniques=profiles[0].dominant_techniques,
                analytical_fit=sum(p.analytical_fit for p in profiles) / n,
                emotional_fit=sum(p.emotional_fit for p in profiles) / n,
                social_fit=sum(p.social_fit for p in profiles) / n,
                impulsive_fit=sum(p.impulsive_fit for p in profiles) / n,
                value_conscious_fit=sum(p.value_conscious_fit for p in profiles) / n,
                persuasion_intensity=sum(p.persuasion_intensity for p in profiles) / n,
                text_analyzed=sum(p.text_analyzed for p in profiles),
            )
        
        return aggregated
    
    def match_brand_to_customer(
        self,
        brand_profile: BrandPersuasionProfile,
        customer_constructs: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Calculate how well a brand's persuasion style matches a customer.
        
        Args:
            brand_profile: Brand's persuasion profile
            customer_constructs: Customer's psychological constructs
            
        Returns:
            Match analysis with fit scores
        """
        # Map customer constructs to persuasion susceptibilities
        suscept_social = customer_constructs.get("suscept_social_proof", 0.5)
        suscept_authority = customer_constructs.get("suscept_authority", 0.5)
        suscept_scarcity = customer_constructs.get("suscept_scarcity", 0.5)
        
        nfc = customer_constructs.get("cognitive_nfc", 0.5)  # Need for cognition
        extraversion = customer_constructs.get("big5_extraversion", 0.5)
        
        # Calculate principle-specific fit
        fit_scores = {
            "social_proof_fit": brand_profile.social_proof_score * suscept_social,
            "authority_fit": brand_profile.authority_score * suscept_authority,
            "scarcity_fit": brand_profile.scarcity_score * suscept_scarcity,
            "liking_fit": brand_profile.liking_score * extraversion,
            "commitment_fit": brand_profile.commitment_score * (1 - nfc * 0.3),  # Low NFC responds to consistency
        }
        
        # Overall match
        overall_fit = sum(fit_scores.values()) / len(fit_scores)
        
        # Warnings for mismatches
        warnings = []
        if nfc > 0.7 and brand_profile.scarcity_score > 0.6:
            warnings.append("High NFC customer may resist urgency tactics")
        if suscept_social < 0.3 and brand_profile.social_proof_score > 0.6:
            warnings.append("Customer skeptical of social proof claims")
        
        return {
            "overall_fit": overall_fit,
            "principle_fits": fit_scores,
            "brand_primary_strategy": brand_profile.primary_principle.value if brand_profile.primary_principle else None,
            "recommended_emphasis": max(fit_scores, key=fit_scores.get),
            "warnings": warnings,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "brands_analyzed": self._brands_analyzed,
            "techniques_detected": self._techniques_detected,
            "technique_types": len(TECHNIQUE_PATTERNS),
            "principles": len(CialdiniPrinciple),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_analyzer: Optional[BrandPersuasionAnalyzer] = None


def get_brand_persuasion_analyzer() -> BrandPersuasionAnalyzer:
    """Get singleton brand persuasion analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = BrandPersuasionAnalyzer()
    return _analyzer


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_brand_copy(
    brand_name: str,
    description: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to analyze brand copy.
    
    Returns dict suitable for API response.
    """
    analyzer = get_brand_persuasion_analyzer()
    profile = analyzer.analyze(brand_name, description, title)
    return profile.to_dict()


def get_brand_customer_fit(
    brand_name: str,
    brand_description: str,
    customer_constructs: Dict[str, float],
) -> Dict[str, Any]:
    """
    Get fit score between brand persuasion style and customer.
    
    Args:
        brand_name: Brand name
        brand_description: Brand's product copy
        customer_constructs: Customer's psychological profile
        
    Returns:
        Fit analysis dict
    """
    analyzer = get_brand_persuasion_analyzer()
    brand_profile = analyzer.analyze(brand_name, brand_description)
    return analyzer.match_brand_to_customer(brand_profile, customer_constructs)
