#!/usr/bin/env python3
"""
ADAM COMPLETE PSYCHOLOGICAL ANALYZER
=====================================

Unified analyzer combining all 82 psychological frameworks.

This is the master intelligence engine for ADAM's persuasion system.

FRAMEWORK COVERAGE:
- Category I: Personality & Individual Differences (1-5)
- Category II: Motivational Frameworks (6-10)
- Category III: Cognitive Mechanisms / Cialdini+ (11-19)
- Category IV: Neuroscience-Grounded (20-24)
- Category V: Social & Evolutionary (25-29)
- Category VI: Decision-Making (30-34)
- Category VII: Psycholinguistic Analysis (35-40)
- Category VIII: Temporal & State (41-45)
- Category IX: Behavioral Signals (46-50)
- Category X: Brand-Consumer Matching (51-53)
- Category XI: Moral & Values (54-55)
- Category XII: Memory & Learning (56-58)
- Category XIII: Narrative & Meaning (59-61)
- Category XIV: Trust & Credibility (62-64)
- Category XV: Price & Value Psychology (65-67)
- Category XVI: Mechanism Interaction (68-70)
- Category XVII: Contextual Modulation (71-73)
- Category XVIII: Cultural & Demographic (74-76)
- Category XIX: Ethical Guardrails (77-79)
- Category XX: Advanced Inference (80-82)

TOTAL: 82 frameworks, 20 categories, ~5,000+ linguistic patterns
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.psychological_frameworks import (
    PsychologicalFrameworkAnalyzer,
    PsychologicalProfile,
)
from adam.intelligence.psychological_frameworks_extended import (
    ExtendedFrameworkAnalyzer,
)


@dataclass
class CompletePsychologicalProfile:
    """
    Complete psychological profile from all 82 frameworks.
    
    This is the master data structure for ADAM's psychological intelligence.
    """
    
    # Core profile from frameworks 1-40
    core_profile: PsychologicalProfile = field(default_factory=PsychologicalProfile)
    
    # Extended analysis from frameworks 41-82
    temporal_state: Dict[str, float] = field(default_factory=dict)
    behavioral: Dict[str, float] = field(default_factory=dict)
    brand: Dict[str, float] = field(default_factory=dict)
    moral_values: Dict[str, float] = field(default_factory=dict)
    memory: Dict[str, float] = field(default_factory=dict)
    narrative: Dict[str, float] = field(default_factory=dict)
    trust: Dict[str, float] = field(default_factory=dict)
    price: Dict[str, float] = field(default_factory=dict)
    mechanism_interaction: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, float] = field(default_factory=dict)
    cultural: Dict[str, float] = field(default_factory=dict)
    ethical: Dict[str, float] = field(default_factory=dict)
    advanced: Dict[str, float] = field(default_factory=dict)
    
    # Derived insights
    primary_archetype: str = ""
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    recommended_mechanisms: List[str] = field(default_factory=list)
    mechanism_synergies: List[Tuple[str, str, float]] = field(default_factory=list)
    
    # Ethical flags
    vulnerability_detected: bool = False
    ethical_concerns: List[str] = field(default_factory=list)
    
    # Confidence
    overall_confidence: float = 0.0
    framework_coverage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "primary_archetype": self.primary_archetype,
            "archetype_scores": self.archetype_scores,
            "personality": self.core_profile.personality_scores,
            "motivation": self.core_profile.motivation_scores,
            "cognitive_mechanisms": self.core_profile.cognitive_mechanism_scores,
            "neuroscience": self.core_profile.neuroscience_scores,
            "social": self.core_profile.social_scores,
            "decision": self.core_profile.decision_scores,
            "linguistic": self.core_profile.linguistic_scores,
            "temporal_state": self.temporal_state,
            "behavioral": self.behavioral,
            "brand": self.brand,
            "moral_values": self.moral_values,
            "memory": self.memory,
            "narrative": self.narrative,
            "trust": self.trust,
            "price": self.price,
            "mechanism_interaction": self.mechanism_interaction,
            "context": self.context,
            "cultural": self.cultural,
            "ethical": self.ethical,
            "advanced": self.advanced,
            "recommended_mechanisms": self.recommended_mechanisms,
            "mechanism_synergies": self.mechanism_synergies,
            "vulnerability_detected": self.vulnerability_detected,
            "ethical_concerns": self.ethical_concerns,
            "overall_confidence": self.overall_confidence,
            "framework_coverage": self.framework_coverage,
        }
    
    def get_persuasion_strategy(self) -> Dict[str, Any]:
        """Generate optimal persuasion strategy from profile."""
        strategy = {
            "archetype": self.primary_archetype,
            "regulatory_focus": "promotion" if self.core_profile.motivation_scores.get("regulatory_promotion", 0.5) > 0.5 else "prevention",
            "construal_level": "abstract" if self.core_profile.motivation_scores.get("construal_abstract", 0.5) > 0.5 else "concrete",
            "processing_route": "central" if self.core_profile.decision_scores.get("system2_deliberate", 0.5) > 0.5 else "peripheral",
            "primary_mechanisms": self.recommended_mechanisms[:3],
            "mechanism_synergies": self.mechanism_synergies[:2],
            "avoid_mechanisms": [],
            "ethical_guardrails": self.ethical_concerns,
        }
        
        # Add framing recommendation
        if strategy["regulatory_focus"] == "promotion":
            strategy["framing"] = "gain"
            strategy["message_focus"] = "what you'll achieve, gain, become"
        else:
            strategy["framing"] = "loss"
            strategy["message_focus"] = "what you'll avoid, prevent, protect"
        
        # Add message complexity
        if strategy["processing_route"] == "central":
            strategy["message_complexity"] = "high"
            strategy["content_type"] = "detailed arguments, comparisons, evidence"
        else:
            strategy["message_complexity"] = "low"
            strategy["content_type"] = "social proof, simple claims, emotional appeals"
        
        return strategy


class CompletePsychologicalAnalyzer:
    """
    Master analyzer combining all 82 psychological frameworks.
    
    This is the primary intelligence engine for ADAM's persuasion system.
    
    Usage:
        analyzer = CompletePsychologicalAnalyzer()
        profile = analyzer.analyze("Review text here...")
        strategy = profile.get_persuasion_strategy()
    """
    
    def __init__(self):
        self.core_analyzer = PsychologicalFrameworkAnalyzer()
        self.extended_analyzer = ExtendedFrameworkAnalyzer()
    
    def analyze(self, text: str, context: Optional[Dict] = None) -> CompletePsychologicalProfile:
        """
        Analyze text against all 82 psychological frameworks.
        
        Args:
            text: Review text to analyze
            context: Optional context (category, price, brand, etc.)
            
        Returns:
            CompletePsychologicalProfile with full analysis
        """
        profile = CompletePsychologicalProfile()
        
        if not text or len(text) < 20:
            return profile
        
        # Run core analysis (frameworks 1-40)
        profile.core_profile = self.core_analyzer.analyze(text)
        
        # Run extended analysis (frameworks 41-82)
        extended_results = self.extended_analyzer.analyze(text)
        
        # Map extended results
        profile.temporal_state = extended_results.get("temporal_state", {})
        profile.behavioral = extended_results.get("behavioral", {})
        profile.brand = extended_results.get("brand", {})
        profile.moral_values = extended_results.get("moral_values", {})
        profile.memory = extended_results.get("memory", {})
        profile.narrative = extended_results.get("narrative", {})
        profile.trust = extended_results.get("trust", {})
        profile.price = extended_results.get("price", {})
        profile.mechanism_interaction = extended_results.get("mechanism_interaction", {})
        profile.context = extended_results.get("context", {})
        profile.cultural = extended_results.get("cultural", {})
        profile.ethical = extended_results.get("ethical", {})
        profile.advanced = extended_results.get("advanced", {})
        
        # Copy archetype results
        profile.archetype_scores = profile.core_profile.archetype_scores
        profile.primary_archetype = profile.core_profile.primary_archetype
        profile.recommended_mechanisms = profile.core_profile.recommended_mechanisms
        
        # Check ethical guardrails
        profile.vulnerability_detected = extended_results.get("ethical", {}).get("VULNERABILITY_FLAG", False)
        if profile.vulnerability_detected:
            profile.ethical_concerns.append("VULNERABILITY_DETECTED: Do not use high-pressure tactics")
        
        # Calculate mechanism synergies
        profile.mechanism_synergies = self._identify_synergies(profile)
        
        # Calculate confidence and coverage
        profile.overall_confidence = self._calculate_confidence(profile)
        profile.framework_coverage = self._calculate_coverage(profile)
        
        return profile
    
    def _identify_synergies(self, profile: CompletePsychologicalProfile) -> List[Tuple[str, str, float]]:
        """Identify mechanism synergies from profile."""
        synergies = []
        
        mechanisms = profile.core_profile.cognitive_mechanism_scores
        
        # Loss aversion + Scarcity = 1.4x effect
        if mechanisms.get("loss_aversion", 0) > 0.2 and mechanisms.get("scarcity", 0) > 0.2:
            synergies.append(("loss_aversion", "scarcity", 1.4))
        
        # Social proof + Authority
        if mechanisms.get("social_proof", 0) > 0.2 and mechanisms.get("authority", 0) > 0.2:
            synergies.append(("social_proof", "authority", 1.3))
        
        # Reciprocity + Commitment
        if mechanisms.get("reciprocity", 0) > 0.2 and mechanisms.get("commitment", 0) > 0.2:
            synergies.append(("reciprocity", "commitment", 1.25))
        
        return synergies
    
    def _calculate_confidence(self, profile: CompletePsychologicalProfile) -> float:
        """Calculate overall confidence in the profile."""
        # Core confidence
        core_conf = profile.core_profile.overall_confidence
        
        # Extended signal strength
        extended_scores = []
        for category in [profile.temporal_state, profile.behavioral, profile.brand,
                        profile.moral_values, profile.memory, profile.narrative,
                        profile.trust, profile.price, profile.context, profile.cultural]:
            for score in category.values():
                if isinstance(score, (int, float)):
                    extended_scores.append(score)
        
        extended_conf = sum(1 for s in extended_scores if s > 0.2) / max(len(extended_scores), 1)
        
        return (core_conf + extended_conf) / 2
    
    def _calculate_coverage(self, profile: CompletePsychologicalProfile) -> float:
        """Calculate framework coverage (how many frameworks had signal)."""
        total_frameworks = 82
        active_frameworks = 0
        
        # Count core frameworks with signal
        for scores in [profile.core_profile.personality_scores,
                      profile.core_profile.motivation_scores,
                      profile.core_profile.cognitive_mechanism_scores,
                      profile.core_profile.neuroscience_scores,
                      profile.core_profile.social_scores,
                      profile.core_profile.decision_scores,
                      profile.core_profile.linguistic_scores]:
            for score in scores.values():
                if abs(score) > 0.1:
                    active_frameworks += 1
                    break
        
        # Count extended frameworks with signal
        for category in [profile.temporal_state, profile.behavioral, profile.brand,
                        profile.moral_values, profile.memory, profile.narrative,
                        profile.trust, profile.price, profile.mechanism_interaction,
                        profile.context, profile.cultural, profile.ethical, profile.advanced]:
            for score in category.values():
                if isinstance(score, (int, float)) and score > 0.2:
                    active_frameworks += 1
                    break
        
        return active_frameworks / total_frameworks
    
    def analyze_batch(self, texts: List[str]) -> CompletePsychologicalProfile:
        """
        Analyze multiple texts and aggregate results.
        
        Useful for analyzing multiple reviews from the same user/segment.
        """
        if not texts:
            return CompletePsychologicalProfile()
        
        profiles = [self.analyze(text) for text in texts]
        
        # Aggregate archetype scores
        aggregated = CompletePsychologicalProfile()
        
        # Average archetype scores
        for archetype in ["achiever", "explorer", "guardian", "connector", "analyst", "pragmatist"]:
            scores = [p.archetype_scores.get(archetype, 0) for p in profiles]
            aggregated.archetype_scores[archetype] = sum(scores) / len(scores)
        
        # Determine primary archetype
        if aggregated.archetype_scores:
            aggregated.primary_archetype = max(
                aggregated.archetype_scores,
                key=aggregated.archetype_scores.get
            )
        
        # Aggregate mechanism recommendations
        all_mechanisms = []
        for p in profiles:
            all_mechanisms.extend(p.recommended_mechanisms)
        
        # Count mechanism frequency
        mechanism_counts = {}
        for m in all_mechanisms:
            mechanism_counts[m] = mechanism_counts.get(m, 0) + 1
        
        aggregated.recommended_mechanisms = sorted(
            mechanism_counts.keys(),
            key=lambda x: mechanism_counts[x],
            reverse=True
        )[:5]
        
        # Check for any vulnerability
        aggregated.vulnerability_detected = any(p.vulnerability_detected for p in profiles)
        
        return aggregated


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_review(text: str) -> CompletePsychologicalProfile:
    """Convenience function for single review analysis."""
    analyzer = CompletePsychologicalAnalyzer()
    return analyzer.analyze(text)


def get_persuasion_strategy(text: str) -> Dict[str, Any]:
    """Convenience function to get persuasion strategy directly."""
    profile = analyze_review(text)
    return profile.get_persuasion_strategy()


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    analyzer = CompletePsychologicalAnalyzer()
    
    test_reviews = [
        """
        After extensive research comparing this to the competition, I can confidently say
        this is the best in its class. The premium quality is immediately apparent - this
        is clearly a professional-grade product. I don't settle for mediocre, and this
        exceeds my high standards. Worth every dollar for those who demand excellence.
        """,
        
        """
        After struggling for months with my skin, I finally found this product.
        I tried everything - nothing worked. Then my dermatologist recommended this.
        It's been a game-changer! My skin has completely transformed. If you're 
        struggling like I was, you NEED to try this. Don't wait like I did.
        """,
        
        """
        I'm desperate. Nothing has worked for my condition. This is my last hope.
        I can't afford much but I had to try something. I'm at rock bottom and
        praying this will help. Please let this work.
        """,
    ]
    
    for i, review in enumerate(test_reviews, 1):
        print(f"\n{'='*80}")
        print(f"REVIEW {i}")
        print("=" * 80)
        print(review.strip()[:150] + "...")
        
        profile = analyzer.analyze(review)
        
        print(f"\n📊 PRIMARY ARCHETYPE: {profile.primary_archetype.upper()}")
        
        print(f"\n🎯 ARCHETYPE SCORES:")
        for arch, score in sorted(profile.archetype_scores.items(), key=lambda x: -x[1]):
            bar = "█" * int(score * 30)
            print(f"   {arch:12}: {bar} {score:.1%}")
        
        # Get strategy
        strategy = profile.get_persuasion_strategy()
        
        print(f"\n⚡ PERSUASION STRATEGY:")
        print(f"   Regulatory Focus: {strategy['regulatory_focus']}")
        print(f"   Framing: {strategy['framing']}")
        print(f"   Message Focus: {strategy['message_focus']}")
        print(f"   Processing Route: {strategy['processing_route']}")
        print(f"   Content Type: {strategy['content_type']}")
        
        print(f"\n🎛️ RECOMMENDED MECHANISMS:")
        for mech in profile.recommended_mechanisms[:5]:
            print(f"   • {mech}")
        
        if profile.mechanism_synergies:
            print(f"\n🔗 MECHANISM SYNERGIES:")
            for m1, m2, mult in profile.mechanism_synergies:
                print(f"   • {m1} + {m2} = {mult}x effect")
        
        print(f"\n📈 CONFIDENCE: {profile.overall_confidence:.1%}")
        print(f"📊 FRAMEWORK COVERAGE: {profile.framework_coverage:.1%}")
        
        # Ethical check
        if profile.vulnerability_detected:
            print(f"\n⚠️  ETHICAL ALERT: {profile.ethical_concerns[0]}")
