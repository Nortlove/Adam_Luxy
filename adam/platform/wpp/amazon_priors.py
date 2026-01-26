# =============================================================================
# ADAM WPP Amazon Priors Service
# Location: adam/platform/wpp/amazon_priors.py
# =============================================================================

"""
AMAZON PRIORS SERVICE

Psychological priors derived from Amazon review corpus.

WPP's unique asset: Access to anonymized, aggregated patterns
from Amazon reviews that reveal:
- Personality indicators from language patterns
- Category-specific psychological profiles
- Mechanism responsiveness by product type
- Regulatory focus tendencies

These priors bootstrap ADAM's reasoning for cold-start users
and validate ongoing predictions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


# =============================================================================
# PRIOR MODELS
# =============================================================================

class PersonalityPrior(BaseModel):
    """
    Personality prior from Amazon review patterns.
    """
    
    # Big Five tendencies
    openness: float = Field(ge=0.0, le=1.0, default=0.5)
    conscientiousness: float = Field(ge=0.0, le=1.0, default=0.5)
    extraversion: float = Field(ge=0.0, le=1.0, default=0.5)
    agreeableness: float = Field(ge=0.0, le=1.0, default=0.5)
    neuroticism: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Confidence in each dimension
    confidence: Dict[str, float] = Field(default_factory=dict)
    
    # Sample size
    review_count: int = Field(default=0, ge=0)


class MechanismPrior(BaseModel):
    """
    Mechanism responsiveness prior from Amazon data.
    """
    
    mechanism_id: str
    
    # Responsiveness score
    responsiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Evidence
    sample_size: int = Field(default=0, ge=0)
    evidence_strength: str = Field(default="moderate")  # "weak", "moderate", "strong"


class CategoryPrior(BaseModel):
    """
    Prior for a product/content category.
    """
    
    category_id: str
    category_name: str
    
    # Personality of typical buyers/consumers
    typical_personality: PersonalityPrior = Field(
        default_factory=PersonalityPrior
    )
    
    # Mechanism effectiveness in this category
    mechanism_priors: Dict[str, MechanismPrior] = Field(default_factory=dict)
    
    # Regulatory focus tendency
    regulatory_focus_tendency: str = Field(default="balanced")
    
    # Construal level tendency
    construal_tendency: str = Field(default="moderate")
    
    # Sample size
    total_reviews_analyzed: int = Field(default=0, ge=0)


class UserArchetypePrior(BaseModel):
    """
    Prior for a user archetype based on Amazon patterns.
    """
    
    archetype_id: str
    archetype_name: str
    description: str
    
    # Personality profile
    personality: PersonalityPrior = Field(default_factory=PersonalityPrior)
    
    # Mechanism responsiveness
    mechanism_responsiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Category affinities
    category_affinities: Dict[str, float] = Field(default_factory=dict)
    
    # Population percentage
    population_percentage: float = Field(ge=0.0, le=1.0, default=0.1)


# =============================================================================
# AMAZON PRIORS SERVICE
# =============================================================================

class AmazonPriorService:
    """
    Service for accessing Amazon-derived psychological priors.
    
    These priors are pre-computed from aggregated, anonymized
    Amazon review patterns and stored in cache.
    """
    
    # Default category priors (would be loaded from database)
    DEFAULT_CATEGORY_PRIORS = {
        "automotive": CategoryPrior(
            category_id="automotive",
            category_name="Automotive",
            typical_personality=PersonalityPrior(
                openness=0.5,
                conscientiousness=0.7,
                extraversion=0.5,
                agreeableness=0.5,
                neuroticism=0.4,
            ),
            mechanism_priors={
                "social_proof": MechanismPrior(mechanism_id="social_proof", responsiveness=0.7),
                "scarcity": MechanismPrior(mechanism_id="scarcity", responsiveness=0.6),
                "identity_construction": MechanismPrior(mechanism_id="identity_construction", responsiveness=0.8),
            },
            regulatory_focus_tendency="promotion",
            total_reviews_analyzed=50000,
        ),
        "electronics": CategoryPrior(
            category_id="electronics",
            category_name="Electronics",
            typical_personality=PersonalityPrior(
                openness=0.7,
                conscientiousness=0.6,
                extraversion=0.5,
                agreeableness=0.5,
                neuroticism=0.5,
            ),
            mechanism_priors={
                "social_proof": MechanismPrior(mechanism_id="social_proof", responsiveness=0.8),
                "anchoring": MechanismPrior(mechanism_id="anchoring", responsiveness=0.7),
            },
            regulatory_focus_tendency="prevention",
            total_reviews_analyzed=100000,
        ),
        "fashion": CategoryPrior(
            category_id="fashion",
            category_name="Fashion",
            typical_personality=PersonalityPrior(
                openness=0.7,
                conscientiousness=0.5,
                extraversion=0.7,
                agreeableness=0.6,
                neuroticism=0.5,
            ),
            mechanism_priors={
                "identity_construction": MechanismPrior(mechanism_id="identity_construction", responsiveness=0.9),
                "mimetic_desire": MechanismPrior(mechanism_id="mimetic_desire", responsiveness=0.8),
                "social_proof": MechanismPrior(mechanism_id="social_proof", responsiveness=0.7),
            },
            regulatory_focus_tendency="promotion",
            total_reviews_analyzed=80000,
        ),
        "health": CategoryPrior(
            category_id="health",
            category_name="Health & Wellness",
            typical_personality=PersonalityPrior(
                openness=0.6,
                conscientiousness=0.7,
                extraversion=0.5,
                agreeableness=0.6,
                neuroticism=0.5,
            ),
            mechanism_priors={
                "regulatory_focus": MechanismPrior(mechanism_id="regulatory_focus", responsiveness=0.8),
                "social_proof": MechanismPrior(mechanism_id="social_proof", responsiveness=0.7),
            },
            regulatory_focus_tendency="prevention",
            total_reviews_analyzed=60000,
        ),
    }
    
    # Default archetype priors
    DEFAULT_ARCHETYPES = {
        "explorer": UserArchetypePrior(
            archetype_id="explorer",
            archetype_name="Explorer",
            description="Open to new experiences, seeks variety",
            personality=PersonalityPrior(openness=0.8, extraversion=0.6),
            mechanism_responsiveness={
                "identity_construction": 0.7,
                "mimetic_desire": 0.6,
            },
            population_percentage=0.15,
        ),
        "achiever": UserArchetypePrior(
            archetype_id="achiever",
            archetype_name="Achiever",
            description="Goal-oriented, conscientious",
            personality=PersonalityPrior(conscientiousness=0.8, openness=0.6),
            mechanism_responsiveness={
                "regulatory_focus": 0.8,
                "goal_gradient": 0.7,
            },
            population_percentage=0.20,
        ),
        "guardian": UserArchetypePrior(
            archetype_id="guardian",
            archetype_name="Guardian",
            description="Risk-averse, values security",
            personality=PersonalityPrior(conscientiousness=0.7, neuroticism=0.6),
            mechanism_responsiveness={
                "scarcity": 0.5,
                "social_proof": 0.8,
            },
            population_percentage=0.25,
        ),
        "connector": UserArchetypePrior(
            archetype_id="connector",
            archetype_name="Connector",
            description="Social, values relationships",
            personality=PersonalityPrior(extraversion=0.8, agreeableness=0.7),
            mechanism_responsiveness={
                "social_proof": 0.9,
                "mimetic_desire": 0.8,
            },
            population_percentage=0.20,
        ),
    }
    
    def __init__(self, cache: Optional[ADAMRedisCache] = None):
        self.cache = cache
        self.category_priors = self.DEFAULT_CATEGORY_PRIORS.copy()
        self.archetypes = self.DEFAULT_ARCHETYPES.copy()
    
    async def get_category_prior(
        self,
        category_id: str,
    ) -> Optional[CategoryPrior]:
        """Get psychological prior for a category."""
        # Check cache first
        if self.cache:
            cache_key = f"adam:amazon_prior:category:{category_id}"
            cached = await self.cache.get(cache_key)
            if cached:
                return CategoryPrior(**cached) if isinstance(cached, dict) else cached
        
        # Return default
        return self.category_priors.get(category_id)
    
    async def get_mechanism_prior(
        self,
        category_id: str,
        mechanism_id: str,
    ) -> Optional[MechanismPrior]:
        """Get mechanism prior for a category."""
        category_prior = await self.get_category_prior(category_id)
        if category_prior:
            return category_prior.mechanism_priors.get(mechanism_id)
        return None
    
    async def get_archetype_prior(
        self,
        archetype_id: str,
    ) -> Optional[UserArchetypePrior]:
        """Get archetype prior."""
        return self.archetypes.get(archetype_id)
    
    async def match_user_to_archetype(
        self,
        personality_features: Dict[str, float],
    ) -> tuple:
        """
        Match a user's features to the best archetype.
        
        Returns: (archetype_id, confidence)
        """
        best_match = None
        best_score = -1.0
        
        for archetype_id, archetype in self.archetypes.items():
            score = self._compute_archetype_match(
                personality_features,
                archetype.personality,
            )
            if score > best_score:
                best_score = score
                best_match = archetype_id
        
        return best_match, best_score
    
    def _compute_archetype_match(
        self,
        user_features: Dict[str, float],
        archetype_personality: PersonalityPrior,
    ) -> float:
        """Compute match score between user and archetype."""
        score = 0.0
        count = 0
        
        arch_dict = archetype_personality.model_dump()
        
        for dim in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            if dim in user_features and dim in arch_dict:
                # Inverse of distance
                distance = abs(user_features[dim] - arch_dict[dim])
                score += 1.0 - distance
                count += 1
        
        return score / count if count > 0 else 0.5
    
    async def inject_priors_into_context(
        self,
        category_id: str,
        user_features: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Build prior context for injection into Claude prompts.
        
        This is the key integration point - priors from Amazon
        are formatted for Claude to use in reasoning.
        """
        context = {
            "has_amazon_priors": True,
            "category_insights": {},
            "archetype_match": None,
        }
        
        # Get category prior
        category_prior = await self.get_category_prior(category_id)
        if category_prior:
            context["category_insights"] = {
                "category": category_prior.category_name,
                "typical_personality": category_prior.typical_personality.model_dump(),
                "regulatory_tendency": category_prior.regulatory_focus_tendency,
                "construal_tendency": category_prior.construal_tendency,
                "mechanism_priors": {
                    m_id: m.responsiveness
                    for m_id, m in category_prior.mechanism_priors.items()
                },
                "sample_size": category_prior.total_reviews_analyzed,
            }
        
        # Match to archetype if features provided
        if user_features:
            archetype_id, confidence = await self.match_user_to_archetype(user_features)
            if archetype_id:
                archetype = await self.get_archetype_prior(archetype_id)
                if archetype:
                    context["archetype_match"] = {
                        "archetype": archetype.archetype_name,
                        "description": archetype.description,
                        "confidence": confidence,
                        "mechanism_hints": archetype.mechanism_responsiveness,
                    }
        
        return context
