# =============================================================================
# Review & Purchase Journey Graph Builder
# Location: adam/intelligence/knowledge_graph/review_graph_builder.py
# =============================================================================

"""
Neo4j Graph Builder for Purchase Journeys

Stores the complete purchase journey evidence as rich graph relationships:

Nodes:
- :Product - Product with psychological positioning
- :Review - Review with psychological profile
- :ReviewerProfile - Inferred reviewer psychology
- :PurchaseJourney - The complete journey record
- :CognitiveMechanism - Persuasion mechanism (existing)
- :CustomerArchetype - Customer archetype (existing)
- :ResearchPrinciple - Academic research principle

Relationships:
- (:Product)-[:USES_MECHANISM]->(:CognitiveMechanism)
- (:Product)-[:TARGETS_ARCHETYPE]->(:CustomerArchetype)
- (:Product)-[:PROMISES_VALUE]->(:ValueProposition)
- (:Review)-[:WRITTEN_BY]->(:ReviewerProfile)
- (:Review)-[:EXHIBITS_CONSTRUCT]->(:PsychologicalConstruct)
- (:ReviewerProfile)-[:HAS_ARCHETYPE]->(:CustomerArchetype)
- (:PurchaseJourney)-[:FOR_PRODUCT]->(:Product)
- (:PurchaseJourney)-[:BY_REVIEWER]->(:ReviewerProfile)
- (:PurchaseJourney)-[:ACTIVATED]->(:CognitiveMechanism) {effectiveness}
- (:PurchaseJourney)-[:VALIDATES]->(:ResearchPrinciple)
- (:CustomerArchetype)-[:RESPONDS_TO]->(:CognitiveMechanism) {weight}

This graph enables:
1. Query: "What mechanisms work for Achiever archetype?"
2. Query: "What archetype distribution actually buys power tools?"
3. Update: Thompson Sampling priors from real evidence
4. Pattern: Discover unexpected archetype-mechanism patterns
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from adam.intelligence.deep_product_analyzer import DeepProductAnalysis
from adam.intelligence.deep_review_analyzer import DeepReviewAnalysis
from adam.intelligence.purchase_journey_analyzer import PurchaseJourneyEvidence

logger = logging.getLogger(__name__)


# =============================================================================
# NEO4J QUERIES
# =============================================================================

MERGE_PRODUCT_NODE = """
MERGE (p:ScrapedProduct {product_id: $product_id})
SET p.title = $title,
    p.brand = $brand,
    p.category = $category,
    p.price = $price,
    p.brand_archetype = $brand_archetype,
    p.target_archetype = $target_archetype,
    p.target_regulatory_focus = $target_regulatory_focus,
    p.core_functional_benefit = $core_functional_benefit,
    p.core_emotional_benefit = $core_emotional_benefit,
    p.mechanism_sophistication = $mechanism_sophistication,
    p.analysis_confidence = $analysis_confidence,
    p.updated_at = datetime()
RETURN p
"""

MERGE_PRODUCT_MECHANISM_REL = """
MATCH (p:ScrapedProduct {product_id: $product_id})
MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
MERGE (p)-[r:USES_MECHANISM]->(m)
SET r.strength = $strength,
    r.confidence = $confidence,
    r.evidence = $evidence
RETURN r
"""

MERGE_PRODUCT_ARCHETYPE_TARGET = """
MATCH (p:ScrapedProduct {product_id: $product_id})
MATCH (a:CustomerArchetype {archetype_id: $archetype_id})
MERGE (p)-[r:TARGETS_ARCHETYPE]->(a)
SET r.confidence = $confidence,
    r.reasoning = $reasoning
RETURN r
"""

MERGE_REVIEW_NODE = """
MERGE (r:ScrapedReview {review_id: $review_id})
SET r.product_id = $product_id,
    r.rating = $rating,
    r.reviewer_archetype = $reviewer_archetype,
    r.reviewer_archetype_confidence = $reviewer_archetype_confidence,
    r.regulatory_focus = $regulatory_focus,
    r.primary_motivation = $primary_motivation,
    r.decision_style = $decision_style,
    r.emotional_tone = $emotional_tone,
    r.expectations_met = $expectations_met,
    r.analysis_confidence = $analysis_confidence,
    r.updated_at = datetime()
RETURN r
"""

MERGE_REVIEWER_PROFILE = """
MERGE (rp:ReviewerProfile {profile_id: $profile_id})
SET rp.inferred_archetype = $archetype,
    rp.archetype_confidence = $archetype_confidence,
    rp.values = $values,
    rp.lifestyle = $lifestyle,
    rp.tribe_signals = $tribe_signals,
    rp.conscientiousness = $conscientiousness,
    rp.openness = $openness,
    rp.extraversion = $extraversion,
    rp.agreeableness = $agreeableness,
    rp.neuroticism = $neuroticism,
    rp.updated_at = datetime()
RETURN rp
"""

MERGE_REVIEW_REVIEWER_REL = """
MATCH (r:ScrapedReview {review_id: $review_id})
MATCH (rp:ReviewerProfile {profile_id: $profile_id})
MERGE (r)-[:WRITTEN_BY]->(rp)
RETURN r, rp
"""

MERGE_REVIEWER_ARCHETYPE_REL = """
MATCH (rp:ReviewerProfile {profile_id: $profile_id})
MATCH (a:CustomerArchetype {archetype_id: $archetype_id})
MERGE (rp)-[r:HAS_ARCHETYPE]->(a)
SET r.confidence = $confidence
RETURN r
"""

MERGE_PURCHASE_JOURNEY = """
MERGE (pj:PurchaseJourney {journey_id: $journey_id})
SET pj.product_id = $product_id,
    pj.review_id = $review_id,
    pj.rating = $rating,
    pj.overall_success = $overall_success,
    pj.archetype_match_type = $archetype_match_type,
    pj.archetype_match_score = $archetype_match_score,
    pj.functional_value_delivered = $functional_value_delivered,
    pj.emotional_value_delivered = $emotional_value_delivered,
    pj.emotional_match = $emotional_match,
    pj.most_effective_mechanism = $most_effective_mechanism,
    pj.decision_style = $decision_style,
    pj.confidence = $confidence,
    pj.created_at = datetime()
RETURN pj
"""

MERGE_JOURNEY_PRODUCT_REL = """
MATCH (pj:PurchaseJourney {journey_id: $journey_id})
MATCH (p:ScrapedProduct {product_id: $product_id})
MERGE (pj)-[:FOR_PRODUCT]->(p)
RETURN pj, p
"""

MERGE_JOURNEY_REVIEWER_REL = """
MATCH (pj:PurchaseJourney {journey_id: $journey_id})
MATCH (rp:ReviewerProfile {profile_id: $profile_id})
MERGE (pj)-[:BY_REVIEWER]->(rp)
RETURN pj, rp
"""

MERGE_JOURNEY_MECHANISM_REL = """
MATCH (pj:PurchaseJourney {journey_id: $journey_id})
MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
MERGE (pj)-[r:ACTIVATED_MECHANISM]->(m)
SET r.effectiveness = $effectiveness,
    r.response = $response,
    r.evidence = $evidence
RETURN r
"""

UPDATE_ARCHETYPE_MECHANISM_WEIGHT = """
MATCH (a:CustomerArchetype {archetype_id: $archetype_id})
MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
MERGE (a)-[r:RESPONDS_TO]->(m)
ON CREATE SET r.weight = $initial_weight, r.evidence_count = 1
ON MATCH SET r.weight = (r.weight * r.evidence_count + $new_evidence) / (r.evidence_count + 1),
             r.evidence_count = r.evidence_count + 1
RETURN r
"""

MERGE_RESEARCH_VALIDATION = """
MERGE (rp:ResearchPrinciple {principle: $principle})
SET rp.researcher = $researcher
WITH rp
MATCH (pj:PurchaseJourney {journey_id: $journey_id})
MERGE (pj)-[r:VALIDATES]->(rp)
SET r.validated = $validated,
    r.strength = $strength,
    r.evidence = $evidence
RETURN rp, r
"""


# =============================================================================
# REVIEW GRAPH BUILDER
# =============================================================================

class ReviewGraphBuilder:
    """
    Builds Neo4j graph from purchase journey evidence.
    
    This creates rich relationships that enable:
    - Querying what mechanisms work for which archetypes
    - Updating Thompson Sampling with real evidence
    - Discovering unexpected patterns
    - Learning from cumulative review data
    """
    
    def __init__(self, neo4j_driver=None):
        """
        Initialize with Neo4j driver.
        
        Args:
            neo4j_driver: Neo4j driver instance (will try to get from infrastructure if None)
        """
        self._driver = neo4j_driver
    
    async def _get_driver(self):
        """Get Neo4j driver."""
        if self._driver is None:
            try:
                from adam.infrastructure.neo4j.client import get_neo4j_client
                client = get_neo4j_client()
                self._driver = client.driver
            except Exception as e:
                logger.error(f"Failed to get Neo4j driver: {e}")
                raise
        return self._driver
    
    async def store_product_analysis(
        self,
        analysis: DeepProductAnalysis,
    ) -> str:
        """
        Store deep product analysis in Neo4j.
        
        Creates:
        - :ScrapedProduct node with psychological positioning
        - Relationships to :CognitiveMechanism nodes
        - Relationships to target :CustomerArchetype nodes
        
        Returns:
            Product node ID
        """
        driver = await self._get_driver()
        
        async with driver.session() as session:
            # Create product node
            await session.run(
                MERGE_PRODUCT_NODE,
                product_id=analysis.product_id,
                title=analysis.title,
                brand=analysis.brand,
                category=analysis.category,
                price=analysis.price,
                brand_archetype=analysis.brand_archetype.value if analysis.brand_archetype else None,
                target_archetype=analysis.target_archetype,
                target_regulatory_focus=analysis.target_regulatory_focus,
                core_functional_benefit=analysis.core_functional_benefit,
                core_emotional_benefit=analysis.core_emotional_benefit,
                mechanism_sophistication=analysis.mechanism_sophistication,
                analysis_confidence=analysis.analysis_confidence,
            )
            
            # Create mechanism relationships
            mechanism_map = {
                "social_proof": "social_proof",
                "authority": "authority",
                "scarcity": "scarcity",
                "reciprocity": "reciprocity",
                "commitment_consistency": "commitment_consistency",
                "liking": "liking",
                "loss_aversion": "loss_aversion",
                "anchoring": "anchoring",
            }
            
            for mech in analysis.mechanisms_detected:
                mech_id = mechanism_map.get(mech.mechanism.value, mech.mechanism.value)
                try:
                    await session.run(
                        MERGE_PRODUCT_MECHANISM_REL,
                        product_id=analysis.product_id,
                        mechanism_id=mech_id,
                        strength=mech.strength,
                        confidence=mech.confidence,
                        evidence=mech.evidence[:3] if mech.evidence else [],
                    )
                except Exception as e:
                    logger.warning(f"Could not link product to mechanism {mech_id}: {e}")
            
            # Create target archetype relationship
            if analysis.target_archetype:
                archetype_map = {
                    "Achiever": "achievement_driven",
                    "Explorer": "explorer",
                    "Guardian": "security_focused",
                    "Connector": "social_connector",
                    "Pragmatist": "value_seeker",
                    "Analyzer": "analytical_thinker",
                }
                archetype_id = archetype_map.get(
                    analysis.target_archetype, 
                    analysis.target_archetype.lower().replace(" ", "_")
                )
                try:
                    await session.run(
                        MERGE_PRODUCT_ARCHETYPE_TARGET,
                        product_id=analysis.product_id,
                        archetype_id=archetype_id,
                        confidence=analysis.target_archetype_confidence,
                        reasoning=f"Based on product positioning for {analysis.target_archetype}",
                    )
                except Exception as e:
                    logger.warning(f"Could not link product to archetype {archetype_id}: {e}")
        
        logger.info(f"Stored product analysis for {analysis.product_id} in Neo4j")
        return analysis.product_id
    
    async def store_review_analysis(
        self,
        analysis: DeepReviewAnalysis,
        product_id: str,
    ) -> str:
        """
        Store deep review analysis in Neo4j.
        
        Creates:
        - :ScrapedReview node
        - :ReviewerProfile node with psychological traits
        - Relationships between review, profile, and archetypes
        
        Returns:
            Review node ID
        """
        driver = await self._get_driver()
        profile_id = f"profile_{analysis.review_id}"
        
        async with driver.session() as session:
            # Create review node
            await session.run(
                MERGE_REVIEW_NODE,
                review_id=analysis.review_id,
                product_id=product_id,
                rating=analysis.rating,
                reviewer_archetype=analysis.identity.inferred_archetype,
                reviewer_archetype_confidence=analysis.identity.archetype_confidence,
                regulatory_focus=analysis.regulatory_focus,
                primary_motivation=analysis.purchase_archaeology.primary_motivation.value,
                decision_style=analysis.purchase_archaeology.decision_style.value,
                emotional_tone=analysis.emotional_journey.overall_emotional_tone,
                expectations_met=analysis.expectations.expectations_met,
                analysis_confidence=analysis.analysis_confidence,
            )
            
            # Create reviewer profile node
            personality = analysis.personality_indicators
            await session.run(
                MERGE_REVIEWER_PROFILE,
                profile_id=profile_id,
                archetype=analysis.identity.inferred_archetype,
                archetype_confidence=analysis.identity.archetype_confidence,
                values=analysis.identity.values_expressed[:5],
                lifestyle=analysis.identity.lifestyle_indicators[:3],
                tribe_signals=analysis.identity.tribe_signals[:3],
                conscientiousness=personality.get("conscientiousness", 0.5),
                openness=personality.get("openness", 0.5),
                extraversion=personality.get("extraversion", 0.5),
                agreeableness=personality.get("agreeableness", 0.5),
                neuroticism=personality.get("neuroticism", 0.5),
            )
            
            # Link review to profile
            await session.run(
                MERGE_REVIEW_REVIEWER_REL,
                review_id=analysis.review_id,
                profile_id=profile_id,
            )
            
            # Link profile to archetype
            if analysis.identity.inferred_archetype:
                archetype_map = {
                    "Achiever": "achievement_driven",
                    "Explorer": "explorer",
                    "Guardian": "security_focused",
                    "Connector": "social_connector",
                    "Pragmatist": "value_seeker",
                    "Analyzer": "analytical_thinker",
                }
                archetype_id = archetype_map.get(
                    analysis.identity.inferred_archetype,
                    analysis.identity.inferred_archetype.lower().replace(" ", "_")
                )
                try:
                    await session.run(
                        MERGE_REVIEWER_ARCHETYPE_REL,
                        profile_id=profile_id,
                        archetype_id=archetype_id,
                        confidence=analysis.identity.archetype_confidence,
                    )
                except Exception as e:
                    logger.warning(f"Could not link profile to archetype: {e}")
        
        logger.info(f"Stored review analysis for {analysis.review_id} in Neo4j")
        return analysis.review_id
    
    async def store_purchase_journey(
        self,
        journey: PurchaseJourneyEvidence,
        product_analysis: DeepProductAnalysis,
        review_analysis: DeepReviewAnalysis,
    ) -> str:
        """
        Store complete purchase journey evidence in Neo4j.
        
        This is the key method that:
        1. Stores the journey node with success metrics
        2. Links to product and reviewer
        3. Records mechanism effectiveness
        4. Updates archetype-mechanism weights
        5. Stores research validations
        
        Returns:
            Journey node ID
        """
        driver = await self._get_driver()
        profile_id = f"profile_{review_analysis.review_id}"
        
        async with driver.session() as session:
            # Store product and review first
            await self.store_product_analysis(product_analysis)
            await self.store_review_analysis(review_analysis, journey.product_id)
            
            # Create journey node
            await session.run(
                MERGE_PURCHASE_JOURNEY,
                journey_id=journey.journey_id,
                product_id=journey.product_id,
                review_id=journey.review_id,
                rating=journey.rating,
                overall_success=journey.overall_journey_success,
                archetype_match_type=journey.archetype_match.match_type if journey.archetype_match else None,
                archetype_match_score=journey.archetype_match.match_score if journey.archetype_match else None,
                functional_value_delivered=journey.functional_value_delivered,
                emotional_value_delivered=journey.emotional_value_delivered,
                emotional_match=journey.emotional_match,
                most_effective_mechanism=journey.most_effective_mechanism,
                decision_style=journey.decision_style_used,
                confidence=journey.confidence,
            )
            
            # Link journey to product
            await session.run(
                MERGE_JOURNEY_PRODUCT_REL,
                journey_id=journey.journey_id,
                product_id=journey.product_id,
            )
            
            # Link journey to reviewer profile
            await session.run(
                MERGE_JOURNEY_REVIEWER_REL,
                journey_id=journey.journey_id,
                profile_id=profile_id,
            )
            
            # Record mechanism effectiveness
            for mech in journey.mechanism_effectiveness:
                mechanism_map = {
                    "social_proof": "social_proof",
                    "authority": "authority",
                    "scarcity": "scarcity",
                    "reciprocity": "reciprocity",
                    "commitment_consistency": "commitment_consistency",
                    "liking": "liking",
                    "loss_aversion": "loss_aversion",
                }
                mech_id = mechanism_map.get(mech.mechanism, mech.mechanism)
                try:
                    await session.run(
                        MERGE_JOURNEY_MECHANISM_REL,
                        journey_id=journey.journey_id,
                        mechanism_id=mech_id,
                        effectiveness=mech.effectiveness_score,
                        response=mech.reviewer_response,
                        evidence=mech.evidence[:3],
                    )
                except Exception as e:
                    logger.warning(f"Could not link journey to mechanism {mech_id}: {e}")
            
            # Update archetype-mechanism weights (THE KEY LEARNING!)
            reviewer_archetype = review_analysis.identity.inferred_archetype
            if reviewer_archetype:
                archetype_map = {
                    "Achiever": "achievement_driven",
                    "Explorer": "explorer",
                    "Guardian": "security_focused",
                    "Connector": "social_connector",
                    "Pragmatist": "value_seeker",
                    "Analyzer": "analytical_thinker",
                }
                archetype_id = archetype_map.get(
                    reviewer_archetype,
                    reviewer_archetype.lower().replace(" ", "_")
                )
                
                for mech in journey.mechanism_effectiveness:
                    if mech.reviewer_response == "responded":
                        mechanism_map = {
                            "social_proof": "social_proof",
                            "authority": "authority",
                            "scarcity": "scarcity",
                            "reciprocity": "reciprocity",
                        }
                        mech_id = mechanism_map.get(mech.mechanism, mech.mechanism)
                        try:
                            await session.run(
                                UPDATE_ARCHETYPE_MECHANISM_WEIGHT,
                                archetype_id=archetype_id,
                                mechanism_id=mech_id,
                                initial_weight=mech.effectiveness_score,
                                new_evidence=mech.effectiveness_score,
                            )
                            logger.info(
                                f"Updated {archetype_id}->{mech_id} weight with evidence {mech.effectiveness_score:.2f}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not update archetype-mechanism weight: {e}")
            
            # Store research validations
            for validation in journey.research_validations:
                try:
                    await session.run(
                        MERGE_RESEARCH_VALIDATION,
                        journey_id=journey.journey_id,
                        principle=validation.principle,
                        researcher=validation.researcher,
                        validated=validation.validated,
                        strength=validation.strength,
                        evidence=validation.evidence,
                    )
                except Exception as e:
                    logger.warning(f"Could not store research validation: {e}")
        
        logger.info(
            f"Stored purchase journey {journey.journey_id} in Neo4j "
            f"(success: {journey.overall_journey_success:.2f})"
        )
        return journey.journey_id
    
    async def get_archetype_mechanism_effectiveness(
        self,
        archetype_id: str,
    ) -> Dict[str, float]:
        """
        Query learned mechanism effectiveness for an archetype.
        
        This returns the accumulated learning from all purchase journeys.
        """
        driver = await self._get_driver()
        
        query = """
        MATCH (a:CustomerArchetype {archetype_id: $archetype_id})-[r:RESPONDS_TO]->(m:CognitiveMechanism)
        RETURN m.mechanism_id as mechanism, r.weight as weight, r.evidence_count as count
        ORDER BY r.weight DESC
        """
        
        results = {}
        async with driver.session() as session:
            result = await session.run(query, archetype_id=archetype_id)
            async for record in result:
                results[record["mechanism"]] = {
                    "weight": record["weight"],
                    "evidence_count": record["count"],
                }
        
        return results
    
    async def get_journey_stats(self) -> Dict[str, Any]:
        """Get statistics about stored purchase journeys."""
        driver = await self._get_driver()
        
        query = """
        MATCH (pj:PurchaseJourney)
        RETURN 
            count(pj) as total_journeys,
            avg(pj.overall_success) as avg_success,
            avg(pj.rating) as avg_rating
        """
        
        async with driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            
            if record:
                return {
                    "total_journeys": record["total_journeys"],
                    "avg_success": record["avg_success"],
                    "avg_rating": record["avg_rating"],
                }
        
        return {"total_journeys": 0, "avg_success": 0, "avg_rating": 0}


# =============================================================================
# SINGLETON
# =============================================================================

_graph_builder: Optional[ReviewGraphBuilder] = None


def get_review_graph_builder() -> ReviewGraphBuilder:
    """Get or create the review graph builder."""
    global _graph_builder
    if _graph_builder is None:
        _graph_builder = ReviewGraphBuilder()
    return _graph_builder
