"""
Google Local Review Intelligence Extractor
==========================================

THE HYPERLOCAL PERSUASION LAYER

Unique Value: 666M reviews across 5M businesses with:
- Precise lat/lng coordinates (GPS-level targeting)
- Business response patterns (how companies handle criticism)
- Business categories with MISC attributes
- Related businesses (competitive graph)

Cookie-Less Power:
- Location → Archetype mapping (neighborhoods have personalities)
- Category × Location → Mechanism effectiveness
- Business response templates for local advertiser messaging
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Tuple
from dataclasses import dataclass
from collections import defaultdict
import math

from ..base_extractor import (
    BaseReviewExtractor,
    ExtractionResult,
    AggregatedIntelligence,
    DataSource,
    PsychologicalConstruct,
    Archetype,
    PersuasionMechanism,
)
from .. import IntelligenceLayer, ContextualSignal, AudienceSegment

logger = logging.getLogger(__name__)


# =============================================================================
# GOOGLE-SPECIFIC DATA STRUCTURES
# =============================================================================

@dataclass
class LocationProfile:
    """Psychological profile of a geographic location."""
    
    # Location identification
    state: str
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Aggregate psychology
    dominant_archetypes: Dict[str, float] = None  # archetype -> prevalence
    mechanism_effectiveness: Dict[str, float] = None  # mechanism -> effectiveness
    category_preferences: Dict[str, float] = None  # category -> affinity
    
    # Business characteristics
    avg_rating: float = 0.0
    price_distribution: Dict[str, float] = None  # "$" -> percentage
    response_rate: float = 0.0  # % of reviews with business response
    
    # Sample size
    review_count: int = 0
    business_count: int = 0


@dataclass
class BusinessResponsePattern:
    """Pattern extracted from business responses to reviews."""
    
    pattern_type: str  # "apology", "explanation", "invitation", "defense"
    template: str
    effectiveness: float  # Based on subsequent review sentiment
    
    # Context
    triggered_by: str  # What kind of review triggered this
    category: str
    rating_context: float  # Rating of review that triggered response


@dataclass
class CategoryLocationMatrix:
    """Mechanism effectiveness by category and location."""
    
    category: str
    location: str  # state or city
    
    # Mechanism effectiveness scores
    mechanisms: Dict[str, float]
    
    # What language works
    effective_phrases: List[str]
    ineffective_phrases: List[str]
    
    # Sample size
    sample_size: int


# =============================================================================
# GOOGLE LOCAL EXTRACTOR
# =============================================================================

class GoogleLocalExtractor(BaseReviewExtractor):
    """
    Extractor for Google Local (Google Maps) review data.
    
    This extractor builds:
    1. Location psychological profiles
    2. Category × Location mechanism matrices
    3. Business response pattern templates
    4. Competitive intelligence from related businesses
    """
    
    # State file mapping
    STATE_FILES = [
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "District_of_Columbia", "Florida", "Georgia",
        "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
        "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
        "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New_Hampshire",
        "New_Jersey", "New_Mexico", "New_York", "North_Carolina", "North_Dakota",
        "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode_Island",
        "South_Carolina", "South_Dakota", "Tennessee", "Texas", "Utah", "Vermont",
        "Virginia", "Washington", "West_Virginia", "Wisconsin", "Wyoming"
    ]
    
    def __init__(
        self,
        data_path: Path,
        batch_size: int = 1000,
        states_to_process: Optional[List[str]] = None,
    ):
        super().__init__(
            data_source=DataSource.GOOGLE_LOCAL,
            data_path=data_path,
            batch_size=batch_size,
        )
        self.states_to_process = states_to_process or self.STATE_FILES
        
        # Caches for efficiency
        self._business_cache: Dict[str, Dict[str, Any]] = {}
        self._location_profiles: Dict[str, LocationProfile] = {}
        self._category_location_matrices: Dict[Tuple[str, str], CategoryLocationMatrix] = {}
        self._response_patterns: List[BusinessResponsePattern] = []
        
        # Initialize category mappings
        self._init_category_mappings()
    
    def _init_category_mappings(self):
        """Map Google categories to psychological profiles."""
        self.category_archetypes = {
            # Service businesses
            "Beauty salon": {Archetype.LOVER: 0.4, Archetype.CREATOR: 0.3},
            "Hair salon": {Archetype.LOVER: 0.4, Archetype.CREATOR: 0.3},
            "Nail salon": {Archetype.LOVER: 0.4, Archetype.CAREGIVER: 0.2},
            "Spa": {Archetype.LOVER: 0.3, Archetype.CAREGIVER: 0.3},
            "Barber shop": {Archetype.EVERYMAN: 0.4, Archetype.HERO: 0.2},
            
            # Food & Dining
            "Restaurant": {Archetype.EVERYMAN: 0.3, Archetype.LOVER: 0.2},
            "Fast food restaurant": {Archetype.EVERYMAN: 0.5, Archetype.JESTER: 0.2},
            "Fine dining restaurant": {Archetype.RULER: 0.3, Archetype.LOVER: 0.3},
            "Coffee shop": {Archetype.SAGE: 0.2, Archetype.CREATOR: 0.2, Archetype.EVERYMAN: 0.2},
            
            # Automotive
            "Auto repair shop": {Archetype.HERO: 0.3, Archetype.CAREGIVER: 0.2},
            "Car dealer": {Archetype.RULER: 0.2, Archetype.HERO: 0.2},
            "Auto body shop": {Archetype.HERO: 0.3, Archetype.CREATOR: 0.2},
            
            # Health & Medical
            "Doctor": {Archetype.SAGE: 0.3, Archetype.CAREGIVER: 0.4},
            "Dentist": {Archetype.CAREGIVER: 0.3, Archetype.SAGE: 0.2},
            "Hospital": {Archetype.CAREGIVER: 0.4, Archetype.HERO: 0.2},
            
            # Professional Services
            "Lawyer": {Archetype.SAGE: 0.3, Archetype.HERO: 0.2, Archetype.RULER: 0.2},
            "Accountant": {Archetype.SAGE: 0.4, Archetype.RULER: 0.2},
            "Insurance agency": {Archetype.CAREGIVER: 0.3, Archetype.RULER: 0.2},
            "Real estate agency": {Archetype.EXPLORER: 0.2, Archetype.RULER: 0.2},
            
            # Retail
            "Clothing store": {Archetype.LOVER: 0.3, Archetype.CREATOR: 0.2},
            "Grocery store": {Archetype.EVERYMAN: 0.4, Archetype.CAREGIVER: 0.2},
            "Gift shop": {Archetype.LOVER: 0.3, Archetype.CREATOR: 0.2},
            
            # Recreation
            "Gym": {Archetype.HERO: 0.4, Archetype.EXPLORER: 0.2},
            "Park": {Archetype.EXPLORER: 0.3, Archetype.INNOCENT: 0.2},
            "Church": {Archetype.INNOCENT: 0.3, Archetype.SAGE: 0.2, Archetype.CAREGIVER: 0.2},
        }
        
        # Category to mechanism mapping
        self.category_mechanisms = {
            "Restaurant": {
                PersuasionMechanism.SOCIAL_PROOF: 0.9,
                PersuasionMechanism.LIKING: 0.8,
                PersuasionMechanism.SCARCITY: 0.4,
            },
            "Doctor": {
                PersuasionMechanism.AUTHORITY: 0.9,
                PersuasionMechanism.TRUST: 0.9,
                PersuasionMechanism.SOCIAL_PROOF: 0.7,
            },
            "Auto repair shop": {
                PersuasionMechanism.TRUST: 0.9,
                PersuasionMechanism.AUTHORITY: 0.7,
                PersuasionMechanism.VALUE_PROPOSITION: 0.8,
            },
            "Beauty salon": {
                PersuasionMechanism.LIKING: 0.9,
                PersuasionMechanism.SOCIAL_PROOF: 0.8,
                PersuasionMechanism.ASPIRATION: 0.7,
            },
            "Gym": {
                PersuasionMechanism.ASPIRATION: 0.9,
                PersuasionMechanism.SOCIAL_PROOF: 0.7,
                PersuasionMechanism.COMMITMENT_CONSISTENCY: 0.8,
            },
        }
    
    # =========================================================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # =========================================================================
    
    def iter_reviews(self) -> Iterator[Dict[str, Any]]:
        """Iterate over Google reviews across all states."""
        for state in self.states_to_process:
            review_file = self.data_path / f"review-{state}.json"
            if not review_file.exists():
                logger.warning(f"Review file not found: {review_file}")
                continue
            
            logger.info(f"Processing reviews for {state}")
            with open(review_file, 'r') as f:
                for line in f:
                    try:
                        review = json.loads(line.strip())
                        review['_state'] = state  # Add state context
                        yield review
                    except json.JSONDecodeError:
                        continue
    
    def iter_reviews_with_meta(
        self,
        state: str,
        load_meta: bool = True,
    ) -> Iterator[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]]:
        """Iterate over reviews with their business metadata."""
        # Load business metadata for this state
        if load_meta:
            self._load_business_meta(state)
        
        review_file = self.data_path / f"review-{state}.json"
        if not review_file.exists():
            return
        
        with open(review_file, 'r') as f:
            for line in f:
                try:
                    review = json.loads(line.strip())
                    review['_state'] = state
                    
                    # Get business metadata
                    gmap_id = review.get('gmap_id')
                    business_meta = self._business_cache.get(gmap_id) if gmap_id else None
                    
                    yield review, business_meta
                except json.JSONDecodeError:
                    continue
    
    def _load_business_meta(self, state: str):
        """Load business metadata for a state into cache."""
        meta_file = self.data_path / f"meta-{state}.json"
        if not meta_file.exists():
            return
        
        logger.info(f"Loading business metadata for {state}")
        with open(meta_file, 'r') as f:
            for line in f:
                try:
                    business = json.loads(line.strip())
                    gmap_id = business.get('gmap_id')
                    if gmap_id:
                        self._business_cache[gmap_id] = business
                except json.JSONDecodeError:
                    continue
    
    def extract_review_text(self, review: Dict[str, Any]) -> str:
        """Extract review text."""
        return review.get('text', '') or ''
    
    def extract_rating(self, review: Dict[str, Any]) -> Optional[float]:
        """Extract and normalize rating to 0-1."""
        rating = review.get('rating')
        if rating is not None:
            return float(rating) / 5.0
        return None
    
    def extract_helpful_signal(self, review: Dict[str, Any]) -> Optional[float]:
        """
        Google doesn't have explicit helpful votes, but we can infer from:
        - Whether business responded (indicates importance)
        - Review length (longer reviews tend to be more helpful)
        """
        has_response = review.get('resp') is not None
        text = self.extract_review_text(review)
        
        # Composite "helpful" score
        score = 0.0
        if has_response:
            score += 0.5  # Business thought it was worth responding to
        if len(text) > 100:
            score += 0.2
        if len(text) > 300:
            score += 0.2
        if review.get('pics'):
            score += 0.1  # Has photos = more effort
        
        return min(1.0, score)
    
    def extract_context(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Extract rich contextual information."""
        context = {
            'state': review.get('_state'),
            'timestamp': review.get('time'),
            'has_photos': review.get('pics') is not None,
            'has_response': review.get('resp') is not None,
            'gmap_id': review.get('gmap_id'),
        }
        
        # Add business context if available
        gmap_id = review.get('gmap_id')
        if gmap_id and gmap_id in self._business_cache:
            business = self._business_cache[gmap_id]
            context.update({
                'business_name': business.get('name'),
                'address': business.get('address'),
                'latitude': business.get('latitude'),
                'longitude': business.get('longitude'),
                'category': business.get('category', []),
                'avg_rating': business.get('avg_rating'),
                'price': business.get('price'),
                'misc_attributes': business.get('MISC', {}),
            })
        
        return context
    
    def get_unique_value(self) -> str:
        """Return what makes Google Local uniquely valuable."""
        return """
        HYPERLOCAL PERSUASION INTELLIGENCE
        
        1. GPS-LEVEL TARGETING: Precise lat/lng for every business
           → Build neighborhood personality profiles
           → Map: LOCATION → ARCHETYPE → MECHANISM_EFFECTIVENESS
        
        2. BUSINESS RESPONSE PATTERNS: How companies handle criticism
           → Extract successful response templates
           → Train: NEGATIVE_REVIEW → OPTIMAL_RESPONSE
        
        3. MISC ATTRIBUTES: Rich business characteristics
           → "Good for kids" → Family archetype
           → "Wheelchair accessible" → Inclusive messaging
           → Service options, atmosphere, amenities
        
        4. RELATED BUSINESSES: Google's competitive graph
           → Automatic competitive intelligence
           → Market positioning recommendations
        
        5. 666 MILLION REVIEWS: Massive scale across all 50 states
           → Statistical significance for any segment
           → Regional variation analysis
        """
    
    def extract_dataset_specific_signals(
        self, review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Google-specific signals."""
        signals = {}
        
        # Business response analysis
        resp = review.get('resp')
        if resp:
            signals['response_time_ms'] = resp.get('time')
            signals['response_text'] = resp.get('text', '')
            signals['response_pattern'] = self._classify_response_pattern(
                resp.get('text', ''),
                self.extract_review_text(review),
                self.extract_rating(review)
            )
        
        # Photo presence (visual evidence)
        pics = review.get('pics')
        if pics:
            signals['photo_count'] = len(pics)
            signals['has_visual_evidence'] = True
        
        # Reviewer patterns
        signals['reviewer_id'] = review.get('user_id')
        signals['reviewer_name'] = review.get('name')
        
        return signals
    
    def _classify_response_pattern(
        self,
        response_text: str,
        review_text: str,
        rating: Optional[float],
    ) -> str:
        """Classify the business response pattern."""
        if not response_text:
            return "none"
        
        response_lower = response_text.lower()
        
        # Detect pattern type
        if any(w in response_lower for w in ["sorry", "apologize", "regret"]):
            return "apology"
        elif any(w in response_lower for w in ["thank", "appreciate", "grateful"]):
            return "gratitude"
        elif any(w in response_lower for w in ["come back", "visit again", "see you"]):
            return "invitation"
        elif any(w in response_lower for w in ["contact", "call", "email", "reach out"]):
            return "follow_up"
        elif any(w in response_lower for w in ["explain", "clarify", "understand"]):
            return "explanation"
        else:
            return "generic"
    
    # =========================================================================
    # ECOSYSTEM OUTPUT METHODS
    # =========================================================================
    
    def format_for_dsp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for DSP (StackAdapt, The Trade Desk).
        
        DSPs need:
        - Contextual targeting segments (no cookies needed)
        - Location-based audience signals
        - Creative optimization data
        """
        return {
            "segment_type": "contextual_location",
            "scope": {
                "type": intelligence.scope_type,
                "value": intelligence.scope_value,
            },
            
            # Contextual targeting data
            "contextual_signals": {
                "location_archetype_profile": {
                    arch.value if hasattr(arch, 'value') else str(arch): score 
                    for arch, score in intelligence.archetype_prevalence.items()
                },
                "mechanism_effectiveness": {
                    mech.value if hasattr(mech, 'value') else str(mech): score
                    for mech, score in intelligence.mechanism_effectiveness.items()
                },
            },
            
            # Audience composition (for modeling)
            "audience_composition": {
                "psychological_constructs": {
                    const.value if hasattr(const, 'value') else str(const): dist
                    for const, dist in intelligence.construct_distributions.items()
                },
            },
            
            # Creative optimization
            "creative_guidance": {
                "top_performing_templates": intelligence.top_templates[:20],
                "recommended_mechanisms": self._get_top_mechanisms(
                    intelligence.mechanism_effectiveness, 3
                ),
                "avoid_mechanisms": self._get_bottom_mechanisms(
                    intelligence.mechanism_effectiveness, 2
                ),
            },
            
            # Metadata
            "sample_size": intelligence.sample_size,
            "confidence": min(1.0, intelligence.sample_size / 1000),
        }
    
    def format_for_ssp(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for SSP (iHeart).
        
        SSPs need:
        - Inventory value signals
        - Audience enrichment data
        - Yield optimization recommendations
        """
        return {
            "inventory_type": "location_contextual",
            "scope": {
                "type": intelligence.scope_type,
                "value": intelligence.scope_value,
            },
            
            # Inventory value signals
            "audience_value_signals": {
                # Premium audiences command higher CPMs
                "archetype_composition": {
                    arch.value if hasattr(arch, 'value') else str(arch): score
                    for arch, score in intelligence.archetype_prevalence.items()
                },
                
                # High-value archetypes for premium pricing
                "premium_segments": self._identify_premium_segments(
                    intelligence.archetype_prevalence
                ),
            },
            
            # Audience enrichment for better targeting
            "audience_enrichment": {
                "psychological_profile": {
                    const.value if hasattr(const, 'value') else str(const): dist.get("mean", 0)
                    for const, dist in intelligence.construct_distributions.items()
                },
                "mechanism_receptivity": {
                    mech.value if hasattr(mech, 'value') else str(mech): score
                    for mech, score in intelligence.mechanism_effectiveness.items()
                },
            },
            
            # Yield optimization
            "yield_optimization": {
                "recommended_advertisers": self._recommend_advertiser_categories(
                    intelligence.archetype_prevalence,
                    intelligence.mechanism_effectiveness
                ),
                "optimal_ad_formats": self._recommend_ad_formats(
                    intelligence.mechanism_effectiveness
                ),
            },
            
            "sample_size": intelligence.sample_size,
        }
    
    def format_for_agency(
        self, intelligence: AggregatedIntelligence
    ) -> Dict[str, Any]:
        """
        Format for Agency (WPP).
        
        Agencies need:
        - Strategic insights
        - Creative briefs
        - Cross-platform recommendations
        """
        return {
            "strategic_context": {
                "scope": {
                    "type": intelligence.scope_type,
                    "value": intelligence.scope_value,
                },
                "market_psychology": {
                    "dominant_archetypes": self._get_dominant_archetypes(
                        intelligence.archetype_prevalence, 3
                    ),
                    "psychological_constructs": {
                        const.value if hasattr(const, 'value') else str(const): dist
                        for const, dist in intelligence.construct_distributions.items()
                    },
                },
            },
            
            # Creative brief elements
            "creative_brief": {
                "recommended_tone": self._recommend_tone(
                    intelligence.archetype_prevalence
                ),
                "key_mechanisms": self._get_top_mechanisms(
                    intelligence.mechanism_effectiveness, 5
                ),
                "messaging_templates": intelligence.top_templates[:10],
                "visual_direction": self._recommend_visual_direction(
                    intelligence.archetype_prevalence
                ),
            },
            
            # Strategic recommendations
            "strategic_recommendations": {
                "positioning": self._recommend_positioning(
                    intelligence.archetype_prevalence,
                    intelligence.mechanism_effectiveness
                ),
                "differentiation_opportunities": self._identify_opportunities(
                    intelligence.archetype_prevalence,
                    intelligence.mechanism_effectiveness
                ),
            },
            
            # Cross-platform guidance
            "cross_platform": {
                "audio_recommendations": self._get_audio_recommendations(
                    intelligence.archetype_prevalence
                ),
                "digital_recommendations": self._get_digital_recommendations(
                    intelligence.mechanism_effectiveness
                ),
            },
            
            "sample_size": intelligence.sample_size,
            "confidence_level": "high" if intelligence.sample_size > 10000 else "medium",
        }
    
    # =========================================================================
    # GOOGLE-SPECIFIC EXTRACTION METHODS
    # =========================================================================
    
    def build_location_profile(
        self,
        state: str,
        city: Optional[str] = None,
    ) -> LocationProfile:
        """Build a psychological profile for a location."""
        profile = LocationProfile(
            state=state,
            city=city,
            dominant_archetypes={},
            mechanism_effectiveness={},
            category_preferences={},
        )
        
        # Aggregate across reviews for this location
        archetype_totals = defaultdict(float)
        mechanism_totals = defaultdict(list)
        category_counts = defaultdict(int)
        price_counts = defaultdict(int)
        response_count = 0
        total_rating = 0.0
        review_count = 0
        business_ids = set()
        
        for review, business in self.iter_reviews_with_meta(state):
            # Filter by city if specified
            if city and business:
                address = business.get('address', '')
                if city.lower() not in address.lower():
                    continue
            
            # Extract and aggregate
            result = self.extract_psychological_signals(review)
            
            # Archetypes
            for arch, score in result.archetypes.items():
                archetype_totals[arch] += score
            
            # Mechanisms
            for mech, score in result.mechanism_receptivity.items():
                mechanism_totals[mech].append(score)
            
            # Business-level data
            if business:
                business_ids.add(business.get('gmap_id'))
                
                # Categories
                for cat in business.get('category', []):
                    category_counts[cat] += 1
                
                # Price
                price = business.get('price')
                if price:
                    price_counts[price] += 1
                
                # Rating
                rating = business.get('avg_rating')
                if rating:
                    total_rating += rating
            
            # Response tracking
            if review.get('resp'):
                response_count += 1
            
            review_count += 1
            
            # Batch logging
            if review_count % 10000 == 0:
                logger.info(f"Processed {review_count} reviews for {state}")
        
        # Normalize and set profile
        if review_count > 0:
            # Normalize archetypes
            total_arch = sum(archetype_totals.values())
            if total_arch > 0:
                profile.dominant_archetypes = {
                    k.value if hasattr(k, 'value') else str(k): v / total_arch
                    for k, v in archetype_totals.items()
                }
            
            # Average mechanisms
            profile.mechanism_effectiveness = {
                k.value if hasattr(k, 'value') else str(k): sum(v) / len(v)
                for k, v in mechanism_totals.items() if v
            }
            
            # Category preferences
            total_cat = sum(category_counts.values())
            if total_cat > 0:
                profile.category_preferences = {
                    k: v / total_cat for k, v in category_counts.items()
                }
            
            # Price distribution
            total_price = sum(price_counts.values())
            if total_price > 0:
                profile.price_distribution = {
                    k: v / total_price for k, v in price_counts.items()
                }
            
            # Other metrics
            profile.avg_rating = total_rating / review_count if review_count > 0 else 0
            profile.response_rate = response_count / review_count
            profile.review_count = review_count
            profile.business_count = len(business_ids)
        
        return profile
    
    def extract_response_patterns(
        self,
        state: str,
        min_rating: float = 0.0,
        max_rating: float = 0.6,  # Focus on negative/neutral reviews
    ) -> List[BusinessResponsePattern]:
        """Extract business response patterns from reviews."""
        patterns = []
        
        for review, business in self.iter_reviews_with_meta(state):
            resp = review.get('resp')
            if not resp or not resp.get('text'):
                continue
            
            rating = self.extract_rating(review)
            if rating is None:
                continue
            
            # Filter by rating range
            if not (min_rating <= rating <= max_rating):
                continue
            
            review_text = self.extract_review_text(review)
            response_text = resp.get('text', '')
            
            # Classify pattern
            pattern_type = self._classify_response_pattern(
                response_text, review_text, rating
            )
            
            # Get category
            category = "Unknown"
            if business and business.get('category'):
                category = business['category'][0]
            
            # Calculate effectiveness (simplified - would need follow-up data)
            effectiveness = self._estimate_response_effectiveness(
                response_text, review_text, rating
            )
            
            patterns.append(BusinessResponsePattern(
                pattern_type=pattern_type,
                template=response_text[:500],  # Truncate long responses
                effectiveness=effectiveness,
                triggered_by=self._classify_review_complaint(review_text),
                category=category,
                rating_context=rating,
            ))
        
        return patterns
    
    def _classify_review_complaint(self, review_text: str) -> str:
        """Classify what the review is complaining about."""
        text_lower = review_text.lower()
        
        if any(w in text_lower for w in ["wait", "slow", "long time", "took forever"]):
            return "wait_time"
        elif any(w in text_lower for w in ["rude", "unfriendly", "attitude", "disrespectful"]):
            return "staff_attitude"
        elif any(w in text_lower for w in ["dirty", "unclean", "filthy", "gross"]):
            return "cleanliness"
        elif any(w in text_lower for w in ["expensive", "overpriced", "cost", "price"]):
            return "price"
        elif any(w in text_lower for w in ["quality", "broken", "didn't work", "defective"]):
            return "quality"
        else:
            return "general"
    
    def _estimate_response_effectiveness(
        self,
        response_text: str,
        review_text: str,
        rating: float,
    ) -> float:
        """Estimate how effective a business response is."""
        effectiveness = 0.5  # Base
        
        response_lower = response_text.lower()
        
        # Personalization signals
        if any(w in response_lower for w in ["your name", "you mentioned", "specifically"]):
            effectiveness += 0.1
        
        # Empathy signals
        if any(w in response_lower for w in ["understand", "sorry", "apologize"]):
            effectiveness += 0.15
        
        # Action signals
        if any(w in response_lower for w in ["will", "going to", "contact", "reach out"]):
            effectiveness += 0.15
        
        # Recovery offer
        if any(w in response_lower for w in ["free", "discount", "complimentary", "on us"]):
            effectiveness += 0.1
        
        return min(1.0, effectiveness)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_top_mechanisms(
        self,
        mechanisms: Dict[PersuasionMechanism, float],
        n: int,
    ) -> List[str]:
        """Get top n mechanisms."""
        sorted_mechs = sorted(
            mechanisms.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [
            m.value if hasattr(m, 'value') else str(m)
            for m, _ in sorted_mechs[:n]
        ]
    
    def _get_bottom_mechanisms(
        self,
        mechanisms: Dict[PersuasionMechanism, float],
        n: int,
    ) -> List[str]:
        """Get bottom n mechanisms (to avoid)."""
        sorted_mechs = sorted(
            mechanisms.items(),
            key=lambda x: x[1]
        )
        return [
            m.value if hasattr(m, 'value') else str(m)
            for m, _ in sorted_mechs[:n]
        ]
    
    def _get_dominant_archetypes(
        self,
        archetypes: Dict[Archetype, float],
        n: int,
    ) -> Dict[str, float]:
        """Get top n dominant archetypes."""
        sorted_archs = sorted(
            archetypes.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return {
            a.value if hasattr(a, 'value') else str(a): score
            for a, score in sorted_archs[:n]
        }
    
    def _identify_premium_segments(
        self,
        archetypes: Dict[Archetype, float],
    ) -> List[str]:
        """Identify premium audience segments (higher CPMs)."""
        premium_archetypes = {
            Archetype.RULER, Archetype.HERO, Archetype.SAGE, Archetype.CREATOR
        }
        
        premium = []
        for arch, score in archetypes.items():
            if arch in premium_archetypes and score > 0.1:
                premium.append(arch.value if hasattr(arch, 'value') else str(arch))
        
        return premium
    
    def _recommend_advertiser_categories(
        self,
        archetypes: Dict[Archetype, float],
        mechanisms: Dict[PersuasionMechanism, float],
    ) -> List[str]:
        """Recommend advertiser categories for this audience."""
        recommendations = []
        
        # Map archetypes to advertiser categories
        archetype_advertisers = {
            Archetype.RULER: ["luxury", "premium", "financial_services"],
            Archetype.HERO: ["fitness", "sports", "automotive"],
            Archetype.EXPLORER: ["travel", "outdoor", "adventure"],
            Archetype.SAGE: ["education", "technology", "consulting"],
            Archetype.CAREGIVER: ["healthcare", "insurance", "family"],
            Archetype.LOVER: ["beauty", "fashion", "hospitality"],
            Archetype.CREATOR: ["arts", "design", "diy"],
            Archetype.EVERYMAN: ["retail", "food", "entertainment"],
        }
        
        for arch, score in archetypes.items():
            if score > 0.15 and arch in archetype_advertisers:
                recommendations.extend(archetype_advertisers[arch])
        
        return list(set(recommendations))
    
    def _recommend_ad_formats(
        self,
        mechanisms: Dict[PersuasionMechanism, float],
    ) -> List[str]:
        """Recommend ad formats based on mechanism effectiveness."""
        formats = []
        
        if mechanisms.get(PersuasionMechanism.STORYTELLING, 0) > 0.6:
            formats.append("video_narrative")
            formats.append("podcast_host_read")
        
        if mechanisms.get(PersuasionMechanism.SOCIAL_PROOF, 0) > 0.6:
            formats.append("testimonial")
            formats.append("user_generated")
        
        if mechanisms.get(PersuasionMechanism.AUTHORITY, 0) > 0.6:
            formats.append("expert_endorsement")
            formats.append("data_driven")
        
        if mechanisms.get(PersuasionMechanism.SCARCITY, 0) > 0.6:
            formats.append("limited_time_offer")
            formats.append("flash_sale")
        
        return formats if formats else ["standard_display", "audio_spot"]
    
    def _recommend_tone(
        self,
        archetypes: Dict[Archetype, float],
    ) -> str:
        """Recommend creative tone based on archetype composition."""
        # Find dominant archetype
        if not archetypes:
            return "friendly_professional"
        
        dominant = max(archetypes, key=archetypes.get)
        
        tone_map = {
            Archetype.INNOCENT: "warm_optimistic",
            Archetype.SAGE: "informative_authoritative",
            Archetype.EXPLORER: "adventurous_inspiring",
            Archetype.OUTLAW: "bold_provocative",
            Archetype.MAGICIAN: "visionary_transformative",
            Archetype.HERO: "empowering_confident",
            Archetype.LOVER: "sensual_intimate",
            Archetype.JESTER: "playful_humorous",
            Archetype.EVERYMAN: "relatable_down_to_earth",
            Archetype.CAREGIVER: "nurturing_supportive",
            Archetype.RULER: "prestigious_commanding",
            Archetype.CREATOR: "innovative_expressive",
        }
        
        return tone_map.get(dominant, "friendly_professional")
    
    def _recommend_visual_direction(
        self,
        archetypes: Dict[Archetype, float],
    ) -> Dict[str, Any]:
        """Recommend visual creative direction."""
        if not archetypes:
            return {"style": "clean_modern", "colors": "neutral"}
        
        dominant = max(archetypes, key=archetypes.get)
        
        visual_map = {
            Archetype.INNOCENT: {
                "style": "light_airy",
                "colors": "pastels_white",
                "imagery": "nature_children_simplicity"
            },
            Archetype.SAGE: {
                "style": "clean_minimal",
                "colors": "blue_gray_white",
                "imagery": "books_technology_data"
            },
            Archetype.EXPLORER: {
                "style": "dynamic_outdoor",
                "colors": "earth_tones_green",
                "imagery": "landscapes_adventure_freedom"
            },
            Archetype.HERO: {
                "style": "bold_powerful",
                "colors": "red_black_gold",
                "imagery": "action_achievement_strength"
            },
            Archetype.RULER: {
                "style": "luxurious_refined",
                "colors": "gold_black_deep_blue",
                "imagery": "elegance_success_prestige"
            },
        }
        
        return visual_map.get(dominant, {
            "style": "clean_modern",
            "colors": "brand_aligned",
            "imagery": "contextual"
        })
    
    def _recommend_positioning(
        self,
        archetypes: Dict[Archetype, float],
        mechanisms: Dict[PersuasionMechanism, float],
    ) -> str:
        """Recommend brand positioning strategy."""
        dominant_arch = max(archetypes, key=archetypes.get) if archetypes else None
        top_mech = max(mechanisms, key=mechanisms.get) if mechanisms else None
        
        if dominant_arch == Archetype.RULER and top_mech == PersuasionMechanism.EXCLUSIVITY:
            return "premium_exclusive"
        elif dominant_arch == Archetype.EVERYMAN and top_mech == PersuasionMechanism.SOCIAL_PROOF:
            return "trusted_mainstream"
        elif dominant_arch == Archetype.HERO and top_mech == PersuasionMechanism.ASPIRATION:
            return "achievement_enabler"
        elif dominant_arch == Archetype.CAREGIVER:
            return "caring_reliable"
        elif dominant_arch == Archetype.EXPLORER:
            return "freedom_discovery"
        else:
            return "value_proposition"
    
    def _identify_opportunities(
        self,
        archetypes: Dict[Archetype, float],
        mechanisms: Dict[PersuasionMechanism, float],
    ) -> List[str]:
        """Identify differentiation opportunities."""
        opportunities = []
        
        # Find underserved mechanisms
        low_mechanisms = [
            m for m, score in mechanisms.items()
            if score < 0.3
        ]
        
        if PersuasionMechanism.HUMOR in low_mechanisms:
            opportunities.append("humor_differentiation")
        if PersuasionMechanism.NOSTALGIA in low_mechanisms:
            opportunities.append("heritage_story")
        if PersuasionMechanism.UNITY in low_mechanisms:
            opportunities.append("community_building")
        
        return opportunities
    
    def _get_audio_recommendations(
        self,
        archetypes: Dict[Archetype, float],
    ) -> Dict[str, Any]:
        """Get audio advertising recommendations (for iHeart)."""
        dominant = max(archetypes, key=archetypes.get) if archetypes else Archetype.EVERYMAN
        
        voice_map = {
            Archetype.SAGE: "authoritative_calm",
            Archetype.HERO: "energetic_confident",
            Archetype.JESTER: "playful_animated",
            Archetype.RULER: "prestigious_refined",
            Archetype.CAREGIVER: "warm_nurturing",
            Archetype.EVERYMAN: "friendly_relatable",
        }
        
        return {
            "voice_style": voice_map.get(dominant, "friendly_relatable"),
            "pacing": "moderate" if dominant in [Archetype.SAGE, Archetype.RULER] else "dynamic",
            "music_style": self._recommend_music_style(dominant),
        }
    
    def _recommend_music_style(self, archetype: Archetype) -> str:
        """Recommend background music style for audio ads."""
        music_map = {
            Archetype.INNOCENT: "acoustic_uplifting",
            Archetype.SAGE: "minimal_contemplative",
            Archetype.EXPLORER: "indie_adventurous",
            Archetype.HERO: "epic_triumphant",
            Archetype.JESTER: "upbeat_fun",
            Archetype.RULER: "orchestral_sophisticated",
            Archetype.CAREGIVER: "soft_emotional",
            Archetype.EVERYMAN: "pop_familiar",
        }
        return music_map.get(archetype, "neutral_background")
    
    def _get_digital_recommendations(
        self,
        mechanisms: Dict[PersuasionMechanism, float],
    ) -> Dict[str, Any]:
        """Get digital advertising recommendations."""
        return {
            "cta_style": self._recommend_cta(mechanisms),
            "landing_page_elements": self._recommend_landing_elements(mechanisms),
            "retargeting_strategy": self._recommend_retargeting(mechanisms),
        }
    
    def _recommend_cta(self, mechanisms: Dict[PersuasionMechanism, float]) -> str:
        """Recommend call-to-action style."""
        if mechanisms.get(PersuasionMechanism.SCARCITY, 0) > 0.6:
            return "urgency_driven"
        elif mechanisms.get(PersuasionMechanism.CURIOSITY, 0) > 0.6:
            return "discovery_oriented"
        elif mechanisms.get(PersuasionMechanism.SOCIAL_PROOF, 0) > 0.6:
            return "social_validation"
        else:
            return "value_focused"
    
    def _recommend_landing_elements(
        self, mechanisms: Dict[PersuasionMechanism, float]
    ) -> List[str]:
        """Recommend landing page elements."""
        elements = []
        
        if mechanisms.get(PersuasionMechanism.SOCIAL_PROOF, 0) > 0.5:
            elements.extend(["testimonials", "review_count", "trust_badges"])
        if mechanisms.get(PersuasionMechanism.AUTHORITY, 0) > 0.5:
            elements.extend(["expert_quotes", "certifications", "awards"])
        if mechanisms.get(PersuasionMechanism.SCARCITY, 0) > 0.5:
            elements.extend(["countdown_timer", "stock_indicator"])
        
        return elements if elements else ["clear_value_prop", "simple_form"]
    
    def _recommend_retargeting(
        self, mechanisms: Dict[PersuasionMechanism, float]
    ) -> str:
        """Recommend retargeting strategy."""
        if mechanisms.get(PersuasionMechanism.RECIPROCITY, 0) > 0.5:
            return "offer_escalation"
        elif mechanisms.get(PersuasionMechanism.SOCIAL_PROOF, 0) > 0.5:
            return "testimonial_sequence"
        else:
            return "benefit_reminder"
