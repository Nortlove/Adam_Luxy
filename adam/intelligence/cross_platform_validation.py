#!/usr/bin/env python3
"""
CROSS-PLATFORM VALIDATION MODULE
================================

Uses Amazon-Reddit matched data to detect authentic psychological patterns
by comparing how the same users express opinions across platforms.

Key Insight:
    When someone reviews a product on Amazon AND discusses it on Reddit,
    the overlapping psychology is highly authentic - they weren't gaming
    either platform, they genuinely care. This creates our "gold standard"
    for psychological pattern validation.

Integration Points:
- LangGraph: prefetch_cross_platform_validation node
- AoT: ReviewAnalysisAtom (validation), PsychologicalExtraction (confidence boost)
- Neo4j: CrossPlatformUser nodes, PlatformExpression relationships
- Learning: Confidence calibration for psychological patterns

The 3,750+ Granular Customer Types get enriched with:
- cross_platform_confidence: How well the type pattern holds across platforms
- platform_expression_variance: How expression differs by platform
- authenticity_boost: Additional confidence for cross-validated patterns
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CrossPlatformProfile:
    """
    Psychological profile validated across multiple platforms.
    
    Users who express consistent patterns across Amazon and Reddit
    are showing authentic psychology, not platform-specific gaming.
    """
    user_id: str
    amazon_reviews: int = 0
    reddit_posts: int = 0
    
    # Consistent patterns across platforms
    consistent_motivations: List[str] = field(default_factory=list)
    consistent_decision_style: Optional[str] = None
    consistent_emotional_intensity: Optional[str] = None
    
    # Platform-specific expression differences
    amazon_formality: float = 0.0  # Higher = more formal
    reddit_formality: float = 0.0
    expression_variance: float = 0.0  # How much they differ
    
    # Validation metrics
    pattern_consistency_score: float = 0.0  # 0-1, how stable across platforms
    authenticity_confidence: float = 0.0    # 0-1, how authentic


@dataclass
class PlatformExpression:
    """
    How psychological dimensions are expressed on different platforms.
    
    Same person, same product, different context = different expression.
    """
    dimension: str  # e.g., "motivation", "decision_style"
    amazon_value: str
    reddit_value: str
    is_consistent: bool
    consistency_score: float  # 0-1


@dataclass
class ValidationResult:
    """
    Result of cross-platform validation for a pattern.
    """
    pattern_name: str
    is_validated: bool
    confidence_boost: float  # How much to increase confidence
    cross_platform_consistency: float  # 0-1
    sample_size: int  # Number of cross-platform users supporting this
    platform_variance: Dict[str, float]  # How pattern varies by platform


# =============================================================================
# PLATFORM EXPRESSION PATTERNS
# =============================================================================

# How psychological patterns are expressed differently across platforms
PLATFORM_EXPRESSION_MAPPING = {
    "motivation": {
        # Amazon tends to be more product-focused, Reddit more social
        "functional_need": {
            "amazon_signals": ["need", "required", "necessary", "had to"],
            "reddit_signals": ["needed something for", "looking for", "requirements"],
            "consistency_expected": 0.85,  # High consistency
        },
        "impulse": {
            "amazon_signals": ["impulse", "couldn't resist", "just had to"],
            "reddit_signals": ["bought on impulse", "retail therapy", "treat yourself"],
            "consistency_expected": 0.70,  # Medium - Reddit more honest about impulse
        },
        "social_proof": {
            "amazon_signals": ["everyone", "popular", "recommended"],
            "reddit_signals": ["everyone here recommends", "hive mind", "consensus"],
            "consistency_expected": 0.60,  # Reddit more explicit about social influence
        },
        "quality_seeking": {
            "amazon_signals": ["quality", "premium", "well-made", "durability"],
            "reddit_signals": ["buy once cry once", "BIFL", "worth the investment"],
            "consistency_expected": 0.75,
        },
        "value_seeking": {
            "amazon_signals": ["deal", "bargain", "price", "value", "worth"],
            "reddit_signals": ["budget", "cheap but good", "bang for buck", "value pick"],
            "consistency_expected": 0.80,
        },
    },
    "decision_style": {
        "deliberate": {
            "amazon_signals": ["researched", "compared", "studied", "analysis"],
            "reddit_signals": ["did my research", "spreadsheet", "compared specs"],
            "consistency_expected": 0.85,  # Research-driven people are consistent
        },
        "fast": {
            "amazon_signals": ["quickly", "immediate", "right away"],
            "reddit_signals": ["just got it", "pulled the trigger", "ordered"],
            "consistency_expected": 0.65,
        },
        "moderate": {
            "amazon_signals": [],  # Less distinctive signals
            "reddit_signals": [],
            "consistency_expected": 0.50,  # Baseline
        },
    },
    "emotional_intensity": {
        "high": {
            "amazon_signals": ["love", "hate", "amazing", "terrible", "!!!"],
            "reddit_signals": ["love", "hate", "obsessed", "can't stand"],
            "consistency_expected": 0.75,
        },
        "low": {
            "amazon_signals": ["adequate", "acceptable", "sufficient", "works"],
            "reddit_signals": ["it's fine", "does the job", "nothing special"],
            "consistency_expected": 0.70,
        },
    },
}

# Patterns that are platform-specific (not cross-validated)
PLATFORM_SPECIFIC_PATTERNS = {
    "amazon": [
        "verified_purchase_mention",
        "star_rating_explicit",
        "seller_feedback",
    ],
    "reddit": [
        "subreddit_jargon",
        "upvote_seeking",
        "community_reference",
    ],
}

# Cross-platform confidence boosts
CONFIDENCE_BOOSTS = {
    "motivation_consistent": 0.25,     # +25% confidence when motivation matches
    "decision_style_consistent": 0.20,  # +20% for decision style
    "emotional_intensity_consistent": 0.15,
    "full_profile_consistent": 0.35,   # +35% when whole profile matches
}


# =============================================================================
# CROSS-PLATFORM ANALYZER
# =============================================================================

class CrossPlatformAnalyzer:
    """
    Analyze and validate patterns across Amazon and Reddit.
    """
    
    def __init__(self):
        self._compiled_patterns: Dict[str, Dict[str, List[re.Pattern]]] = {}
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        for dimension, values in PLATFORM_EXPRESSION_MAPPING.items():
            self._compiled_patterns[dimension] = {}
            for value_name, value_patterns in values.items():
                self._compiled_patterns[dimension][value_name] = {
                    "amazon": [
                        re.compile(rf"\b{p}\b", re.I) 
                        for p in value_patterns.get("amazon_signals", [])
                    ],
                    "reddit": [
                        re.compile(rf"\b{p}\b", re.I)
                        for p in value_patterns.get("reddit_signals", [])
                    ],
                }
    
    def detect_platform_style(self, text: str) -> str:
        """
        Detect which platform a text likely came from.
        
        Args:
            text: The text to analyze
            
        Returns:
            "amazon", "reddit", or "unknown"
        """
        amazon_score = 0
        reddit_score = 0
        
        # Amazon indicators
        amazon_indicators = [
            r"\bverified\s+purchase\b",
            r"\bstars?\b",
            r"\bseller\b",
            r"\bpackaging\b",
            r"\bdelivery\b",
            r"\b\d+/\d+\s*stars?\b",
        ]
        
        # Reddit indicators
        reddit_indicators = [
            r"\bOP\b",
            r"\br/\w+\b",
            r"\bEDIT:\b",
            r"\bIMO\b",
            r"\bTL;DR\b",
            r"\bupvote\b",
            r"\bdownvote\b",
        ]
        
        for pattern in amazon_indicators:
            if re.search(pattern, text, re.I):
                amazon_score += 1
        
        for pattern in reddit_indicators:
            if re.search(pattern, text, re.I):
                reddit_score += 1
        
        if amazon_score > reddit_score:
            return "amazon"
        elif reddit_score > amazon_score:
            return "reddit"
        else:
            return "unknown"
    
    def detect_dimension_value(
        self,
        text: str,
        dimension: str,
        platform: str = "unknown"
    ) -> Tuple[Optional[str], float]:
        """
        Detect the value of a psychological dimension from text.
        
        Args:
            text: The text to analyze
            dimension: Which dimension ("motivation", "decision_style", etc.)
            platform: Which platform ("amazon", "reddit", "unknown")
            
        Returns:
            Tuple of (detected_value, confidence)
        """
        if dimension not in self._compiled_patterns:
            return None, 0.0
        
        scores = {}
        
        for value_name, patterns in self._compiled_patterns[dimension].items():
            score = 0
            
            # Check platform-specific patterns
            if platform in patterns:
                for pattern in patterns[platform]:
                    if pattern.search(text):
                        score += 1
            
            # Also check other platform patterns (less weight)
            other_platform = "reddit" if platform == "amazon" else "amazon"
            if other_platform in patterns:
                for pattern in patterns[other_platform]:
                    if pattern.search(text):
                        score += 0.5
            
            if score > 0:
                scores[value_name] = score
        
        if not scores:
            return None, 0.0
        
        # Return highest scoring value
        best_value = max(scores.keys(), key=lambda k: scores[k])
        max_possible = len(self._compiled_patterns[dimension].get(best_value, {}).get(platform, [])) + 1
        confidence = min(scores[best_value] / max_possible, 1.0)
        
        return best_value, confidence
    
    def compare_expressions(
        self,
        amazon_text: str,
        reddit_text: str,
    ) -> List[PlatformExpression]:
        """
        Compare psychological expression across platforms.
        
        Args:
            amazon_text: Text from Amazon review
            reddit_text: Text from Reddit post
            
        Returns:
            List of PlatformExpression comparisons
        """
        results = []
        
        for dimension in PLATFORM_EXPRESSION_MAPPING.keys():
            amazon_value, amazon_conf = self.detect_dimension_value(
                amazon_text, dimension, "amazon"
            )
            reddit_value, reddit_conf = self.detect_dimension_value(
                reddit_text, dimension, "reddit"
            )
            
            if amazon_value or reddit_value:
                is_consistent = amazon_value == reddit_value
                
                # Get expected consistency
                if amazon_value in PLATFORM_EXPRESSION_MAPPING.get(dimension, {}):
                    expected = PLATFORM_EXPRESSION_MAPPING[dimension][amazon_value].get(
                        "consistency_expected", 0.5
                    )
                else:
                    expected = 0.5
                
                consistency_score = 1.0 if is_consistent else (1.0 - expected)
                
                results.append(PlatformExpression(
                    dimension=dimension,
                    amazon_value=amazon_value or "unknown",
                    reddit_value=reddit_value or "unknown",
                    is_consistent=is_consistent,
                    consistency_score=consistency_score,
                ))
        
        return results


# =============================================================================
# CROSS-PLATFORM VALIDATION SERVICE
# =============================================================================

class CrossPlatformValidationService:
    """
    Service for cross-platform validation.
    
    Uses Amazon-Reddit matched data to validate psychological patterns
    and boost confidence in authentically-expressed patterns.
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the cross-platform service.
        
        Args:
            data_path: Path to Amazon-Reddit matched data
        """
        self._analyzer = CrossPlatformAnalyzer()
        self._loaded = False
        self._validated_patterns: Dict[str, ValidationResult] = {}
        
        if data_path:
            self._load_validation_data(data_path)
    
    def _load_validation_data(self, path: str) -> None:
        """Load pre-computed validation data."""
        try:
            path = Path(path)
            
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
                    for pattern_name, validation in data.get('validations', {}).items():
                        self._validated_patterns[pattern_name] = ValidationResult(
                            pattern_name=pattern_name,
                            **validation
                        )
                self._loaded = True
                logger.info(f"Loaded {len(self._validated_patterns)} validated patterns")
                
        except Exception as e:
            logger.warning(f"Could not load validation data: {e}")
    
    def validate_pattern(
        self,
        pattern_name: str,
        amazon_texts: List[str],
        reddit_texts: List[str],
    ) -> ValidationResult:
        """
        Validate a psychological pattern across platforms.
        
        Args:
            pattern_name: Name of the pattern to validate
            amazon_texts: Sample Amazon texts showing this pattern
            reddit_texts: Sample Reddit texts from same users
            
        Returns:
            ValidationResult
        """
        if not amazon_texts or not reddit_texts:
            return ValidationResult(
                pattern_name=pattern_name,
                is_validated=False,
                confidence_boost=0.0,
                cross_platform_consistency=0.0,
                sample_size=0,
                platform_variance={},
            )
        
        consistencies = []
        platform_variances = {"amazon": [], "reddit": []}
        
        for amazon_text, reddit_text in zip(amazon_texts, reddit_texts):
            expressions = self._analyzer.compare_expressions(amazon_text, reddit_text)
            
            for expr in expressions:
                if pattern_name.startswith(expr.dimension):
                    consistencies.append(expr.consistency_score)
        
        if not consistencies:
            return ValidationResult(
                pattern_name=pattern_name,
                is_validated=False,
                confidence_boost=0.0,
                cross_platform_consistency=0.0,
                sample_size=len(amazon_texts),
                platform_variance={},
            )
        
        avg_consistency = sum(consistencies) / len(consistencies)
        is_validated = avg_consistency >= 0.6
        
        # Calculate confidence boost
        if is_validated:
            # Higher consistency = higher boost
            base_boost = CONFIDENCE_BOOSTS.get(
                f"{pattern_name.split('_')[0]}_consistent", 0.15
            )
            confidence_boost = base_boost * avg_consistency
        else:
            confidence_boost = 0.0
        
        return ValidationResult(
            pattern_name=pattern_name,
            is_validated=is_validated,
            confidence_boost=confidence_boost,
            cross_platform_consistency=avg_consistency,
            sample_size=len(amazon_texts),
            platform_variance={
                "amazon": sum(platform_variances["amazon"]) / len(platform_variances["amazon"]) if platform_variances["amazon"] else 0,
                "reddit": sum(platform_variances["reddit"]) / len(platform_variances["reddit"]) if platform_variances["reddit"] else 0,
            },
        )
    
    def get_confidence_boost(
        self,
        motivation: str,
        decision_style: str,
        emotional_intensity: str,
    ) -> float:
        """
        Get confidence boost for a granular type based on cross-platform validation.
        
        Args:
            motivation: Motivation dimension value
            decision_style: Decision style value
            emotional_intensity: Emotional intensity value
            
        Returns:
            Confidence boost (0-1, to be added to base confidence)
        """
        # Check pre-validated patterns
        pattern_key = f"{motivation}_{decision_style}_{emotional_intensity}"
        
        if pattern_key in self._validated_patterns:
            return self._validated_patterns[pattern_key].confidence_boost
        
        # Calculate from known consistency expectations
        total_boost = 0.0
        
        # Motivation boost
        if motivation in PLATFORM_EXPRESSION_MAPPING.get("motivation", {}):
            expected = PLATFORM_EXPRESSION_MAPPING["motivation"][motivation].get(
                "consistency_expected", 0.5
            )
            total_boost += CONFIDENCE_BOOSTS["motivation_consistent"] * expected
        
        # Decision style boost
        if decision_style in PLATFORM_EXPRESSION_MAPPING.get("decision_style", {}):
            expected = PLATFORM_EXPRESSION_MAPPING["decision_style"][decision_style].get(
                "consistency_expected", 0.5
            )
            total_boost += CONFIDENCE_BOOSTS["decision_style_consistent"] * expected
        
        # Emotional intensity boost
        if emotional_intensity in PLATFORM_EXPRESSION_MAPPING.get("emotional_intensity", {}):
            expected = PLATFORM_EXPRESSION_MAPPING["emotional_intensity"][emotional_intensity].get(
                "consistency_expected", 0.5
            )
            total_boost += CONFIDENCE_BOOSTS["emotional_intensity_consistent"] * expected
        
        return min(total_boost, 0.35)  # Cap at full profile consistent boost
    
    def analyze_user_consistency(
        self,
        amazon_reviews: List[str],
        reddit_posts: List[str],
    ) -> CrossPlatformProfile:
        """
        Analyze consistency of a user across platforms.
        
        Args:
            amazon_reviews: User's Amazon reviews
            reddit_posts: User's Reddit posts
            
        Returns:
            CrossPlatformProfile
        """
        if not amazon_reviews or not reddit_posts:
            return CrossPlatformProfile(
                user_id="anonymous",
                amazon_reviews=len(amazon_reviews),
                reddit_posts=len(reddit_posts),
            )
        
        # Detect patterns in each platform
        amazon_patterns = {"motivation": [], "decision_style": [], "emotional_intensity": []}
        reddit_patterns = {"motivation": [], "decision_style": [], "emotional_intensity": []}
        
        for text in amazon_reviews:
            for dim in amazon_patterns.keys():
                value, conf = self._analyzer.detect_dimension_value(text, dim, "amazon")
                if value and conf > 0.3:
                    amazon_patterns[dim].append(value)
        
        for text in reddit_posts:
            for dim in reddit_patterns.keys():
                value, conf = self._analyzer.detect_dimension_value(text, dim, "reddit")
                if value and conf > 0.3:
                    reddit_patterns[dim].append(value)
        
        # Find consistent patterns
        consistent_motivations = list(
            set(amazon_patterns["motivation"]) & set(reddit_patterns["motivation"])
        )
        
        # Most common decision style
        all_decision = amazon_patterns["decision_style"] + reddit_patterns["decision_style"]
        consistent_decision = max(set(all_decision), key=all_decision.count) if all_decision else None
        
        # Most common emotional intensity
        all_emotional = amazon_patterns["emotional_intensity"] + reddit_patterns["emotional_intensity"]
        consistent_emotional = max(set(all_emotional), key=all_emotional.count) if all_emotional else None
        
        # Calculate consistency score
        total_patterns = sum(len(v) for v in amazon_patterns.values())
        consistent_patterns = len(consistent_motivations) + (1 if consistent_decision else 0) + (1 if consistent_emotional else 0)
        consistency_score = consistent_patterns / max(total_patterns, 1)
        
        # Formality comparison
        amazon_formality = self._calculate_formality(amazon_reviews)
        reddit_formality = self._calculate_formality(reddit_posts)
        
        return CrossPlatformProfile(
            user_id="anonymous",
            amazon_reviews=len(amazon_reviews),
            reddit_posts=len(reddit_posts),
            consistent_motivations=consistent_motivations,
            consistent_decision_style=consistent_decision,
            consistent_emotional_intensity=consistent_emotional,
            amazon_formality=amazon_formality,
            reddit_formality=reddit_formality,
            expression_variance=abs(amazon_formality - reddit_formality),
            pattern_consistency_score=consistency_score,
            authenticity_confidence=0.5 + consistency_score * 0.4,
        )
    
    def _calculate_formality(self, texts: List[str]) -> float:
        """Calculate formality score of texts."""
        if not texts:
            return 0.5
        
        informal_markers = [
            r"\blol\b", r"\bhaha\b", r"\bomg\b", r"\bbtw\b", r"\bidk\b",
            r"!", r"\.\.\.", r"gonna", r"wanna", r"kinda", r"sorta",
        ]
        
        formal_markers = [
            r"\bhowever\b", r"\bfurthermore\b", r"\btherefore\b",
            r"\bpurchase\b", r"\bproduct\b", r"\bquality\b",
        ]
        
        total_text = " ".join(texts)
        
        informal_count = sum(
            len(re.findall(p, total_text, re.I)) for p in informal_markers
        )
        formal_count = sum(
            len(re.findall(p, total_text, re.I)) for p in formal_markers
        )
        
        total = informal_count + formal_count
        if total == 0:
            return 0.5
        
        return formal_count / total


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_cross_platform_service: Optional[CrossPlatformValidationService] = None


def get_cross_platform_service(
    data_path: Optional[str] = None
) -> CrossPlatformValidationService:
    """
    Get the singleton cross-platform validation service.
    
    Args:
        data_path: Optional path to Amazon-Reddit matched data
        
    Returns:
        CrossPlatformValidationService instance
    """
    global _cross_platform_service
    
    if _cross_platform_service is None:
        if data_path is None:
            default_paths = [
                "/Volumes/Sped/new_reviews_and_data/hf_datasets/amazon_reddit",
                "data/learning/cross_platform_validation.json",
            ]
            for path in default_paths:
                if Path(path).exists():
                    data_path = path
                    break
        
        _cross_platform_service = CrossPlatformValidationService(data_path)
        logger.info("Cross-platform validation service initialized")
    
    return _cross_platform_service


# =============================================================================
# COLD-START PRIORS EXPORT
# =============================================================================

def export_cross_platform_priors() -> Dict[str, Any]:
    """
    Export cross-platform validation data for cold-start priors.
    
    Returns:
        Dict suitable for adding to complete_coldstart_priors.json
    """
    return {
        "cross_platform_validation": {
            "platform_expression_mapping": {
                dimension: {
                    value: {
                        "consistency_expected": info["consistency_expected"],
                        "amazon_signals": info.get("amazon_signals", []),
                        "reddit_signals": info.get("reddit_signals", []),
                    }
                    for value, info in values.items()
                }
                for dimension, values in PLATFORM_EXPRESSION_MAPPING.items()
            },
            "confidence_boosts": CONFIDENCE_BOOSTS,
            "version": "1.0",
            "source": "McAuley-Lab/Amazon-Reddit-Matched-with-Meta",
        }
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = get_cross_platform_service()
    
    print("\n" + "="*60)
    print("CROSS-PLATFORM VALIDATION TEST")
    print("="*60)
    
    # Test confidence boosts for different types
    test_types = [
        ("functional_need", "deliberate", "low"),
        ("impulse", "fast", "high"),
        ("quality_seeking", "moderate", "moderate"),
        ("research_driven", "deliberate", "low"),
    ]
    
    for motivation, decision, emotional in test_types:
        boost = service.get_confidence_boost(motivation, decision, emotional)
        print(f"\n{motivation} / {decision} / {emotional}")
        print(f"  Cross-platform confidence boost: +{boost:.0%}")
    
    # Test expression comparison
    print("\n" + "-"*40)
    print("EXPRESSION COMPARISON TEST")
    
    amazon_text = "After extensive research comparing multiple models, I chose this for its quality and durability. The build quality is excellent."
    reddit_text = "Did my research and went with this one. BIFL quality, worth the investment IMO."
    
    analyzer = CrossPlatformAnalyzer()
    expressions = analyzer.compare_expressions(amazon_text, reddit_text)
    
    print(f"\nAmazon: {amazon_text[:50]}...")
    print(f"Reddit: {reddit_text[:50]}...")
    
    for expr in expressions:
        print(f"\n  {expr.dimension}:")
        print(f"    Amazon: {expr.amazon_value}")
        print(f"    Reddit: {expr.reddit_value}")
        print(f"    Consistent: {expr.is_consistent}")
        print(f"    Score: {expr.consistency_score:.0%}")
