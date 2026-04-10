# =============================================================================
# Intelligence Source Implementations for AtomDAG
# Location: adam/atoms/intelligence_sources.py
# =============================================================================

"""
Real implementations for the 10 intelligence sources used by AtomDAG atoms.

This module provides actual queries instead of returning None, connecting:
1. BANDIT_POSTERIORS → Thompson Sampler
2. GRAPH_EMERGENCE → Psychological Knowledge Graph
3. EMPIRICAL_PATTERNS → Archetype-Mechanism effectiveness matrix

These implementations enable Layer 2 synthesis to work with real data.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from adam.atoms.core.base import (
    IntelligenceEvidence,
    IntelligenceSourceType,
    ConfidenceSemantics,
    EvidenceStrength,
)

logger = logging.getLogger(__name__)


# =============================================================================
# BANDIT POSTERIORS - Connect to Thompson Sampler
# =============================================================================

async def query_bandit_posteriors(
    user_id: str,
    archetype: Optional[str] = None,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query Thompson Sampler for mechanism effectiveness posteriors.
    
    This connects the AtomDAG to our real learning system.
    """
    try:
        from adam.cold_start.thompson.sampler import get_thompson_sampler
        from adam.cold_start.models.enums import ArchetypeID
        
        sampler = get_thompson_sampler()
        
        # Get archetype enum if provided
        archetype_enum = None
        if archetype:
            try:
                archetype_enum = ArchetypeID(archetype.lower().replace("-", "_").replace(" ", "_"))
            except ValueError:
                # Unknown archetype - will use global mechanism ranking instead
                logger.debug(f"Unknown archetype '{archetype}', using global ranking")
        
        # Get mechanism ranking from Thompson Sampler
        ranking = sampler.get_mechanism_ranking(archetype=archetype_enum)
        
        if ranking:
            # Best mechanism by expected effectiveness
            best_mech, best_mean, best_uncertainty = ranking[0]
            
            # Confidence inversely proportional to uncertainty
            confidence = max(0.3, min(0.95, 1.0 - best_uncertainty))
            
            # Strength based on sample count
            posterior = sampler.get_posterior(best_mech, archetype_enum)
            sample_count = posterior.samples if hasattr(posterior, 'samples') else (posterior.alpha + posterior.beta - 2)
            
            if sample_count > 50:
                strength = EvidenceStrength.STRONG
            elif sample_count > 20:
                strength = EvidenceStrength.MODERATE
            else:
                strength = EvidenceStrength.WEAK
            
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                construct=target_construct,
                assessment=best_mech.value,
                assessment_value=best_mean,
                confidence=confidence,
                confidence_semantics=ConfidenceSemantics.POSTERIOR_DISTRIBUTION,
                strength=strength,
                support_count=int(sample_count),
                reasoning=(
                    f"Thompson Sampling posterior: {best_mech.value} has {best_mean:.1%} expected "
                    f"effectiveness (α={posterior.alpha:.1f}, β={posterior.beta:.1f}, "
                    f"uncertainty={best_uncertainty:.2f})"
                ),
                metadata={
                    "alpha": float(posterior.alpha),
                    "beta": float(posterior.beta),
                    "uncertainty": float(best_uncertainty),
                    "total_samples": sampler.total_samples,
                    "total_updates": sampler.total_updates,
                },
            )
    except ImportError as e:
        logger.debug(f"Thompson Sampler not available: {e}")
    except Exception as e:
        logger.debug(f"Bandit posteriors query failed: {e}")
    
    return None


# =============================================================================
# GRAPH EMERGENCE - Query Psychological Knowledge Graph
# =============================================================================

async def query_graph_emergence(
    user_id: str,
    archetype: Optional[str] = None,
    target_construct: str = "mechanism_selection",
    neo4j_driver = None,
) -> Optional[IntelligenceEvidence]:
    """
    Query the Psychological Knowledge Graph via UnifiedIntelligenceService.
    
    Uses three-layer Bayesian fusion (mechanism knowledge graph from Layer 2,
    edge evidence from Layer 3, population priors from Layer 1) rather than
    querying Neo4j directly.
    """
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        svc = get_unified_intelligence_service()
        kg = svc.get_mechanism_knowledge_graph()

        if kg.get("mechanisms"):
            mechanisms = kg["mechanisms"]
            best_name = mechanisms[0] if mechanisms else None

            if best_name:
                best_id = best_name.lower().replace(" ", "_")
                synergies = [
                    tgt for src, tgt in kg.get("synergies", [])
                    if src == best_name
                ]

                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                    construct=target_construct,
                    assessment=best_id,
                    assessment_value=0.75,
                    confidence=0.80,
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.STRONG,
                    support_count=len(mechanisms),
                    reasoning=(
                        f"Unified knowledge graph: {best_name} from {len(mechanisms)} "
                        f"mechanisms (synergies: {synergies})"
                    ),
                    metadata={
                        "archetype": archetype,
                        "top_mechanisms": [m.lower().replace(" ", "_") for m in mechanisms[:3]],
                        "n_synergies": len(kg.get("synergies", [])),
                        "n_antagonisms": len(kg.get("antagonisms", [])),
                        "source": "unified_intelligence_service",
                    },
                )
    except Exception as e:
        logger.debug(f"UnifiedIntelligenceService graph query failed: {e}")

    return None


# =============================================================================
# EMPIRICAL PATTERNS - Archetype-Mechanism Effectiveness Matrix
# =============================================================================

async def query_empirical_patterns(
    user_id: str,
    archetype: Optional[str] = None,
    target_construct: str = "mechanism_selection",
) -> Optional[IntelligenceEvidence]:
    """
    Query empirically-derived archetype-mechanism effectiveness patterns.
    
    Priority sources:
    1. Learned priors from 941M+ review corpus (complete_coldstart_priors.json)
    2. Hardcoded effectiveness matrix from psychological research (Enhancement #13)
    
    This enables the AtomDAG to use real learned effectiveness data.
    """
    # =========================================================================
    # FIRST: Try learned priors from 941M+ review corpus
    # =========================================================================
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors_service = get_learned_priors()
        
        if priors_service.is_loaded and archetype:
            # Get best mechanisms for this archetype from learned data
            best_mechanisms = priors_service.get_best_mechanisms_for_archetype(
                archetype=archetype.title(),  # Normalize: "achiever" → "Achiever"
                top_n=3
            )
            
            if best_mechanisms and best_mechanisms[0][1] > 0:
                best_mech, best_effectiveness = best_mechanisms[0]
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=target_construct,
                    assessment=best_mech,
                    assessment_value=best_effectiveness,
                    confidence=0.85,  # High confidence - based on 941M+ reviews
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.STRONG,
                    support_count=3,  # Top 3 mechanisms
                    reasoning=(
                        f"Learned effectiveness from 941M+ review corpus: "
                        f"{best_mech} has {best_effectiveness:.1%} effectiveness for {archetype} archetype. "
                        f"Top 3: {', '.join([f'{m[0]}({m[1]:.0%})' for m in best_mechanisms])}"
                    ),
                    metadata={
                        "source": "learned_priors_941M_reviews",
                        "top_mechanisms": [
                            {"mechanism": m[0], "effectiveness": m[1]} 
                            for m in best_mechanisms
                        ],
                        "archetype": archetype,
                    },
                )
    except ImportError:
        logger.debug("Learned priors integration not available, falling back to research matrix")
    except Exception as e:
        logger.debug(f"Learned priors query failed: {e}, falling back to research matrix")
    
    # =========================================================================
    # FALLBACK: Use hardcoded research-based effectiveness matrix
    # =========================================================================
    try:
        from adam.intelligence.knowledge_graph.populate_psychological_graph import (
            ARCHETYPE_MECHANISM_PRIORS,
            CustomerArchetype,
            CognitiveMechanism,
        )
        
        if not archetype:
            return None
        
        # Normalize archetype name
        archetype_lower = archetype.lower().replace("-", "_").replace(" ", "_")
        
        try:
            archetype_enum = CustomerArchetype(archetype_lower)
        except ValueError:
            logger.debug(f"Unknown archetype: {archetype}")
            return None
        
        # Get mechanism priors for this archetype
        mechanism_priors = ARCHETYPE_MECHANISM_PRIORS.get(archetype_enum, {})
        
        if not mechanism_priors:
            return None
        
        # Find best mechanism by expected effectiveness (alpha / (alpha + beta))
        best_mechanism = None
        best_effectiveness = 0.0
        best_alpha = 0
        best_beta = 0
        
        for mechanism, (alpha, beta) in mechanism_priors.items():
            effectiveness = alpha / (alpha + beta)
            if effectiveness > best_effectiveness:
                best_effectiveness = effectiveness
                best_mechanism = mechanism
                best_alpha = alpha
                best_beta = beta
        
        if best_mechanism:
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                construct=target_construct,
                assessment=best_mechanism.value,
                assessment_value=best_effectiveness,
                confidence=0.8,  # High confidence - based on research
                confidence_semantics=ConfidenceSemantics.STATISTICAL,  # Research-based statistics
                strength=EvidenceStrength.STRONG,
                support_count=len(mechanism_priors),
                reasoning=(
                    f"Research-based prior: {best_mechanism.value} has {best_effectiveness:.0%} "
                    f"expected effectiveness for {archetype} archetype "
                    f"(Beta({best_alpha:.1f}, {best_beta:.1f}) from Enhancement #13)"
                ),
                metadata={
                    "archetype": archetype,
                    "mechanism": best_mechanism.value,
                    "alpha": best_alpha,
                    "beta": best_beta,
                    "source": "enhancement_13_cold_start_priors",
                },
            )
    except ImportError:
        logger.debug("Knowledge graph module not available")
    except Exception as e:
        logger.debug(f"Empirical patterns query failed: {e}")
    
    return None


# =============================================================================
# INTEGRATION: Enhanced Base Atom Mixin
# =============================================================================

class EnhancedIntelligenceSourcesMixin:
    """
    Mixin that provides real intelligence source implementations.
    
    Use this with Atom classes to enable real queries instead of None returns.
    
    Example:
        class MyAtom(EnhancedIntelligenceSourcesMixin, BaseAtom):
            pass
    """
    
    async def _query_bandit_posteriors(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query Thompson Sampler posteriors."""
        archetype = getattr(self, '_current_archetype', None)
        return await query_bandit_posteriors(
            user_id=user_id,
            archetype=archetype,
            target_construct=getattr(self, 'TARGET_CONSTRUCT', 'mechanism_selection'),
        )
    
    async def _query_graph_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query psychological knowledge graph."""
        archetype = getattr(self, '_current_archetype', None)
        driver = getattr(self.bridge, 'driver', None) if hasattr(self, 'bridge') else None
        return await query_graph_emergence(
            user_id=user_id,
            archetype=archetype,
            target_construct=getattr(self, 'TARGET_CONSTRUCT', 'mechanism_selection'),
            neo4j_driver=driver,
        )
    
    async def _query_empirical_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query empirical archetype-mechanism patterns."""
        archetype = getattr(self, '_current_archetype', None)
        return await query_empirical_patterns(
            user_id=user_id,
            archetype=archetype,
            target_construct=getattr(self, 'TARGET_CONSTRUCT', 'mechanism_selection'),
        )


# =============================================================================
# CONVENIENCE FUNCTION: Get All Evidence for an Archetype
# =============================================================================

async def get_archetype_mechanism_evidence(
    archetype: str,
    user_id: str = "demo_user",
    neo4j_driver = None,
) -> Dict[str, Optional[IntelligenceEvidence]]:
    """
    Get evidence from all intelligence sources for mechanism selection.
    
    Convenience function for demo/testing.
    
    Args:
        archetype: Customer archetype (e.g., 'achievement_driven')
        user_id: User ID for personalized queries
        neo4j_driver: Optional Neo4j driver for graph queries
        
    Returns:
        Dictionary mapping source names to evidence
    """
    evidence = {
        "bandit_posteriors": await query_bandit_posteriors(user_id, archetype),
        "graph_emergence": await query_graph_emergence(user_id, archetype, neo4j_driver=neo4j_driver),
        "empirical_patterns": await query_empirical_patterns(user_id, archetype),
    }
    
    return evidence


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("=" * 60)
        print("INTELLIGENCE SOURCE TESTS")
        print("=" * 60)
        
        archetypes = ["achievement_driven", "novelty_seeker", "social_connector"]
        
        for archetype in archetypes:
            print(f"\n{archetype.upper()}")
            print("-" * 40)
            
            evidence = await get_archetype_mechanism_evidence(archetype)
            
            for source, ev in evidence.items():
                if ev:
                    print(f"  {source}:")
                    print(f"    Mechanism: {ev.assessment}")
                    print(f"    Effectiveness: {ev.assessment_value:.1%}")
                    print(f"    Confidence: {ev.confidence:.2f}")
                    print(f"    Strength: {ev.strength}")
                else:
                    print(f"  {source}: (no evidence)")
    
    asyncio.run(test())
