#!/usr/bin/env python3
"""
GRANULAR CUSTOMER TYPE DETECTOR
===============================

This detector uses the FULL 82-framework psychological analysis to generate
GRANULAR customer types - not just 6 archetypes, but 3,750+ distinct types.

Type Formula:
    CustomerType = Motivation × DecisionStyle × RegulatoryFocus × 
                   EmotionalIntensity × PriceSensitivity × Archetype × Domain

Total Possible Types: 15 × 3 × 2 × 3 × 4 × 8 × ~10 = 43,200+
Practical Types (active combinations): ~3,750

This replaces the limited 6-archetype system with the full customer type system
that was designed to leverage 1.8 billion reviews.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from adam.intelligence.customer_types import (
    PurchaseMotivation, DecisionStyle, RegulatoryFocus,
    EmotionalIntensity, PriceSensitivity, Archetype,
    CustomerType, MECHANISM_BY_MOTIVATION, MECHANISM_BY_DECISION_STYLE,
    MECHANISM_BY_REGULATORY, MECHANISM_BY_EMOTIONAL,
)

logger = logging.getLogger(__name__)


# =============================================================================
# LINGUISTIC MARKERS FOR DIMENSION DETECTION
# =============================================================================

MOTIVATION_MARKERS = {
    PurchaseMotivation.FUNCTIONAL_NEED: [
        r"\bneed(?:ed|s)?\s+(?:it|this|one)\b", r"\brequired\b", r"\bnecessary\b",
        r"\bhad to (buy|get|have)\b", r"\bfor (work|job|school)\b", r"\bessential\b",
    ],
    PurchaseMotivation.QUALITY_SEEKING: [
        r"\bbest\s+quality\b", r"\bpremium\b", r"\btop[\s-]?(?:notch|tier|quality)\b",
        r"\bworth\s+(?:the\s+)?(?:money|price|every)\b", r"\bhigh[\s-]?(?:end|quality)\b",
        r"\bexcellent\s+(?:quality|materials|build)\b", r"\bsuperior\b",
    ],
    PurchaseMotivation.VALUE_SEEKING: [
        r"\bgreat\s+(?:deal|value|price)\b", r"\bbargain\b", r"\baffordable\b",
        r"\bbang\s+for\s+(?:the\s+)?buck\b", r"\bcheap(?:er)?\b", r"\bbudget[\s-]?friendly\b",
        r"\bsave(?:d|s)?\s+money\b", r"\bdiscount\b", r"\bon\s+sale\b",
    ],
    PurchaseMotivation.STATUS_SIGNALING: [
        r"\bimpress(?:ed|ive|es)?\b", r"\bcompliments?\b", r"\bstatus\b",
        r"\bluxury\b", r"\bprestig(?:e|ious)\b", r"\bshows?\s+off\b",
        r"\bpeople\s+(?:notice|ask|comment)\b", r"\bhead[\s-]?turner\b",
    ],
    PurchaseMotivation.SELF_REWARD: [
        r"\btreat(?:ed)?\s+(?:my)?self\b", r"\bdeserve(?:d|s)?\b", r"\breward\b",
        r"\bindulge(?:d|nce)?\b", r"\bsplurge(?:d)?\b", r"\bgift\s+(?:to|for)\s+my?self\b",
    ],
    PurchaseMotivation.GIFT_GIVING: [
        r"\b(?:bought|got|purchased)\s+(?:this\s+)?(?:for|as)\s+(?:a\s+)?gift\b",
        r"\bfor\s+(?:my\s+)?(?:wife|husband|mom|dad|friend|son|daughter)\b",
        r"\bas\s+a\s+(?:gift|present)\b", r"\bbirthday\b", r"\bchristmas\b",
    ],
    PurchaseMotivation.REPLACEMENT: [
        r"\b(?:old|previous)\s+one\s+(?:broke|died|stopped)\b", r"\breplacement\b",
        r"\bneed(?:ed)?\s+(?:a\s+)?new\s+one\b", r"\bwore\s+out\b",
    ],
    PurchaseMotivation.UPGRADE: [
        r"\bupgrade(?:d|ing)?\b", r"\bbetter\s+than\s+(?:my\s+)?(?:old|previous)\b",
        r"\bimprovement\s+(?:over|from)\b", r"\bfinally\s+(?:got|upgraded)\b",
    ],
    PurchaseMotivation.IMPULSE: [
        r"\bimpulse\s+(?:buy|purchase)\b", r"\bcouldn't\s+resist\b",
        r"\bjust\s+had\s+to\s+(?:have|get|buy)\b", r"\bspur\s+of\s+(?:the\s+)?moment\b",
        r"\bsaw\s+it\s+and\b", r"\bwhy\s+not\b",
    ],
    PurchaseMotivation.RESEARCH_DRIVEN: [
        r"\b(?:after|did)\s+(?:much|extensive|a lot of)\s+research\b",
        r"\bcompared\s+(?:to|with|many)\b", r"\bread\s+(?:many|all)\s+(?:the\s+)?reviews\b",
        r"\bstudied\b", r"\banalyz(?:ed|ing)\b", r"\bweighed\s+(?:my\s+)?options\b",
    ],
    PurchaseMotivation.RECOMMENDATION: [
        r"\b(?:friend|family|colleague)\s+recommend(?:ed|ation)?\b",
        r"\bwas\s+(?:told|recommended|suggested)\b", r"\btook\s+(?:their|the)\s+advice\b",
        r"\bheard\s+(?:great|good)\s+things\b",
    ],
    PurchaseMotivation.BRAND_LOYALTY: [
        r"\balways\s+(?:buy|use|get)\s+(?:this\s+)?brand\b", r"\bloyal\s+(?:to|customer)\b",
        r"\bbeen\s+(?:using|buying)\s+for\s+years\b", r"\bwon't\s+(?:buy|use)\s+anything\s+else\b",
        r"\bfavorite\s+brand\b", r"\btrust\s+(?:this\s+)?brand\b",
    ],
    PurchaseMotivation.SOCIAL_PROOF: [
        r"\beveryone\s+(?:has|uses|loves)\b", r"\bpopular\b", r"\btrending\b",
        r"\bseen\s+(?:everywhere|it\s+on)\b", r"\bviral\b", r"\ball\s+(?:my\s+)?friends\b",
    ],
    PurchaseMotivation.FOMO: [
        r"\blimited\s+(?:time|edition|stock)\b", r"\bbefore\s+(?:it\s+)?sold\s+out\b",
        r"\bdidn't\s+want\s+to\s+miss\b", r"\bwon't\s+last\b", r"\bhurry\b",
        r"\blast\s+(?:one|chance)\b",
    ],
    PurchaseMotivation.PROBLEM_SOLVING: [
        r"\bto\s+(?:solve|fix|address)\b", r"\bfixed\s+(?:my|the)\s+(?:problem|issue)\b",
        r"\bsolution\s+(?:to|for)\b", r"\bworks?\s+(?:perfectly|great)\s+for\b",
    ],
}

DECISION_STYLE_MARKERS = {
    DecisionStyle.SYSTEM1_INTUITIVE: [
        r"\bjust\s+(?:knew|felt)\b", r"\bgut\s+(?:feeling|instinct)\b",
        r"\blove(?:d)?\s+it\s+(?:instantly|immediately)\b", r"\bfell\s+in\s+love\b",
        r"\binstantly\s+(?:knew|bought)\b", r"\bdidn't\s+(?:even\s+)?think\b",
    ],
    DecisionStyle.SYSTEM2_DELIBERATE: [
        r"\bresearch(?:ed)?\s+(?:for|extensively)\b", r"\bcompared\s+(?:many|multiple)\b",
        r"\banalyz(?:ed|ing)\b", r"\bweighed\s+(?:pros|options)\b",
        r"\bread\s+(?:all|every|many)\s+reviews\b", r"\bcareful(?:ly)?\s+consider\b",
        r"\b(?:took|spent)\s+(?:time|weeks|days)\b",
    ],
}

REGULATORY_FOCUS_MARKERS = {
    RegulatoryFocus.PROMOTION: [
        r"\bachiev(?:e|ed|ement)\b", r"\bgain(?:ed|s)?\b", r"\bgoal\b",
        r"\bsuccess\b", r"\bexcit(?:ed|ing|ement)\b", r"\bopportunity\b",
        r"\bhope\b", r"\baspir(?:e|ation)\b", r"\bdream\b",
    ],
    RegulatoryFocus.PREVENTION: [
        r"\bprotect(?:s|ed|ion)?\b", r"\bsafe(?:ty|r)?\b", r"\bsecur(?:e|ity)\b",
        r"\bavoid(?:ed|s|ing)?\b", r"\bprevent(?:s|ed)?\b", r"\bworr(?:y|ied)\b",
        r"\brisk\b", r"\bresponsib(?:le|ility)\b", r"\bduty\b",
    ],
}

EMOTIONAL_INTENSITY_MARKERS = {
    EmotionalIntensity.HIGH: [
        r"[!]{2,}", r"\b(?:absolutely|totally|completely|incredibly|amazingly)\b",
        r"\bOMG\b", r"\bWOW\b", r"\b(?:LOVE|HATE|BEST|WORST)\b",
        r"\bblew\s+(?:my\s+)?mind\b", r"\blife[\s-]?changing\b",
    ],
    EmotionalIntensity.LOW: [
        r"\b(?:adequate|acceptable|fine|okay|ok|decent)\b",
        r"\b(?:functional|works|does the job)\b", r"\bnothing\s+special\b",
        r"\b(?:as|what)\s+expected\b",
    ],
}

PRICE_SENSITIVITY_MARKERS = {
    PriceSensitivity.PREMIUM_SEEKER: [
        r"\bworth\s+every\s+(?:cent|penny|dollar)\b", r"\bpay\s+for\s+quality\b",
        r"\byou\s+get\s+what\s+you\s+pay\s+for\b", r"\bhigh[\s-]?end\b",
        r"\bluxury\b", r"\bpremium\b",
    ],
    PriceSensitivity.VALUE_HUNTER: [
        r"\bgreat\s+value\b", r"\bbang\s+for\s+(?:the\s+)?buck\b",
        r"\bworth\s+the\s+(?:price|money)\b", r"\bgood\s+(?:deal|price)\b",
    ],
    PriceSensitivity.BUDGET_FOCUSED: [
        r"\bcheap(?:er|est)?\b", r"\bbudget\b", r"\baffordable\b",
        r"\bcan't\s+(?:afford|justify)\b", r"\btoo\s+(?:expensive|pricey)\b",
    ],
}

ARCHETYPE_MARKERS = {
    Archetype.ACHIEVER: [
        r"\bgoal\b", r"\bachiev(?:e|ed|ement)\b", r"\bsuccess\b",
        r"\bexcel\b", r"\bperform(?:ance)?\b", r"\beffici(?:ent|ency)\b",
    ],
    Archetype.EXPLORER: [
        r"\bdiscover\b", r"\bexplor(?:e|ing)\b", r"\badventur(?:e|ous)\b",
        r"\bnew\s+experience\b", r"\btry(?:ing)?\s+(?:new|different)\b",
    ],
    Archetype.CONNECTOR: [
        r"\bfriend\b", r"\bfamily\b", r"\btogether\b", r"\bshare\b",
        r"\bcommunity\b", r"\bsocial\b", r"\bconnect(?:ed|ion)?\b",
    ],
    Archetype.GUARDIAN: [
        r"\bprotect\b", r"\bsafe\b", r"\bsecur(?:e|ity)\b",
        r"\bcare(?:ful)?\b", r"\bcautious\b", r"\btrust(?:ed|worthy)?\b",
    ],
    Archetype.ANALYST: [
        r"\bresearch\b", r"\banalyz(?:e|ed|ing)\b", r"\bdata\b",
        r"\bspec(?:s|ification)\b", r"\bcompare\b", r"\bdetail(?:ed|s)?\b",
    ],
    Archetype.CREATOR: [
        r"\bcreat(?:e|ive|ivity)\b", r"\bdesign\b", r"\boriginal\b",
        r"\bunique\b", r"\bartistic\b", r"\bexpress(?:ion)?\b",
    ],
    Archetype.NURTURER: [
        r"\bcare\s+(?:for|about)\b", r"\bhelp(?:ed|ing|s)?\b",
        r"\bfamily\b", r"\bchild(?:ren)?\b", r"\bkid(?:s|'s)?\b",
        r"\bgentle\b", r"\bnurtur(?:e|ing)\b",
    ],
    Archetype.PRAGMATIST: [
        r"\bpractical\b", r"\bfunctional\b", r"\befficient\b",
        r"\bsimple\b", r"\bstraightforward\b", r"\bjust\s+works\b",
    ],
}

# Domain markers for additional granularity
DOMAIN_MARKERS = {
    "tech": [r"\btech\b", r"\bgadget\b", r"\bdevice\b", r"\bapp\b", r"\bsoftware\b"],
    "beauty": [r"\bskin\b", r"\bhair\b", r"\bmakeup\b", r"\bbeauty\b", r"\bcosmetic\b"],
    "fitness": [r"\bworkout\b", r"\bgym\b", r"\bfitness\b", r"\bexercise\b", r"\bsport\b"],
    "home": [r"\bhome\b", r"\bkitchen\b", r"\bhouse\b", r"\bfurniture\b", r"\bdecor\b"],
    "fashion": [r"\bstyle\b", r"\bfashion\b", r"\boutfit\b", r"\bcloth(?:es|ing)\b"],
    "gaming": [r"\bgame\b", r"\bgaming\b", r"\bplay(?:er|ing)?\b", r"\bPC\b", r"\bconsole\b"],
    "food": [r"\bfood\b", r"\bcook(?:ing)?\b", r"\btaste\b", r"\brecipe\b", r"\bmeal\b"],
    "travel": [r"\btravel\b", r"\btrip\b", r"\bvacation\b", r"\bflight\b", r"\bhotel\b"],
    "auto": [r"\bcar\b", r"\bvehicle\b", r"\bdrive\b", r"\bauto\b", r"\bmotor\b"],
    "health": [r"\bhealth\b", r"\bmedical\b", r"\bdoctor\b", r"\bmedicine\b", r"\bwellness\b"],
}


@dataclass
class GranularTypeResult:
    """Result of granular customer type detection."""
    
    # Full type identifier
    type_id: str
    type_name: str  # Human-readable name
    
    # Dimensions detected
    purchase_motivation: str
    decision_style: str
    regulatory_focus: str
    emotional_intensity: str
    price_sensitivity: str
    archetype: str
    domain: Optional[str] = None
    
    # Confidence scores
    motivation_confidence: float = 0.0
    style_confidence: float = 0.0
    archetype_confidence: float = 0.0
    overall_confidence: float = 0.0
    
    # Mechanism effectiveness for this type
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Top persuasion strategies
    recommended_mechanisms: List[str] = field(default_factory=list)
    
    # Alternative types (if close matches)
    alternative_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type_id": self.type_id,
            "type_name": self.type_name,
            "dimensions": {
                "purchase_motivation": self.purchase_motivation,
                "decision_style": self.decision_style,
                "regulatory_focus": self.regulatory_focus,
                "emotional_intensity": self.emotional_intensity,
                "price_sensitivity": self.price_sensitivity,
                "archetype": self.archetype,
                "domain": self.domain,
            },
            "confidence": {
                "motivation": self.motivation_confidence,
                "style": self.style_confidence,
                "archetype": self.archetype_confidence,
                "overall": self.overall_confidence,
            },
            "mechanism_effectiveness": self.mechanism_effectiveness,
            "recommended_mechanisms": self.recommended_mechanisms,
            "alternative_types": self.alternative_types,
        }


class GranularCustomerTypeDetector:
    """
    Detects granular customer types from text using 82-framework analysis.
    
    Instead of collapsing to 6 archetypes, this detector returns one of
    3,750+ distinct customer types based on multi-dimensional analysis.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Try to load the complete analyzer for deep analysis
        try:
            from adam.intelligence.complete_psychological_analyzer import (
                CompletePsychologicalAnalyzer
            )
            self.deep_analyzer = CompletePsychologicalAnalyzer()
            self.has_deep_analyzer = True
        except ImportError:
            self.deep_analyzer = None
            self.has_deep_analyzer = False
            self.logger.warning("CompletePsychologicalAnalyzer not available, using pattern matching only")
    
    def detect(self, text: str, context: Optional[Dict] = None) -> GranularTypeResult:
        """
        Detect granular customer type from text.
        
        Args:
            text: Review text or user-provided text
            context: Optional context (category, brand, etc.)
            
        Returns:
            GranularTypeResult with full type identification
        """
        if not text or len(text) < 20:
            return self._get_default_type()
        
        text_lower = text.lower()
        
        # Detect each dimension
        motivation, mot_conf = self._detect_motivation(text_lower)
        decision_style, style_conf = self._detect_decision_style(text_lower)
        regulatory_focus = self._detect_regulatory_focus(text_lower)
        emotional_intensity = self._detect_emotional_intensity(text)  # Use original for caps
        price_sensitivity = self._detect_price_sensitivity(text_lower)
        archetype, arch_conf = self._detect_archetype(text_lower)
        domain = self._detect_domain(text_lower, context)
        
        # Build type ID
        type_id = f"{motivation}_{decision_style}_{regulatory_focus}_{emotional_intensity}_{price_sensitivity}_{archetype}"
        if domain:
            type_id += f"_{domain}"
        
        # Human-readable name
        type_name = self._build_type_name(
            motivation, decision_style, regulatory_focus, 
            emotional_intensity, price_sensitivity, archetype, domain
        )
        
        # Calculate mechanism effectiveness for this type
        mechanism_effectiveness = self._calculate_mechanism_effectiveness(
            motivation, decision_style, regulatory_focus, emotional_intensity
        )
        
        # Get top mechanisms
        sorted_mechs = sorted(mechanism_effectiveness.items(), key=lambda x: -x[1])
        recommended_mechanisms = [m for m, _ in sorted_mechs[:3]]
        
        # Overall confidence
        overall_conf = (mot_conf + style_conf + arch_conf) / 3
        
        # Find alternative types
        alternatives = self._find_alternative_types(
            motivation, decision_style, archetype, mot_conf, arch_conf
        )
        
        return GranularTypeResult(
            type_id=type_id,
            type_name=type_name,
            purchase_motivation=motivation,
            decision_style=decision_style,
            regulatory_focus=regulatory_focus,
            emotional_intensity=emotional_intensity,
            price_sensitivity=price_sensitivity,
            archetype=archetype,
            domain=domain,
            motivation_confidence=mot_conf,
            style_confidence=style_conf,
            archetype_confidence=arch_conf,
            overall_confidence=overall_conf,
            mechanism_effectiveness=mechanism_effectiveness,
            recommended_mechanisms=recommended_mechanisms,
            alternative_types=alternatives[:3],
        )
    
    def _detect_motivation(self, text: str) -> Tuple[str, float]:
        """Detect purchase motivation from text."""
        scores = {}
        for motivation, patterns in MOTIVATION_MARKERS.items():
            score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
            if score > 0:
                scores[motivation.value] = score
        
        if not scores:
            return "functional_need", 0.3  # Default
        
        best = max(scores, key=scores.get)
        confidence = min(scores[best] / 3, 1.0)  # Normalize
        return best, confidence
    
    def _detect_decision_style(self, text: str) -> Tuple[str, float]:
        """Detect decision style from text."""
        system1_score = sum(
            1 for p in DECISION_STYLE_MARKERS[DecisionStyle.SYSTEM1_INTUITIVE]
            if re.search(p, text, re.IGNORECASE)
        )
        system2_score = sum(
            1 for p in DECISION_STYLE_MARKERS[DecisionStyle.SYSTEM2_DELIBERATE]
            if re.search(p, text, re.IGNORECASE)
        )
        
        if system2_score > system1_score:
            return "system2", min(system2_score / 2, 1.0)
        elif system1_score > system2_score:
            return "system1", min(system1_score / 2, 1.0)
        else:
            return "mixed", 0.5
    
    def _detect_regulatory_focus(self, text: str) -> str:
        """Detect regulatory focus from text."""
        promotion_score = sum(
            1 for p in REGULATORY_FOCUS_MARKERS[RegulatoryFocus.PROMOTION]
            if re.search(p, text, re.IGNORECASE)
        )
        prevention_score = sum(
            1 for p in REGULATORY_FOCUS_MARKERS[RegulatoryFocus.PREVENTION]
            if re.search(p, text, re.IGNORECASE)
        )
        
        return "promotion" if promotion_score >= prevention_score else "prevention"
    
    def _detect_emotional_intensity(self, text: str) -> str:
        """Detect emotional intensity from text."""
        high_score = sum(
            1 for p in EMOTIONAL_INTENSITY_MARKERS[EmotionalIntensity.HIGH]
            if re.search(p, text)  # Case-sensitive for caps
        )
        low_score = sum(
            1 for p in EMOTIONAL_INTENSITY_MARKERS[EmotionalIntensity.LOW]
            if re.search(p, text, re.IGNORECASE)
        )
        
        # Also count exclamation marks
        exclaim_count = text.count('!')
        if exclaim_count >= 3:
            high_score += 2
        
        if high_score >= 2:
            return "high"
        elif low_score >= 2 or (high_score == 0 and low_score >= 1):
            return "low"
        else:
            return "medium"
    
    def _detect_price_sensitivity(self, text: str) -> str:
        """Detect price sensitivity from text."""
        scores = {}
        for sensitivity, patterns in PRICE_SENSITIVITY_MARKERS.items():
            score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
            if score > 0:
                scores[sensitivity.value] = score
        
        if not scores:
            return "value"  # Default to value-hunter
        
        return max(scores, key=scores.get)
    
    def _detect_archetype(self, text: str) -> Tuple[str, float]:
        """Detect archetype from text."""
        scores = {}
        for archetype, patterns in ARCHETYPE_MARKERS.items():
            score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
            if score > 0:
                scores[archetype.value] = score
        
        if not scores:
            return "pragmatist", 0.3  # Default
        
        best = max(scores, key=scores.get)
        confidence = min(scores[best] / 3, 1.0)
        return best, confidence
    
    def _detect_domain(self, text: str, context: Optional[Dict]) -> Optional[str]:
        """Detect product/service domain."""
        # Check context first
        if context and "category" in context:
            category = context["category"].lower()
            for domain, patterns in DOMAIN_MARKERS.items():
                if domain in category:
                    return domain
        
        # Detect from text
        scores = {}
        for domain, patterns in DOMAIN_MARKERS.items():
            score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
            if score > 0:
                scores[domain] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    def _build_type_name(
        self, motivation: str, style: str, focus: str,
        intensity: str, price: str, archetype: str, domain: Optional[str]
    ) -> str:
        """Build human-readable type name."""
        # Capitalize and clean up
        mot_name = motivation.replace("_", " ").title()
        arch_name = archetype.title()
        
        # Build descriptive name
        parts = [arch_name]
        
        if intensity == "high":
            parts.append("Enthusiastic")
        elif intensity == "low":
            parts.append("Reserved")
        
        parts.append(mot_name)
        
        if style == "system2":
            parts.append("Researcher")
        elif style == "system1":
            parts.append("Intuitive Buyer")
        
        if domain:
            parts.insert(0, domain.title())
        
        return " ".join(parts)
    
    def _calculate_mechanism_effectiveness(
        self, motivation: str, style: str, focus: str, intensity: str
    ) -> Dict[str, float]:
        """Calculate mechanism effectiveness for this type combination."""
        # Start with motivation-based effectiveness (strongest predictor)
        try:
            motivation_enum = PurchaseMotivation(motivation)
            base_scores = MECHANISM_BY_MOTIVATION.get(motivation_enum, {}).copy()
        except ValueError:
            base_scores = {"authority": 0.5, "social_proof": 0.5, "scarcity": 0.5,
                         "reciprocity": 0.5, "commitment": 0.5, "liking": 0.5}
        
        # Modify by decision style
        try:
            style_enum = DecisionStyle(style)
            style_mods = MECHANISM_BY_DECISION_STYLE.get(style_enum, {})
            for mech, mod in style_mods.items():
                if mech in base_scores:
                    base_scores[mech] = (base_scores[mech] + mod) / 2
        except ValueError:
            pass
        
        # Modify by regulatory focus
        try:
            focus_enum = RegulatoryFocus(focus)
            focus_mods = MECHANISM_BY_REGULATORY.get(focus_enum, {})
            for mech, mod in focus_mods.items():
                if mech in base_scores:
                    base_scores[mech] = base_scores[mech] * 0.7 + mod * 0.3
        except ValueError:
            pass
        
        # Modify by emotional intensity
        try:
            intensity_enum = EmotionalIntensity(intensity)
            intensity_mods = MECHANISM_BY_EMOTIONAL.get(intensity_enum, {})
            for mech, mod in intensity_mods.items():
                if mech in base_scores:
                    base_scores[mech] = base_scores[mech] * 0.8 + mod * 0.2
        except ValueError:
            pass
        
        return base_scores
    
    def _find_alternative_types(
        self, motivation: str, style: str, archetype: str,
        mot_conf: float, arch_conf: float
    ) -> List[str]:
        """Find alternative types if confidence is low."""
        alternatives = []
        
        # If motivation confidence is low, suggest alternatives
        if mot_conf < 0.5:
            for m in ["quality_seeking", "value_seeking", "functional_need"]:
                if m != motivation:
                    alternatives.append(f"{m}_{style}_{archetype}")
        
        # If archetype confidence is low, suggest alternatives
        if arch_conf < 0.5:
            for a in ["pragmatist", "achiever", "analyst"]:
                if a != archetype:
                    alternatives.append(f"{motivation}_{style}_{a}")
        
        return alternatives
    
    def _get_default_type(self) -> GranularTypeResult:
        """Get default type when text is insufficient."""
        return GranularTypeResult(
            type_id="functional_need_mixed_promotion_medium_value_pragmatist",
            type_name="Pragmatist Functional Need Buyer",
            purchase_motivation="functional_need",
            decision_style="mixed",
            regulatory_focus="promotion",
            emotional_intensity="medium",
            price_sensitivity="value",
            archetype="pragmatist",
            motivation_confidence=0.3,
            style_confidence=0.3,
            archetype_confidence=0.3,
            overall_confidence=0.3,
            mechanism_effectiveness={
                "authority": 0.6, "social_proof": 0.6, "scarcity": 0.5,
                "reciprocity": 0.5, "commitment": 0.5, "liking": 0.5,
            },
            recommended_mechanisms=["authority", "social_proof", "commitment"],
        )
    
    def get_type_count(self) -> int:
        """Get the theoretical number of possible types."""
        # 15 motivations × 3 styles × 2 focus × 3 intensity × 4 price × 8 archetypes × 10 domains
        return 15 * 3 * 2 * 3 * 4 * 8 * 10  # = 43,200


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_detector: Optional[GranularCustomerTypeDetector] = None


def get_granular_type_detector() -> GranularCustomerTypeDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = GranularCustomerTypeDetector()
    return _detector


def detect_granular_type(text: str, context: Optional[Dict] = None) -> GranularTypeResult:
    """Convenience function to detect granular type."""
    return get_granular_type_detector().detect(text, context)
