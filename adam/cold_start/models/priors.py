# =============================================================================
# ADAM Enhancement #13: Prior Distribution Models
# Location: adam/cold_start/models/priors.py
# =============================================================================

"""
Prior distribution models for Bayesian cold start profiling.

These models implement:
- Beta distributions for mechanism effectiveness (conjugate to Bernoulli)
- Gaussian distributions for personality traits
- Hierarchical combination of prior levels
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, computed_field
import numpy as np

from .enums import (
    PriorSource, PersonalityTrait, ExtendedConstruct,
    CognitiveMechanism, ArchetypeID
)


class BetaDistribution(BaseModel):
    """
    Beta distribution parameters for mechanism effectiveness.
    
    Beta(α, β) is the conjugate prior for Bernoulli likelihood,
    making it ideal for binary outcomes (convert/no-convert).
    
    Properties:
    - mean = α / (α + β)
    - variance = αβ / ((α+β)²(α+β+1))
    - samples = α + β (pseudo-observations)
    """
    alpha: float = Field(ge=0.0, default=1.0, description="Success parameter")
    beta: float = Field(ge=0.0, default=1.0, description="Failure parameter")
    
    @computed_field
    @property
    def mean(self) -> float:
        """Expected value: α / (α + β)"""
        total = self.alpha + self.beta
        if total == 0:
            return 0.5
        return self.alpha / total
    
    @computed_field
    @property
    def variance(self) -> float:
        """Variance: αβ / ((α+β)²(α+β+1))"""
        total = self.alpha + self.beta
        if total == 0:
            return 0.25
        return (self.alpha * self.beta) / (total ** 2 * (total + 1))
    
    @computed_field
    @property
    def samples(self) -> int:
        """Effective sample size (pseudo-observations)."""
        return int(self.alpha + self.beta)
    
    @computed_field
    @property
    def uncertainty(self) -> float:
        """Uncertainty measure (0-1, higher = more uncertain)."""
        # Low sample count = high uncertainty
        return 1.0 / (1.0 + np.sqrt(self.alpha + self.beta))
    
    def sample(self) -> float:
        """Sample from the distribution (Thompson Sampling)."""
        if self.alpha == 0 and self.beta == 0:
            return 0.5
        return float(np.random.beta(max(0.001, self.alpha), max(0.001, self.beta)))
    
    def update(self, success: bool) -> "BetaDistribution":
        """
        Bayesian update with new observation.
        
        Args:
            success: Whether outcome was successful
            
        Returns:
            New BetaDistribution with updated parameters
        """
        if success:
            return BetaDistribution(alpha=self.alpha + 1, beta=self.beta)
        return BetaDistribution(alpha=self.alpha, beta=self.beta + 1)
    
    def blend(
        self, 
        other: "BetaDistribution", 
        weight: float = 0.5
    ) -> "BetaDistribution":
        """
        Blend with another distribution using weighted average.
        
        Args:
            other: Distribution to blend with
            weight: Weight for self (1-weight for other)
            
        Returns:
            Blended BetaDistribution
        """
        return BetaDistribution(
            alpha=self.alpha * weight + other.alpha * (1 - weight),
            beta=self.beta * weight + other.beta * (1 - weight)
        )


class GaussianDistribution(BaseModel):
    """
    Gaussian distribution for continuous traits like personality.
    
    Used for Big Five traits and extended constructs.
    """
    mean: float = Field(ge=0.0, le=1.0, default=0.5, description="Mean value")
    variance: float = Field(ge=0.0, default=0.04, description="Variance")
    
    @computed_field
    @property
    def std(self) -> float:
        """Standard deviation."""
        return float(np.sqrt(self.variance))
    
    @computed_field
    @property
    def confidence(self) -> float:
        """Confidence (inverse of uncertainty)."""
        # Lower variance = higher confidence
        return 1.0 / (1.0 + self.variance * 10)
    
    def sample(self) -> float:
        """Sample from distribution, clipped to [0, 1]."""
        sample = np.random.normal(self.mean, self.std)
        return float(np.clip(sample, 0.0, 1.0))
    
    def update(
        self, 
        observation: float, 
        observation_variance: float = 0.1
    ) -> "GaussianDistribution":
        """
        Bayesian update with new observation.
        
        Uses conjugate normal-normal update.
        """
        # Precision-weighted update
        prior_precision = 1.0 / max(self.variance, 0.001)
        obs_precision = 1.0 / max(observation_variance, 0.001)
        
        posterior_precision = prior_precision + obs_precision
        posterior_mean = (
            prior_precision * self.mean + obs_precision * observation
        ) / posterior_precision
        posterior_variance = 1.0 / posterior_precision
        
        return GaussianDistribution(
            mean=float(np.clip(posterior_mean, 0.0, 1.0)),
            variance=posterior_variance
        )


class TraitPrior(BaseModel):
    """Prior distribution for a single personality trait."""
    trait: PersonalityTrait
    distribution: GaussianDistribution
    source: PriorSource
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    observation_count: int = 0


class MechanismPrior(BaseModel):
    """Prior distribution for mechanism effectiveness."""
    mechanism: CognitiveMechanism
    distribution: BetaDistribution
    source: PriorSource
    archetype_source: Optional[ArchetypeID] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PsychologicalPrior(BaseModel):
    """
    Complete psychological prior for a user or archetype.
    
    Contains priors for all traits and mechanisms.
    """
    # Big Five trait priors
    trait_priors: Dict[PersonalityTrait, TraitPrior] = Field(
        default_factory=dict
    )
    
    # Extended construct priors
    extended_priors: Dict[ExtendedConstruct, TraitPrior] = Field(
        default_factory=dict
    )
    
    # Mechanism effectiveness priors
    mechanism_priors: Dict[CognitiveMechanism, MechanismPrior] = Field(
        default_factory=dict
    )
    
    # Metadata
    primary_source: PriorSource = PriorSource.POPULATION
    sources_used: List[PriorSource] = Field(default_factory=list)
    overall_confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_trait_mean(self, trait: PersonalityTrait) -> float:
        """Get mean value for a trait."""
        if trait in self.trait_priors:
            return self.trait_priors[trait].distribution.mean
        return 0.5  # Default neutral
    
    def get_mechanism_effectiveness(
        self, 
        mechanism: CognitiveMechanism
    ) -> float:
        """Get expected effectiveness for a mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].distribution.mean
        return 0.5  # Default neutral
    
    def sample_mechanism(
        self, 
        mechanism: CognitiveMechanism
    ) -> float:
        """Thompson sample for mechanism."""
        if mechanism in self.mechanism_priors:
            return self.mechanism_priors[mechanism].distribution.sample()
        return float(np.random.beta(1, 1))  # Uninformative prior
    
    def to_feature_dict(self) -> Dict[str, float]:
        """Convert to flat feature dictionary for ML models."""
        features = {}
        
        # Trait means
        for trait, prior in self.trait_priors.items():
            features[f"trait_{trait.value}_mean"] = prior.distribution.mean
            features[f"trait_{trait.value}_confidence"] = prior.confidence
        
        # Mechanism effectiveness
        for mech, prior in self.mechanism_priors.items():
            features[f"mechanism_{mech.value}_mean"] = prior.distribution.mean
            features[f"mechanism_{mech.value}_uncertainty"] = prior.distribution.uncertainty
        
        features["overall_confidence"] = self.overall_confidence
        
        return features


class HierarchicalPrior(BaseModel):
    """
    Hierarchical prior combining multiple levels.
    
    Levels (in order of specificity):
    1. Population (least specific)
    2. Cluster
    3. Demographic
    4. Contextual
    5. User historical (most specific, if available)
    
    More specific priors receive higher weight when available.
    """
    population_prior: Optional[PsychologicalPrior] = None
    cluster_prior: Optional[PsychologicalPrior] = None
    demographic_prior: Optional[PsychologicalPrior] = None
    contextual_prior: Optional[PsychologicalPrior] = None
    user_prior: Optional[PsychologicalPrior] = None
    
    # Combination weights (learned from data)
    level_weights: Dict[PriorSource, float] = Field(
        default_factory=lambda: {
            PriorSource.POPULATION: 0.1,
            PriorSource.CLUSTER: 0.2,
            PriorSource.DEMOGRAPHIC: 0.25,
            PriorSource.CONTEXTUAL: 0.2,
            PriorSource.HISTORICAL_USER: 0.25
        }
    )
    
    def compute_combined_prior(self) -> PsychologicalPrior:
        """
        Compute combined prior using hierarchical Bayesian combination.
        
        More specific priors receive higher weight when available.
        Uses precision-weighted combination for traits and
        weighted average for mechanism priors.
        """
        # Collect available priors with weights
        available: List[tuple] = []
        weight_sum = 0.0
        
        if self.population_prior:
            w = self.level_weights[PriorSource.POPULATION]
            available.append((self.population_prior, w))
            weight_sum += w
            
        if self.cluster_prior:
            w = self.level_weights[PriorSource.CLUSTER]
            available.append((self.cluster_prior, w))
            weight_sum += w
            
        if self.demographic_prior:
            w = self.level_weights[PriorSource.DEMOGRAPHIC]
            available.append((self.demographic_prior, w))
            weight_sum += w
            
        if self.contextual_prior:
            w = self.level_weights[PriorSource.CONTEXTUAL]
            available.append((self.contextual_prior, w))
            weight_sum += w
            
        if self.user_prior:
            w = self.level_weights[PriorSource.HISTORICAL_USER]
            available.append((self.user_prior, w))
            weight_sum += w
        
        # Normalize weights
        if weight_sum == 0 or not available:
            return self.population_prior or PsychologicalPrior()
        
        # Combine trait priors (precision-weighted)
        combined_traits: Dict[PersonalityTrait, TraitPrior] = {}
        for trait in PersonalityTrait:
            means = []
            variances = []
            weights = []
            
            for prior, weight in available:
                if trait in prior.trait_priors:
                    tp = prior.trait_priors[trait]
                    means.append(tp.distribution.mean)
                    variances.append(tp.distribution.variance)
                    weights.append(weight / weight_sum)
            
            if means:
                # Precision-weighted combination
                precisions = [1.0 / max(v, 0.001) for v in variances]
                total_precision = sum(p * w for p, w in zip(precisions, weights))
                combined_mean = sum(
                    m * p * w / total_precision 
                    for m, p, w in zip(means, precisions, weights)
                )
                combined_variance = 1.0 / total_precision
                
                combined_traits[trait] = TraitPrior(
                    trait=trait,
                    distribution=GaussianDistribution(
                        mean=float(np.clip(combined_mean, 0.0, 1.0)),
                        variance=combined_variance
                    ),
                    source=PriorSource.CLUSTER,  # Combined
                    confidence=1.0 - float(np.sqrt(combined_variance))
                )
        
        # Combine mechanism priors (weighted average)
        combined_mechs: Dict[CognitiveMechanism, MechanismPrior] = {}
        for mech in CognitiveMechanism:
            alphas = []
            betas = []
            weights = []
            
            for prior, weight in available:
                if mech in prior.mechanism_priors:
                    mp = prior.mechanism_priors[mech]
                    alphas.append(mp.distribution.alpha)
                    betas.append(mp.distribution.beta)
                    weights.append(weight / weight_sum)
            
            if alphas:
                # Weighted combination of Beta parameters
                combined_alpha = sum(a * w for a, w in zip(alphas, weights))
                combined_beta = sum(b * w for b, w in zip(betas, weights))
                
                combined_mechs[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=BetaDistribution(
                        alpha=combined_alpha,
                        beta=combined_beta
                    ),
                    source=PriorSource.CLUSTER  # Combined
                )
        
        # Build combined prior
        sources_used = [
            prior.primary_source for prior, _ in available
        ]
        
        overall_confidence = sum(
            prior.overall_confidence * (weight / weight_sum)
            for prior, weight in available
        )
        
        return PsychologicalPrior(
            trait_priors=combined_traits,
            mechanism_priors=combined_mechs,
            primary_source=PriorSource.CLUSTER,
            sources_used=sources_used,
            overall_confidence=overall_confidence
        )
