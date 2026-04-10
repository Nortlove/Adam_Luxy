#!/usr/bin/env python3
"""
CONTEXT INTELLIGENCE MODULE
===========================

Provides context-aware mechanism selection based on domain/placement context.
Uses 693K domain-to-ad-category mappings to detect user mindset and adjust
mechanism effectiveness accordingly.

Integration Points:
- LangGraph: prefetch_context_intelligence node
- AoT: UserStateAtom (mindset), MechanismActivationAtom (adjustments)
- Neo4j: Domain nodes, Mindset-Mechanism relationships
- Learning: domain_context section in cold-start priors

Core Insight:
    Same ad, different contexts = different effectiveness
    News site (high attention) → Authority works well
    Entertainment (low attention) → Keep it simple, use liking
    E-commerce (purchase intent) → Scarcity works well
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DomainContext:
    """
    Context information derived from domain/placement.
    
    Attributes:
        domain: The website domain (e.g., "nytimes.com")
        category: IAB category (e.g., "News", "Entertainment", "Shopping")
        mindset: Inferred user mindset (e.g., "informed", "entertained", "purchasing")
        attention_level: Expected attention level (high/medium/low)
        mechanism_adjustments: Dict of mechanism → adjustment factor
        confidence: Confidence in the context detection (0-1)
    """
    domain: str
    category: str
    mindset: str
    attention_level: str  # high, medium, low
    mechanism_adjustments: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.8
    
    def get_adjusted_score(self, mechanism: str, base_score: float) -> float:
        """Apply context adjustment to mechanism score."""
        adjustment = self.mechanism_adjustments.get(mechanism, 1.0)
        return base_score * adjustment


@dataclass 
class MindsetProfile:
    """
    Profile for a user mindset state.
    
    Different mindsets have different receptivity to persuasion mechanisms.
    """
    mindset: str
    description: str
    attention_level: str
    cognitive_load: str  # low, medium, high
    purchase_intent: str  # none, browsing, considering, ready
    mechanism_effectiveness: Dict[str, float]
    recommended_complexity: str  # simple, moderate, detailed
    optimal_tone: str


# =============================================================================
# MINDSET DEFINITIONS
# =============================================================================

MINDSET_PROFILES = {
    "informed": MindsetProfile(
        mindset="informed",
        description="User is consuming news/educational content, high attention",
        attention_level="high",
        cognitive_load="high",
        purchase_intent="none",
        mechanism_effectiveness={
            "authority": 1.25,      # +25% - Trust experts
            "social_proof": 1.10,   # +10% - Others think so too
            "commitment": 1.15,     # +15% - Logical consistency
            "scarcity": 0.80,       # -20% - Seen as manipulative
            "liking": 0.90,         # -10% - Less emotional
            "reciprocity": 1.10,    # +10% - Value information
            "unity": 1.00,          # Neutral
        },
        recommended_complexity="detailed",
        optimal_tone="informative, credible",
    ),
    "entertained": MindsetProfile(
        mindset="entertained",
        description="User is consuming entertainment, lower attention",
        attention_level="low",
        cognitive_load="low",
        purchase_intent="none",
        mechanism_effectiveness={
            "authority": 0.85,      # -15% - Not in analytical mode
            "social_proof": 1.15,   # +15% - Goes with the crowd
            "commitment": 0.80,     # -20% - Not thinking deeply
            "scarcity": 1.10,       # +10% - FOMO active
            "liking": 1.30,         # +30% - Emotional state
            "reciprocity": 0.90,    # -10% - Transactional feels off
            "unity": 1.20,          # +20% - Community feeling
        },
        recommended_complexity="simple",
        optimal_tone="fun, engaging",
    ),
    "purchasing": MindsetProfile(
        mindset="purchasing",
        description="User is on e-commerce/shopping site, high purchase intent",
        attention_level="high",
        cognitive_load="medium",
        purchase_intent="considering",
        mechanism_effectiveness={
            "authority": 1.15,      # +15% - Expert recommendations
            "social_proof": 1.35,   # +35% - Reviews matter
            "commitment": 1.20,     # +20% - Already invested
            "scarcity": 1.40,       # +40% - Limited stock!
            "liking": 1.10,         # +10% - Brand affinity
            "reciprocity": 1.25,    # +25% - Free shipping, discounts
            "unity": 1.00,          # Neutral
        },
        recommended_complexity="moderate",
        optimal_tone="persuasive, value-focused",
    ),
    "social": MindsetProfile(
        mindset="social",
        description="User is on social media, peer-focused",
        attention_level="medium",
        cognitive_load="low",
        purchase_intent="browsing",
        mechanism_effectiveness={
            "authority": 0.90,      # -10% - Peer opinions > experts
            "social_proof": 1.45,   # +45% - Everyone doing it
            "commitment": 0.85,     # -15% - Scrolling mode
            "scarcity": 1.20,       # +20% - FOMO
            "liking": 1.35,         # +35% - Influencer effect
            "reciprocity": 1.00,    # Neutral
            "unity": 1.40,          # +40% - Tribe identity
        },
        recommended_complexity="simple",
        optimal_tone="conversational, relatable",
    ),
    "researching": MindsetProfile(
        mindset="researching",
        description="User is on reference/wiki/how-to site, information seeking",
        attention_level="high",
        cognitive_load="high",
        purchase_intent="considering",
        mechanism_effectiveness={
            "authority": 1.35,      # +35% - Expert sources
            "social_proof": 1.10,   # +10% - Validation
            "commitment": 1.25,     # +25% - Thorough process
            "scarcity": 0.70,       # -30% - Not impulsive
            "liking": 0.85,         # -15% - Logic over emotion
            "reciprocity": 1.20,    # +20% - Value good info
            "unity": 0.90,          # -10% - Individual decision
        },
        recommended_complexity="detailed",
        optimal_tone="educational, thorough",
    ),
    "relaxed": MindsetProfile(
        mindset="relaxed",
        description="User is on lifestyle/hobby content, casual browsing",
        attention_level="medium",
        cognitive_load="low",
        purchase_intent="browsing",
        mechanism_effectiveness={
            "authority": 1.00,      # Neutral
            "social_proof": 1.20,   # +20% - Community validation
            "commitment": 0.90,     # -10% - Not committed
            "scarcity": 1.10,       # +10% - Might spark interest
            "liking": 1.25,         # +25% - Enjoying content
            "reciprocity": 1.15,    # +15% - Generous mood
            "unity": 1.20,          # +20% - Shared interests
        },
        recommended_complexity="moderate",
        optimal_tone="friendly, aspirational",
    ),
    "professional": MindsetProfile(
        mindset="professional",
        description="User is on B2B/professional content",
        attention_level="high",
        cognitive_load="high",
        purchase_intent="considering",
        mechanism_effectiveness={
            "authority": 1.40,      # +40% - Credentials matter
            "social_proof": 1.25,   # +25% - Case studies
            "commitment": 1.30,     # +30% - ROI thinking
            "scarcity": 0.90,       # -10% - Rational decisions
            "liking": 0.80,         # -20% - Business focus
            "reciprocity": 1.20,    # +20% - Value exchange
            "unity": 1.15,          # +15% - Industry identity
        },
        recommended_complexity="detailed",
        optimal_tone="professional, results-oriented",
    ),
    "unknown": MindsetProfile(
        mindset="unknown",
        description="Unknown context, use neutral adjustments",
        attention_level="medium",
        cognitive_load="medium",
        purchase_intent="unknown",
        mechanism_effectiveness={
            "authority": 1.0,
            "social_proof": 1.0,
            "commitment": 1.0,
            "scarcity": 1.0,
            "liking": 1.0,
            "reciprocity": 1.0,
            "unity": 1.0,
        },
        recommended_complexity="moderate",
        optimal_tone="balanced",
    ),
}


# =============================================================================
# CATEGORY TO MINDSET MAPPING
# =============================================================================

CATEGORY_TO_MINDSET = {
    # News & Information
    "News": "informed",
    "News & Politics": "informed",
    "World News": "informed",
    "Business News": "informed",
    "Technology News": "informed",
    "Science": "informed",
    "Education": "researching",
    "Reference": "researching",
    
    # Entertainment
    "Entertainment": "entertained",
    "Movies": "entertained",
    "Television": "entertained",
    "Music": "entertained",
    "Gaming": "entertained",
    "Video Games": "entertained",
    "Humor": "entertained",
    "Celebrity": "entertained",
    
    # Shopping & E-commerce
    "Shopping": "purchasing",
    "E-Commerce": "purchasing",
    "Retail": "purchasing",
    "Classifieds": "purchasing",
    "Deals": "purchasing",
    "Coupons": "purchasing",
    "Auctions": "purchasing",
    
    # Social
    "Social Networking": "social",
    "Social Media": "social",
    "Forums": "social",
    "Community": "social",
    "Dating": "social",
    
    # Lifestyle & Hobbies
    "Lifestyle": "relaxed",
    "Home & Garden": "relaxed",
    "Food & Drink": "relaxed",
    "Travel": "relaxed",
    "Arts": "relaxed",
    "Hobbies": "relaxed",
    "Sports": "relaxed",
    "Fitness": "relaxed",
    "Fashion": "relaxed",
    "Beauty": "relaxed",
    "Automotive": "researching",
    
    # Professional & B2B
    "Business": "professional",
    "Finance": "professional",
    "Career": "professional",
    "Legal": "professional",
    "Real Estate": "professional",
    "Industry": "professional",
    
    # Health & Wellness
    "Health": "researching",
    "Medical": "researching",
    "Wellness": "relaxed",
    
    # Technology
    "Technology": "researching",
    "Software": "researching",
    "Hardware": "researching",
    "Mobile": "researching",
    
    # Default
    "General": "unknown",
    "Other": "unknown",
}


# =============================================================================
# CONTEXT DETECTION SERVICE
# =============================================================================

class ContextIntelligenceService:
    """
    Service for detecting context and adjusting mechanism effectiveness.
    
    Uses 693K domain mappings to determine user mindset and provide
    context-appropriate mechanism adjustments.
    """
    
    def __init__(self, domain_data_path: Optional[str] = None):
        """
        Initialize the context intelligence service.
        
        Args:
            domain_data_path: Path to domain mapping data (Parquet/JSON/Arrow)
        """
        self._domain_to_category: Dict[str, str] = {}
        self._loaded = False
        self._data_path = domain_data_path
        
        # Load domain data if path provided
        if domain_data_path:
            self._load_domain_data(domain_data_path)
    
    def _load_domain_data(self, path: str) -> None:
        """Load domain-to-category mappings from data file."""
        try:
            path = Path(path)
            
            if path.is_dir():
                # Arrow dataset format
                try:
                    from datasets import load_from_disk
                    ds = load_from_disk(str(path))
                    for row in ds['train'] if 'train' in ds else ds:
                        domain = row.get('domain', row.get('url', ''))
                        category = row.get('category', row.get('ad_category', ''))
                        if domain and category:
                            self._domain_to_category[domain.lower()] = category
                except Exception as e:
                    logger.warning(f"Could not load as Arrow dataset: {e}")
                    
            elif path.suffix == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._domain_to_category = {k.lower(): v for k, v in data.items()}
                    elif isinstance(data, list):
                        for item in data:
                            domain = item.get('domain', '')
                            category = item.get('category', '')
                            if domain and category:
                                self._domain_to_category[domain.lower()] = category
                                
            elif path.suffix == '.parquet':
                import pandas as pd
                df = pd.read_parquet(path)
                for _, row in df.iterrows():
                    domain = row.get('domain', row.get('url', ''))
                    category = row.get('category', row.get('ad_category', ''))
                    if domain and category:
                        self._domain_to_category[str(domain).lower()] = str(category)
            
            self._loaded = True
            logger.info(f"Loaded {len(self._domain_to_category):,} domain mappings")
            
        except Exception as e:
            logger.error(f"Failed to load domain data: {e}")
            self._loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """Check if domain data is loaded."""
        return self._loaded and len(self._domain_to_category) > 0
    
    @property
    def domain_count(self) -> int:
        """Number of domains loaded."""
        return len(self._domain_to_category)
    
    def get_category(self, domain: str) -> Optional[str]:
        """
        Get the ad category for a domain.
        
        Args:
            domain: Website domain (e.g., "nytimes.com")
            
        Returns:
            Category string or None if not found
        """
        if not domain:
            return None
            
        # Normalize domain
        domain = domain.lower().strip()
        
        # Remove protocol and www
        for prefix in ['https://', 'http://', 'www.']:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        
        # Remove path
        domain = domain.split('/')[0]
        
        # Try exact match
        if domain in self._domain_to_category:
            return self._domain_to_category[domain]
        
        # Try without subdomain
        parts = domain.split('.')
        if len(parts) > 2:
            parent = '.'.join(parts[-2:])
            if parent in self._domain_to_category:
                return self._domain_to_category[parent]
        
        return None
    
    def get_mindset(self, category: str) -> str:
        """
        Get the user mindset for a category.
        
        Args:
            category: IAB ad category
            
        Returns:
            Mindset string
        """
        if not category:
            return "unknown"
        return CATEGORY_TO_MINDSET.get(category, "unknown")
    
    def get_mindset_profile(self, mindset: str) -> MindsetProfile:
        """
        Get the full profile for a mindset.
        
        Args:
            mindset: Mindset string
            
        Returns:
            MindsetProfile with effectiveness adjustments
        """
        return MINDSET_PROFILES.get(mindset, MINDSET_PROFILES["unknown"])
    
    def detect_context(self, domain: str) -> DomainContext:
        """
        Detect full context from domain.
        
        Args:
            domain: Website domain
            
        Returns:
            DomainContext with all context information
        """
        category = self.get_category(domain)
        
        if category:
            mindset = self.get_mindset(category)
            profile = self.get_mindset_profile(mindset)
            confidence = 0.85
        else:
            # Infer from domain name
            mindset, confidence = self._infer_mindset_from_domain(domain)
            profile = self.get_mindset_profile(mindset)
            category = "Inferred"
        
        return DomainContext(
            domain=domain,
            category=category or "Unknown",
            mindset=mindset,
            attention_level=profile.attention_level,
            mechanism_adjustments=profile.mechanism_effectiveness,
            confidence=confidence,
        )
    
    def _infer_mindset_from_domain(self, domain: str) -> Tuple[str, float]:
        """
        Infer mindset from domain name when not in database.
        
        Returns:
            Tuple of (mindset, confidence)
        """
        domain_lower = domain.lower()
        
        # News indicators
        news_indicators = ['news', 'times', 'post', 'herald', 'tribune', 'journal', 
                         'daily', 'reuters', 'ap', 'bbc', 'cnn', 'nbc', 'abc', 'cbs']
        if any(ind in domain_lower for ind in news_indicators):
            return "informed", 0.70
        
        # Shopping indicators
        shop_indicators = ['shop', 'store', 'buy', 'deal', 'amazon', 'ebay', 'walmart',
                         'target', 'bestbuy', 'overstock', 'wayfair']
        if any(ind in domain_lower for ind in shop_indicators):
            return "purchasing", 0.75
        
        # Social indicators
        social_indicators = ['facebook', 'twitter', 'instagram', 'tiktok', 'reddit',
                           'linkedin', 'pinterest', 'snapchat', 'discord']
        if any(ind in domain_lower for ind in social_indicators):
            return "social", 0.80
        
        # Entertainment indicators
        entertainment_indicators = ['youtube', 'netflix', 'hulu', 'spotify', 'twitch',
                                   'video', 'movie', 'tv', 'stream', 'game']
        if any(ind in domain_lower for ind in entertainment_indicators):
            return "entertained", 0.70
        
        # Professional indicators
        professional_indicators = ['linkedin', 'salesforce', 'hubspot', 'b2b',
                                 'enterprise', 'business', 'corporate']
        if any(ind in domain_lower for ind in professional_indicators):
            return "professional", 0.65
        
        # Research indicators
        research_indicators = ['wiki', 'how', 'learn', 'edu', 'research', 'study',
                             'guide', 'tutorial', 'review']
        if any(ind in domain_lower for ind in research_indicators):
            return "researching", 0.60
        
        return "unknown", 0.30
    
    def get_mechanism_adjustments(
        self, 
        domain: str,
        base_scores: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Apply context adjustments to mechanism scores.
        
        Args:
            domain: Website domain
            base_scores: Base mechanism effectiveness scores
            
        Returns:
            Adjusted mechanism scores
        """
        context = self.detect_context(domain)
        
        adjusted = {}
        for mechanism, score in base_scores.items():
            adjusted[mechanism] = context.get_adjusted_score(mechanism, score)
        
        return adjusted
    
    def get_context_recommendation(self, domain: str) -> Dict[str, Any]:
        """
        Get full context recommendation for a domain.
        
        Args:
            domain: Website domain
            
        Returns:
            Dict with context info and recommendations
        """
        context = self.detect_context(domain)
        profile = self.get_mindset_profile(context.mindset)
        
        # Rank mechanisms by effectiveness
        sorted_mechs = sorted(
            context.mechanism_adjustments.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "domain": domain,
            "category": context.category,
            "mindset": context.mindset,
            "mindset_description": profile.description,
            "attention_level": context.attention_level,
            "cognitive_load": profile.cognitive_load,
            "purchase_intent": profile.purchase_intent,
            "confidence": context.confidence,
            "recommended_mechanisms": [m for m, _ in sorted_mechs[:3]],
            "avoid_mechanisms": [m for m, s in sorted_mechs if s < 0.9],
            "mechanism_adjustments": context.mechanism_adjustments,
            "recommended_complexity": profile.recommended_complexity,
            "optimal_tone": profile.optimal_tone,
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_context_service: Optional[ContextIntelligenceService] = None


def get_context_intelligence_service(
    data_path: Optional[str] = None
) -> ContextIntelligenceService:
    """
    Get the singleton context intelligence service.
    
    Args:
        data_path: Optional path to domain mapping data
        
    Returns:
        ContextIntelligenceService instance
    """
    global _context_service
    
    if _context_service is None:
        # Try default paths
        if data_path is None:
            default_paths = [
                "/Volumes/Sped/new_reviews_and_data/hf_datasets/domain_mapping",
                "data/domain_mapping",
                "data/learning/domain_mapping.json",
            ]
            for path in default_paths:
                if Path(path).exists():
                    data_path = path
                    break
        
        _context_service = ContextIntelligenceService(data_path)
        
        if _context_service.is_loaded:
            logger.info(
                f"Context intelligence service initialized with "
                f"{_context_service.domain_count:,} domains"
            )
        else:
            logger.warning(
                "Context intelligence service initialized without domain data. "
                "Context-based adjustments will use inference only."
            )
    
    return _context_service


def detect_context(domain: str) -> DomainContext:
    """
    Convenience function to detect context for a domain.
    
    Args:
        domain: Website domain
        
    Returns:
        DomainContext
    """
    service = get_context_intelligence_service()
    return service.detect_context(domain)


def get_context_adjustments(
    domain: str, 
    base_scores: Dict[str, float]
) -> Dict[str, float]:
    """
    Convenience function to get adjusted mechanism scores.
    
    Args:
        domain: Website domain
        base_scores: Base mechanism scores
        
    Returns:
        Adjusted scores
    """
    service = get_context_intelligence_service()
    return service.get_mechanism_adjustments(domain, base_scores)


# =============================================================================
# COLD-START PRIORS EXPORT
# =============================================================================

def export_context_priors() -> Dict[str, Any]:
    """
    Export context intelligence data for cold-start priors.
    
    Returns:
        Dict suitable for adding to complete_coldstart_priors.json
    """
    return {
        "domain_context": {
            "mindset_profiles": {
                name: {
                    "description": profile.description,
                    "attention_level": profile.attention_level,
                    "cognitive_load": profile.cognitive_load,
                    "purchase_intent": profile.purchase_intent,
                    "mechanism_effectiveness": profile.mechanism_effectiveness,
                    "recommended_complexity": profile.recommended_complexity,
                    "optimal_tone": profile.optimal_tone,
                }
                for name, profile in MINDSET_PROFILES.items()
            },
            "category_to_mindset": CATEGORY_TO_MINDSET,
            "version": "1.0",
            "source": "ansi-code/domain-advertising-classes-693k",
        }
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test without domain data
    service = get_context_intelligence_service()
    
    test_domains = [
        "nytimes.com",
        "amazon.com",
        "facebook.com",
        "youtube.com",
        "wikipedia.org",
        "linkedin.com",
        "unknown-domain.xyz",
    ]
    
    print("\n" + "="*60)
    print("CONTEXT INTELLIGENCE TEST")
    print("="*60)
    
    for domain in test_domains:
        result = service.get_context_recommendation(domain)
        print(f"\nDomain: {domain}")
        print(f"  Category: {result['category']}")
        print(f"  Mindset: {result['mindset']} ({result['mindset_description'][:50]}...)")
        print(f"  Attention: {result['attention_level']}")
        print(f"  Confidence: {result['confidence']:.0%}")
        print(f"  Top mechanisms: {', '.join(result['recommended_mechanisms'])}")
        print(f"  Recommended tone: {result['optimal_tone']}")
