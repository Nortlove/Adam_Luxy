"""
Yelp Review Intelligence Extractor
==================================

THE SOCIAL INFLUENCE LAYER

Unique Value: 7M reviews + 2M user profiles with:
- Friends network (SOCIAL GRAPH!)
- Elite reviewer status (authority)
- Useful/Funny/Cool votes (response type differentiation)
- Rich business attributes
- Checkin patterns (temporal behavior)
- Tips (short-form advice)

Cookie-Less Power:
- User influence networks for social proof amplification
- Elite reviewer templates for authority messaging
- Response type targeting (rational vs humor vs social)
- Checkin patterns for temporal optimization
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import networkx as nx

from ..base_extractor import (
    BaseReviewExtractor,
    ExtractionResult,
    AggregatedIntelligence,
    DataSource,
    PsychologicalConstruct,
    Archetype,
    PersuasionMechanism,
)
from .. import IntelligenceLayer

logger = logging.getLogger(__name__)


# =============================================================================
# YELP-SPECIFIC DATA STRUCTURES
# =============================================================================

@dataclass
class YelpInfluencerProfile:
    """Profile of a Yelp influencer."""
    
    user_id: str
    name: str
    
    # Influence metrics
    review_count: int = 0
    useful_received: int = 0
    funny_received: int = 0
    cool_received: int = 0
    fans: int = 0
    
    # Status
    elite_years: List[str] = field(default_factory=list)
    is_elite: bool = False
    
    # Social network
    friend_count: int = 0
    friend_ids: List[str] = field(default_factory=list)
    
    # Compliment profile (what they're known for)
    compliment_profile: Dict[str, int] = field(default_factory=dict)
    
    # Calculated influence score
    influence_score: float = 0.0
    
    # Psychological profile inferred from compliments
    psychological_profile: Dict[str, float] = field(default_factory=dict)


@dataclass
class ReviewResponseProfile:
    """Profile based on useful/funny/cool votes."""
    
    # What type of content resonates
    useful_affinity: float = 0.0  # Rational, informational content
    funny_affinity: float = 0.0  # Humor, entertainment content
    cool_affinity: float = 0.0  # Trend-following, social content
    
    # Dominant response type
    dominant_type: str = "useful"  # useful, funny, or cool
    
    # Mechanism implications
    mechanism_receptivity: Dict[str, float] = field(default_factory=dict)


@dataclass
class CheckinPattern:
    """Temporal visitation patterns from checkins."""
    
    business_id: str
    business_name: Optional[str] = None
    category: Optional[str] = None
    
    # Temporal patterns
    hour_distribution: Dict[int, float] = field(default_factory=dict)  # hour -> frequency
    day_distribution: Dict[int, float] = field(default_factory=dict)  # weekday -> frequency
    
    # Visit frequency
    total_checkins: int = 0
    unique_visitors: int = 0  # estimated
    
    # Psychology implications
    audience_type: str = "general"  # "routine", "event", "spontaneous"


# =============================================================================
# YELP EXTRACTOR
# =============================================================================

class YelpExtractor(BaseReviewExtractor):
    """
    Extractor for Yelp Academic Dataset.
    
    This extractor builds:
    1. User influence networks from friends
    2. Elite reviewer authority patterns
    3. Useful/Funny/Cool response type targeting
    4. Compliment-based personality profiling
    5. Checkin temporal patterns
    """
    
    # Compliment types and their psychological implications
    COMPLIMENT_PSYCHOLOGY = {
        "hot": {
            "trait": "attractiveness_valuing",
            "archetypes": [Archetype.LOVER],
            "mechanisms": [PersuasionMechanism.LIKING, PersuasionMechanism.ASPIRATION],
        },
        "more": {
            "trait": "quantity_appreciator",
            "archetypes": [Archetype.EVERYMAN],
            "mechanisms": [PersuasionMechanism.SOCIAL_PROOF],
        },
        "profile": {
            "trait": "detail_oriented",
            "archetypes": [Archetype.SAGE],
            "mechanisms": [PersuasionMechanism.AUTHORITY],
        },
        "cute": {
            "trait": "warmth_valuing",
            "archetypes": [Archetype.CAREGIVER, Archetype.INNOCENT],
            "mechanisms": [PersuasionMechanism.LIKING],
        },
        "list": {
            "trait": "organized_systematic",
            "archetypes": [Archetype.SAGE, Archetype.RULER],
            "mechanisms": [PersuasionMechanism.AUTHORITY, PersuasionMechanism.LOGICAL_APPEAL],
        },
        "note": {
            "trait": "thoughtful_considerate",
            "archetypes": [Archetype.SAGE, Archetype.CAREGIVER],
            "mechanisms": [PersuasionMechanism.RECIPROCITY],
        },
        "plain": {
            "trait": "authenticity_valuing",
            "archetypes": [Archetype.EVERYMAN],
            "mechanisms": [PersuasionMechanism.AUTHENTICITY],
        },
        "cool": {
            "trait": "trend_following",
            "archetypes": [Archetype.EXPLORER, Archetype.OUTLAW],
            "mechanisms": [PersuasionMechanism.SOCIAL_PROOF, PersuasionMechanism.EXCLUSIVITY],
        },
        "funny": {
            "trait": "humor_valuing",
            "archetypes": [Archetype.JESTER],
            "mechanisms": [PersuasionMechanism.HUMOR, PersuasionMechanism.LIKING],
        },
        "writer": {
            "trait": "eloquence_appreciator",
            "archetypes": [Archetype.SAGE, Archetype.CREATOR],
            "mechanisms": [PersuasionMechanism.STORYTELLING, PersuasionMechanism.AUTHORITY],
        },
        "photos": {
            "trait": "visual_appreciator",
            "archetypes": [Archetype.CREATOR, Archetype.EXPLORER],
            "mechanisms": [PersuasionMechanism.SOCIAL_PROOF],
        },
    }
    
    def __init__(
        self,
        data_path: Path,
        batch_size: int = 1000,
    ):
        super().__init__(
            data_source=DataSource.YELP,
            data_path=data_path,
            batch_size=batch_size,
        )
        
        # Caches
        self._user_cache: Dict[str, Dict[str, Any]] = {}
        self._business_cache: Dict[str, Dict[str, Any]] = {}
        self._influencer_profiles: Dict[str, YelpInfluencerProfile] = {}
        
        # Social graph
        self._social_graph: Optional[nx.Graph] = None
        
        # Response type patterns
        self._response_type_patterns: Dict[str, ReviewResponseProfile] = {}
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def iter_reviews(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Yelp reviews."""
        review_file = self.data_path / "yelp_academic_dataset_review.json"
        
        if not review_file.exists():
            logger.error(f"Review file not found: {review_file}")
            return
        
        with open(review_file, 'r') as f:
            for line in f:
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
    
    def iter_users(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Yelp users."""
        user_file = self.data_path / "yelp_academic_dataset_user.json"
        
        if not user_file.exists():
            logger.warning(f"User file not found: {user_file}")
            return
        
        with open(user_file, 'r') as f:
            for line in f:
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
    
    def iter_businesses(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Yelp businesses."""
        business_file = self.data_path / "yelp_academic_dataset_business.json"
        
        if not business_file.exists():
            logger.warning(f"Business file not found: {business_file}")
            return
        
        with open(business_file, 'r') as f:
            for line in f:
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
    
    def iter_checkins(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Yelp checkins."""
        checkin_file = self.data_path / "yelp_academic_dataset_checkin.json"
        
        if not checkin_file.exists():
            logger.warning(f"Checkin file not found: {checkin_file}")
            return
        
        with open(checkin_file, 'r') as f:
            for line in f:
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
    
    def iter_tips(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Yelp tips (short advice)."""
        tips_file = self.data_path / "yelp_academic_dataset_tip.json"
        
        if not tips_file.exists():
            logger.warning(f"Tips file not found: {tips_file}")
            return
        
        with open(tips_file, 'r') as f:
            for line in f:
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
    
    def extract_review_text(self, review: Dict[str, Any]) -> str:
        """Extract review text."""
        return review.get('text', '') or ''
    
    def extract_rating(self, review: Dict[str, Any]) -> Optional[float]:
        """Extract and normalize rating."""
        stars = review.get('stars')
        if stars is not None:
            return float(stars) / 5.0
        return None
    
    def extract_helpful_signal(self, review: Dict[str, Any]) -> Optional[float]:
        """
        Extract helpful signal from useful/funny/cool votes.
        
        Yelp's unique value: THREE types of "helpful"!
        - Useful: Rational, informational
        - Funny: Entertainment value
        - Cool: Social/trend value
        """
        useful = int(review.get('useful', 0) or 0)
        funny = int(review.get('funny', 0) or 0)
        cool = int(review.get('cool', 0) or 0)
        
        # Combined score with weights
        total = useful * 1.5 + funny * 1.0 + cool * 1.2
        
        # Log normalize
        if total == 0:
            return 0.3  # Base
        elif total < 5:
            return 0.5
        elif total < 20:
            return 0.7
        elif total < 100:
            return 0.85
        else:
            return 0.95
    
    def extract_context(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contextual information."""
        context = {
            'business_id': review.get('business_id'),
            'user_id': review.get('user_id'),
            'date': review.get('date'),
            
            # Vote types (unique to Yelp)
            'useful_votes': review.get('useful', 0),
            'funny_votes': review.get('funny', 0),
            'cool_votes': review.get('cool', 0),
        }
        
        # Add business context if cached
        business_id = review.get('business_id')
        if business_id and business_id in self._business_cache:
            business = self._business_cache[business_id]
            context.update({
                'business_name': business.get('name'),
                'business_city': business.get('city'),
                'business_state': business.get('state'),
                'business_categories': business.get('categories'),
                'business_rating': business.get('stars'),
            })
        
        # Add user context if cached
        user_id = review.get('user_id')
        if user_id and user_id in self._user_cache:
            user = self._user_cache[user_id]
            context.update({
                'user_review_count': user.get('review_count'),
                'user_is_elite': bool(user.get('elite')),
            })
        
        return context
    
    def get_unique_value(self) -> str:
        """Return what makes Yelp uniquely valuable."""
        return """
        SOCIAL INFLUENCE INTELLIGENCE LAYER
        
        1. FRIENDS NETWORK: Full social graph!
           - Who follows who
           - Influence diffusion paths
           - Community detection
           → Build: USER → INFLUENCES → USER network
        
        2. ELITE REVIEWER STATUS: Authority signals
           - Years of elite status
           - Trusted expert templates
           → Weight their patterns higher in learning
        
        3. USEFUL/FUNNY/COOL VOTES: Response type differentiation
           - "Useful" = rational/analytical audience
           - "Funny" = entertainment-seeking audience
           - "Cool" = trend-following audience
           → Different mechanisms work for each!
        
        4. COMPLIMENT TYPES: Personality signals
           - compliment_hot → values attractiveness
           - compliment_funny → values humor
           - compliment_writer → values eloquence
           → Build reviewer archetypes from compliments
        
        5. CHECKIN PATTERNS: Temporal behavior
           - When do people visit?
           - Day-of-week patterns
           - Time-of-day patterns
           → Temporal targeting optimization
        
        6. TIPS: Short-form persuasive advice
           - Concise recommendations
           - "Must try" language patterns
           → Extract compact persuasive templates
        """
    
    def extract_dataset_specific_signals(
        self, review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Yelp-specific signals."""
        signals = {}
        
        # Response type profile
        useful = int(review.get('useful', 0) or 0)
        funny = int(review.get('funny', 0) or 0)
        cool = int(review.get('cool', 0) or 0)
        total = useful + funny + cool
        
        if total > 0:
            signals['response_profile'] = {
                'useful_ratio': useful / total,
                'funny_ratio': funny / total,
                'cool_ratio': cool / total,
                'dominant_type': max(
                    [('useful', useful), ('funny', funny), ('cool', cool)],
                    key=lambda x: x[1]
                )[0],
            }
        
        # User authority signals
        user_id = review.get('user_id')
        if user_id and user_id in self._user_cache:
            user = self._user_cache[user_id]
            signals['user_authority'] = {
                'is_elite': bool(user.get('elite')),
                'review_count': user.get('review_count', 0),
                'fans': user.get('fans', 0),
                'friend_count': len(user.get('friends', '').split(', ')) if user.get('friends') else 0,
            }
        
        return signals
    
    # =========================================================================
    # ECOSYSTEM OUTPUT METHODS
    # =========================================================================
    
    def format_for_dsp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for DSP.
        
        DSPs get:
        - Response type segments (useful/funny/cool audiences)
        - Influence network segments
        - Elite-validated templates
        """
        return {
            "segment_type": "social_influence",
            "scope": {
                "type": intelligence.scope_type,
                "value": intelligence.scope_value,
            },
            
            # Response type targeting
            "response_type_segments": {
                "useful_audience": {
                    "description": "Rational, information-seeking",
                    "recommended_mechanisms": [
                        "authority", "logical_appeal", "value_proposition"
                    ],
                    "creative_tone": "informative_factual",
                },
                "funny_audience": {
                    "description": "Entertainment-seeking, humor-appreciating",
                    "recommended_mechanisms": [
                        "humor", "liking", "storytelling"
                    ],
                    "creative_tone": "playful_witty",
                },
                "cool_audience": {
                    "description": "Trend-following, socially-motivated",
                    "recommended_mechanisms": [
                        "social_proof", "exclusivity", "aspiration"
                    ],
                    "creative_tone": "trendy_aspirational",
                },
            },
            
            # Influence amplification
            "influence_targeting": {
                "elite_reviewers": self._get_elite_insights(intelligence),
                "high_influence_users": self._get_influence_segments(),
            },
            
            # Creative optimization
            "creative_guidance": {
                "top_templates": intelligence.top_templates[:20],
                "mechanism_effectiveness": {
                    mech.value if hasattr(mech, 'value') else str(mech): score
                    for mech, score in intelligence.mechanism_effectiveness.items()
                },
            },
            
            "sample_size": intelligence.sample_size,
        }
    
    def format_for_ssp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for SSP.
        
        SSPs get:
        - Audience composition by response type
        - Influencer density signals
        - Temporal patterns from checkins
        """
        return {
            "inventory_type": "social_local",
            "scope": {
                "type": intelligence.scope_type,
                "value": intelligence.scope_value,
            },
            
            # Audience value signals
            "audience_composition": {
                "response_type_distribution": self._get_response_distribution(intelligence),
                "elite_user_percentage": self._get_elite_percentage(),
                "influencer_density": self._get_influencer_density(),
            },
            
            # Temporal optimization
            "temporal_patterns": {
                "checkin_patterns": self._get_checkin_patterns(intelligence.scope_value),
                "peak_engagement_times": self._get_peak_times(),
            },
            
            # Yield optimization
            "yield_signals": {
                "premium_audience_present": self._has_premium_audience(intelligence),
                "recommended_floor_adjustment": self._get_floor_adjustment(intelligence),
            },
            
            "sample_size": intelligence.sample_size,
        }
    
    def format_for_agency(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for Agency.
        
        Agencies get:
        - Social influence strategy
        - Response type creative briefs
        - Community insights
        """
        return {
            "strategic_context": {
                "social_landscape": {
                    "community_structure": self._get_community_insights(),
                    "influencer_map": self._get_influencer_map(),
                    "response_type_composition": self._get_response_distribution(intelligence),
                },
            },
            
            # Creative briefs by response type
            "creative_briefs": {
                "useful_audience_brief": {
                    "psychology": "analytical_decision_maker",
                    "value_proposition": "factual_evidence_based",
                    "cta": "learn_more_compare",
                    "avoid": "hype_empty_claims",
                },
                "funny_audience_brief": {
                    "psychology": "entertainment_seeking",
                    "value_proposition": "enjoyable_memorable",
                    "cta": "engage_share",
                    "avoid": "boring_corporate",
                },
                "cool_audience_brief": {
                    "psychology": "trend_conscious",
                    "value_proposition": "status_belonging",
                    "cta": "join_be_part",
                    "avoid": "mass_market_generic",
                },
            },
            
            # Influence strategy
            "influence_strategy": {
                "seed_users": self._get_seed_users(),
                "amplification_approach": self._get_amplification_strategy(),
                "community_activation": self._get_community_activation(),
            },
            
            # Cross-platform
            "cross_platform": {
                "audio_alignment": self._get_audio_alignment(intelligence),
                "social_alignment": self._get_social_alignment(intelligence),
            },
            
            "sample_size": intelligence.sample_size,
        }
    
    # =========================================================================
    # YELP-SPECIFIC EXTRACTION METHODS
    # =========================================================================
    
    def build_social_graph(self, sample_limit: Optional[int] = None) -> nx.Graph:
        """
        Build social graph from friends connections.
        
        This is powerful for:
        - Identifying influencers (high centrality)
        - Community detection
        - Influence propagation modeling
        """
        logger.info("Building social graph from Yelp friends...")
        
        G = nx.Graph()
        count = 0
        
        for user in self.iter_users():
            user_id = user.get('user_id')
            if not user_id:
                continue
            
            # Add user node with attributes
            G.add_node(
                user_id,
                review_count=user.get('review_count', 0),
                useful=user.get('useful', 0),
                fans=user.get('fans', 0),
                is_elite=bool(user.get('elite')),
            )
            
            # Add friend edges
            friends_str = user.get('friends', '')
            if friends_str and friends_str != 'None':
                friends = [f.strip() for f in friends_str.split(',') if f.strip()]
                for friend_id in friends:
                    G.add_edge(user_id, friend_id)
            
            count += 1
            if sample_limit and count >= sample_limit:
                break
            
            if count % 100000 == 0:
                logger.info(f"Processed {count} users, {G.number_of_edges()} edges")
        
        logger.info(f"Built graph with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        self._social_graph = G
        return G
    
    def calculate_influence_scores(self) -> Dict[str, float]:
        """
        Calculate influence scores using graph centrality.
        
        Uses PageRank - the same algorithm Google uses for web pages.
        """
        if self._social_graph is None:
            self.build_social_graph()
        
        logger.info("Calculating PageRank influence scores...")
        
        # PageRank for influence
        pagerank = nx.pagerank(self._social_graph, alpha=0.85)
        
        # Normalize to 0-1
        max_pr = max(pagerank.values()) if pagerank else 1
        normalized = {k: v / max_pr for k, v in pagerank.items()}
        
        return normalized
    
    def build_influencer_profiles(
        self,
        min_influence_score: float = 0.1,
    ) -> Dict[str, YelpInfluencerProfile]:
        """Build profiles of influential users."""
        influence_scores = self.calculate_influence_scores()
        
        profiles = {}
        
        for user in self.iter_users():
            user_id = user.get('user_id')
            if not user_id:
                continue
            
            # Check influence threshold
            influence = influence_scores.get(user_id, 0)
            if influence < min_influence_score:
                continue
            
            # Build profile
            profile = YelpInfluencerProfile(
                user_id=user_id,
                name=user.get('name', ''),
                review_count=user.get('review_count', 0),
                useful_received=user.get('useful', 0),
                funny_received=user.get('funny', 0),
                cool_received=user.get('cool', 0),
                fans=user.get('fans', 0),
                influence_score=influence,
            )
            
            # Elite status
            elite = user.get('elite', '')
            if elite and elite != 'None':
                profile.elite_years = elite.split(',')
                profile.is_elite = True
            
            # Friends
            friends_str = user.get('friends', '')
            if friends_str and friends_str != 'None':
                profile.friend_ids = [f.strip() for f in friends_str.split(',')]
                profile.friend_count = len(profile.friend_ids)
            
            # Compliment profile
            profile.compliment_profile = {
                'hot': user.get('compliment_hot', 0),
                'more': user.get('compliment_more', 0),
                'profile': user.get('compliment_profile', 0),
                'cute': user.get('compliment_cute', 0),
                'list': user.get('compliment_list', 0),
                'note': user.get('compliment_note', 0),
                'plain': user.get('compliment_plain', 0),
                'cool': user.get('compliment_cool', 0),
                'funny': user.get('compliment_funny', 0),
                'writer': user.get('compliment_writer', 0),
                'photos': user.get('compliment_photos', 0),
            }
            
            # Infer psychological profile from compliments
            profile.psychological_profile = self._infer_psychology_from_compliments(
                profile.compliment_profile
            )
            
            profiles[user_id] = profile
        
        self._influencer_profiles = profiles
        return profiles
    
    def build_response_type_profiles(self) -> Dict[str, ReviewResponseProfile]:
        """
        Build profiles based on useful/funny/cool response patterns.
        
        This identifies three audience types:
        - Useful-preferring: Analytical, rational decision-makers
        - Funny-preferring: Entertainment-seekers
        - Cool-preferring: Trend-followers, social-motivated
        """
        profiles = {}
        
        # Aggregate by category
        category_votes: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {'useful': 0, 'funny': 0, 'cool': 0, 'count': 0}
        )
        
        for review in self.iter_reviews():
            business_id = review.get('business_id')
            
            # Get category
            category = "General"
            if business_id and business_id in self._business_cache:
                cats = self._business_cache[business_id].get('categories', '')
                if cats:
                    category = cats.split(',')[0].strip()
            
            category_votes[category]['useful'] += int(review.get('useful', 0) or 0)
            category_votes[category]['funny'] += int(review.get('funny', 0) or 0)
            category_votes[category]['cool'] += int(review.get('cool', 0) or 0)
            category_votes[category]['count'] += 1
        
        # Build profiles
        for category, votes in category_votes.items():
            total = votes['useful'] + votes['funny'] + votes['cool']
            if total == 0:
                continue
            
            profile = ReviewResponseProfile(
                useful_affinity=votes['useful'] / total,
                funny_affinity=votes['funny'] / total,
                cool_affinity=votes['cool'] / total,
            )
            
            # Determine dominant type
            if profile.useful_affinity > profile.funny_affinity and profile.useful_affinity > profile.cool_affinity:
                profile.dominant_type = "useful"
            elif profile.funny_affinity > profile.cool_affinity:
                profile.dominant_type = "funny"
            else:
                profile.dominant_type = "cool"
            
            # Set mechanism receptivity based on dominant type
            profile.mechanism_receptivity = self._get_mechanism_receptivity_for_type(
                profile.dominant_type
            )
            
            profiles[category] = profile
        
        self._response_type_patterns = profiles
        return profiles
    
    def build_checkin_patterns(self) -> Dict[str, CheckinPattern]:
        """Build temporal patterns from checkin data."""
        patterns = {}
        
        for checkin in self.iter_checkins():
            business_id = checkin.get('business_id')
            if not business_id:
                continue
            
            dates_str = checkin.get('date', '')
            if not dates_str:
                continue
            
            # Parse dates
            dates = [d.strip() for d in dates_str.split(',')]
            
            pattern = CheckinPattern(
                business_id=business_id,
                total_checkins=len(dates),
            )
            
            # Analyze temporal distribution
            hour_counts = defaultdict(int)
            day_counts = defaultdict(int)
            
            for date_str in dates:
                try:
                    from datetime import datetime
                    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    hour_counts[dt.hour] += 1
                    day_counts[dt.weekday()] += 1
                except:
                    continue
            
            # Normalize
            total = sum(hour_counts.values())
            if total > 0:
                pattern.hour_distribution = {h: c/total for h, c in hour_counts.items()}
                pattern.day_distribution = {d: c/total for d, c in day_counts.items()}
            
            # Classify audience type
            pattern.audience_type = self._classify_audience_type(pattern)
            
            patterns[business_id] = pattern
        
        return patterns
    
    def extract_tip_templates(
        self,
        min_compliments: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Extract persuasive templates from tips.
        
        Tips are short-form advice - perfect for:
        - Concise ad copy
        - Call-to-action language
        - "Must try" recommendations
        """
        templates = []
        
        for tip in self.iter_tips():
            text = tip.get('text', '')
            compliments = tip.get('compliment_count', 0)
            
            if not text or compliments < min_compliments:
                continue
            
            # Classify tip type
            tip_type = self._classify_tip_type(text)
            
            templates.append({
                'text': text,
                'compliment_count': compliments,
                'tip_type': tip_type,
                'mechanisms': self._detect_mechanisms_in_text(text),
                'business_id': tip.get('business_id'),
                'user_id': tip.get('user_id'),
            })
        
        # Sort by compliments
        templates.sort(key=lambda x: x['compliment_count'], reverse=True)
        
        return templates
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _infer_psychology_from_compliments(
        self,
        compliments: Dict[str, int],
    ) -> Dict[str, float]:
        """Infer psychological profile from compliment distribution."""
        total = sum(compliments.values())
        if total == 0:
            return {}
        
        # Aggregate archetype and mechanism scores
        archetype_scores = defaultdict(float)
        mechanism_scores = defaultdict(float)
        
        for compliment_type, count in compliments.items():
            if count == 0:
                continue
            
            weight = count / total
            
            psych = self.COMPLIMENT_PSYCHOLOGY.get(compliment_type, {})
            
            for archetype in psych.get('archetypes', []):
                archetype_scores[archetype.value] += weight
            
            for mechanism in psych.get('mechanisms', []):
                mechanism_scores[mechanism.value] += weight
        
        return {
            'archetypes': dict(archetype_scores),
            'mechanisms': dict(mechanism_scores),
        }
    
    def _get_mechanism_receptivity_for_type(
        self,
        response_type: str,
    ) -> Dict[str, float]:
        """Get mechanism receptivity for a response type."""
        type_mechanisms = {
            "useful": {
                PersuasionMechanism.AUTHORITY.value: 0.9,
                PersuasionMechanism.LOGICAL_APPEAL.value: 0.9,
                PersuasionMechanism.VALUE_PROPOSITION.value: 0.8,
                PersuasionMechanism.TRUST.value: 0.8,
                PersuasionMechanism.SOCIAL_PROOF.value: 0.7,
            },
            "funny": {
                PersuasionMechanism.HUMOR.value: 0.9,
                PersuasionMechanism.LIKING.value: 0.9,
                PersuasionMechanism.STORYTELLING.value: 0.8,
                PersuasionMechanism.EMOTIONAL_APPEAL.value: 0.7,
            },
            "cool": {
                PersuasionMechanism.SOCIAL_PROOF.value: 0.9,
                PersuasionMechanism.EXCLUSIVITY.value: 0.9,
                PersuasionMechanism.ASPIRATION.value: 0.8,
                PersuasionMechanism.SCARCITY.value: 0.7,
            },
        }
        return type_mechanisms.get(response_type, {})
    
    def _classify_audience_type(self, pattern: CheckinPattern) -> str:
        """Classify audience type from checkin patterns."""
        if not pattern.hour_distribution:
            return "general"
        
        # Check for routine patterns (consistent times)
        variance = self._calculate_variance(list(pattern.hour_distribution.values()))
        
        if variance < 0.01:
            return "routine"  # Very consistent timing
        
        # Check for event patterns (spikes)
        max_ratio = max(pattern.hour_distribution.values())
        if max_ratio > 0.3:
            return "event"  # Strong peak times
        
        return "spontaneous"  # More random
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if not values:
            return 0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _classify_tip_type(self, text: str) -> str:
        """Classify the type of tip."""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ["must try", "must have", "don't miss"]):
            return "recommendation"
        elif any(w in text_lower for w in ["avoid", "don't", "skip"]):
            return "warning"
        elif any(w in text_lower for w in ["order", "get the", "try the"]):
            return "suggestion"
        elif any(w in text_lower for w in ["tip:", "pro tip", "insider"]):
            return "insider"
        else:
            return "general"
    
    def _detect_mechanisms_in_text(self, text: str) -> List[str]:
        """Detect persuasion mechanisms in text."""
        mechanisms = []
        text_lower = text.lower()
        
        for mechanism, markers in self.mechanism_markers.items():
            if any(m in text_lower for m in markers):
                mechanisms.append(mechanism.value)
        
        return mechanisms
    
    # Format helper methods
    def _get_elite_insights(self, intelligence: AggregatedIntelligence) -> Dict[str, Any]:
        """Get insights from elite reviewers."""
        return {
            "available": bool(self._influencer_profiles),
            "count": len([p for p in self._influencer_profiles.values() if p.is_elite]),
        }
    
    def _get_influence_segments(self) -> Dict[str, Any]:
        """Get influence-based segments."""
        if not self._influencer_profiles:
            return {"available": False}
        
        return {
            "available": True,
            "total_influencers": len(self._influencer_profiles),
            "high_influence": len([p for p in self._influencer_profiles.values() if p.influence_score > 0.5]),
        }
    
    def _get_response_distribution(self, intelligence: AggregatedIntelligence) -> Dict[str, float]:
        """Get distribution of response types."""
        return {
            "useful": 0.5,  # Would be calculated from actual data
            "funny": 0.3,
            "cool": 0.2,
        }
    
    def _get_elite_percentage(self) -> float:
        """Get percentage of elite users."""
        return 0.05  # Would be calculated
    
    def _get_influencer_density(self) -> float:
        """Get influencer density."""
        return 0.1  # Would be calculated
    
    def _get_checkin_patterns(self, scope_value: str) -> Dict[str, Any]:
        """Get checkin patterns for scope."""
        return {"peak_hours": [12, 18, 19, 20]}
    
    def _get_peak_times(self) -> List[int]:
        """Get peak engagement times."""
        return [11, 12, 18, 19, 20]
    
    def _has_premium_audience(self, intelligence: AggregatedIntelligence) -> bool:
        """Check for premium audience."""
        return True  # Would be calculated
    
    def _get_floor_adjustment(self, intelligence: AggregatedIntelligence) -> float:
        """Get recommended floor price adjustment."""
        return 1.2  # 20% premium
    
    def _get_community_insights(self) -> Dict[str, Any]:
        """Get community structure insights."""
        return {
            "has_social_graph": self._social_graph is not None,
            "communities_detected": 0,  # Would run community detection
        }
    
    def _get_influencer_map(self) -> Dict[str, Any]:
        """Get influencer mapping."""
        return {
            "total": len(self._influencer_profiles),
            "elite": len([p for p in self._influencer_profiles.values() if p.is_elite]),
        }
    
    def _get_seed_users(self) -> List[str]:
        """Get seed users for influence campaigns."""
        # Return top influencers
        sorted_influencers = sorted(
            self._influencer_profiles.items(),
            key=lambda x: x[1].influence_score,
            reverse=True
        )
        return [uid for uid, _ in sorted_influencers[:10]]
    
    def _get_amplification_strategy(self) -> str:
        """Get recommended amplification strategy."""
        return "influencer_seeding_with_social_proof"
    
    def _get_community_activation(self) -> Dict[str, Any]:
        """Get community activation recommendations."""
        return {
            "approach": "elite_reviewer_partnership",
            "content_type": "authentic_reviews",
        }
    
    def _get_audio_alignment(self, intelligence: AggregatedIntelligence) -> Dict[str, Any]:
        """Get audio advertising alignment."""
        return {
            "format": "local_business_spotlight",
            "tone": "authentic_community",
        }
    
    def _get_social_alignment(self, intelligence: AggregatedIntelligence) -> Dict[str, Any]:
        """Get social media alignment."""
        return {
            "platform": "instagram_local",
            "content_type": "user_generated",
        }
