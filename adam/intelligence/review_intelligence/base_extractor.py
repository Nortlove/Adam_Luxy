"""
Base Review Intelligence Extractor
==================================

The foundation for all dataset-specific extractors.

Each dataset extractor MUST implement:
1. extract_psychological_signals() - Pull psychological indicators
2. extract_persuasive_patterns() - Find what language persuades
3. extract_contextual_intelligence() - Build context -> psychology mappings
4. get_ecosystem_outputs() - Format for DSP/SSP/Agency consumption
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Iterator, Tuple
from enum import Enum
import logging
from pathlib import Path

from . import (
    DataSource,
    IntelligenceLayer,
    PsychologicalSignal,
    AudienceSegment,
    ContextualSignal,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PSYCHOLOGICAL CONSTRUCTS (The 35 we extract)
# =============================================================================

class PsychologicalConstruct(str, Enum):
    """The 35 psychological constructs ADAM extracts and models."""
    
    # Tier 1: Customer Susceptibility (13)
    SOCIAL_PROOF_SUSCEPTIBILITY = "social_proof_susceptibility"
    SCARCITY_SUSCEPTIBILITY = "scarcity_susceptibility"
    AUTHORITY_SUSCEPTIBILITY = "authority_susceptibility"
    RECIPROCITY_SUSCEPTIBILITY = "reciprocity_susceptibility"
    COMMITMENT_SUSCEPTIBILITY = "commitment_susceptibility"
    LIKING_SUSCEPTIBILITY = "liking_susceptibility"
    UNITY_SUSCEPTIBILITY = "unity_susceptibility"
    FOMO_SUSCEPTIBILITY = "fomo_susceptibility"
    NOVELTY_SEEKING = "novelty_seeking"
    PRICE_SENSITIVITY = "price_sensitivity"
    BRAND_LOYALTY_TENDENCY = "brand_loyalty_tendency"
    IMPULSE_TENDENCY = "impulse_tendency"
    DELIBERATION_TENDENCY = "deliberation_tendency"
    
    # Tier 2: Message Crafting (12)
    REGULATORY_FOCUS = "regulatory_focus"  # promotion vs prevention
    CONSTRUAL_LEVEL = "construal_level"  # abstract vs concrete
    SELF_CONSTRUAL = "self_construal"  # independent vs interdependent
    COGNITIVE_STYLE = "cognitive_style"  # analytical vs intuitive
    NARRATIVE_PREFERENCE = "narrative_preference"  # story vs facts
    JUSTIFICATION_STYLE = "justification_style"  # rational vs emotional
    TEMPORAL_ORIENTATION = "temporal_orientation"  # past/present/future
    RISK_ORIENTATION = "risk_orientation"  # seeking vs averse
    AUTHORITY_ORIENTATION = "authority_orientation"  # trust vs skepticism
    SOCIAL_COMPARISON = "social_comparison"  # upward vs downward
    NEED_FOR_UNIQUENESS = "need_for_uniqueness"
    NEED_FOR_BELONGING = "need_for_belonging"
    
    # Tier 3: Brand-Customer Matching (10)
    SINCERITY_ALIGNMENT = "sincerity_alignment"  # Aaker
    EXCITEMENT_ALIGNMENT = "excitement_alignment"
    COMPETENCE_ALIGNMENT = "competence_alignment"
    SOPHISTICATION_ALIGNMENT = "sophistication_alignment"
    RUGGEDNESS_ALIGNMENT = "ruggedness_alignment"
    OPENNESS = "openness"  # Big Five
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


# =============================================================================
# ARCHETYPE DEFINITIONS
# =============================================================================

class Archetype(str, Enum):
    """The 12 Jungian brand archetypes."""
    INNOCENT = "innocent"
    SAGE = "sage"
    EXPLORER = "explorer"
    OUTLAW = "outlaw"
    MAGICIAN = "magician"
    HERO = "hero"
    LOVER = "lover"
    JESTER = "jester"
    EVERYMAN = "everyman"
    CAREGIVER = "caregiver"
    RULER = "ruler"
    CREATOR = "creator"


# =============================================================================
# PERSUASION MECHANISMS
# =============================================================================

class PersuasionMechanism(str, Enum):
    """Cialdini + extended persuasion mechanisms."""
    # Cialdini's 7
    SOCIAL_PROOF = "social_proof"
    SCARCITY = "scarcity"
    AUTHORITY = "authority"
    RECIPROCITY = "reciprocity"
    COMMITMENT_CONSISTENCY = "commitment_consistency"
    LIKING = "liking"
    UNITY = "unity"
    
    # Extended mechanisms
    STORYTELLING = "storytelling"
    FEAR_APPEAL = "fear_appeal"
    HUMOR = "humor"
    NOSTALGIA = "nostalgia"
    ASPIRATION = "aspiration"
    CURIOSITY = "curiosity"
    EXCLUSIVITY = "exclusivity"
    URGENCY = "urgency"
    TRUST = "trust"
    AUTHENTICITY = "authenticity"
    VALUE_PROPOSITION = "value_proposition"
    EMOTIONAL_APPEAL = "emotional_appeal"
    LOGICAL_APPEAL = "logical_appeal"


# =============================================================================
# EXTRACTION RESULTS
# =============================================================================

@dataclass
class ExtractionResult:
    """Results from extracting intelligence from a review."""
    
    # Source identification
    review_id: str
    source: DataSource
    
    # Extracted constructs
    constructs: Dict[PsychologicalConstruct, float]  # construct -> score
    
    # Detected archetypes
    archetypes: Dict[Archetype, float]  # archetype -> probability
    
    # Mechanism receptivity
    mechanism_receptivity: Dict[PersuasionMechanism, float]
    
    # Persuasive patterns found
    persuasive_patterns: List[Dict[str, Any]]
    
    # Contextual signals
    context: Dict[str, Any]  # location, category, time, etc.
    
    # Quality metrics
    confidence: float
    text_quality: float  # How useful the text is for extraction


@dataclass
class AggregatedIntelligence:
    """Aggregated intelligence across many reviews."""
    
    # Aggregation scope
    scope_type: str  # "category", "location", "brand", "segment"
    scope_value: str
    source: DataSource
    sample_size: int
    
    # Aggregated construct scores
    construct_distributions: Dict[PsychologicalConstruct, Dict[str, float]]
    # e.g., {"social_proof_susceptibility": {"mean": 0.7, "std": 0.15, "median": 0.72}}
    
    # Archetype prevalence
    archetype_prevalence: Dict[Archetype, float]
    
    # Mechanism effectiveness
    mechanism_effectiveness: Dict[PersuasionMechanism, float]
    
    # Top persuasive templates
    top_templates: List[Dict[str, Any]]
    
    # Contextual patterns
    temporal_patterns: Optional[Dict[str, float]] = None
    geographic_patterns: Optional[Dict[str, float]] = None


# =============================================================================
# BASE EXTRACTOR
# =============================================================================

class BaseReviewExtractor(ABC):
    """
    Base class for all review intelligence extractors.
    
    Each dataset extractor inherits from this and implements
    the abstract methods to extract dataset-specific intelligence.
    """
    
    def __init__(
        self,
        data_source: DataSource,
        data_path: Path,
        batch_size: int = 1000,
    ):
        self.data_source = data_source
        self.data_path = data_path
        self.batch_size = batch_size
        
        # Initialize psychological marker detectors
        self._init_construct_markers()
        self._init_archetype_markers()
        self._init_mechanism_markers()
    
    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by each dataset extractor
    # =========================================================================
    
    @abstractmethod
    def iter_reviews(self) -> Iterator[Dict[str, Any]]:
        """Iterate over reviews in the dataset."""
        pass
    
    @abstractmethod
    def extract_review_text(self, review: Dict[str, Any]) -> str:
        """Extract the review text from a review record."""
        pass
    
    @abstractmethod
    def extract_rating(self, review: Dict[str, Any]) -> Optional[float]:
        """Extract the rating (normalized to 0-1 scale)."""
        pass
    
    @abstractmethod
    def extract_helpful_signal(self, review: Dict[str, Any]) -> Optional[float]:
        """Extract any helpful/useful vote signal (normalized to 0-1)."""
        pass
    
    @abstractmethod
    def extract_context(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contextual information (location, category, time, etc.)."""
        pass
    
    @abstractmethod
    def get_unique_value(self) -> str:
        """Return what makes this dataset uniquely valuable."""
        pass
    
    @abstractmethod
    def extract_dataset_specific_signals(
        self, review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract signals unique to this dataset."""
        pass
    
    # =========================================================================
    # ECOSYSTEM OUTPUT METHODS - Format for DSP/SSP/Agency
    # =========================================================================
    
    @abstractmethod
    def format_for_dsp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format intelligence for DSP consumption (StackAdapt, TTD).
        
        DSPs need:
        - Audience segments to target
        - Contextual signals for cookie-less targeting
        - Creative optimization recommendations
        """
        pass
    
    @abstractmethod
    def format_for_ssp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format intelligence for SSP consumption (iHeart).
        
        SSPs need:
        - Inventory value signals (what makes this slot valuable)
        - Audience composition data
        - Content affinity mappings
        """
        pass
    
    @abstractmethod
    def format_for_agency(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format intelligence for Agency consumption (WPP).
        
        Agencies need:
        - Strategic insights for campaign planning
        - Creative briefs informed by psychology
        - Cross-platform optimization recommendations
        """
        pass
    
    # =========================================================================
    # COMMON EXTRACTION METHODS
    # =========================================================================
    
    def extract_psychological_signals(
        self, review: Dict[str, Any]
    ) -> ExtractionResult:
        """
        Extract all psychological signals from a single review.
        
        This is the main extraction method that calls:
        1. Construct extraction
        2. Archetype detection
        3. Mechanism receptivity
        4. Persuasive pattern detection
        """
        text = self.extract_review_text(review)
        rating = self.extract_rating(review)
        helpful = self.extract_helpful_signal(review)
        context = self.extract_context(review)
        
        # Skip low-quality text
        if not text or len(text) < 20:
            return ExtractionResult(
                review_id=str(review.get("review_id", review.get("id", "unknown"))),
                source=self.data_source,
                constructs={},
                archetypes={},
                mechanism_receptivity={},
                persuasive_patterns=[],
                context=context,
                confidence=0.0,
                text_quality=0.0,
            )
        
        # Extract constructs
        constructs = self._extract_constructs(text, rating, helpful)
        
        # Detect archetypes
        archetypes = self._detect_archetypes(text, context)
        
        # Assess mechanism receptivity
        mechanism_receptivity = self._assess_mechanism_receptivity(
            text, rating, helpful, context
        )
        
        # Find persuasive patterns
        persuasive_patterns = self._extract_persuasive_patterns(
            text, rating, helpful
        )
        
        # Get dataset-specific signals
        specific_signals = self.extract_dataset_specific_signals(review)
        
        # Calculate confidence
        confidence = self._calculate_extraction_confidence(
            text, rating, helpful, constructs, archetypes
        )
        
        # Merge specific signals into context
        context.update(specific_signals)
        
        return ExtractionResult(
            review_id=str(review.get("review_id", review.get("id", "unknown"))),
            source=self.data_source,
            constructs=constructs,
            archetypes=archetypes,
            mechanism_receptivity=mechanism_receptivity,
            persuasive_patterns=persuasive_patterns,
            context=context,
            confidence=confidence,
            text_quality=min(1.0, len(text) / 500),  # Normalize by expected length
        )
    
    def aggregate_intelligence(
        self,
        results: List[ExtractionResult],
        scope_type: str,
        scope_value: str,
    ) -> AggregatedIntelligence:
        """Aggregate extraction results into intelligence."""
        if not results:
            return AggregatedIntelligence(
                scope_type=scope_type,
                scope_value=scope_value,
                source=self.data_source,
                sample_size=0,
                construct_distributions={},
                archetype_prevalence={},
                mechanism_effectiveness={},
                top_templates=[],
            )
        
        # Aggregate constructs
        construct_distributions = self._aggregate_constructs(results)
        
        # Aggregate archetypes
        archetype_prevalence = self._aggregate_archetypes(results)
        
        # Calculate mechanism effectiveness
        mechanism_effectiveness = self._calculate_mechanism_effectiveness(results)
        
        # Extract top templates
        top_templates = self._extract_top_templates(results)
        
        return AggregatedIntelligence(
            scope_type=scope_type,
            scope_value=scope_value,
            source=self.data_source,
            sample_size=len(results),
            construct_distributions=construct_distributions,
            archetype_prevalence=archetype_prevalence,
            mechanism_effectiveness=mechanism_effectiveness,
            top_templates=top_templates,
        )
    
    # =========================================================================
    # INTERNAL EXTRACTION METHODS
    # =========================================================================
    
    def _init_construct_markers(self):
        """Initialize linguistic markers for construct detection."""
        self.construct_markers = {
            PsychologicalConstruct.SOCIAL_PROOF_SUSCEPTIBILITY: {
                "positive": [
                    "everyone", "popular", "bestseller", "trending", "most people",
                    "others love", "highly rated", "recommended by", "trusted by",
                    "millions", "thousands", "reviews", "ratings"
                ],
                "negative": [
                    "don't care what others", "my own opinion", "regardless of reviews"
                ],
            },
            PsychologicalConstruct.SCARCITY_SUSCEPTIBILITY: {
                "positive": [
                    "limited", "rare", "exclusive", "only", "last chance",
                    "sold out", "hard to find", "special edition", "while supplies"
                ],
                "negative": [
                    "always available", "plenty", "no rush"
                ],
            },
            PsychologicalConstruct.AUTHORITY_SUSCEPTIBILITY: {
                "positive": [
                    "expert", "professional", "doctor", "scientist", "certified",
                    "award", "endorsed", "recommended by", "approved", "official"
                ],
                "negative": [
                    "don't trust experts", "do my own research", "skeptical"
                ],
            },
            PsychologicalConstruct.NOVELTY_SEEKING: {
                "positive": [
                    "new", "innovative", "unique", "different", "first",
                    "cutting edge", "latest", "never seen", "revolutionary"
                ],
                "negative": [
                    "classic", "traditional", "tried and true", "old school"
                ],
            },
            PsychologicalConstruct.PRICE_SENSITIVITY: {
                "positive": [
                    "expensive", "overpriced", "not worth", "cheaper", "deal",
                    "value", "budget", "affordable", "cost", "price"
                ],
                "negative": [
                    "worth every penny", "money well spent", "price doesn't matter"
                ],
            },
            PsychologicalConstruct.BRAND_LOYALTY_TENDENCY: {
                "positive": [
                    "always buy", "loyal", "favorite brand", "only brand",
                    "been using for years", "never switch", "trust this brand"
                ],
                "negative": [
                    "switching", "trying new", "brand doesn't matter"
                ],
            },
            PsychologicalConstruct.REGULATORY_FOCUS: {
                "promotion": [
                    "gain", "achieve", "success", "accomplish", "ideal",
                    "aspiration", "hope", "wish", "dream", "opportunity"
                ],
                "prevention": [
                    "avoid", "prevent", "protect", "safe", "secure",
                    "responsible", "ought", "should", "duty", "obligation"
                ],
            },
            PsychologicalConstruct.CONSTRUAL_LEVEL: {
                "abstract": [
                    "overall", "generally", "concept", "idea", "purpose",
                    "meaning", "why", "philosophy", "essence"
                ],
                "concrete": [
                    "specifically", "exactly", "detail", "step", "how",
                    "feature", "specification", "measurement"
                ],
            },
        }
    
    def _init_archetype_markers(self):
        """Initialize linguistic markers for archetype detection."""
        self.archetype_markers = {
            Archetype.INNOCENT: [
                "pure", "simple", "honest", "trust", "faith", "optimistic",
                "wholesome", "clean", "natural", "genuine"
            ],
            Archetype.SAGE: [
                "understand", "knowledge", "wisdom", "learn", "truth",
                "insight", "analyze", "research", "intelligent", "expert"
            ],
            Archetype.EXPLORER: [
                "adventure", "discover", "freedom", "journey", "explore",
                "authentic", "independent", "pioneer", "wanderlust"
            ],
            Archetype.OUTLAW: [
                "rebel", "break", "disrupt", "radical", "revolution",
                "different", "unconventional", "bold", "provocative"
            ],
            Archetype.MAGICIAN: [
                "transform", "magic", "dream", "vision", "create",
                "imagine", "miracle", "possibility", "spiritual"
            ],
            Archetype.HERO: [
                "challenge", "overcome", "achieve", "strength", "courage",
                "victory", "champion", "warrior", "compete", "win"
            ],
            Archetype.LOVER: [
                "love", "passion", "beautiful", "intimate", "sensual",
                "romantic", "desire", "indulge", "pleasure"
            ],
            Archetype.JESTER: [
                "fun", "laugh", "play", "enjoy", "humor", "joke",
                "entertaining", "lighthearted", "silly", "amusing"
            ],
            Archetype.EVERYMAN: [
                "everyone", "common", "regular", "down to earth", "relatable",
                "belong", "community", "neighbor", "friend", "ordinary"
            ],
            Archetype.CAREGIVER: [
                "care", "help", "support", "protect", "nurture",
                "compassion", "generous", "selfless", "comfort"
            ],
            Archetype.RULER: [
                "control", "lead", "power", "premium", "luxury",
                "status", "success", "exclusive", "prestige", "best"
            ],
            Archetype.CREATOR: [
                "create", "imagine", "design", "innovative", "artistic",
                "original", "vision", "express", "craft", "build"
            ],
        }
    
    def _init_mechanism_markers(self):
        """Initialize markers for persuasion mechanism detection."""
        self.mechanism_markers = {
            PersuasionMechanism.SOCIAL_PROOF: [
                "everyone", "popular", "reviews", "recommended", "bestseller",
                "trusted", "rated", "millions use", "others love"
            ],
            PersuasionMechanism.SCARCITY: [
                "limited", "only", "last", "exclusive", "rare",
                "while supplies", "hurry", "selling fast"
            ],
            PersuasionMechanism.AUTHORITY: [
                "expert", "doctor", "certified", "award", "professional",
                "endorsed", "approved", "scientific"
            ],
            PersuasionMechanism.RECIPROCITY: [
                "free", "gift", "bonus", "included", "complimentary",
                "gave me", "provided", "sample"
            ],
            PersuasionMechanism.COMMITMENT_CONSISTENCY: [
                "always", "committed", "consistent", "loyal", "habit",
                "routine", "every day", "never miss"
            ],
            PersuasionMechanism.LIKING: [
                "love", "like", "enjoy", "pleasant", "friendly",
                "beautiful", "attractive", "nice"
            ],
            PersuasionMechanism.UNITY: [
                "we", "us", "together", "family", "community",
                "belong", "share", "our"
            ],
            PersuasionMechanism.STORYTELLING: [
                "story", "journey", "experience", "happened", "remember",
                "when I", "once upon", "let me tell"
            ],
            PersuasionMechanism.FEAR_APPEAL: [
                "worry", "afraid", "risk", "danger", "threat",
                "avoid", "prevent", "protect from"
            ],
            PersuasionMechanism.NOSTALGIA: [
                "remember", "classic", "traditional", "childhood", "heritage",
                "vintage", "retro", "old school", "back when"
            ],
            PersuasionMechanism.ASPIRATION: [
                "dream", "goal", "aspire", "become", "future",
                "achieve", "success", "ideal", "best version"
            ],
        }
    
    def _extract_constructs(
        self,
        text: str,
        rating: Optional[float],
        helpful: Optional[float],
    ) -> Dict[PsychologicalConstruct, float]:
        """Extract psychological construct scores from text."""
        text_lower = text.lower()
        constructs = {}
        
        for construct, markers in self.construct_markers.items():
            if isinstance(markers, dict):
                # Handle constructs with multiple dimensions
                if "positive" in markers and "negative" in markers:
                    pos_count = sum(1 for m in markers["positive"] if m in text_lower)
                    neg_count = sum(1 for m in markers["negative"] if m in text_lower)
                    total = pos_count + neg_count
                    if total > 0:
                        constructs[construct] = pos_count / total
                elif "promotion" in markers and "prevention" in markers:
                    # Regulatory focus
                    promo = sum(1 for m in markers["promotion"] if m in text_lower)
                    prev = sum(1 for m in markers["prevention"] if m in text_lower)
                    total = promo + prev
                    if total > 0:
                        constructs[construct] = promo / total  # Higher = promotion
                elif "abstract" in markers and "concrete" in markers:
                    # Construal level
                    abstract = sum(1 for m in markers["abstract"] if m in text_lower)
                    concrete = sum(1 for m in markers["concrete"] if m in text_lower)
                    total = abstract + concrete
                    if total > 0:
                        constructs[construct] = abstract / total  # Higher = abstract
            else:
                # Simple marker count
                count = sum(1 for m in markers if m in text_lower)
                constructs[construct] = min(1.0, count / 5)  # Normalize
        
        return constructs
    
    def _detect_archetypes(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> Dict[Archetype, float]:
        """Detect archetype signals in text."""
        text_lower = text.lower()
        archetypes = {}
        
        total_matches = 0
        for archetype, markers in self.archetype_markers.items():
            count = sum(1 for m in markers if m in text_lower)
            archetypes[archetype] = count
            total_matches += count
        
        # Normalize to probabilities
        if total_matches > 0:
            archetypes = {k: v / total_matches for k, v in archetypes.items()}
        else:
            # Default to everyman if no signals
            archetypes = {Archetype.EVERYMAN: 1.0}
        
        return archetypes
    
    def _assess_mechanism_receptivity(
        self,
        text: str,
        rating: Optional[float],
        helpful: Optional[float],
        context: Dict[str, Any],
    ) -> Dict[PersuasionMechanism, float]:
        """Assess receptivity to different persuasion mechanisms."""
        text_lower = text.lower()
        receptivity = {}
        
        for mechanism, markers in self.mechanism_markers.items():
            count = sum(1 for m in markers if m in text_lower)
            # Base receptivity on marker presence
            base_receptivity = min(1.0, count / 3)
            
            # Adjust by rating (positive reviews = mechanism worked)
            if rating is not None and count > 0:
                base_receptivity *= (0.5 + rating * 0.5)  # Boost if positive
            
            # Adjust by helpful votes (high votes = persuasive)
            if helpful is not None and helpful > 0.5:
                base_receptivity *= 1.2
            
            receptivity[mechanism] = min(1.0, base_receptivity)
        
        return receptivity
    
    def _extract_persuasive_patterns(
        self,
        text: str,
        rating: Optional[float],
        helpful: Optional[float],
    ) -> List[Dict[str, Any]]:
        """Extract persuasive language patterns from text."""
        patterns = []
        
        # Only extract from high-quality, persuasive reviews
        if helpful is not None and helpful > 0.5 and rating is not None:
            # This is a review that others found helpful
            # Extract the key phrases that make it persuasive
            
            sentences = text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and len(sentence) < 200:
                    # Detect which mechanisms are present
                    mechanisms = []
                    sentence_lower = sentence.lower()
                    for mech, markers in self.mechanism_markers.items():
                        if any(m in sentence_lower for m in markers):
                            mechanisms.append(mech.value)
                    
                    if mechanisms:
                        patterns.append({
                            "text": sentence,
                            "mechanisms": mechanisms,
                            "rating": rating,
                            "helpful_score": helpful,
                        })
        
        return patterns
    
    def _calculate_extraction_confidence(
        self,
        text: str,
        rating: Optional[float],
        helpful: Optional[float],
        constructs: Dict[PsychologicalConstruct, float],
        archetypes: Dict[Archetype, float],
    ) -> float:
        """Calculate confidence in the extraction."""
        confidence = 0.5  # Base confidence
        
        # Text length contributes
        if len(text) > 100:
            confidence += 0.1
        if len(text) > 300:
            confidence += 0.1
        
        # Having rating helps
        if rating is not None:
            confidence += 0.1
        
        # Having helpful signal helps
        if helpful is not None:
            confidence += 0.1
        
        # Having clear construct signals helps
        if len(constructs) > 3:
            confidence += 0.05
        
        # Having clear archetype helps
        if archetypes and max(archetypes.values()) > 0.3:
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def _aggregate_constructs(
        self,
        results: List[ExtractionResult],
    ) -> Dict[PsychologicalConstruct, Dict[str, float]]:
        """Aggregate construct scores across results."""
        from collections import defaultdict
        import statistics
        
        construct_values = defaultdict(list)
        
        for result in results:
            for construct, score in result.constructs.items():
                construct_values[construct].append(score)
        
        distributions = {}
        for construct, values in construct_values.items():
            if values:
                distributions[construct] = {
                    "mean": statistics.mean(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "median": statistics.median(values),
                    "count": len(values),
                }
        
        return distributions
    
    def _aggregate_archetypes(
        self,
        results: List[ExtractionResult],
    ) -> Dict[Archetype, float]:
        """Aggregate archetype prevalence."""
        from collections import defaultdict
        
        archetype_sum = defaultdict(float)
        count = 0
        
        for result in results:
            for archetype, prob in result.archetypes.items():
                archetype_sum[archetype] += prob
            count += 1
        
        if count == 0:
            return {}
        
        return {k: v / count for k, v in archetype_sum.items()}
    
    def _calculate_mechanism_effectiveness(
        self,
        results: List[ExtractionResult],
    ) -> Dict[PersuasionMechanism, float]:
        """Calculate mechanism effectiveness from results."""
        from collections import defaultdict
        
        mechanism_scores = defaultdict(list)
        
        for result in results:
            for mechanism, receptivity in result.mechanism_receptivity.items():
                mechanism_scores[mechanism].append(receptivity)
        
        effectiveness = {}
        for mechanism, scores in mechanism_scores.items():
            if scores:
                effectiveness[mechanism] = sum(scores) / len(scores)
        
        return effectiveness
    
    def _extract_top_templates(
        self,
        results: List[ExtractionResult],
        top_n: int = 100,
    ) -> List[Dict[str, Any]]:
        """Extract top persuasive templates from results."""
        all_patterns = []
        
        for result in results:
            all_patterns.extend(result.persuasive_patterns)
        
        # Sort by helpful score
        all_patterns.sort(
            key=lambda x: x.get("helpful_score", 0),
            reverse=True
        )
        
        return all_patterns[:top_n]
