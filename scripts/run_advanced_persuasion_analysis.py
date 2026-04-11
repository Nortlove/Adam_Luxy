#!/usr/bin/env python3
"""
ADVANCED PERSUASION PATTERN ANALYSIS
=====================================

Analyzes review data to discover additional predictive patterns for
personalized persuasion recommendations.

ANALYSIS DIMENSIONS:
1. Persuasion Susceptibility Indicators
2. Social Proof Responsiveness Patterns
3. Review Engagement Predictors
4. Cross-Category Behavior Patterns
5. Sentiment-Persuasion Correlations
6. Linguistic Persuasion Markers
7. Temporal Receptivity Windows
8. Authority Sensitivity Indicators
9. Scarcity Response Patterns
10. Reciprocity Triggers
"""

import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("/Users/chrisnocera/Sites/adam-platform/data/learning")
OUTPUT_DIR = DATA_DIR


# =============================================================================
# PERSUASION MARKER DEFINITIONS
# =============================================================================

# Cialdini's 6 Principles - Language Markers
SOCIAL_PROOF_MARKERS = {
    "positive": [
        r"\beveryone\b", r"\beverybody\b", r"\bpopular\b", r"\btrending\b",
        r"\bmost people\b", r"\bothers (say|said|love|recommend)",
        r"\bfriends? recommend", r"\breviews? (said|mentioned|noted)",
        r"\bbest[- ]?seller", r"\bviral\b", r"\bhighly rated\b",
        r"\b\d+\s*(people|customers|users|reviewers)\b",
    ],
    "negative": [
        r"\bno one\b", r"\bnobody\b", r"\bfew people\b", r"\bunpopular\b",
        r"\boverrated\b",
    ],
}

AUTHORITY_MARKERS = {
    "positive": [
        r"\bexpert\b", r"\bprofessional\b", r"\bspecialist\b", r"\bdoctor\b",
        r"\bscientist\b", r"\bresearch(er)?s?\b", r"\bstud(y|ies)\b",
        r"\bproven\b", r"\bcertified\b", r"\baward[- ]?winning\b",
        r"\brecommended by\b", r"\bendorsed\b", r"\btrusted\b",
        r"\bindustry[- ]?leading\b", r"\b(FDA|CE|ISO) approved\b",
    ],
    "negative": [
        r"\bunqualified\b", r"\bamateurish\b", r"\bquestionable\b",
    ],
}

SCARCITY_MARKERS = {
    "positive": [
        r"\blimited\b", r"\brare\b", r"\bexclusive\b", r"\bonly \d+\s*left",
        r"\blast (chance|one|few)", r"\bselling (fast|out)\b",
        r"\bwhile (supplies|stocks?) last", r"\bhurry\b", r"\bdon't miss\b",
        r"\bending soon\b", r"\btime[- ]?sensitive\b",
    ],
    "urgency": [
        r"\bimmediately\b", r"\bright away\b", r"\bnow\b", r"\btoday\b",
        r"\basap\b", r"\burgent\b",
    ],
}

RECIPROCITY_MARKERS = {
    "positive": [
        r"\bfree\b", r"\bbonus\b", r"\bgift\b", r"\bcomplimentary\b",
        r"\bincluded\b", r"\bextra\b", r"\bno charge\b", r"\bthank(s|ing)?\b",
        r"\bappreciate\b", r"\bgrateful\b",
    ],
}

COMMITMENT_MARKERS = {
    "positive": [
        r"\bcommit(ted|ment)?\b", r"\bpromise\b", r"\bguarantee\b",
        r"\bloyalt?y?\b", r"\bsubscri(be|ption)\b", r"\bmember(ship)?\b",
        r"\bjoined?\b", r"\bbelieve in\b", r"\bstand (by|behind)\b",
    ],
}

LIKING_MARKERS = {
    "positive": [
        r"\blove\b", r"\badore\b", r"\bfavorite\b", r"\bfan of\b",
        r"\bfriendly\b", r"\bpersonable\b", r"\bwarm\b", r"\bwelcoming\b",
        r"\brelatable\b", r"\bsimilar to me\b",
    ],
}


# Decision Style Markers
ANALYTICAL_MARKERS = [
    r"\bresearch(ed)?\b", r"\bcompar(e|ed|ing)\b", r"\banalyz(e|ed|ing)\b",
    r"\bdetail(s|ed)?\b", r"\bspec(s|ification)?\b", r"\btechnical\b",
    r"\bpros? (and|&) cons?\b", r"\bweigh(ed|ing)?\b", r"\bdata\b",
    r"\bfact(s|ual)?\b", r"\bevidence\b", r"\bmetric(s)?\b",
]

IMPULSIVE_MARKERS = [
    r"\binstant(ly)?\b", r"\bimmediate(ly)?\b", r"\bjust bought\b",
    r"\bhad to (have|get|buy)\b", r"\bcouldn't resist\b", r"\bspur of\b",
    r"\bno brainer\b", r"\binstapurchase\b", r"\bbought without\b",
]

SOCIAL_MARKERS = [
    r"\bfriend(s)? (said|recommended|suggested|told)\b",
    r"\beveryone('s| is| has)\b", r"\bgroup\b", r"\bfamily\b",
    r"\bcoworker(s)?\b", r"\bcolleague(s)?\b", r"\bpartner\b",
]


# Emotional Intensity Markers
POSITIVE_INTENSITY = {
    "low": [r"\bokay\b", r"\bfine\b", r"\bdecent\b", r"\bacceptable\b"],
    "medium": [r"\bgood\b", r"\bnice\b", r"\bhappy\b", r"\bpleased\b"],
    "high": [r"\bgreat\b", r"\bexcellent\b", r"\bwonderful\b", r"\bfantastic\b"],
    "extreme": [r"\bamazing\b", r"\bincredible\b", r"\bperfect\b", r"\bbest ever\b", r"\bmind[- ]?blowing\b"],
}

NEGATIVE_INTENSITY = {
    "low": [r"\bnot great\b", r"\bcould be better\b", r"\bmeh\b"],
    "medium": [r"\bdisappointed\b", r"\bfrustrat(ed|ing)\b", r"\bunhappy\b"],
    "high": [r"\bterrible\b", r"\bawful\b", r"\bhorrible\b", r"\bwaste\b"],
    "extreme": [r"\bworst\b", r"\bnightmare\b", r"\bscam\b", r"\bfraud\b", r"\bdisgusting\b"],
}


# =============================================================================
# ANALYSIS CLASSES
# =============================================================================

@dataclass
class PersuasionProfile:
    """Comprehensive persuasion susceptibility profile."""
    archetype: str
    
    # Cialdini Principle Sensitivity (0-1)
    social_proof_sensitivity: float = 0.5
    authority_sensitivity: float = 0.5
    scarcity_sensitivity: float = 0.5
    reciprocity_sensitivity: float = 0.5
    commitment_sensitivity: float = 0.5
    liking_sensitivity: float = 0.5
    
    # Decision Style Weights
    analytical_weight: float = 0.33
    impulsive_weight: float = 0.33
    social_weight: float = 0.33
    
    # Emotional Responsiveness
    positive_emotion_responsiveness: float = 0.5
    negative_emotion_responsiveness: float = 0.5
    intensity_preference: str = "medium"  # low/medium/high/extreme
    
    # Behavioral Patterns
    avg_review_length: float = 0.0
    review_depth_score: float = 0.0
    engagement_rate: float = 0.0  # helpful votes received/given ratio
    
    # Sample counts
    review_count: int = 0
    
    # Raw scores for averaging
    _social_proof_scores: List[float] = field(default_factory=list)
    _authority_scores: List[float] = field(default_factory=list)
    _scarcity_scores: List[float] = field(default_factory=list)
    _reciprocity_scores: List[float] = field(default_factory=list)
    _commitment_scores: List[float] = field(default_factory=list)
    _liking_scores: List[float] = field(default_factory=list)


@dataclass  
class PersuasionSignal:
    """A single persuasion signal extracted from a review."""
    review_id: str
    archetype: str
    
    # Principle presence (count of markers)
    social_proof_count: int = 0
    authority_count: int = 0
    scarcity_count: int = 0
    reciprocity_count: int = 0
    commitment_count: int = 0
    liking_count: int = 0
    
    # Decision style
    decision_style: str = "balanced"  # analytical/impulsive/social/balanced
    
    # Emotional characteristics
    emotional_intensity: str = "medium"
    sentiment_polarity: float = 0.0  # -1 to 1
    
    # Engagement indicators
    review_length: int = 0
    helpful_votes: int = 0
    rating: float = 0.0


class AdvancedPersuasionAnalyzer:
    """
    Extracts advanced persuasion patterns from review text.
    """
    
    def __init__(self):
        self.profiles: Dict[str, PersuasionProfile] = {}
        self.signals: List[PersuasionSignal] = []
        
        # Compile regex patterns
        self._compile_patterns()
        
        # Additional pattern trackers
        self.archetype_phrase_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.archetype_intensity_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.archetype_decision_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Cross-pattern correlations
        self.principle_cooccurrence: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Rating-principle correlations
        self.rating_principle_correlation: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = {
            "social_proof_positive": [re.compile(p, re.IGNORECASE) for p in SOCIAL_PROOF_MARKERS["positive"]],
            "social_proof_negative": [re.compile(p, re.IGNORECASE) for p in SOCIAL_PROOF_MARKERS["negative"]],
            "authority_positive": [re.compile(p, re.IGNORECASE) for p in AUTHORITY_MARKERS["positive"]],
            "scarcity_positive": [re.compile(p, re.IGNORECASE) for p in SCARCITY_MARKERS["positive"]],
            "scarcity_urgency": [re.compile(p, re.IGNORECASE) for p in SCARCITY_MARKERS["urgency"]],
            "reciprocity_positive": [re.compile(p, re.IGNORECASE) for p in RECIPROCITY_MARKERS["positive"]],
            "commitment_positive": [re.compile(p, re.IGNORECASE) for p in COMMITMENT_MARKERS["positive"]],
            "liking_positive": [re.compile(p, re.IGNORECASE) for p in LIKING_MARKERS["positive"]],
            "analytical": [re.compile(p, re.IGNORECASE) for p in ANALYTICAL_MARKERS],
            "impulsive": [re.compile(p, re.IGNORECASE) for p in IMPULSIVE_MARKERS],
            "social": [re.compile(p, re.IGNORECASE) for p in SOCIAL_MARKERS],
        }
        
        # Compile intensity patterns
        self.intensity_patterns = {}
        for level, patterns in POSITIVE_INTENSITY.items():
            self.intensity_patterns[f"positive_{level}"] = [re.compile(p, re.IGNORECASE) for p in patterns]
        for level, patterns in NEGATIVE_INTENSITY.items():
            self.intensity_patterns[f"negative_{level}"] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def _count_pattern_matches(self, text: str, pattern_key: str) -> int:
        """Count how many patterns match in the text."""
        count = 0
        for pattern in self.compiled_patterns.get(pattern_key, []):
            count += len(pattern.findall(text))
        return count
    
    def _detect_emotional_intensity(self, text: str) -> Tuple[str, float]:
        """Detect emotional intensity level and sentiment."""
        positive_scores = {"low": 0, "medium": 0, "high": 0, "extreme": 0}
        negative_scores = {"low": 0, "medium": 0, "high": 0, "extreme": 0}
        
        for level, patterns in POSITIVE_INTENSITY.items():
            for pattern in [re.compile(p, re.IGNORECASE) for p in patterns]:
                positive_scores[level] += len(pattern.findall(text))
        
        for level, patterns in NEGATIVE_INTENSITY.items():
            for pattern in [re.compile(p, re.IGNORECASE) for p in patterns]:
                negative_scores[level] += len(pattern.findall(text))
        
        # Determine dominant intensity
        total_positive = sum(positive_scores.values())
        total_negative = sum(negative_scores.values())
        
        if total_positive + total_negative == 0:
            return "medium", 0.0
        
        # Calculate sentiment polarity
        polarity = (total_positive - total_negative) / (total_positive + total_negative)
        
        # Determine intensity level
        scores = positive_scores if total_positive > total_negative else negative_scores
        if scores["extreme"] > 0:
            intensity = "extreme"
        elif scores["high"] > 0:
            intensity = "high"
        elif scores["medium"] > 0:
            intensity = "medium"
        else:
            intensity = "low"
        
        return intensity, polarity
    
    def _detect_decision_style(self, text: str) -> str:
        """Detect the decision-making style from text."""
        analytical = self._count_pattern_matches(text, "analytical")
        impulsive = self._count_pattern_matches(text, "impulsive")
        social = self._count_pattern_matches(text, "social")
        
        total = analytical + impulsive + social
        if total == 0:
            return "balanced"
        
        if analytical >= impulsive and analytical >= social:
            return "analytical"
        elif impulsive >= analytical and impulsive >= social:
            return "impulsive"
        elif social >= analytical and social >= impulsive:
            return "social"
        return "balanced"
    
    def analyze_review(
        self,
        review_id: str,
        text: str,
        archetype: str,
        rating: float = 0.0,
        helpful_votes: int = 0,
    ) -> PersuasionSignal:
        """Analyze a single review for persuasion patterns."""
        
        # Count principle markers
        social_proof = self._count_pattern_matches(text, "social_proof_positive")
        authority = self._count_pattern_matches(text, "authority_positive")
        scarcity = (self._count_pattern_matches(text, "scarcity_positive") + 
                   self._count_pattern_matches(text, "scarcity_urgency"))
        reciprocity = self._count_pattern_matches(text, "reciprocity_positive")
        commitment = self._count_pattern_matches(text, "commitment_positive")
        liking = self._count_pattern_matches(text, "liking_positive")
        
        # Detect decision style
        decision_style = self._detect_decision_style(text)
        
        # Detect emotional intensity
        intensity, polarity = self._detect_emotional_intensity(text)
        
        signal = PersuasionSignal(
            review_id=review_id,
            archetype=archetype,
            social_proof_count=social_proof,
            authority_count=authority,
            scarcity_count=scarcity,
            reciprocity_count=reciprocity,
            commitment_count=commitment,
            liking_count=liking,
            decision_style=decision_style,
            emotional_intensity=intensity,
            sentiment_polarity=polarity,
            review_length=len(text),
            helpful_votes=helpful_votes,
            rating=rating,
        )
        
        self.signals.append(signal)
        
        # Track patterns by archetype
        self.archetype_decision_patterns[archetype][decision_style] += 1
        self.archetype_intensity_patterns[archetype][intensity] += 1
        
        # Track principle co-occurrence
        principles_present = []
        if social_proof > 0: principles_present.append("social_proof")
        if authority > 0: principles_present.append("authority")
        if scarcity > 0: principles_present.append("scarcity")
        if reciprocity > 0: principles_present.append("reciprocity")
        if commitment > 0: principles_present.append("commitment")
        if liking > 0: principles_present.append("liking")
        
        for i, p1 in enumerate(principles_present):
            for p2 in principles_present[i+1:]:
                self.principle_cooccurrence[p1][p2] += 1
                self.principle_cooccurrence[p2][p1] += 1
        
        # Track rating-principle correlation
        rating_bucket = int(rating)
        if social_proof > 0:
            self.rating_principle_correlation["social_proof"][rating_bucket].append(social_proof)
        if authority > 0:
            self.rating_principle_correlation["authority"][rating_bucket].append(authority)
        
        return signal
    
    def compute_archetype_profiles(self) -> Dict[str, PersuasionProfile]:
        """Compute aggregated persuasion profiles by archetype."""
        
        archetype_signals: Dict[str, List[PersuasionSignal]] = defaultdict(list)
        for signal in self.signals:
            archetype_signals[signal.archetype].append(signal)
        
        for archetype, signals in archetype_signals.items():
            if not signals:
                continue
            
            profile = PersuasionProfile(archetype=archetype)
            profile.review_count = len(signals)
            
            # Aggregate principle sensitivities
            total_social_proof = sum(s.social_proof_count for s in signals)
            total_authority = sum(s.authority_count for s in signals)
            total_scarcity = sum(s.scarcity_count for s in signals)
            total_reciprocity = sum(s.reciprocity_count for s in signals)
            total_commitment = sum(s.commitment_count for s in signals)
            total_liking = sum(s.liking_count for s in signals)
            
            total_principles = (total_social_proof + total_authority + total_scarcity + 
                               total_reciprocity + total_commitment + total_liking)
            
            if total_principles > 0:
                profile.social_proof_sensitivity = total_social_proof / total_principles
                profile.authority_sensitivity = total_authority / total_principles
                profile.scarcity_sensitivity = total_scarcity / total_principles
                profile.reciprocity_sensitivity = total_reciprocity / total_principles
                profile.commitment_sensitivity = total_commitment / total_principles
                profile.liking_sensitivity = total_liking / total_principles
            
            # Aggregate decision styles
            decision_counts = self.archetype_decision_patterns[archetype]
            total_decisions = sum(decision_counts.values())
            if total_decisions > 0:
                profile.analytical_weight = decision_counts.get("analytical", 0) / total_decisions
                profile.impulsive_weight = decision_counts.get("impulsive", 0) / total_decisions
                profile.social_weight = decision_counts.get("social", 0) / total_decisions
            
            # Aggregate emotional patterns
            intensity_counts = self.archetype_intensity_patterns[archetype]
            if intensity_counts:
                profile.intensity_preference = max(intensity_counts, key=intensity_counts.get)
            
            # Aggregate sentiment
            sentiments = [s.sentiment_polarity for s in signals]
            if sentiments:
                avg_sentiment = np.mean(sentiments)
                profile.positive_emotion_responsiveness = max(0, avg_sentiment)
                profile.negative_emotion_responsiveness = max(0, -avg_sentiment)
            
            # Review characteristics
            profile.avg_review_length = np.mean([s.review_length for s in signals])
            profile.engagement_rate = np.mean([s.helpful_votes for s in signals]) if signals else 0
            
            self.profiles[archetype] = profile
        
        return self.profiles
    
    def get_principle_synergies(self) -> Dict[str, List[Tuple[str, float]]]:
        """Get principle combinations that frequently co-occur."""
        synergies = {}
        
        for p1, cooccurrences in self.principle_cooccurrence.items():
            total = sum(cooccurrences.values())
            if total > 0:
                synergies[p1] = sorted(
                    [(p2, count/total) for p2, count in cooccurrences.items()],
                    key=lambda x: x[1],
                    reverse=True
                )
        
        return synergies
    
    def get_rating_principle_insights(self) -> Dict[str, Dict[str, float]]:
        """Get insights on how principles correlate with ratings."""
        insights = {}
        
        for principle, rating_data in self.rating_principle_correlation.items():
            principle_insights = {}
            
            # High rating correlation (4-5 stars)
            high_ratings = rating_data.get(4, []) + rating_data.get(5, [])
            low_ratings = rating_data.get(1, []) + rating_data.get(2, [])
            
            if high_ratings:
                principle_insights["high_rating_avg_usage"] = np.mean(high_ratings)
            if low_ratings:
                principle_insights["low_rating_avg_usage"] = np.mean(low_ratings)
            
            if high_ratings and low_ratings:
                principle_insights["positive_correlation"] = (
                    np.mean(high_ratings) > np.mean(low_ratings)
                )
            
            insights[principle] = principle_insights
        
        return insights


# =============================================================================
# ADDITIONAL PATTERN DISCOVERY
# =============================================================================

class AdvancedPatternDiscovery:
    """
    Discovers additional predictive patterns beyond basic persuasion markers.
    """
    
    def __init__(self):
        # Pattern trackers
        self.word_archetype_correlation: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.phrase_archetype_correlation: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.rating_behavior_patterns: Dict[str, Dict] = defaultdict(dict)
        self.review_length_patterns: Dict[str, List[int]] = defaultdict(list)
        self.exclamation_patterns: Dict[str, int] = defaultdict(int)
        self.question_patterns: Dict[str, int] = defaultdict(int)
        
        # Persuasion indicator phrases
        self.power_phrases = defaultdict(lambda: defaultdict(int))
        self.hesitation_phrases = defaultdict(lambda: defaultdict(int))
        self.confidence_phrases = defaultdict(lambda: defaultdict(int))
        
        # Behavioral sequences
        self.rating_sequences: Dict[str, List[List[int]]] = defaultdict(list)
    
    def extract_ngrams(self, text: str, n: int = 2) -> List[str]:
        """Extract n-grams from text."""
        words = re.findall(r'\b[a-z]+\b', text.lower())
        return [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]
    
    def analyze_review_patterns(
        self,
        text: str,
        archetype: str,
        rating: float,
    ):
        """Extract additional patterns from a review."""
        
        text_lower = text.lower()
        
        # Track word correlations
        words = re.findall(r'\b[a-z]+\b', text_lower)
        for word in set(words):
            self.word_archetype_correlation[word][archetype] += 1
        
        # Track bigram correlations
        bigrams = self.extract_ngrams(text_lower, 2)
        for bigram in set(bigrams):
            self.phrase_archetype_correlation[bigram][archetype] += 1
        
        # Track review length
        self.review_length_patterns[archetype].append(len(text))
        
        # Track punctuation patterns
        exclamation_count = text.count('!')
        question_count = text.count('?')
        self.exclamation_patterns[archetype] += exclamation_count
        self.question_patterns[archetype] += question_count
        
        # Power phrases (confident, persuasive language)
        power_patterns = [
            r"\bdefinitely\b", r"\babsolutely\b", r"\bwithout a doubt\b",
            r"\bhighly recommend\b", r"\bmust (have|buy|get)\b",
            r"\bcan't go wrong\b", r"\bbest (decision|purchase|choice)\b",
        ]
        for pattern in power_patterns:
            if re.search(pattern, text_lower):
                self.power_phrases[archetype][pattern] += 1
        
        # Hesitation phrases (uncertain language)
        hesitation_patterns = [
            r"\bmaybe\b", r"\bperhaps\b", r"\bi think\b", r"\bi guess\b",
            r"\bnot sure\b", r"\bit depends\b", r"\bmight be\b",
        ]
        for pattern in hesitation_patterns:
            if re.search(pattern, text_lower):
                self.hesitation_phrases[archetype][pattern] += 1
        
        # Confidence phrases
        confidence_patterns = [
            r"\bi know\b", r"\bi'm (certain|sure|confident)\b",
            r"\btrust me\b", r"\bbelieve me\b", r"\bguaranteed\b",
        ]
        for pattern in confidence_patterns:
            if re.search(pattern, text_lower):
                self.confidence_phrases[archetype][pattern] += 1
    
    def get_discriminative_phrases(self, min_count: int = 10) -> Dict[str, List[Tuple[str, float]]]:
        """
        Find phrases that are most discriminative for each archetype.
        
        Uses TF-IDF-like scoring to find phrases unique to each archetype.
        """
        discriminative = {}
        
        # Calculate document frequency (how many archetypes use each phrase)
        phrase_df = defaultdict(int)
        for phrase, archetype_counts in self.phrase_archetype_correlation.items():
            phrase_df[phrase] = len(archetype_counts)
        
        # Calculate discriminative score for each archetype
        archetypes = set()
        for phrase_data in self.phrase_archetype_correlation.values():
            archetypes.update(phrase_data.keys())
        
        for archetype in archetypes:
            scores = []
            for phrase, archetype_counts in self.phrase_archetype_correlation.items():
                count = archetype_counts.get(archetype, 0)
                if count < min_count:
                    continue
                
                # TF-IDF-like score
                total_count = sum(archetype_counts.values())
                tf = count / total_count if total_count > 0 else 0
                idf = np.log(len(archetypes) / phrase_df[phrase]) if phrase_df[phrase] > 0 else 0
                
                score = tf * idf
                if score > 0:
                    scores.append((phrase, score, count))
            
            # Sort by score
            scores.sort(key=lambda x: x[1], reverse=True)
            discriminative[archetype] = [(p, s) for p, s, c in scores[:20]]
        
        return discriminative
    
    def get_behavioral_signatures(self) -> Dict[str, Dict[str, Any]]:
        """Get behavioral signatures for each archetype."""
        signatures = {}
        
        for archetype in self.review_length_patterns.keys():
            lengths = self.review_length_patterns[archetype]
            if not lengths:
                continue
            
            total_reviews = len(lengths)
            
            # Power phrase density
            power_total = sum(self.power_phrases[archetype].values())
            hesitation_total = sum(self.hesitation_phrases[archetype].values())
            confidence_total = sum(self.confidence_phrases[archetype].values())
            
            signatures[archetype] = {
                "avg_review_length": np.mean(lengths),
                "review_length_std": np.std(lengths),
                "exclamation_rate": self.exclamation_patterns[archetype] / total_reviews,
                "question_rate": self.question_patterns[archetype] / total_reviews,
                "power_phrase_rate": power_total / total_reviews,
                "hesitation_phrase_rate": hesitation_total / total_reviews,
                "confidence_phrase_rate": confidence_total / total_reviews,
                "confidence_ratio": (
                    confidence_total / (hesitation_total + 0.1)  # Avoid division by zero
                ),
                "persuasion_susceptibility_score": (
                    (power_total + confidence_total) / (hesitation_total + 1)
                ) / total_reviews * 100,
            }
        
        return signatures


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def run_advanced_analysis():
    """Run the complete advanced persuasion analysis."""
    
    logger.info("=" * 60)
    logger.info("ADVANCED PERSUASION PATTERN ANALYSIS")
    logger.info("=" * 60)
    
    # Load existing priors to get archetype assignments
    priors_path = DATA_DIR / "complete_coldstart_priors.json"
    if not priors_path.exists():
        logger.error("complete_coldstart_priors.json not found")
        return
    
    with open(priors_path) as f:
        priors = json.load(f)
    
    # Initialize analyzers
    persuasion_analyzer = AdvancedPersuasionAnalyzer()
    pattern_discovery = AdvancedPatternDiscovery()
    
    # Load and analyze language patterns if available
    language_path = DATA_DIR / "language_patterns.json"
    if language_path.exists():
        logger.info("Loading language patterns...")
        with open(language_path) as f:
            language_data = json.load(f)
        
        # Process by archetype
        for archetype, patterns in language_data.get("archetype_language_patterns", {}).items():
            # Analyze sample phrases
            for phrase_type, phrases in patterns.items():
                if isinstance(phrases, list):
                    for phrase_data in phrases[:100]:  # Sample
                        if isinstance(phrase_data, dict):
                            phrase = phrase_data.get("phrase", "")
                        else:
                            phrase = str(phrase_data)
                        
                        # Analyze the phrase
                        persuasion_analyzer.analyze_review(
                            review_id=f"{archetype}_{phrase_type}_{hash(phrase)}",
                            text=phrase,
                            archetype=archetype,
                            rating=4.0,  # Assume average rating for phrases
                        )
                        pattern_discovery.analyze_review_patterns(phrase, archetype, 4.0)
    
    # Load enhanced psycholinguistic priors
    enhanced_path = DATA_DIR / "enhanced_psycholinguistic_priors.json"
    if enhanced_path.exists():
        logger.info("Loading enhanced psycholinguistic priors...")
        with open(enhanced_path) as f:
            enhanced_data = json.load(f)
        
        # Extract linguistic patterns
        for archetype, data in enhanced_data.items():
            if isinstance(data, dict):
                for field, value in data.items():
                    if isinstance(value, str) and len(value) > 20:
                        persuasion_analyzer.analyze_review(
                            review_id=f"enhanced_{archetype}_{field}",
                            text=value,
                            archetype=archetype,
                            rating=4.0,
                        )
                        pattern_discovery.analyze_review_patterns(value, archetype, 4.0)
    
    # Load persuasion priors for additional analysis
    persuasion_path = DATA_DIR / "persuasion_priors.json"
    if persuasion_path.exists():
        logger.info("Loading persuasion priors...")
        with open(persuasion_path) as f:
            persuasion_data = json.load(f)
        
        # Analyze vote-based patterns
        for archetype, arch_data in persuasion_data.get("archetype_vote_patterns", {}).items():
            if isinstance(arch_data, dict):
                # Create synthetic reviews from vote patterns
                useful_rate = arch_data.get("useful_rate", 0.5)
                funny_rate = arch_data.get("funny_rate", 0.2)
                cool_rate = arch_data.get("cool_rate", 0.3)
                
                # These rates indicate social influence type
                pattern_discovery.power_phrases[archetype]["useful_oriented"] = int(useful_rate * 100)
                pattern_discovery.power_phrases[archetype]["entertainment_oriented"] = int(funny_rate * 100)
                pattern_discovery.power_phrases[archetype]["status_oriented"] = int(cool_rate * 100)
    
    # Compute profiles
    logger.info("Computing persuasion profiles...")
    profiles = persuasion_analyzer.compute_archetype_profiles()
    
    # Get additional insights
    logger.info("Extracting principle synergies...")
    synergies = persuasion_analyzer.get_principle_synergies()
    
    logger.info("Analyzing rating-principle correlations...")
    rating_insights = persuasion_analyzer.get_rating_principle_insights()
    
    logger.info("Discovering discriminative phrases...")
    discriminative_phrases = pattern_discovery.get_discriminative_phrases(min_count=5)
    
    logger.info("Computing behavioral signatures...")
    signatures = pattern_discovery.get_behavioral_signatures()
    
    # ==========================================================================
    # BUILD COMPREHENSIVE OUTPUT
    # ==========================================================================
    
    output = {
        "analysis_timestamp": datetime.now().isoformat(),
        "signals_analyzed": len(persuasion_analyzer.signals),
        
        # Archetype persuasion profiles
        "archetype_persuasion_profiles": {},
        
        # Principle synergies (which principles work well together)
        "principle_synergies": synergies,
        
        # Rating-principle insights
        "rating_principle_correlations": rating_insights,
        
        # Discriminative phrases by archetype
        "discriminative_phrases": discriminative_phrases,
        
        # Behavioral signatures
        "behavioral_signatures": signatures,
        
        # Persuasion recommendations by archetype
        "persuasion_recommendations": {},
    }
    
    # Build profile output
    for archetype, profile in profiles.items():
        output["archetype_persuasion_profiles"][archetype] = {
            "review_count": profile.review_count,
            "principle_sensitivities": {
                "social_proof": round(profile.social_proof_sensitivity, 4),
                "authority": round(profile.authority_sensitivity, 4),
                "scarcity": round(profile.scarcity_sensitivity, 4),
                "reciprocity": round(profile.reciprocity_sensitivity, 4),
                "commitment": round(profile.commitment_sensitivity, 4),
                "liking": round(profile.liking_sensitivity, 4),
            },
            "decision_style_weights": {
                "analytical": round(profile.analytical_weight, 4),
                "impulsive": round(profile.impulsive_weight, 4),
                "social": round(profile.social_weight, 4),
            },
            "emotional_profile": {
                "intensity_preference": profile.intensity_preference,
                "positive_responsiveness": round(profile.positive_emotion_responsiveness, 4),
                "negative_responsiveness": round(profile.negative_emotion_responsiveness, 4),
            },
            "engagement_metrics": {
                "avg_review_length": round(profile.avg_review_length, 2),
                "engagement_rate": round(profile.engagement_rate, 4),
            },
        }
        
        # Generate recommendations
        principles = output["archetype_persuasion_profiles"][archetype]["principle_sensitivities"]
        sorted_principles = sorted(principles.items(), key=lambda x: x[1], reverse=True)
        
        output["persuasion_recommendations"][archetype] = {
            "primary_principle": sorted_principles[0][0] if sorted_principles else "social_proof",
            "secondary_principle": sorted_principles[1][0] if len(sorted_principles) > 1 else "liking",
            "tertiary_principle": sorted_principles[2][0] if len(sorted_principles) > 2 else "authority",
            "decision_approach": max(
                [("analytical", profile.analytical_weight),
                 ("impulsive", profile.impulsive_weight),
                 ("social", profile.social_weight)],
                key=lambda x: x[1]
            )[0],
            "emotional_intensity_target": profile.intensity_preference,
            "recommended_cta_style": {
                "analytical": "Learn more / Compare options / See details",
                "impulsive": "Buy now / Get it today / Limited time",
                "social": "Join others / Share / See what friends say",
            }.get(max(
                [("analytical", profile.analytical_weight),
                 ("impulsive", profile.impulsive_weight),
                 ("social", profile.social_weight)],
                key=lambda x: x[1]
            )[0], "Discover now"),
        }
    
    # Save results
    output_path = OUTPUT_DIR / "advanced_persuasion_patterns.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Saved advanced persuasion patterns to {output_path}")
    
    # ==========================================================================
    # PRINT SUMMARY
    # ==========================================================================
    
    print("\n" + "=" * 70)
    print("ADVANCED PERSUASION ANALYSIS RESULTS")
    print("=" * 70)
    
    print(f"\nTotal signals analyzed: {len(persuasion_analyzer.signals)}")
    print(f"Archetypes profiled: {len(profiles)}")
    
    print("\n--- TOP PERSUASION PRINCIPLES BY ARCHETYPE ---")
    for archetype, rec in output["persuasion_recommendations"].items():
        print(f"\n{archetype}:")
        print(f"  Primary: {rec['primary_principle']}")
        print(f"  Secondary: {rec['secondary_principle']}")
        print(f"  Decision style: {rec['decision_approach']}")
        print(f"  CTA style: {rec['recommended_cta_style']}")
    
    print("\n--- PRINCIPLE SYNERGIES (Co-occurrence) ---")
    for principle, coocs in list(synergies.items())[:3]:
        print(f"\n{principle} commonly pairs with:")
        for other, rate in coocs[:3]:
            print(f"  - {other}: {rate:.1%}")
    
    print("\n--- BEHAVIORAL SIGNATURES ---")
    for archetype, sig in list(signatures.items())[:3]:
        print(f"\n{archetype}:")
        print(f"  Avg review length: {sig.get('avg_review_length', 0):.0f} chars")
        print(f"  Exclamation rate: {sig.get('exclamation_rate', 0):.2f}/review")
        print(f"  Confidence ratio: {sig.get('confidence_ratio', 0):.2f}")
        print(f"  Persuasion susceptibility: {sig.get('persuasion_susceptibility_score', 0):.2f}")
    
    return output


if __name__ == "__main__":
    results = run_advanced_analysis()
