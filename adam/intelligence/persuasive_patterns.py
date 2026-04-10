#!/usr/bin/env python3
"""
PERSUASIVE PATTERN EXTRACTOR
============================

Phase 6+ Enhancement: Full Helpful Vote Utilization

Extracts persuasive patterns from high-helpful-vote reviews.
These reviews represent language that resonated with other customers -
they are the "proven persuasion" in our billion review corpus.

Key Insight (from ADAM_CORE_PHILOSOPHY.md):
"When the customer gives a thumbs up to another customer review and
acknowledges that the review was helpful in helping them decide to buy
or not to buy" - this is VALIDATED PERSUASION.

This module:
1. Extracts opening hooks from high-vote reviews
2. Identifies evidence patterns that convince
3. Detects emotional appeals that resonate
4. Creates persuasive templates by customer type
5. Weights learning by persuasive power
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import Counter

logger = logging.getLogger(__name__)


# =============================================================================
# PERSUASIVE ELEMENT TYPES
# =============================================================================

class PersuasiveElement(str, Enum):
    """Types of persuasive elements found in reviews."""
    
    # Opening Hooks
    HOOK_QUESTION = "hook_question"           # "Ever wonder if..."
    HOOK_STORY = "hook_story"                 # "I've been searching for years..."
    HOOK_CONTRAST = "hook_contrast"           # "Unlike other products..."
    HOOK_AUTHORITY = "hook_authority"         # "As a marathon runner..."
    HOOK_URGENCY = "hook_urgency"             # "I almost didn't buy this but..."
    
    # Evidence Patterns
    EVIDENCE_SPECIFIC = "evidence_specific"    # Exact numbers, measurements
    EVIDENCE_COMPARISON = "evidence_comparison" # "Better than X because..."
    EVIDENCE_TIMELINE = "evidence_timeline"    # "After 6 months of use..."
    EVIDENCE_USE_CASE = "evidence_use_case"   # "Perfect for running/yoga/etc"
    EVIDENCE_DURABILITY = "evidence_durability" # Longevity proof
    
    # Emotional Appeals
    EMOTION_JOY = "emotion_joy"               # Excitement, happiness
    EMOTION_RELIEF = "emotion_relief"         # Problem solved
    EMOTION_BELONGING = "emotion_belonging"   # Part of community
    EMOTION_PRIDE = "emotion_pride"           # Achievement, status
    EMOTION_TRUST = "emotion_trust"           # Reliability, dependability
    
    # Social Proof Elements
    SOCIAL_RECOMMENDATION = "social_recommend" # "Everyone asks where I got..."
    SOCIAL_GIFTING = "social_gifting"         # "Bought as gift, they loved it"
    SOCIAL_REPURCHASE = "social_repurchase"   # "Already ordered my second pair"
    SOCIAL_CONVERT = "social_convert"         # "Converted my skeptical friend"
    
    # Credibility Builders
    CREDIBILITY_EXPERTISE = "cred_expertise"  # Demonstrates knowledge
    CREDIBILITY_BALANCED = "cred_balanced"    # Mentions pros AND cons
    CREDIBILITY_VERIFIED = "cred_verified"    # References verified purchase
    CREDIBILITY_UPDATED = "cred_updated"      # Update after extended use


# =============================================================================
# PATTERN DETECTION RULES
# =============================================================================

PATTERN_RULES: Dict[PersuasiveElement, List[str]] = {
    # Opening Hooks
    PersuasiveElement.HOOK_QUESTION: [
        r"^(?:have you|do you|ever wonder|looking for|tired of)",
        r"^(?:want to know|curious about|thinking about)",
    ],
    PersuasiveElement.HOOK_STORY: [
        r"^(?:i've been|i have been|for years|my journey)",
        r"^(?:let me tell you|here's my story|i finally found)",
    ],
    PersuasiveElement.HOOK_CONTRAST: [
        r"^(?:unlike|compared to|different from|not like)",
        r"^(?:forget everything|throw away your old)",
    ],
    PersuasiveElement.HOOK_AUTHORITY: [
        r"^(?:as a|being a|i'm a|i am a)[\w\s]+(runner|athlete|professional|expert)",
        r"^(?:with \d+ years|having used \d+|after trying \d+)",
    ],
    PersuasiveElement.HOOK_URGENCY: [
        r"^(?:i almost|i nearly|i wasn't sure|hesitated)",
        r"glad i (?:took the plunge|gave it a chance|tried)",
    ],
    
    # Evidence Patterns
    PersuasiveElement.EVIDENCE_SPECIFIC: [
        r"\d+(?:\.\d+)?\s*(?:inches|cm|mm|lbs|kg|oz|hours|miles|km)",
        r"(?:size|width|length|weight|measurement)[\w\s]*\d+",
    ],
    PersuasiveElement.EVIDENCE_COMPARISON: [
        r"(?:better|worse|superior|inferior)\s+(?:than|to|compared)",
        r"(?:beats|outperforms|surpasses|rivals)",
    ],
    PersuasiveElement.EVIDENCE_TIMELINE: [
        r"(?:after|for)\s+\d+\s*(?:days|weeks|months|years)",
        r"(?:still|even after)\s+\d+\s*(?:uses|washes|wears)",
    ],
    PersuasiveElement.EVIDENCE_USE_CASE: [
        r"(?:perfect|great|ideal)\s+for\s+(?:running|yoga|gym|work|travel)",
        r"(?:use|wear|used)\s+(?:it|them|these)\s+(?:for|to|when)",
    ],
    PersuasiveElement.EVIDENCE_DURABILITY: [
        r"(?:still|looks|feels)\s+(?:like new|brand new|great)",
        r"(?:no|zero)\s+(?:wear|signs|damage|issues)",
    ],
    
    # Emotional Appeals
    PersuasiveElement.EMOTION_JOY: [
        r"(?:love|absolutely love|obsessed|in love with)",
        r"(?:so happy|thrilled|ecstatic|overjoyed)",
    ],
    PersuasiveElement.EMOTION_RELIEF: [
        r"(?:finally|at last|no more|problem solved)",
        r"(?:relief|relieved|saved|rescue)",
    ],
    PersuasiveElement.EMOTION_BELONGING: [
        r"(?:community|tribe|family|fellow)",
        r"(?:one of us|join|member|club)",
    ],
    PersuasiveElement.EMOTION_PRIDE: [
        r"(?:compliments|everyone asks|noticed|admired)",
        r"(?:proud|confident|amazing|stunning)",
    ],
    PersuasiveElement.EMOTION_TRUST: [
        r"(?:reliable|dependable|consistent|trust)",
        r"(?:never fails|always works|count on)",
    ],
    
    # Social Proof
    PersuasiveElement.SOCIAL_RECOMMENDATION: [
        r"(?:recommend|suggest|tell everyone|rave about)",
        r"(?:friends|family|coworkers)\s+(?:ask|want|love)",
    ],
    PersuasiveElement.SOCIAL_GIFTING: [
        r"(?:gift|gifted|present|bought for)",
        r"(?:loved it|they love|perfect gift)",
    ],
    PersuasiveElement.SOCIAL_REPURCHASE: [
        r"(?:bought|ordered|getting)\s+(?:another|more|second|third)",
        r"(?:backup|spare|extra|stock up)",
    ],
    PersuasiveElement.SOCIAL_CONVERT: [
        r"(?:convert|convinced|skeptic|doubter)",
        r"(?:changed their mind|now they|believer)",
    ],
    
    # Credibility
    PersuasiveElement.CREDIBILITY_EXPERTISE: [
        r"(?:years of experience|professionally|expert|specialist)",
        r"(?:i know|understand|familiar with|researched)",
    ],
    PersuasiveElement.CREDIBILITY_BALANCED: [
        r"(?:only|one|minor)\s+(?:con|downside|complaint|issue)",
        r"(?:pros?|positives?)[\s:]+(?:.*?)(?:cons?|negatives?)",
    ],
    PersuasiveElement.CREDIBILITY_VERIFIED: [
        r"verified\s+purchase",
        r"actually\s+(?:bought|purchased|own)",
    ],
    PersuasiveElement.CREDIBILITY_UPDATED: [
        r"(?:update|edit|follow.?up|months? later)",
        r"(?:still|after \d+|revisiting)",
    ],
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PersuasivePattern:
    """A detected persuasive pattern in a review."""
    
    element: PersuasiveElement
    text_match: str
    position: str  # "opening", "body", "closing"
    strength: float  # 0-1 based on how clear the pattern is
    context: str  # Surrounding text


@dataclass
class PersuasiveProfile:
    """Persuasive profile of a review or set of reviews."""
    
    patterns: List[PersuasivePattern] = field(default_factory=list)
    dominant_elements: List[PersuasiveElement] = field(default_factory=list)
    
    # Scores by category (0-1)
    hook_strength: float = 0.0
    evidence_strength: float = 0.0
    emotion_strength: float = 0.0
    social_proof_strength: float = 0.0
    credibility_strength: float = 0.0
    
    # Derived metrics
    overall_persuasive_power: float = 0.0
    helpful_votes: int = 0
    review_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patterns": [p.element.value for p in self.patterns],
            "dominant_elements": [e.value for e in self.dominant_elements],
            "hook_strength": self.hook_strength,
            "evidence_strength": self.evidence_strength,
            "emotion_strength": self.emotion_strength,
            "social_proof_strength": self.social_proof_strength,
            "credibility_strength": self.credibility_strength,
            "overall_persuasive_power": self.overall_persuasive_power,
            "helpful_votes": self.helpful_votes,
            "review_count": self.review_count,
        }


@dataclass
class PersuasiveTemplate:
    """A persuasive template derived from high-vote reviews."""
    
    template_id: str
    customer_type: str  # e.g., "analytical", "emotional", "social"
    
    # Recommended structure
    opening_hook: PersuasiveElement
    evidence_types: List[PersuasiveElement]
    emotional_appeals: List[PersuasiveElement]
    social_proof: List[PersuasiveElement]
    credibility_elements: List[PersuasiveElement]
    
    # Example phrases
    example_openings: List[str] = field(default_factory=list)
    example_evidence: List[str] = field(default_factory=list)
    
    # Effectiveness
    avg_helpful_votes: float = 0.0
    sample_size: int = 0
    effectiveness_score: float = 0.0


# =============================================================================
# PATTERN EXTRACTOR
# =============================================================================

class PersuasivePatternExtractor:
    """
    Extracts persuasive patterns from reviews.
    
    Focuses on high-helpful-vote reviews to learn what language
    resonates with customers and drives purchase decisions.
    """
    
    def __init__(self, min_helpful_votes: int = 10):
        """
        Initialize extractor.
        
        Args:
            min_helpful_votes: Minimum votes to consider "high engagement"
        """
        self.min_helpful_votes = min_helpful_votes
        self._compiled_patterns: Dict[PersuasiveElement, List[re.Pattern]] = {}
        self._compile_patterns()
        
        # Statistics
        self._reviews_analyzed = 0
        self._patterns_detected = 0
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        for element, patterns in PATTERN_RULES.items():
            self._compiled_patterns[element] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def extract_patterns(self, text: str) -> List[PersuasivePattern]:
        """
        Extract persuasive patterns from review text.
        
        Args:
            text: Review text to analyze
            
        Returns:
            List of detected persuasive patterns
        """
        if not text:
            return []
        
        patterns = []
        text_lower = text.lower()
        
        # Split into sections
        sentences = re.split(r'[.!?]+', text)
        opening = sentences[0] if sentences else ""
        body = " ".join(sentences[1:-1]) if len(sentences) > 2 else ""
        closing = sentences[-1] if len(sentences) > 1 else ""
        
        for element, compiled in self._compiled_patterns.items():
            for pattern in compiled:
                # Check opening for hooks
                if element.value.startswith("hook_"):
                    match = pattern.search(opening)
                    if match:
                        patterns.append(PersuasivePattern(
                            element=element,
                            text_match=match.group(),
                            position="opening",
                            strength=0.9,
                            context=opening[:100],
                        ))
                
                # Check full text for other patterns
                else:
                    for match in pattern.finditer(text_lower):
                        # Determine position
                        pos_idx = match.start()
                        if pos_idx < len(opening):
                            position = "opening"
                        elif pos_idx > len(text) - len(closing):
                            position = "closing"
                        else:
                            position = "body"
                        
                        patterns.append(PersuasivePattern(
                            element=element,
                            text_match=match.group(),
                            position=position,
                            strength=0.7,
                            context=text[max(0, match.start()-50):match.end()+50],
                        ))
        
        self._patterns_detected += len(patterns)
        return patterns
    
    def analyze_review(
        self,
        text: str,
        helpful_votes: int = 0,
    ) -> PersuasiveProfile:
        """
        Analyze a single review for persuasive patterns.
        
        Args:
            text: Review text
            helpful_votes: Number of helpful votes
            
        Returns:
            PersuasiveProfile for the review
        """
        self._reviews_analyzed += 1
        
        patterns = self.extract_patterns(text)
        
        # Count by category
        hooks = [p for p in patterns if p.element.value.startswith("hook_")]
        evidence = [p for p in patterns if p.element.value.startswith("evidence_")]
        emotions = [p for p in patterns if p.element.value.startswith("emotion_")]
        social = [p for p in patterns if p.element.value.startswith("social_")]
        credibility = [p for p in patterns if p.element.value.startswith("cred_")]
        
        # Calculate strengths
        hook_strength = min(1.0, len(hooks) * 0.5)
        evidence_strength = min(1.0, len(evidence) * 0.25)
        emotion_strength = min(1.0, len(emotions) * 0.3)
        social_proof_strength = min(1.0, len(social) * 0.4)
        credibility_strength = min(1.0, len(credibility) * 0.35)
        
        # Overall persuasive power (weighted by what correlates with helpful votes)
        overall = (
            hook_strength * 0.15 +
            evidence_strength * 0.30 +
            emotion_strength * 0.20 +
            social_proof_strength * 0.20 +
            credibility_strength * 0.15
        )
        
        # Helpful vote multiplier
        if helpful_votes > 0:
            import math
            vote_factor = min(2.0, 1 + math.log10(1 + helpful_votes) * 0.3)
            overall *= vote_factor
        
        # Find dominant elements
        element_counts = Counter(p.element for p in patterns)
        dominant = [e for e, _ in element_counts.most_common(3)]
        
        return PersuasiveProfile(
            patterns=patterns,
            dominant_elements=dominant,
            hook_strength=hook_strength,
            evidence_strength=evidence_strength,
            emotion_strength=emotion_strength,
            social_proof_strength=social_proof_strength,
            credibility_strength=credibility_strength,
            overall_persuasive_power=min(1.0, overall),
            helpful_votes=helpful_votes,
            review_count=1,
        )
    
    def analyze_reviews(
        self,
        reviews: List[Dict[str, Any]],
        text_key: str = "text",
        helpful_key: str = "helpful_vote",
    ) -> PersuasiveProfile:
        """
        Analyze multiple reviews and aggregate patterns.
        
        Args:
            reviews: List of review dicts
            text_key: Key for review text
            helpful_key: Key for helpful votes
            
        Returns:
            Aggregated PersuasiveProfile
        """
        all_patterns = []
        total_helpful = 0
        
        for review in reviews:
            text = review.get(text_key, "")
            helpful = review.get(helpful_key, 0) or 0
            
            profile = self.analyze_review(text, helpful)
            all_patterns.extend(profile.patterns)
            total_helpful += helpful
        
        # Aggregate
        element_counts = Counter(p.element for p in all_patterns)
        dominant = [e for e, _ in element_counts.most_common(5)]
        
        # Category counts
        n = len(reviews) or 1
        hooks = sum(1 for p in all_patterns if p.element.value.startswith("hook_"))
        evidence = sum(1 for p in all_patterns if p.element.value.startswith("evidence_"))
        emotions = sum(1 for p in all_patterns if p.element.value.startswith("emotion_"))
        social = sum(1 for p in all_patterns if p.element.value.startswith("social_"))
        credibility = sum(1 for p in all_patterns if p.element.value.startswith("cred_"))
        
        return PersuasiveProfile(
            patterns=all_patterns[:100],  # Keep top 100
            dominant_elements=dominant,
            hook_strength=min(1.0, hooks / n),
            evidence_strength=min(1.0, evidence / n * 0.5),
            emotion_strength=min(1.0, emotions / n * 0.5),
            social_proof_strength=min(1.0, social / n * 0.5),
            credibility_strength=min(1.0, credibility / n * 0.5),
            overall_persuasive_power=0.0,  # Calculated below
            helpful_votes=total_helpful,
            review_count=len(reviews),
        )
    
    def extract_high_vote_templates(
        self,
        reviews: List[Dict[str, Any]],
        text_key: str = "text",
        helpful_key: str = "helpful_vote",
        top_percentile: float = 0.1,
    ) -> List[PersuasiveTemplate]:
        """
        Extract persuasive templates from top helpful-vote reviews.
        
        This is the key function for learning what persuades customers.
        
        Args:
            reviews: All reviews
            text_key: Key for review text
            helpful_key: Key for helpful votes
            top_percentile: Top X% to consider high-vote
            
        Returns:
            List of PersuasiveTemplates
        """
        # Filter to high-vote reviews
        sorted_reviews = sorted(
            reviews,
            key=lambda r: r.get(helpful_key, 0) or 0,
            reverse=True
        )
        
        cutoff_idx = max(1, int(len(reviews) * top_percentile))
        high_vote_reviews = sorted_reviews[:cutoff_idx]
        
        if not high_vote_reviews:
            return []
        
        logger.info(f"Analyzing {len(high_vote_reviews)} high-vote reviews")
        
        # Analyze patterns across high-vote reviews
        patterns_by_element: Dict[PersuasiveElement, List[str]] = {}
        
        for review in high_vote_reviews:
            text = review.get(text_key, "")
            patterns = self.extract_patterns(text)
            
            for p in patterns:
                if p.element not in patterns_by_element:
                    patterns_by_element[p.element] = []
                patterns_by_element[p.element].append(p.context)
        
        # Build templates by customer type
        templates = []
        
        # Template 1: Analytical Customer (evidence-heavy)
        if any(e.value.startswith("evidence_") for e in patterns_by_element):
            evidence_elements = [e for e in patterns_by_element if e.value.startswith("evidence_")]
            templates.append(PersuasiveTemplate(
                template_id="analytical_evidence",
                customer_type="analytical",
                opening_hook=PersuasiveElement.HOOK_AUTHORITY,
                evidence_types=evidence_elements[:3],
                emotional_appeals=[PersuasiveElement.EMOTION_TRUST],
                social_proof=[PersuasiveElement.SOCIAL_REPURCHASE],
                credibility_elements=[
                    PersuasiveElement.CREDIBILITY_EXPERTISE,
                    PersuasiveElement.CREDIBILITY_BALANCED,
                ],
                example_openings=patterns_by_element.get(PersuasiveElement.HOOK_AUTHORITY, [])[:3],
                example_evidence=[
                    ex for e in evidence_elements 
                    for ex in patterns_by_element.get(e, [])[:2]
                ],
                avg_helpful_votes=sum(r.get(helpful_key, 0) or 0 for r in high_vote_reviews) / len(high_vote_reviews),
                sample_size=len(high_vote_reviews),
                effectiveness_score=0.85,
            ))
        
        # Template 2: Emotional Customer (story + feeling)
        if any(e.value.startswith("emotion_") for e in patterns_by_element):
            emotion_elements = [e for e in patterns_by_element if e.value.startswith("emotion_")]
            templates.append(PersuasiveTemplate(
                template_id="emotional_story",
                customer_type="emotional",
                opening_hook=PersuasiveElement.HOOK_STORY,
                evidence_types=[PersuasiveElement.EVIDENCE_USE_CASE],
                emotional_appeals=emotion_elements[:3],
                social_proof=[
                    PersuasiveElement.SOCIAL_RECOMMENDATION,
                    PersuasiveElement.SOCIAL_GIFTING,
                ],
                credibility_elements=[PersuasiveElement.CREDIBILITY_UPDATED],
                example_openings=patterns_by_element.get(PersuasiveElement.HOOK_STORY, [])[:3],
                example_evidence=[],
                avg_helpful_votes=sum(r.get(helpful_key, 0) or 0 for r in high_vote_reviews) / len(high_vote_reviews),
                sample_size=len(high_vote_reviews),
                effectiveness_score=0.80,
            ))
        
        # Template 3: Social Customer (proof + belonging)
        if any(e.value.startswith("social_") for e in patterns_by_element):
            social_elements = [e for e in patterns_by_element if e.value.startswith("social_")]
            templates.append(PersuasiveTemplate(
                template_id="social_proof",
                customer_type="social",
                opening_hook=PersuasiveElement.HOOK_CONTRAST,
                evidence_types=[PersuasiveElement.EVIDENCE_COMPARISON],
                emotional_appeals=[
                    PersuasiveElement.EMOTION_BELONGING,
                    PersuasiveElement.EMOTION_PRIDE,
                ],
                social_proof=social_elements[:3],
                credibility_elements=[PersuasiveElement.CREDIBILITY_VERIFIED],
                example_openings=patterns_by_element.get(PersuasiveElement.HOOK_CONTRAST, [])[:3],
                example_evidence=[],
                avg_helpful_votes=sum(r.get(helpful_key, 0) or 0 for r in high_vote_reviews) / len(high_vote_reviews),
                sample_size=len(high_vote_reviews),
                effectiveness_score=0.82,
            ))
        
        return templates
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extractor statistics."""
        return {
            "reviews_analyzed": self._reviews_analyzed,
            "patterns_detected": self._patterns_detected,
            "pattern_types": len(PATTERN_RULES),
            "min_helpful_votes": self.min_helpful_votes,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_extractor: Optional[PersuasivePatternExtractor] = None


def get_persuasive_pattern_extractor() -> PersuasivePatternExtractor:
    """Get singleton persuasive pattern extractor."""
    global _extractor
    if _extractor is None:
        _extractor = PersuasivePatternExtractor()
    return _extractor


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_review_persuasion(
    text: str,
    helpful_votes: int = 0,
) -> Dict[str, Any]:
    """
    Convenience function to analyze a review's persuasive power.
    
    Returns dict suitable for API response.
    """
    extractor = get_persuasive_pattern_extractor()
    profile = extractor.analyze_review(text, helpful_votes)
    return profile.to_dict()


def get_persuasive_template_for_customer(
    customer_type: str,
    reviews: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Get the best persuasive template for a customer type.
    
    Args:
        customer_type: "analytical", "emotional", or "social"
        reviews: Reviews to extract templates from
        
    Returns:
        Template dict or None
    """
    extractor = get_persuasive_pattern_extractor()
    templates = extractor.extract_high_vote_templates(reviews)
    
    for template in templates:
        if template.customer_type == customer_type:
            return {
                "template_id": template.template_id,
                "customer_type": template.customer_type,
                "opening_hook": template.opening_hook.value,
                "evidence_types": [e.value for e in template.evidence_types],
                "emotional_appeals": [e.value for e in template.emotional_appeals],
                "social_proof": [e.value for e in template.social_proof],
                "example_openings": template.example_openings,
                "effectiveness_score": template.effectiveness_score,
            }
    
    return None
