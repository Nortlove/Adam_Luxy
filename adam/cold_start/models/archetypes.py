# =============================================================================
# ADAM Enhancement #13: Archetype Models
# Location: adam/cold_start/models/archetypes.py
# =============================================================================

"""
Psychological archetype models for cold start profiling.

Each archetype represents a research-grounded behavioral cluster with:
- Big Five trait profile (mean + variance)
- Regulatory focus distribution
- Mechanism effectiveness priors
- Message frame preferences
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, computed_field
import numpy as np

from .enums import (
    ArchetypeID, PersonalityTrait, CognitiveMechanism, 
    PriorSource
)
from .priors import (
    BetaDistribution, GaussianDistribution, TraitPrior,
    MechanismPrior, PsychologicalPrior
)


class ArchetypeTraitProfile(BaseModel):
    """
    Big Five trait profile for an archetype.
    
    Based on research literature for personality-behavior correlations.
    Each trait is a Gaussian with mean and variance.
    """
    openness: GaussianDistribution
    conscientiousness: GaussianDistribution
    extraversion: GaussianDistribution
    agreeableness: GaussianDistribution
    neuroticism: GaussianDistribution
    
    def to_dict(self) -> Dict[PersonalityTrait, GaussianDistribution]:
        """Convert to trait dictionary."""
        return {
            PersonalityTrait.OPENNESS: self.openness,
            PersonalityTrait.CONSCIENTIOUSNESS: self.conscientiousness,
            PersonalityTrait.EXTRAVERSION: self.extraversion,
            PersonalityTrait.AGREEABLENESS: self.agreeableness,
            PersonalityTrait.NEUROTICISM: self.neuroticism,
        }
    
    def similarity_to(
        self, 
        trait_values: Dict[PersonalityTrait, float]
    ) -> float:
        """
        Compute similarity to observed trait values.
        
        Uses Mahalanobis-like distance normalized to [0, 1].
        Higher = more similar.
        """
        profile_dict = self.to_dict()
        
        squared_distances = []
        for trait, dist in profile_dict.items():
            if trait in trait_values:
                diff = trait_values[trait] - dist.mean
                # Normalize by variance
                squared_dist = (diff ** 2) / max(dist.variance, 0.01)
                squared_distances.append(squared_dist)
        
        if not squared_distances:
            return 0.5  # No data
        
        # Convert distance to similarity
        mean_squared_dist = np.mean(squared_distances)
        similarity = np.exp(-mean_squared_dist / 2)
        
        return float(similarity)


class ArchetypeMechanismProfile(BaseModel):
    """
    Mechanism effectiveness profile for an archetype.
    
    Each mechanism has a Beta prior representing expected effectiveness.
    These are learned from outcome data and updated continuously.
    """
    mechanism_priors: Dict[CognitiveMechanism, BetaDistribution] = Field(
        default_factory=dict
    )
    
    def get_effectiveness(self, mechanism: CognitiveMechanism) -> float:
        """Get expected effectiveness for mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].mean
        return 0.5
    
    def sample_effectiveness(self, mechanism: CognitiveMechanism) -> float:
        """Thompson sample for mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].sample()
        return float(np.random.beta(1, 1))
    
    def get_top_mechanisms(self, n: int = 3) -> List[Tuple[CognitiveMechanism, float]]:
        """Get top N most effective mechanisms."""
        effectiveness = [
            (mech, prior.mean)
            for mech, prior in self.mechanism_priors.items()
        ]
        effectiveness.sort(key=lambda x: x[1], reverse=True)
        return effectiveness[:n]
    
    def update_mechanism(
        self, 
        mechanism: CognitiveMechanism, 
        success: bool
    ) -> None:
        """Update mechanism prior with new outcome."""
        if mechanism in self.mechanism_priors:
            self.mechanism_priors[mechanism] = \
                self.mechanism_priors[mechanism].update(success)


class ArchetypeDefinition(BaseModel):
    """
    Complete definition of a psychological archetype.
    
    Based on Jung's psychological types, validated through
    Big Five research and advertising response studies.
    """
    archetype_id: ArchetypeID
    name: str
    description: str
    
    # Trait profile
    trait_profile: ArchetypeTraitProfile
    
    # Extended constructs
    regulatory_focus_promotion: float = Field(ge=0.0, le=1.0, default=0.5)
    regulatory_focus_prevention: float = Field(ge=0.0, le=1.0, default=0.5)
    need_for_cognition: float = Field(ge=0.0, le=1.0, default=0.5)
    construal_level_abstract: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Mechanism effectiveness
    mechanism_profile: ArchetypeMechanismProfile
    
    # Message preferences
    preferred_message_frames: List[str] = Field(default_factory=list)
    avoided_message_frames: List[str] = Field(default_factory=list)
    
    # Performance tracking
    total_assignments: int = 0
    total_conversions: int = 0
    conversion_rate: float = 0.0
    
    # Metadata
    research_basis: str = ""
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def dominant_regulatory_focus(self) -> str:
        """Get dominant regulatory focus."""
        if self.regulatory_focus_promotion > self.regulatory_focus_prevention:
            return "promotion"
        return "prevention"
    
    def to_psychological_prior(self) -> PsychologicalPrior:
        """Convert archetype to psychological prior."""
        # Build trait priors
        trait_priors = {}
        for trait, dist in self.trait_profile.to_dict().items():
            trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=dist,
                source=PriorSource.ARCHETYPE,
                confidence=1.0 - dist.variance
            )
        
        # Build mechanism priors
        mechanism_priors = {}
        for mech, dist in self.mechanism_profile.mechanism_priors.items():
            mechanism_priors[mech] = MechanismPrior(
                mechanism=mech,
                distribution=dist,
                source=PriorSource.ARCHETYPE,
                archetype_source=self.archetype_id
            )
        
        return PsychologicalPrior(
            trait_priors=trait_priors,
            mechanism_priors=mechanism_priors,
            primary_source=PriorSource.ARCHETYPE,
            sources_used=[PriorSource.ARCHETYPE],
            overall_confidence=0.4  # Archetype is moderate confidence
        )


class ArchetypeMatchResult(BaseModel):
    """Result of archetype matching for a user."""
    matched_archetype: ArchetypeID
    confidence: float = Field(ge=0.0, le=1.0)
    
    # All archetype scores
    archetype_scores: Dict[ArchetypeID, float] = Field(default_factory=dict)
    
    # Matching method used
    matching_method: str = "trait_similarity"
    
    # Evidence used
    trait_evidence: Dict[PersonalityTrait, float] = Field(default_factory=dict)
    behavioral_evidence: List[str] = Field(default_factory=list)
    contextual_evidence: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def second_best_archetype(self) -> Optional[ArchetypeID]:
        """Get second-best matching archetype."""
        sorted_scores = sorted(
            self.archetype_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        if len(sorted_scores) >= 2:
            return sorted_scores[1][0]
        return None
    
    @computed_field
    @property
    def match_clarity(self) -> float:
        """
        How clearly the top archetype wins.
        High clarity = confident match, low clarity = could be multiple.
        """
        if len(self.archetype_scores) < 2:
            return 1.0
        
        sorted_scores = sorted(
            self.archetype_scores.values(), 
            reverse=True
        )
        if sorted_scores[0] == 0:
            return 0.0
        
        # Ratio of best to second-best
        clarity = 1.0 - (sorted_scores[1] / sorted_scores[0])
        return max(0.0, min(1.0, clarity))
