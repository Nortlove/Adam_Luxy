# =============================================================================
# ADAM Behavioral Analytics: Graph Knowledge Integration
# Location: adam/behavioral_analytics/knowledge/graph_integration.py
# =============================================================================

"""
GRAPH KNOWLEDGE INTEGRATION

Integrates behavioral knowledge into Neo4j for:
- Atom of Thought queries
- LangGraph decision enhancement
- Cross-component knowledge sharing
- Hypothesis validation tracking
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    BehavioralHypothesis,
    KnowledgeValidationEvent,
    KnowledgeType,
    KnowledgeStatus,
    HypothesisStatus,
)
from adam.behavioral_analytics.models.advertising_knowledge import (
    AdvertisingKnowledge,
    AdvertisingInteraction,
)
from adam.behavioral_analytics.models.advertising_psychology import (
    RegulatoryFocusProfile,
    CognitiveStateProfile,
    MoralFoundationsProfile,
    UserAdvertisingPsychologyProfile,
    ConfidenceTier,
)

logger = logging.getLogger(__name__)


class BehavioralKnowledgeGraph:
    """
    Neo4j integration for behavioral knowledge.
    
    Schema:
    - (BehavioralKnowledge) - Research and system knowledge nodes
    - (BehavioralHypothesis) - Hypotheses under testing
    - (PsychologicalConstruct) - Target constructs
    - (BehavioralSignal) - Signal definitions
    
    Relationships:
    - (BehavioralKnowledge)-[:MAPS_TO]->(PsychologicalConstruct)
    - (BehavioralKnowledge)-[:DERIVED_FROM]->(BehavioralSignal)
    - (BehavioralHypothesis)-[:TESTS_RELATIONSHIP_BETWEEN]->(BehavioralSignal)
    - (BehavioralHypothesis)-[:PREDICTS]->(Outcome)
    - (User)-[:VALIDATED]->(BehavioralKnowledge)
    """
    
    def __init__(self, neo4j_driver):
        self._driver = neo4j_driver
    
    async def create_schema(self) -> None:
        """Create indexes and constraints for behavioral knowledge."""
        queries = [
            # Knowledge constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (k:BehavioralKnowledge) REQUIRE k.knowledge_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (h:BehavioralHypothesis) REQUIRE h.hypothesis_id IS UNIQUE",
            
            # Indexes for fast lookups
            "CREATE INDEX IF NOT EXISTS FOR (k:BehavioralKnowledge) ON (k.maps_to_construct)",
            "CREATE INDEX IF NOT EXISTS FOR (k:BehavioralKnowledge) ON (k.signal_name)",
            "CREATE INDEX IF NOT EXISTS FOR (k:BehavioralKnowledge) ON (k.knowledge_type)",
            "CREATE INDEX IF NOT EXISTS FOR (k:BehavioralKnowledge) ON (k.tier)",
            "CREATE INDEX IF NOT EXISTS FOR (k:BehavioralKnowledge) ON (k.status)",
            
            "CREATE INDEX IF NOT EXISTS FOR (h:BehavioralHypothesis) ON (h.status)",
            "CREATE INDEX IF NOT EXISTS FOR (h:BehavioralHypothesis) ON (h.predicted_outcome)",
        ]
        
        async with self._driver.session() as session:
            for query in queries:
                await session.run(query)
        
        logger.info("Behavioral knowledge graph schema created")
    
    async def store_knowledge(
        self,
        knowledge: BehavioralKnowledge
    ) -> str:
        """
        Store behavioral knowledge in Neo4j.
        
        Creates:
        - BehavioralKnowledge node
        - Links to PsychologicalConstruct
        - Links to research sources
        """
        query = """
        MERGE (k:BehavioralKnowledge {knowledge_id: $knowledge_id})
        ON CREATE SET
            k.created_at = datetime(),
            k.knowledge_type = $knowledge_type,
            k.status = $status,
            k.signal_name = $signal_name,
            k.signal_category = $signal_category,
            k.signal_description = $signal_description,
            k.feature_name = $feature_name,
            k.feature_computation = $feature_computation,
            k.maps_to_construct = $maps_to_construct,
            k.mapping_direction = $mapping_direction,
            k.mapping_description = $mapping_description,
            k.effect_size = $effect_size,
            k.effect_type = $effect_type,
            k.confidence_interval_lower = $ci_lower,
            k.confidence_interval_upper = $ci_upper,
            k.p_value = $p_value,
            k.study_count = $study_count,
            k.total_sample_size = $total_sample_size,
            k.tier = $tier,
            k.implementation_notes = $implementation_notes,
            k.requires_baseline = $requires_baseline,
            k.min_observations = $min_observations,
            k.validation_count = 0,
            k.validation_successes = 0
        ON MATCH SET
            k.updated_at = datetime(),
            k.status = $status,
            k.effect_size = $effect_size,
            k.validation_count = $validation_count,
            k.validation_successes = $validation_successes
        
        // Link to psychological construct
        MERGE (c:PsychologicalConstruct {name: $maps_to_construct})
        MERGE (k)-[:MAPS_TO {
            direction: $mapping_direction,
            effect_size: $effect_size,
            effect_type: $effect_type
        }]->(c)
        
        // Link to behavioral signal definition
        MERGE (s:BehavioralSignal {name: $signal_name})
        ON CREATE SET
            s.category = $signal_category,
            s.description = $signal_description
        MERGE (k)-[:DERIVED_FROM {
            feature_name: $feature_name,
            computation: $feature_computation
        }]->(s)
        
        RETURN k.knowledge_id as id
        """
        
        params = {
            "knowledge_id": knowledge.knowledge_id,
            "knowledge_type": knowledge.knowledge_type.value,
            "status": knowledge.status.value,
            "signal_name": knowledge.signal_name,
            "signal_category": knowledge.signal_category.value,
            "signal_description": knowledge.signal_description,
            "feature_name": knowledge.feature_name,
            "feature_computation": knowledge.feature_computation,
            "maps_to_construct": knowledge.maps_to_construct,
            "mapping_direction": knowledge.mapping_direction,
            "mapping_description": knowledge.mapping_description,
            "effect_size": knowledge.effect_size,
            "effect_type": knowledge.effect_type.value,
            "ci_lower": knowledge.confidence_interval_lower,
            "ci_upper": knowledge.confidence_interval_upper,
            "p_value": knowledge.p_value,
            "study_count": knowledge.study_count,
            "total_sample_size": knowledge.total_sample_size,
            "tier": knowledge.tier.value,
            "implementation_notes": knowledge.implementation_notes,
            "requires_baseline": knowledge.requires_baseline,
            "min_observations": knowledge.min_observations,
            "validation_count": knowledge.validation_count,
            "validation_successes": knowledge.validation_successes,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["id"]
    
    async def store_hypothesis(
        self,
        hypothesis: BehavioralHypothesis
    ) -> str:
        """Store behavioral hypothesis in Neo4j."""
        query = """
        MERGE (h:BehavioralHypothesis {hypothesis_id: $hypothesis_id})
        ON CREATE SET
            h.generated_at = datetime(),
            h.status = $status,
            h.signal_pattern = $signal_pattern,
            h.predicted_outcome = $predicted_outcome,
            h.predicted_direction = $predicted_direction,
            h.hypothesis_description = $hypothesis_description,
            h.observations = 0,
            h.positive_outcomes = 0,
            h.negative_outcomes = 0,
            h.min_observations_required = $min_observations_required,
            h.significance_threshold = $significance_threshold
        ON MATCH SET
            h.updated_at = datetime(),
            h.status = $status,
            h.observations = $observations,
            h.positive_outcomes = $positive_outcomes,
            h.negative_outcomes = $negative_outcomes,
            h.observed_effect_size = $observed_effect_size,
            h.p_value = $p_value,
            h.cv_folds_passed = $cv_folds_passed
        
        RETURN h.hypothesis_id as id
        """
        
        params = {
            "hypothesis_id": hypothesis.hypothesis_id,
            "status": hypothesis.status.value,
            "signal_pattern": hypothesis.signal_pattern,
            "predicted_outcome": hypothesis.predicted_outcome,
            "predicted_direction": hypothesis.predicted_direction,
            "hypothesis_description": hypothesis.hypothesis_description,
            "observations": hypothesis.observations,
            "positive_outcomes": hypothesis.positive_outcomes,
            "negative_outcomes": hypothesis.negative_outcomes,
            "observed_effect_size": hypothesis.observed_effect_size,
            "p_value": hypothesis.p_value,
            "cv_folds_passed": hypothesis.cv_folds_passed,
            "min_observations_required": hypothesis.min_observations_required,
            "significance_threshold": hypothesis.significance_threshold,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["id"]
    
    async def get_knowledge_for_construct(
        self,
        construct: str,
        tier: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all behavioral knowledge mapping to a psychological construct.
        
        Used by Atom of Thought to get relevant knowledge for reasoning.
        """
        query = """
        MATCH (k:BehavioralKnowledge)-[r:MAPS_TO]->(c:PsychologicalConstruct {name: $construct})
        WHERE ($tier IS NULL OR k.tier = $tier)
        AND ($active_only = false OR k.status = 'active')
        RETURN k {
            .*,
            construct: c.name,
            mapping_direction: r.direction,
            effect_strength: r.effect_size
        } as knowledge
        ORDER BY k.tier ASC, k.effect_size DESC
        """
        
        params = {
            "construct": construct,
            "tier": tier,
            "active_only": active_only,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()
            return [r["knowledge"] for r in records]
    
    async def get_knowledge_for_signal(
        self,
        signal_name: str
    ) -> List[Dict[str, Any]]:
        """Get all knowledge derived from a behavioral signal."""
        query = """
        MATCH (k:BehavioralKnowledge)-[:DERIVED_FROM]->(s:BehavioralSignal {name: $signal_name})
        WHERE k.status = 'active'
        RETURN k { .* } as knowledge
        ORDER BY k.tier ASC, k.effect_size DESC
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"signal_name": signal_name})
            records = await result.data()
            return [r["knowledge"] for r in records]
    
    async def get_active_hypotheses(
        self,
        predicted_outcome: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get hypotheses currently being tested."""
        query = """
        MATCH (h:BehavioralHypothesis)
        WHERE h.status IN ['generated', 'testing']
        AND ($outcome IS NULL OR h.predicted_outcome = $outcome)
        RETURN h { .* } as hypothesis
        ORDER BY h.observations DESC
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"outcome": predicted_outcome})
            records = await result.data()
            return [r["hypothesis"] for r in records]
    
    async def record_validation(
        self,
        event: KnowledgeValidationEvent
    ) -> None:
        """
        Record a knowledge validation event.
        
        Updates the knowledge's validation metrics.
        """
        query = """
        MATCH (k:BehavioralKnowledge {knowledge_id: $knowledge_id})
        SET 
            k.validation_count = k.validation_count + 1,
            k.validation_successes = k.validation_successes + CASE WHEN $matched THEN 1 ELSE 0 END,
            k.last_validated = datetime()
        
        // Create validation event node
        CREATE (v:KnowledgeValidation {
            event_id: $event_id,
            user_id: $user_id,
            session_id: $session_id,
            signal_value: $signal_value,
            outcome_type: $outcome_type,
            outcome_value: $outcome_value,
            prediction_matched: $matched,
            confidence: $confidence,
            observed_at: datetime()
        })
        
        // Link validation to knowledge
        CREATE (k)-[:VALIDATED_BY]->(v)
        
        // Link validation to user if exists
        FOREACH (u IN CASE WHEN $user_id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (user:User {user_id: $user_id})
            CREATE (user)-[:PROVIDED_VALIDATION]->(v)
        )
        """
        
        params = {
            "knowledge_id": event.knowledge_id,
            "event_id": event.event_id,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "signal_value": event.signal_value,
            "outcome_type": event.outcome_type,
            "outcome_value": event.outcome_value,
            "matched": event.prediction_matched,
            "confidence": event.prediction_confidence,
        }
        
        async with self._driver.session() as session:
            await session.run(query, params)
    
    async def update_hypothesis_observation(
        self,
        hypothesis_id: str,
        positive_outcome: bool,
        new_effect_size: Optional[float] = None,
        new_p_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update a hypothesis with a new observation.
        
        Returns updated hypothesis state.
        """
        query = """
        MATCH (h:BehavioralHypothesis {hypothesis_id: $hypothesis_id})
        SET 
            h.observations = h.observations + 1,
            h.positive_outcomes = h.positive_outcomes + CASE WHEN $positive THEN 1 ELSE 0 END,
            h.negative_outcomes = h.negative_outcomes + CASE WHEN $positive THEN 0 ELSE 1 END,
            h.last_observation = datetime(),
            h.observed_effect_size = COALESCE($effect_size, h.observed_effect_size),
            h.p_value = COALESCE($p_value, h.p_value)
        
        // Update status to testing if was generated
        SET h.status = CASE 
            WHEN h.status = 'generated' THEN 'testing'
            ELSE h.status
        END
        
        RETURN h { .* } as hypothesis
        """
        
        params = {
            "hypothesis_id": hypothesis_id,
            "positive": positive_outcome,
            "effect_size": new_effect_size,
            "p_value": new_p_value,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["hypothesis"] if record else {}
    
    async def promote_hypothesis(
        self,
        hypothesis_id: str,
        knowledge_id: str
    ) -> None:
        """
        Promote a validated hypothesis to system knowledge.
        
        Creates a new BehavioralKnowledge node from the hypothesis.
        """
        query = """
        MATCH (h:BehavioralHypothesis {hypothesis_id: $hypothesis_id})
        WHERE h.status = 'validated'
        SET 
            h.status = 'promoted',
            h.promoted_at = datetime(),
            h.promoted_knowledge_id = $knowledge_id
        
        // Link hypothesis to promoted knowledge
        WITH h
        MATCH (k:BehavioralKnowledge {knowledge_id: $knowledge_id})
        CREATE (h)-[:PROMOTED_TO]->(k)
        
        RETURN h.hypothesis_id as promoted
        """
        
        async with self._driver.session() as session:
            await session.run(query, {
                "hypothesis_id": hypothesis_id,
                "knowledge_id": knowledge_id
            })
        
        logger.info(f"Promoted hypothesis {hypothesis_id} to knowledge {knowledge_id}")
    
    async def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary statistics of behavioral knowledge."""
        query = """
        MATCH (k:BehavioralKnowledge)
        WITH 
            count(k) as total,
            sum(CASE WHEN k.knowledge_type = 'research_validated' THEN 1 ELSE 0 END) as research,
            sum(CASE WHEN k.knowledge_type = 'system_discovered' THEN 1 ELSE 0 END) as discovered,
            sum(CASE WHEN k.status = 'active' THEN 1 ELSE 0 END) as active,
            sum(CASE WHEN k.tier = 1 THEN 1 ELSE 0 END) as tier1,
            sum(CASE WHEN k.tier = 2 THEN 1 ELSE 0 END) as tier2,
            sum(CASE WHEN k.tier = 3 THEN 1 ELSE 0 END) as tier3,
            avg(k.effect_size) as avg_effect
        
        OPTIONAL MATCH (h:BehavioralHypothesis)
        WITH *, count(h) as hypotheses_total
        
        OPTIONAL MATCH (h2:BehavioralHypothesis)
        WHERE h2.status = 'testing'
        WITH *, count(h2) as hypotheses_testing
        
        RETURN {
            total_knowledge: total,
            research_validated: research,
            system_discovered: discovered,
            active: active,
            tier_1: tier1,
            tier_2: tier2,
            tier_3: tier3,
            average_effect_size: avg_effect,
            total_hypotheses: hypotheses_total,
            hypotheses_testing: hypotheses_testing
        } as summary
        """
        
        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            return record["summary"] if record else {}
    
    # =========================================================================
    # ADVERTISING PSYCHOLOGY KNOWLEDGE METHODS
    # =========================================================================
    
    async def store_advertising_knowledge(
        self,
        knowledge: AdvertisingKnowledge
    ) -> str:
        """
        Store advertising psychology knowledge in Neo4j.
        
        Creates:
        - AdvertisingPsychologyKnowledge node
        - Links to research domain
        - Links to cognitive mechanisms
        """
        query = """
        MERGE (k:AdvertisingPsychologyKnowledge {knowledge_id: $knowledge_id})
        ON CREATE SET
            k.created_at = datetime(),
            k.predictor_category = $predictor_category,
            k.predictor_name = $predictor_name,
            k.predictor_value = $predictor_value,
            k.predictor_description = $predictor_description,
            k.ad_element = $ad_element,
            k.element_specification = $element_specification,
            k.element_description = $element_description,
            k.outcome_metric = $outcome_metric,
            k.outcome_direction = $outcome_direction,
            k.outcome_description = $outcome_description,
            k.effect_size = $effect_size,
            k.effect_type = $effect_type,
            k.confidence_interval_lower = $ci_lower,
            k.confidence_interval_upper = $ci_upper,
            k.p_value = $p_value,
            k.robustness_tier = $robustness_tier,
            k.study_count = $study_count,
            k.total_sample_size = $total_sample_size,
            k.implementation_notes = $implementation_notes,
            k.related_mechanisms = $related_mechanisms,
            k.status = 'active'
        ON MATCH SET
            k.updated_at = datetime(),
            k.effect_size = $effect_size
        
        // Link to research domain based on predictor
        WITH k
        OPTIONAL MATCH (rd:ResearchDomain)
        WHERE rd.name CONTAINS $predictor_name OR $predictor_name CONTAINS rd.name
        FOREACH (r IN CASE WHEN rd IS NOT NULL THEN [rd] ELSE [] END |
            MERGE (k)-[:BELONGS_TO_DOMAIN]->(r)
        )
        
        // Link to confidence tier
        WITH k
        MATCH (ct:ConfidenceTier {tier: $robustness_tier})
        MERGE (k)-[:HAS_CONFIDENCE_TIER]->(ct)
        
        RETURN k.knowledge_id as id
        """
        
        params = {
            "knowledge_id": knowledge.knowledge_id,
            "predictor_category": knowledge.predictor_category.value,
            "predictor_name": knowledge.predictor_name,
            "predictor_value": knowledge.predictor_value,
            "predictor_description": knowledge.predictor_description,
            "ad_element": knowledge.ad_element.value,
            "element_specification": knowledge.element_specification,
            "element_description": knowledge.element_description,
            "outcome_metric": knowledge.outcome_metric.value,
            "outcome_direction": knowledge.outcome_direction,
            "outcome_description": knowledge.outcome_description,
            "effect_size": knowledge.effect_size,
            "effect_type": knowledge.effect_type.value,
            "ci_lower": knowledge.confidence_interval_lower,
            "ci_upper": knowledge.confidence_interval_upper,
            "p_value": knowledge.p_value,
            "robustness_tier": knowledge.robustness_tier.value,
            "study_count": knowledge.study_count,
            "total_sample_size": knowledge.total_sample_size,
            "implementation_notes": knowledge.implementation_notes,
            "related_mechanisms": knowledge.related_mechanisms,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["id"]
    
    async def store_advertising_interaction(
        self,
        interaction: AdvertisingInteraction
    ) -> str:
        """Store advertising interaction effect in Neo4j."""
        query = """
        MERGE (i:AdvertisingInteraction {interaction_id: $interaction_id})
        ON CREATE SET
            i.created_at = datetime(),
            i.primary_variable = $primary_variable,
            i.primary_value = $primary_value,
            i.moderating_variable = $moderating_variable,
            i.moderating_value = $moderating_value,
            i.interaction_type = $interaction_type,
            i.interaction_description = $interaction_description,
            i.effect_when_moderator_present = $effect_present,
            i.effect_when_moderator_absent = $effect_absent,
            i.effect_type = $effect_type,
            i.robustness_tier = $robustness_tier,
            i.implementation_notes = $implementation_notes
        ON MATCH SET
            i.updated_at = datetime()
        
        RETURN i.interaction_id as id
        """
        
        params = {
            "interaction_id": interaction.interaction_id,
            "primary_variable": interaction.primary_variable,
            "primary_value": interaction.primary_value,
            "moderating_variable": interaction.moderating_variable,
            "moderating_value": interaction.moderating_value,
            "interaction_type": interaction.interaction_type.value,
            "interaction_description": interaction.interaction_description,
            "effect_present": interaction.effect_when_moderator_present,
            "effect_absent": interaction.effect_when_moderator_absent,
            "effect_type": interaction.effect_type.value,
            "robustness_tier": interaction.robustness_tier.value,
            "implementation_notes": interaction.implementation_notes,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["id"]
    
    async def store_user_psychology_profile(
        self,
        profile: UserAdvertisingPsychologyProfile
    ) -> str:
        """
        Store user's advertising psychology profile in Neo4j.
        
        Creates or updates the user's psychological profile for ad targeting.
        """
        query = """
        MERGE (u:User {user_id: $user_id})
        MERGE (p:UserPsychologyProfile {profile_id: $profile_id})
        ON CREATE SET
            p.created_at = datetime(),
            p.user_id = $user_id,
            p.overall_confidence = $overall_confidence,
            p.domains_populated = $domains_populated
        ON MATCH SET
            p.updated_at = datetime(),
            p.overall_confidence = $overall_confidence,
            p.domains_populated = $domains_populated
        
        MERGE (u)-[:HAS_PSYCHOLOGY_PROFILE]->(p)
        
        // Store regulatory focus if present
        FOREACH (rf IN CASE WHEN $regulatory_focus IS NOT NULL THEN [1] ELSE [] END |
            MERGE (rfn:RegulatoryFocusProfile {user_id: $user_id})
            SET rfn.focus_type = $reg_focus_type,
                rfn.focus_strength = $reg_focus_strength,
                rfn.recommended_frame = $reg_recommended_frame,
                rfn.updated_at = datetime()
            MERGE (p)-[:HAS_REGULATORY_FOCUS]->(rfn)
        )
        
        // Store cognitive state if present
        FOREACH (cs IN CASE WHEN $cognitive_state IS NOT NULL THEN [1] ELSE [] END |
            MERGE (csn:CognitiveStateProfile {user_id: $user_id})
            SET csn.cognitive_load = $cognitive_load,
                csn.recommended_complexity = $recommended_complexity,
                csn.processing_route = $processing_route,
                csn.updated_at = datetime()
            MERGE (p)-[:HAS_COGNITIVE_STATE]->(csn)
        )
        
        RETURN p.profile_id as id
        """
        
        # Extract nested profile data
        reg_focus = profile.regulatory_focus
        cog_state = profile.cognitive_state
        
        params = {
            "user_id": profile.user_id,
            "profile_id": profile.profile_id,
            "overall_confidence": profile.overall_confidence,
            "domains_populated": profile.domains_populated,
            "regulatory_focus": reg_focus is not None,
            "reg_focus_type": reg_focus.focus_type if reg_focus else None,
            "reg_focus_strength": reg_focus.focus_strength if reg_focus else None,
            "reg_recommended_frame": reg_focus.recommended_frame if reg_focus else None,
            "cognitive_state": cog_state is not None,
            "cognitive_load": cog_state.cognitive_load if cog_state else None,
            "recommended_complexity": cog_state.recommended_complexity if cog_state else None,
            "processing_route": cog_state.processing_route if cog_state else None,
        }
        
        async with self._driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["id"]
    
    async def get_advertising_knowledge_for_predictor(
        self,
        predictor_name: str,
        tier: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get advertising knowledge for a predictor variable.
        
        Used by Atom of Thought for ad recommendation reasoning.
        """
        query = """
        MATCH (k:AdvertisingPsychologyKnowledge)
        WHERE k.predictor_name = $predictor_name
        AND ($tier IS NULL OR k.robustness_tier = $tier)
        AND k.status = 'active'
        RETURN k { .* } as knowledge
        ORDER BY k.robustness_tier ASC, k.effect_size DESC
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {
                "predictor_name": predictor_name,
                "tier": tier
            })
            records = await result.data()
            return [r["knowledge"] for r in records]
    
    async def get_advertising_knowledge_for_mechanism(
        self,
        mechanism: str
    ) -> List[Dict[str, Any]]:
        """
        Get advertising knowledge related to a cognitive mechanism.
        
        Used for mechanism-based reasoning.
        """
        query = """
        MATCH (k:AdvertisingPsychologyKnowledge)
        WHERE $mechanism IN k.related_mechanisms
        AND k.status = 'active'
        RETURN k { .* } as knowledge
        ORDER BY k.robustness_tier ASC, k.effect_size DESC
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"mechanism": mechanism})
            records = await result.data()
            return [r["knowledge"] for r in records]
    
    async def get_message_templates_for_focus(
        self,
        focus_type: str
    ) -> List[Dict[str, Any]]:
        """Get message frame templates matching regulatory focus."""
        query = """
        MATCH (mft:MessageFrameTemplate)
        WHERE mft.focus_type = $focus_type
        RETURN mft { .* } as template
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"focus_type": focus_type})
            records = await result.data()
            return [r["template"] for r in records]
    
    async def get_moral_foundation_appeals(
        self,
        foundation_name: str
    ) -> Dict[str, Any]:
        """Get advertising appeals for a moral foundation."""
        query = """
        MATCH (mf:MoralFoundation {name: $name})
        RETURN mf { .* } as foundation
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"name": foundation_name})
            record = await result.single()
            return record["foundation"] if record else {}
    
    async def get_temporal_pattern(
        self,
        pattern_type: str,
        funnel_stage: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get temporal patterns for timing optimization."""
        query = """
        MATCH (tp:TemporalPattern)
        WHERE tp.pattern_type = $pattern_type
        AND ($funnel_stage IS NULL OR tp.funnel_stage = $funnel_stage)
        RETURN tp { .* } as pattern
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {
                "pattern_type": pattern_type,
                "funnel_stage": funnel_stage
            })
            records = await result.data()
            return [r["pattern"] for r in records]
    
    async def get_signal_construct_mapping(
        self,
        signal_name: str
    ) -> List[Dict[str, Any]]:
        """Get signal-to-construct mappings from advertising psychology research."""
        query = """
        MATCH (scm:SignalConstructMapping {signal_name: $signal_name})
        OPTIONAL MATCH (scm)-[:HAS_CONFIDENCE_TIER]->(ct:ConfidenceTier)
        OPTIONAL MATCH (scm)-[:BELONGS_TO_DOMAIN]->(rd:ResearchDomain)
        RETURN scm { 
            .*,
            tier_name: ct.name,
            domain_name: rd.name
        } as mapping
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"signal_name": signal_name})
            records = await result.data()
            return [r["mapping"] for r in records]
    
    async def get_tier1_advertising_knowledge(self) -> List[Dict[str, Any]]:
        """
        Get all Tier 1 (meta-analyzed) advertising knowledge.
        
        These are the highest-confidence findings for primary targeting.
        """
        query = """
        MATCH (k:AdvertisingPsychologyKnowledge)
        WHERE k.robustness_tier = 1 AND k.status = 'active'
        RETURN k { .* } as knowledge
        ORDER BY k.effect_size DESC
        """
        
        async with self._driver.session() as session:
            result = await session.run(query)
            records = await result.data()
            return [r["knowledge"] for r in records]
    
    async def get_user_psychology_profile(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user's psychology profile for ad targeting."""
        query = """
        MATCH (u:User {user_id: $user_id})-[:HAS_PSYCHOLOGY_PROFILE]->(p:UserPsychologyProfile)
        OPTIONAL MATCH (p)-[:HAS_REGULATORY_FOCUS]->(rf:RegulatoryFocusProfile)
        OPTIONAL MATCH (p)-[:HAS_COGNITIVE_STATE]->(cs:CognitiveStateProfile)
        RETURN p {
            .*,
            regulatory_focus: rf { .* },
            cognitive_state: cs { .* }
        } as profile
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, {"user_id": user_id})
            record = await result.single()
            return record["profile"] if record else None
    
    async def get_advertising_psychology_summary(self) -> Dict[str, Any]:
        """Get summary of advertising psychology knowledge in the graph."""
        query = """
        OPTIONAL MATCH (apk:AdvertisingPsychologyKnowledge)
        WITH count(apk) as adv_knowledge_count
        
        OPTIONAL MATCH (scm:SignalConstructMapping)
        WITH adv_knowledge_count, count(scm) as signal_mapping_count
        
        OPTIONAL MATCH (mft:MessageFrameTemplate)
        WITH adv_knowledge_count, signal_mapping_count, count(mft) as template_count
        
        OPTIONAL MATCH (mf:MoralFoundation)
        WITH adv_knowledge_count, signal_mapping_count, template_count, count(mf) as foundation_count
        
        OPTIONAL MATCH (rd:ResearchDomain)
        WITH adv_knowledge_count, signal_mapping_count, template_count, foundation_count, count(rd) as domain_count
        
        OPTIONAL MATCH (tp:TemporalPattern)
        WITH adv_knowledge_count, signal_mapping_count, template_count, foundation_count, domain_count, count(tp) as temporal_pattern_count
        
        OPTIONAL MATCH (ai:AdvertisingInteraction)
        WITH adv_knowledge_count, signal_mapping_count, template_count, foundation_count, domain_count, temporal_pattern_count, count(ai) as interaction_count
        
        RETURN {
            advertising_knowledge: adv_knowledge_count,
            signal_mappings: signal_mapping_count,
            message_templates: template_count,
            moral_foundations: foundation_count,
            research_domains: domain_count,
            temporal_patterns: temporal_pattern_count,
            interactions: interaction_count
        } as summary
        """
        
        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            return record["summary"] if record else {}


# Dependency injection
_graph: Optional[BehavioralKnowledgeGraph] = None


def get_behavioral_knowledge_graph(neo4j_driver=None) -> BehavioralKnowledgeGraph:
    """Get behavioral knowledge graph instance."""
    global _graph
    if _graph is None and neo4j_driver is not None:
        _graph = BehavioralKnowledgeGraph(neo4j_driver)
    return _graph


async def seed_research_knowledge(neo4j_driver) -> int:
    """
    Seed all research knowledge into Neo4j.
    
    Called at system startup to ensure foundational knowledge exists.
    Returns count of knowledge items seeded.
    """
    from adam.behavioral_analytics.knowledge.research_seeder import (
        get_research_knowledge_seeder
    )
    
    graph = BehavioralKnowledgeGraph(neo4j_driver)
    await graph.create_schema()
    
    seeder = get_research_knowledge_seeder()
    knowledge_items = seeder.seed_all_knowledge()
    
    count = 0
    for knowledge in knowledge_items:
        await graph.store_knowledge(knowledge)
        count += 1
    
    logger.info(f"Seeded {count} research knowledge items to Neo4j")
    return count


async def seed_advertising_psychology_knowledge(neo4j_driver) -> int:
    """
    Seed advertising psychology research knowledge into Neo4j.
    
    Seeds 200+ empirical findings across 22 scientific domains (1989-2025).
    
    Called at system startup to ensure foundational advertising psychology
    knowledge exists for:
    - Signal collection (linguistic, desktop, mobile)
    - Psychological construct inference
    - Message framing and timing
    - Memory optimization
    - Social and values-based targeting
    
    Returns count of knowledge items seeded.
    """
    from adam.behavioral_analytics.knowledge.advertising_psychology_seeder import (
        get_advertising_psychology_seeder
    )
    
    graph = BehavioralKnowledgeGraph(neo4j_driver)
    
    seeder = get_advertising_psychology_seeder()
    behavioral, advertising, interactions = seeder.seed_all_knowledge()
    
    count = 0
    
    # Store behavioral knowledge (signals → constructs)
    for knowledge in behavioral:
        await graph.store_knowledge(knowledge)
        count += 1
    
    logger.info(f"Seeded {len(behavioral)} behavioral signal knowledge items")
    
    # Store advertising knowledge (predictor → ad element → outcome)
    for knowledge in advertising:
        await graph.store_advertising_knowledge(knowledge)
        count += 1
    
    logger.info(f"Seeded {len(advertising)} advertising knowledge items")
    
    # Store interaction effects
    for interaction in interactions:
        await graph.store_advertising_interaction(interaction)
        count += 1
    
    logger.info(f"Seeded {len(interactions)} interaction effects")
    
    logger.info(f"Total advertising psychology knowledge seeded: {count} items")
    return count


async def seed_cross_disciplinary_knowledge(neo4j_driver) -> int:
    """
    Seed cross-disciplinary science knowledge into Neo4j.
    
    Seeds 85+ empirical findings from:
    - Evolutionary Psychology (costly signaling, life history)
    - Social Physics (network effects, contagion)
    - Reinforcement Learning (model-based/free, prediction error)
    - Predictive Processing (free energy, curiosity)
    - Psychophysics (Weber-Fechner, fluency)
    - Memory Research (reconsolidation, testing effect)
    - Embodied Cognition (approach-avoidance, IKEA effect)
    
    Returns count of knowledge items seeded.
    """
    from adam.behavioral_analytics.knowledge.cross_disciplinary_seeder import (
        get_cross_disciplinary_seeder
    )
    
    graph = BehavioralKnowledgeGraph(neo4j_driver)
    
    seeder = get_cross_disciplinary_seeder()
    knowledge = seeder.seed_all_knowledge()
    
    count = 0
    
    # Store behavioral knowledge
    for item in knowledge["behavioral"]:
        await graph.store_knowledge(item)
        count += 1
    
    # Store advertising knowledge
    for item in knowledge["advertising"]:
        await graph.store_advertising_knowledge(item)
        count += 1
    
    logger.info(f"Seeded {count} cross-disciplinary knowledge items")
    return count


async def seed_media_preferences_knowledge(neo4j_driver) -> int:
    """
    Seed media preferences → personality correlations into Neo4j.
    
    Seeds 50+ validated correlations from:
    - MUSIC Model (music → personality)
    - Podcast preferences (true crime → morbid curiosity)
    - Book preferences (fiction → empathy)
    - Film/TV preferences (genre → personality)
    
    Returns count of knowledge items seeded.
    """
    from adam.behavioral_analytics.knowledge.media_preferences_seeder import (
        get_media_preferences_seeder
    )
    
    graph = BehavioralKnowledgeGraph(neo4j_driver)
    
    seeder = get_media_preferences_seeder()
    knowledge = seeder.seed_all_knowledge()
    
    count = 0
    
    # Store behavioral knowledge
    for item in knowledge["behavioral"]:
        await graph.store_knowledge(item)
        count += 1
    
    logger.info(f"Seeded {count} media preferences knowledge items")
    return count


async def seed_all_knowledge(neo4j_driver) -> Dict[str, int]:
    """
    Seed all behavioral and advertising psychology knowledge.
    
    Comprehensive seeding function that initializes all research knowledge
    in the Neo4j graph database for learning and recommendation.
    
    Knowledge Sources:
    1. Core Behavioral Research - Signal → Construct mappings
    2. Advertising Psychology - 200+ empirical findings (1989-2025)
    3. Cross-Disciplinary Science - 85+ findings from evolutionary psych, social physics, etc.
    4. Media Preferences - 50+ personality-media correlations
    
    Returns dict with counts by category.
    """
    results = {}
    
    # Seed core behavioral knowledge
    research_count = await seed_research_knowledge(neo4j_driver)
    results["behavioral_research"] = research_count
    
    # Seed advertising psychology knowledge
    adv_count = await seed_advertising_psychology_knowledge(neo4j_driver)
    results["advertising_psychology"] = adv_count
    
    # Seed cross-disciplinary science knowledge
    cross_count = await seed_cross_disciplinary_knowledge(neo4j_driver)
    results["cross_disciplinary"] = cross_count
    
    # Seed media preferences knowledge
    media_count = await seed_media_preferences_knowledge(neo4j_driver)
    results["media_preferences"] = media_count
    
    results["total"] = research_count + adv_count + cross_count + media_count
    
    logger.info(
        f"Seeded all knowledge: {results['total']} total items "
        f"({results['behavioral_research']} behavioral, "
        f"{results['advertising_psychology']} advertising psychology, "
        f"{results['cross_disciplinary']} cross-disciplinary, "
        f"{results['media_preferences']} media preferences)"
    )
    
    return results
