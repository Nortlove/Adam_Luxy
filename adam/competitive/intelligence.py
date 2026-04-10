# =============================================================================
# ADAM Competitive Intelligence
# Location: adam/competitive/intelligence.py
# =============================================================================

"""
COMPETITIVE PSYCHOLOGICAL INTELLIGENCE

Analyzes competitor advertising to:
1. Detect their persuasion mechanisms
2. Identify their target archetypes
3. Find psychological vulnerabilities they're not addressing
4. Recommend counter-strategies

KEY INSIGHT:
If a competitor is using Social Proof heavily, they may have saturated that
mechanism. ADAM can exploit underutilized mechanisms (Authority, Scarcity)
that the competitor is neglecting.

GAME THEORY APPROACH:
- If competitor dominates Mechanism A, we have diminishing returns on A
- Unexploited mechanisms offer higher marginal value
- First-mover advantage on mechanisms creates barriers

ARCHITECTURE:
                    ┌─────────────────────┐
                    │  Competitor Ad      │
                    │  (text, images)     │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Mechanism          │
                    │  Detector           │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │ Vulnerability   │ │ Counter-    │ │ Game Theory     │
    │ Mapper          │ │ Strategy    │ │ Optimizer       │
    └─────────────────┘ └─────────────┘ └─────────────────┘
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Cialdini mechanisms and their detection patterns
MECHANISM_PATTERNS = {
    "social_proof": {
        "keywords": [
            "best seller", "bestseller", "#1", "top rated", "millions",
            "thousands", "customers", "reviews", "popular", "favorite",
            "trending", "award-winning", "recommended",
        ],
        "patterns": [
            r"\d+\s*(?:million|thousand|k)\s*(?:customers?|users?|reviews?)",
            r"(?:best|top)\s*(?:seller|rated|reviewed)",
            r"#\d+\s*(?:in|on)",
        ],
        "strength": "high_trust",
    },
    
    "authority": {
        "keywords": [
            "expert", "doctor", "scientist", "clinically proven",
            "tested", "certified", "approved", "professional",
            "recommended by", "endorsed", "patented",
        ],
        "patterns": [
            r"(?:doctor|expert|scientist)s?\s+recommend",
            r"clinically\s+(?:proven|tested|verified)",
            r"fda\s+(?:approved|cleared)",
        ],
        "strength": "high_credibility",
    },
    
    "scarcity": {
        "keywords": [
            "limited", "exclusive", "only", "last chance",
            "while supplies last", "rare", "special edition",
            "one-time", "ending soon",
        ],
        "patterns": [
            r"(?:only|just)\s*\d+\s*left",
            r"limited\s*(?:time|edition|supply)",
            r"ends?\s*(?:soon|today|tomorrow)",
        ],
        "strength": "high_urgency",
    },
    
    "reciprocity": {
        "keywords": [
            "free", "bonus", "gift", "complimentary",
            "included", "extra", "value", "no cost",
        ],
        "patterns": [
            r"free\s+\w+",
            r"(?:get|receive)\s+\w+\s+free",
            r"bonus\s+\w+",
        ],
        "strength": "creates_obligation",
    },
    
    "commitment": {
        "keywords": [
            "join", "become", "start", "try",
            "guarantee", "money back", "risk-free",
            "satisfaction",
        ],
        "patterns": [
            r"(?:join|become)\s+(?:a\s+)?member",
            r"(?:\d+|money)\s*(?:day|back)\s*guarantee",
            r"risk[- ]?free",
        ],
        "strength": "reduces_risk",
    },
    
    "liking": {
        "keywords": [
            "love", "amazing", "beautiful", "gorgeous",
            "you", "your", "personalized", "just for you",
        ],
        "patterns": [
            r"you(?:'ll)?\s+(?:will\s+)?love",
            r"just\s+for\s+you",
            r"made\s+for\s+you",
        ],
        "strength": "emotional_connection",
    },
    
    "unity": {
        "keywords": [
            "family", "community", "together", "we",
            "our", "tribe", "belong", "like you",
        ],
        "patterns": [
            r"(?:join|part\s+of)\s+(?:our|the)\s+(?:family|community)",
            r"people\s+like\s+you",
            r"we(?:'re)?\s+(?:all|together)",
        ],
        "strength": "identity",
    },
}

# Archetype susceptibilities to mechanisms
ARCHETYPE_MECHANISM_SUSCEPTIBILITY = {
    "explorer": ["scarcity", "unity", "commitment"],
    "sage": ["authority", "social_proof", "commitment"],
    "hero": ["social_proof", "authority", "scarcity"],
    "everyman": ["social_proof", "liking", "reciprocity"],
    "rebel": ["scarcity", "unity", "authority"],  # rebels respond to anti-authority authority
    "lover": ["liking", "reciprocity", "unity"],
    "jester": ["liking", "social_proof", "reciprocity"],
    "caregiver": ["reciprocity", "unity", "liking"],
    "creator": ["authority", "scarcity", "commitment"],
    "ruler": ["authority", "social_proof", "scarcity"],
    "magician": ["scarcity", "authority", "unity"],
    "innocent": ["liking", "reciprocity", "social_proof"],
}


# =============================================================================
# DATA MODELS
# =============================================================================

class CompetitorStrength(str, Enum):
    """Strength of competitor's use of a mechanism."""
    DOMINANT = "dominant"      # Heavy, saturated use
    STRONG = "strong"          # Significant presence
    MODERATE = "moderate"      # Some use
    WEAK = "weak"              # Minimal use
    ABSENT = "absent"          # Not using


@dataclass
class MechanismDetection:
    """Detection of a mechanism in competitor ad."""
    mechanism: str
    confidence: float
    evidence: List[str]  # Keywords/patterns found
    strength: CompetitorStrength
    
    @property
    def is_strong(self) -> bool:
        return self.strength in [CompetitorStrength.DOMINANT, CompetitorStrength.STRONG]


@dataclass
class CompetitorAnalysis:
    """Analysis of a competitor's advertising."""
    competitor_name: str
    ad_text: str
    
    # Mechanism analysis
    mechanisms_detected: List[MechanismDetection] = field(default_factory=list)
    primary_mechanism: str = ""
    secondary_mechanisms: List[str] = field(default_factory=list)
    
    # Target archetype inference
    inferred_target_archetypes: List[str] = field(default_factory=list)
    archetype_confidence: float = 0.0
    
    # Overall assessment
    persuasion_sophistication: str = "moderate"  # basic, moderate, advanced
    total_mechanisms_used: int = 0
    
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Vulnerability:
    """A psychological vulnerability not being exploited by competitors."""
    mechanism: str
    opportunity_score: float  # Higher = better opportunity
    rationale: str
    counter_strategy: str
    target_archetypes: List[str]


@dataclass
class CounterStrategy:
    """A recommended counter-strategy against competitor."""
    strategy_name: str
    description: str
    primary_mechanism: str
    secondary_mechanisms: List[str]
    target_archetypes: List[str]
    expected_effectiveness: float
    implementation_hints: List[str]


@dataclass
class CompetitiveIntelligence:
    """Complete competitive intelligence package."""
    
    # Input
    our_brand: str
    competitor_analyses: List[CompetitorAnalysis] = field(default_factory=list)
    
    # Market-level insights
    market_mechanism_saturation: Dict[str, float] = field(default_factory=dict)
    underutilized_mechanisms: List[str] = field(default_factory=list)
    
    # Vulnerabilities and opportunities
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    
    # Recommended strategies
    counter_strategies: List[CounterStrategy] = field(default_factory=list)
    
    # Target archetypes not being served
    underserved_archetypes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "our_brand": self.our_brand,
            "competitor_count": len(self.competitor_analyses),
            "market_saturation": self.market_mechanism_saturation,
            "underutilized_mechanisms": self.underutilized_mechanisms,
            "top_vulnerabilities": [
                {
                    "mechanism": v.mechanism,
                    "opportunity": v.opportunity_score,
                    "strategy": v.counter_strategy,
                }
                for v in self.vulnerabilities[:5]
            ],
            "recommended_strategies": [
                {
                    "name": s.strategy_name,
                    "mechanism": s.primary_mechanism,
                    "effectiveness": s.expected_effectiveness,
                }
                for s in self.counter_strategies[:3]
            ],
            "underserved_archetypes": self.underserved_archetypes,
        }


# =============================================================================
# COMPETITIVE INTELLIGENCE SERVICE
# =============================================================================

class CompetitiveIntelligenceService:
    """
    Analyzes competitor advertising and recommends counter-strategies.
    
    Usage:
        service = CompetitiveIntelligenceService()
        
        # Analyze competitor ads
        analysis = service.analyze_competitor_ad(
            competitor_name="Nike",
            ad_text="Just Do It. Millions of athletes trust Nike..."
        )
        
        # Get full competitive intelligence
        intel = service.build_competitive_intelligence(
            our_brand="Adidas",
            competitor_analyses=[analysis],
        )
        
        print(intel.counter_strategies[0].strategy_name)
    """
    
    def __init__(self):
        """Initialize the service."""
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile regex patterns for efficiency."""
        compiled = {}
        for mechanism, config in MECHANISM_PATTERNS.items():
            compiled[mechanism] = [
                re.compile(p, re.IGNORECASE)
                for p in config.get("patterns", [])
            ]
        return compiled
    
    # -------------------------------------------------------------------------
    # MECHANISM DETECTION
    # -------------------------------------------------------------------------
    
    def detect_mechanisms(self, text: str) -> List[MechanismDetection]:
        """
        Detect persuasion mechanisms in text.
        
        Returns list of detected mechanisms with confidence scores.
        """
        text_lower = text.lower()
        detections = []
        
        for mechanism, config in MECHANISM_PATTERNS.items():
            evidence = []
            score = 0.0
            
            # Check keywords
            keywords = config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    evidence.append(f"keyword:{keyword}")
                    score += 0.3
            
            # Check patterns
            for pattern in self._compiled_patterns.get(mechanism, []):
                matches = pattern.findall(text)
                if matches:
                    evidence.extend([f"pattern:{m}" for m in matches[:3]])
                    score += 0.5 * len(matches)
            
            if score > 0:
                # Determine strength based on score
                if score >= 2.0:
                    strength = CompetitorStrength.DOMINANT
                elif score >= 1.0:
                    strength = CompetitorStrength.STRONG
                elif score >= 0.5:
                    strength = CompetitorStrength.MODERATE
                else:
                    strength = CompetitorStrength.WEAK
                
                detections.append(MechanismDetection(
                    mechanism=mechanism,
                    confidence=min(score / 3.0, 1.0),
                    evidence=evidence,
                    strength=strength,
                ))
        
        # Sort by confidence
        detections.sort(key=lambda d: d.confidence, reverse=True)
        
        return detections
    
    # -------------------------------------------------------------------------
    # COMPETITOR ANALYSIS
    # -------------------------------------------------------------------------
    
    def analyze_competitor_ad(
        self,
        competitor_name: str,
        ad_text: str,
    ) -> CompetitorAnalysis:
        """
        Analyze a competitor's ad for persuasion tactics.
        
        Args:
            competitor_name: Name of the competitor
            ad_text: Full text of the ad
            
        Returns:
            CompetitorAnalysis with all detected mechanisms and insights
        """
        analysis = CompetitorAnalysis(
            competitor_name=competitor_name,
            ad_text=ad_text,
        )
        
        # Detect mechanisms
        analysis.mechanisms_detected = self.detect_mechanisms(ad_text)
        analysis.total_mechanisms_used = len(analysis.mechanisms_detected)
        
        # Identify primary and secondary mechanisms
        if analysis.mechanisms_detected:
            analysis.primary_mechanism = analysis.mechanisms_detected[0].mechanism
            analysis.secondary_mechanisms = [
                d.mechanism for d in analysis.mechanisms_detected[1:4]
            ]
        
        # Infer target archetypes
        analysis.inferred_target_archetypes = self._infer_target_archetypes(
            analysis.mechanisms_detected
        )
        if analysis.inferred_target_archetypes:
            analysis.archetype_confidence = min(
                analysis.mechanisms_detected[0].confidence * 0.8,
                0.85,
            )
        
        # Assess sophistication
        if analysis.total_mechanisms_used >= 4:
            analysis.persuasion_sophistication = "advanced"
        elif analysis.total_mechanisms_used >= 2:
            analysis.persuasion_sophistication = "moderate"
        else:
            analysis.persuasion_sophistication = "basic"
        
        return analysis
    
    def _infer_target_archetypes(
        self,
        mechanisms: List[MechanismDetection],
    ) -> List[str]:
        """Infer which archetypes the ad is targeting based on mechanisms used."""
        if not mechanisms:
            return []
        
        # Score each archetype by how well mechanisms match their susceptibilities
        archetype_scores: Dict[str, float] = defaultdict(float)
        
        for mech in mechanisms:
            for archetype, susceptible_to in ARCHETYPE_MECHANISM_SUSCEPTIBILITY.items():
                if mech.mechanism in susceptible_to:
                    # Weight by position in susceptibility list and mechanism confidence
                    position_weight = 1.0 - (susceptible_to.index(mech.mechanism) * 0.2)
                    archetype_scores[archetype] += mech.confidence * position_weight
        
        # Sort and return top archetypes
        sorted_archetypes = sorted(
            archetype_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return [a[0] for a in sorted_archetypes[:3] if a[1] > 0.3]
    
    # -------------------------------------------------------------------------
    # COMPETITIVE INTELLIGENCE
    # -------------------------------------------------------------------------
    
    def build_competitive_intelligence(
        self,
        our_brand: str,
        competitor_analyses: List[CompetitorAnalysis],
        target_archetypes: Optional[List[str]] = None,
    ) -> CompetitiveIntelligence:
        """
        Build complete competitive intelligence from competitor analyses.
        
        Args:
            our_brand: Our brand name
            competitor_analyses: List of analyzed competitor ads
            target_archetypes: Our target archetypes (optional)
            
        Returns:
            CompetitiveIntelligence with vulnerabilities and counter-strategies
        """
        intel = CompetitiveIntelligence(
            our_brand=our_brand,
            competitor_analyses=competitor_analyses,
        )
        
        # Calculate market mechanism saturation
        intel.market_mechanism_saturation = self._calculate_market_saturation(
            competitor_analyses
        )
        
        # Find underutilized mechanisms
        intel.underutilized_mechanisms = self._find_underutilized_mechanisms(
            intel.market_mechanism_saturation
        )
        
        # Find vulnerabilities
        intel.vulnerabilities = self._find_vulnerabilities(
            intel.market_mechanism_saturation,
            target_archetypes or [],
        )
        
        # Generate counter-strategies
        intel.counter_strategies = self._generate_counter_strategies(
            intel.vulnerabilities,
            intel.market_mechanism_saturation,
            target_archetypes or [],
        )
        
        # Find underserved archetypes
        competitor_archetypes = set()
        for analysis in competitor_analyses:
            competitor_archetypes.update(analysis.inferred_target_archetypes)
        
        all_archetypes = set(ARCHETYPE_MECHANISM_SUSCEPTIBILITY.keys())
        intel.underserved_archetypes = list(all_archetypes - competitor_archetypes)
        
        return intel
    
    def _calculate_market_saturation(
        self,
        analyses: List[CompetitorAnalysis],
    ) -> Dict[str, float]:
        """Calculate how saturated each mechanism is in the market."""
        if not analyses:
            return {}
        
        mechanism_counts: Dict[str, int] = defaultdict(int)
        mechanism_strengths: Dict[str, float] = defaultdict(float)
        
        for analysis in analyses:
            for detection in analysis.mechanisms_detected:
                mechanism_counts[detection.mechanism] += 1
                mechanism_strengths[detection.mechanism] += detection.confidence
        
        # Calculate saturation as normalized score
        saturation = {}
        for mechanism in MECHANISM_PATTERNS.keys():
            count = mechanism_counts.get(mechanism, 0)
            strength = mechanism_strengths.get(mechanism, 0.0)
            
            # Saturation = (count/total_competitors) * avg_strength
            saturation[mechanism] = (count / len(analyses)) * (
                strength / count if count > 0 else 0
            )
        
        return saturation
    
    def _find_underutilized_mechanisms(
        self,
        saturation: Dict[str, float],
    ) -> List[str]:
        """Find mechanisms with low market saturation."""
        return [
            mech for mech, sat in sorted(saturation.items(), key=lambda x: x[1])
            if sat < 0.3
        ]
    
    def _find_vulnerabilities(
        self,
        saturation: Dict[str, float],
        target_archetypes: List[str],
    ) -> List[Vulnerability]:
        """Find psychological vulnerabilities competitors aren't exploiting."""
        vulnerabilities = []
        
        for mechanism in MECHANISM_PATTERNS.keys():
            sat = saturation.get(mechanism, 0.0)
            
            # Low saturation = high opportunity
            if sat < 0.4:
                # Find which archetypes respond to this mechanism
                responsive_archetypes = [
                    arch for arch, mechs in ARCHETYPE_MECHANISM_SUSCEPTIBILITY.items()
                    if mechanism in mechs
                ]
                
                # Higher score if our target archetypes are responsive
                opportunity = (1.0 - sat)
                if target_archetypes:
                    overlap = len(set(target_archetypes) & set(responsive_archetypes))
                    opportunity *= (1.0 + 0.2 * overlap)
                
                vulnerabilities.append(Vulnerability(
                    mechanism=mechanism,
                    opportunity_score=opportunity,
                    rationale=f"Low competitor use ({sat:.0%} saturation) with "
                              f"{len(responsive_archetypes)} responsive archetypes",
                    counter_strategy=self._get_counter_strategy_hint(mechanism),
                    target_archetypes=responsive_archetypes[:3],
                ))
        
        # Sort by opportunity
        vulnerabilities.sort(key=lambda v: v.opportunity_score, reverse=True)
        
        return vulnerabilities
    
    def _get_counter_strategy_hint(self, mechanism: str) -> str:
        """Get a brief counter-strategy hint for a mechanism."""
        hints = {
            "social_proof": "Emphasize unique community, exclusive reviews",
            "authority": "Partner with credible experts, highlight certifications",
            "scarcity": "Create genuine limited editions, time-sensitive offers",
            "reciprocity": "Offer valuable free content, samples, bonuses",
            "commitment": "Low-risk trial, satisfaction guarantees",
            "liking": "Personalization, relatable brand voice",
            "unity": "Build tribe identity, shared values messaging",
        }
        return hints.get(mechanism, "Develop unique positioning")
    
    def _generate_counter_strategies(
        self,
        vulnerabilities: List[Vulnerability],
        saturation: Dict[str, float],
        target_archetypes: List[str],
    ) -> List[CounterStrategy]:
        """Generate recommended counter-strategies."""
        strategies = []
        
        # Strategy 1: Exploit top vulnerability
        if vulnerabilities:
            top_vuln = vulnerabilities[0]
            strategies.append(CounterStrategy(
                strategy_name="Blue Ocean",
                description=f"Dominate the underutilized {top_vuln.mechanism} mechanism "
                           f"where competitors have only {saturation.get(top_vuln.mechanism, 0):.0%} presence",
                primary_mechanism=top_vuln.mechanism,
                secondary_mechanisms=[v.mechanism for v in vulnerabilities[1:3]],
                target_archetypes=top_vuln.target_archetypes,
                expected_effectiveness=top_vuln.opportunity_score,
                implementation_hints=[
                    top_vuln.counter_strategy,
                    "First-mover advantage on this mechanism",
                    "Low competitive noise",
                ],
            ))
        
        # Strategy 2: Multi-mechanism sophistication
        if len(vulnerabilities) >= 3:
            mechanisms = [v.mechanism for v in vulnerabilities[:4]]
            strategies.append(CounterStrategy(
                strategy_name="Sophistication Play",
                description="Use multiple underutilized mechanisms in combination "
                           "for higher persuasion sophistication than competitors",
                primary_mechanism=mechanisms[0],
                secondary_mechanisms=mechanisms[1:],
                target_archetypes=target_archetypes or ["sage", "creator"],
                expected_effectiveness=0.7,
                implementation_hints=[
                    "Layer mechanisms across customer journey",
                    "Authority + Scarcity is particularly powerful",
                    "Reciprocity creates commitment foundation",
                ],
            ))
        
        # Strategy 3: Archetype focus
        if target_archetypes:
            # Find best mechanisms for target archetypes that aren't saturated
            best_mechanisms = []
            for archetype in target_archetypes:
                susceptible = ARCHETYPE_MECHANISM_SUSCEPTIBILITY.get(archetype, [])
                for mech in susceptible:
                    if saturation.get(mech, 0) < 0.5 and mech not in best_mechanisms:
                        best_mechanisms.append(mech)
            
            if best_mechanisms:
                strategies.append(CounterStrategy(
                    strategy_name="Archetype Precision",
                    description=f"Target {', '.join(target_archetypes[:2])} archetypes "
                               f"with mechanisms they're most susceptible to",
                    primary_mechanism=best_mechanisms[0],
                    secondary_mechanisms=best_mechanisms[1:3],
                    target_archetypes=target_archetypes,
                    expected_effectiveness=0.75,
                    implementation_hints=[
                        f"These archetypes respond strongly to {best_mechanisms[0]}",
                        "Competitors are not optimizing for these archetypes",
                        "Personalization increases effectiveness",
                    ],
                ))
        
        return strategies


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[CompetitiveIntelligenceService] = None


def get_competitive_intelligence_service() -> CompetitiveIntelligenceService:
    """Get singleton competitive intelligence service."""
    global _service
    if _service is None:
        _service = CompetitiveIntelligenceService()
    return _service


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_competitor(
    competitor_name: str,
    ad_text: str,
) -> CompetitorAnalysis:
    """Convenience function to analyze a competitor ad."""
    service = get_competitive_intelligence_service()
    return service.analyze_competitor_ad(competitor_name, ad_text)


def get_counter_strategies(
    our_brand: str,
    competitor_ads: List[Tuple[str, str]],  # [(competitor_name, ad_text), ...]
    target_archetypes: Optional[List[str]] = None,
) -> CompetitiveIntelligence:
    """
    Convenience function to get competitive intelligence.
    
    Usage:
        intel = get_counter_strategies(
            our_brand="Nike",
            competitor_ads=[
                ("Adidas", "Impossible is Nothing. Join millions of athletes..."),
                ("Puma", "Be fast. Limited edition collection available now..."),
            ],
            target_archetypes=["hero", "explorer"],
        )
    """
    service = get_competitive_intelligence_service()
    
    # Analyze all competitors
    analyses = [
        service.analyze_competitor_ad(name, text)
        for name, text in competitor_ads
    ]
    
    # Build intelligence
    return service.build_competitive_intelligence(
        our_brand=our_brand,
        competitor_analyses=analyses,
        target_archetypes=target_archetypes,
    )
