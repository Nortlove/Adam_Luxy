# =============================================================================
# ADAM Context Query Executor
# Location: adam/graph_reasoning/bridge/context_queries.py
# =============================================================================

"""
CONTEXT QUERY EXECUTOR

Executes Cypher queries to pull context from Neo4j.

Queries are optimized for:
- Parallelization where possible
- Caching at multiple levels
- Graceful degradation on partial failure
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neo4j import AsyncDriver
from pydantic import BaseModel

from adam.graph_reasoning.models.graph_context import (
    BigFiveProfile,
    RegulatoryFocus,
    ConstrualLevel,
    UserProfileSnapshot,
    MechanismEffectiveness,
    MechanismHistory,
    TemporalUserState,
    StateHistory,
    ArchetypeMatch,
    CategoryMechanismPrior,
    CategoryPriors,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CYPHER QUERIES
# =============================================================================

QUERY_USER_PROFILE = """
// Pull user profile with Big Five and extended traits
MATCH (u:User {user_id: $user_id})
OPTIONAL MATCH (u)-[ht:HAS_TRAIT]->(t:PersonalityDimension)
RETURN u {
    .user_id,
    .created_at,
    .total_decisions,
    .total_conversions,
    .last_decision_at,
    .profile_completeness,
    traits: collect({
        dimension_id: t.dimension_id,
        name: t.name,
        domain: t.domain,
        value: ht.value,
        confidence: ht.confidence,
        updated_at: ht.updated_at
    })
} AS profile
"""

QUERY_MECHANISM_HISTORY = """
// Pull mechanism effectiveness for a user
MATCH (u:User {user_id: $user_id})
OPTIONAL MATCH (u)-[rt:RESPONDS_TO]->(m:CognitiveMechanism)
RETURN collect({
    mechanism_id: m.mechanism_id,
    mechanism_name: m.name,
    success_rate: rt.success_rate,
    effect_size: rt.effect_size,
    trial_count: rt.trial_count,
    confidence: rt.confidence,
    last_applied_at: rt.last_applied_at,
    last_success_at: rt.last_success_at,
    trend_direction: rt.trend_direction
}) AS mechanism_history
"""

QUERY_STATE_HISTORY = """
// Pull recent state trajectory
MATCH (u:User {user_id: $user_id})
OPTIONAL MATCH (u)-[:IN_STATE]->(s:TemporalUserState)
WHERE s.timestamp > datetime() - duration({hours: $hours_lookback})
RETURN collect(s {
    .state_id,
    .arousal,
    .valence,
    .current_regulatory_focus,
    .current_construal_level,
    .session_id,
    .timestamp
}) AS states
ORDER BY s.timestamp DESC
LIMIT 10
"""

QUERY_ARCHETYPE_MATCH = """
// Find best matching archetype for cold-start
MATCH (u:User {user_id: $user_id})
OPTIONAL MATCH (u)-[ma:MATCHES_ARCHETYPE]->(a:ReviewerArchetype)
WHERE ma.is_current = true
OPTIONAL MATCH (a)-[mp:MECHANISM_PRIOR]->(m:CognitiveMechanism)
RETURN a {
    .archetype_id,
    .name,
    .openness_centroid,
    .conscientiousness_centroid,
    .extraversion_centroid,
    .agreeableness_centroid,
    .neuroticism_centroid,
    match_confidence: ma.confidence,
    distance: ma.distance,
    mechanism_priors: collect({
        mechanism_id: m.mechanism_id,
        mechanism_name: m.name,
        prior: mp.prior_effectiveness
    })
} AS archetype
"""

QUERY_CATEGORY_PRIORS = """
// Pull category-level mechanism priors
MATCH (c:AmazonCategory {name: $category_name})
OPTIONAL MATCH (c)-[me:MECHANISM_EFFECTIVENESS]->(m:CognitiveMechanism)
RETURN c {
    .name,
    mechanism_priors: collect({
        mechanism_id: m.mechanism_id,
        mechanism_name: m.name,
        prior_mean: me.mean_effectiveness,
        prior_variance: me.variance,
        sample_size: me.sample_size,
        confidence: me.confidence
    })
} AS category
"""


# =============================================================================
# PATTERN DISCOVERY QUERIES
# =============================================================================

QUERY_DISCOVER_MECHANISM_INTERACTIONS = """
// Discover mechanism interactions from co-occurrence patterns
// Finds mechanisms that succeed together more often than expected
MATCH (u:User)-[r1:RESPONDS_TO]->(m1:CognitiveMechanism)
MATCH (u)-[r2:RESPONDS_TO]->(m2:CognitiveMechanism)
WHERE m1.mechanism_id < m2.mechanism_id  // Avoid duplicates
  AND r1.trial_count >= $min_trials
  AND r2.trial_count >= $min_trials
WITH m1, m2,
     count(u) AS co_occurrence_count,
     avg(r1.success_rate * r2.success_rate) AS joint_success,
     avg(r1.success_rate) AS m1_avg_success,
     avg(r2.success_rate) AS m2_avg_success
WHERE co_occurrence_count >= $min_co_occurrences
WITH m1, m2, co_occurrence_count, joint_success, m1_avg_success, m2_avg_success,
     joint_success - (m1_avg_success * m2_avg_success) AS interaction_lift
WHERE abs(interaction_lift) > $min_interaction_strength
RETURN m1.mechanism_id AS mechanism_a,
       m1.name AS mechanism_a_name,
       m2.mechanism_id AS mechanism_b,
       m2.name AS mechanism_b_name,
       co_occurrence_count,
       interaction_lift,
       CASE WHEN interaction_lift > 0 THEN 'synergistic' ELSE 'suppressive' END AS interaction_type
ORDER BY abs(interaction_lift) DESC
LIMIT 20
"""

QUERY_DISCOVER_BEHAVIORAL_PATTERNS = """
// Find behavioral patterns that predict outcomes
// Looks for signal combinations that correlate with success
MATCH (u:User)-[:HAS_SESSION]->(s:BehavioralSession)
WHERE s.outcome_value IS NOT NULL
  AND s.created_at > datetime() - duration({days: $lookback_days})
OPTIONAL MATCH (s)-[:HAS_SIGNAL]->(sig:BehavioralSignal)
WITH u, s,
     collect({
         signal_type: sig.signal_type,
         value: sig.value,
         domain: sig.domain
     }) AS signals,
     s.outcome_value AS outcome
// Aggregate by signal patterns
WITH signals, outcome,
     [sig IN signals WHERE sig.value > 0.7 | sig.signal_type] AS high_signals,
     count(*) AS pattern_count
WHERE pattern_count >= $min_pattern_occurrences
WITH high_signals, 
     count(*) AS occurrences,
     avg(outcome) AS avg_outcome,
     stdev(outcome) AS outcome_stdev
WHERE size(high_signals) > 0
RETURN high_signals AS signal_pattern,
       occurrences,
       avg_outcome,
       outcome_stdev,
       avg_outcome - 0.5 AS lift_over_baseline
ORDER BY abs(lift_over_baseline) DESC
LIMIT 20
"""

QUERY_FIND_USERS_EXHIBITING_PATTERN = """
// Find users who exhibit a specific behavioral pattern
MATCH (u:User)-[:HAS_SESSION]->(s:BehavioralSession)
WHERE s.created_at > datetime() - duration({days: $lookback_days})
OPTIONAL MATCH (s)-[:HAS_SIGNAL]->(sig:BehavioralSignal)
WHERE sig.signal_type IN $signal_types
WITH u, s, collect(sig.value) AS signal_values
WHERE size(signal_values) = size($signal_types)
  AND all(v IN signal_values WHERE v > $threshold)
RETURN DISTINCT u.user_id AS user_id,
       count(s) AS session_count,
       avg(s.outcome_value) AS avg_outcome
ORDER BY session_count DESC
LIMIT 100
"""

QUERY_DISCOVER_COHORTS = """
// Discover natural user cohorts based on mechanism response patterns
MATCH (u:User)-[r:RESPONDS_TO]->(m:CognitiveMechanism)
WHERE r.trial_count >= $min_trials
WITH u, 
     collect({mechanism: m.mechanism_id, success_rate: r.success_rate}) AS mech_profile,
     avg(r.success_rate) AS overall_success
// Create feature vector for clustering
WITH u, mech_profile, overall_success,
     [mp IN mech_profile | mp.success_rate] AS success_vector
WHERE size(success_vector) >= 3  // Need enough mechanisms for meaningful clustering
RETURN u.user_id AS user_id,
       mech_profile,
       overall_success,
       success_vector
ORDER BY overall_success DESC
"""

QUERY_TEMPORAL_PATTERNS = """
// Discover temporal patterns in user behavior
MATCH (u:User)-[:IN_STATE]->(s:TemporalUserState)
WHERE s.timestamp > datetime() - duration({days: $lookback_days})
WITH u, s
ORDER BY u.user_id, s.timestamp
WITH u, collect(s) AS states
WHERE size(states) >= 3
// Analyze state trajectory
WITH u,
     [i IN range(0, size(states)-2) | 
         states[i+1].arousal - states[i].arousal
     ] AS arousal_changes,
     [i IN range(0, size(states)-2) | 
         states[i+1].valence - states[i].valence
     ] AS valence_changes
WITH u,
     reduce(sum = 0.0, x IN arousal_changes | sum + x) / size(arousal_changes) AS avg_arousal_trend,
     reduce(sum = 0.0, x IN valence_changes | sum + x) / size(valence_changes) AS avg_valence_trend
RETURN u.user_id AS user_id,
       avg_arousal_trend,
       avg_valence_trend,
       CASE 
           WHEN avg_arousal_trend > 0.1 AND avg_valence_trend > 0.1 THEN 'engaging'
           WHEN avg_arousal_trend < -0.1 AND avg_valence_trend < -0.1 THEN 'disengaging'
           WHEN avg_arousal_trend > 0.1 AND avg_valence_trend < -0.1 THEN 'frustrated'
           WHEN avg_arousal_trend < -0.1 AND avg_valence_trend > 0.1 THEN 'calming'
           ELSE 'stable'
       END AS trajectory_type
"""

QUERY_CROSS_DOMAIN_PATTERNS = """
// Find patterns that transfer across categories
MATCH (u:User)-[:VIEWED_IN_CATEGORY]->(c1:AmazonCategory)
MATCH (u)-[:VIEWED_IN_CATEGORY]->(c2:AmazonCategory)
WHERE c1.name <> c2.name
MATCH (u)-[r1:RESPONDS_TO_IN {category: c1.name}]->(m:CognitiveMechanism)
MATCH (u)-[r2:RESPONDS_TO_IN {category: c2.name}]->(m)
WHERE r1.trial_count >= $min_trials AND r2.trial_count >= $min_trials
WITH m, c1.name AS category_a, c2.name AS category_b,
     count(u) AS user_count,
     avg(r1.success_rate) AS success_in_a,
     avg(r2.success_rate) AS success_in_b,
     abs(avg(r1.success_rate) - avg(r2.success_rate)) AS success_diff
WHERE user_count >= $min_users
  AND success_diff < $max_success_diff  // Similar success = transferable pattern
RETURN m.mechanism_id AS mechanism,
       m.name AS mechanism_name,
       category_a,
       category_b,
       user_count,
       success_in_a,
       success_in_b,
       (success_in_a + success_in_b) / 2 AS avg_success,
       'transferable' AS pattern_type
ORDER BY user_count DESC
LIMIT 20
"""


# =============================================================================
# HYPOTHESIS MANAGEMENT QUERIES
# =============================================================================

QUERY_CREATE_HYPOTHESIS = """
// Create a new hypothesis node
CREATE (h:Hypothesis {
    hypothesis_id: $hypothesis_id,
    hypothesis_type: $hypothesis_type,
    statement: $statement,
    expected_effect_size: $expected_effect_size,
    status: 'pending',
    created_at: datetime(),
    created_by: $created_by,
    source: $source,
    related_pattern_id: $related_pattern_id,
    test_count: 0,
    validation_rate: 0.0,
    confidence: 0.0
})
RETURN h
"""

QUERY_UPDATE_HYPOTHESIS = """
// Update hypothesis after test
MATCH (h:Hypothesis {hypothesis_id: $hypothesis_id})
SET h.test_count = h.test_count + 1,
    h.validation_rate = (h.validation_rate * (h.test_count - 1) + $success) / h.test_count,
    h.confidence = CASE 
        WHEN h.test_count > 50 THEN 0.9
        WHEN h.test_count > 20 THEN 0.7
        WHEN h.test_count > 10 THEN 0.5
        ELSE 0.3
    END,
    h.status = CASE 
        WHEN h.test_count >= $min_tests_for_validation AND h.validation_rate >= $validation_threshold THEN 'validated'
        WHEN h.test_count >= $min_tests_for_validation AND h.validation_rate < $rejection_threshold THEN 'rejected'
        ELSE 'testing'
    END,
    h.last_tested_at = datetime()
RETURN h
"""

QUERY_GET_TESTABLE_HYPOTHESES = """
// Get hypotheses ready for testing
MATCH (h:Hypothesis)
WHERE h.status IN ['pending', 'testing']
  AND (h.last_tested_at IS NULL OR h.last_tested_at < datetime() - duration({hours: $cooldown_hours}))
RETURN h {
    .hypothesis_id,
    .hypothesis_type,
    .statement,
    .expected_effect_size,
    .test_count,
    .validation_rate,
    .confidence,
    .source
}
ORDER BY h.test_count ASC, h.created_at ASC
LIMIT $limit
"""


# =============================================================================
# PSYCHOLOGICAL CONSTRUCT QUERIES
# =============================================================================

QUERY_GET_PSYCHOLOGICAL_CONSTRUCTS = """
// Get all psychological constructs with their current state
MATCH (c:PsychologicalConstruct)
OPTIONAL MATCH (c)-[:ACTIVATES]->(m:CognitiveMechanism)
OPTIONAL MATCH (c)<-[:MAPS_TO]-(s:BehavioralSignal)
RETURN c {
    .construct_id,
    .name,
    .domain,
    .description,
    .is_validated,
    .sample_size,
    .effect_size,
    activated_mechanisms: collect(DISTINCT m.mechanism_id),
    signal_mappings: collect(DISTINCT s.signal_type)
}
"""

QUERY_CREATE_BEHAVIORAL_PATTERN = """
// Create a discovered behavioral pattern
CREATE (p:BehavioralPattern {
    pattern_id: $pattern_id,
    pattern_name: $pattern_name,
    description: $description,
    signal_pattern: $signal_pattern,
    predicted_outcome: $predicted_outcome,
    sample_size: $sample_size,
    effect_size: $effect_size,
    p_value: $p_value,
    lift: $lift,
    status: 'discovered',
    discovered_at: datetime(),
    discovered_by: $discovered_by
})
// Link to predicted construct if provided
WITH p
OPTIONAL MATCH (c:PsychologicalConstruct {construct_id: $construct_id})
FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
    CREATE (p)-[:PREDICTS]->(c)
)
// Link to related mechanisms
WITH p
UNWIND $mechanism_ids AS mech_id
OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: mech_id})
FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
    CREATE (p)-[:ASSOCIATED_WITH]->(m)
)
RETURN p
"""

QUERY_LINK_USER_TO_PATTERN = """
// Create EXHIBITS relationship when user matches pattern
MATCH (u:User {user_id: $user_id})
MATCH (p:BehavioralPattern {pattern_id: $pattern_id})
MERGE (u)-[e:EXHIBITS]->(p)
ON CREATE SET
    e.first_observed = datetime(),
    e.observation_count = 1,
    e.confidence = $confidence
ON MATCH SET
    e.observation_count = e.observation_count + 1,
    e.last_observed = datetime(),
    e.confidence = CASE 
        WHEN e.observation_count > 10 THEN 0.9
        WHEN e.observation_count > 5 THEN 0.7
        ELSE e.confidence
    END
RETURN e
"""


# =============================================================================
# CONTEXT QUERY EXECUTOR
# =============================================================================

class ContextQueryExecutor:
    """
    Executes context queries against Neo4j.
    
    Features:
    - Parallel query execution
    - Result caching
    - Graceful degradation
    """
    
    def __init__(self, neo4j_driver: AsyncDriver, redis_cache=None):
        self.neo4j = neo4j_driver
        self.cache = redis_cache
        self._cache_ttl = 300  # 5 minutes
    
    async def pull_user_profile(self, user_id: str) -> UserProfileSnapshot:
        """Pull user profile from Neo4j."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(QUERY_USER_PROFILE, user_id=user_id)
                record = await result.single()
                
                if not record or not record["profile"]:
                    # Return cold-start profile
                    return UserProfileSnapshot(
                        user_id=user_id,
                        is_cold_start=True,
                        profile_completeness=0.0,
                    )
                
                profile_data = record["profile"]
                traits = profile_data.get("traits", [])
                
                # Extract Big Five
                big_five = BigFiveProfile()
                for trait in traits:
                    if trait.get("domain") == "Big Five":
                        name = trait.get("name", "").lower()
                        value = trait.get("value", 0.5)
                        confidence = trait.get("confidence", 0.5)
                        
                        if name == "openness":
                            big_five.openness = value
                            big_five.openness_confidence = confidence
                        elif name == "conscientiousness":
                            big_five.conscientiousness = value
                            big_five.conscientiousness_confidence = confidence
                        elif name == "extraversion":
                            big_five.extraversion = value
                            big_five.extraversion_confidence = confidence
                        elif name == "agreeableness":
                            big_five.agreeableness = value
                            big_five.agreeableness_confidence = confidence
                        elif name == "neuroticism":
                            big_five.neuroticism = value
                            big_five.neuroticism_confidence = confidence
                
                # Extract extended traits
                extended_traits = {}
                extended_confidence = {}
                for trait in traits:
                    if trait.get("domain") != "Big Five":
                        trait_name = trait.get("name")
                        if trait_name:
                            extended_traits[trait_name] = trait.get("value", 0.5)
                            extended_confidence[trait_name] = trait.get("confidence", 0.5)
                
                # Build profile
                total_decisions = profile_data.get("total_decisions", 0) or 0
                total_conversions = profile_data.get("total_conversions", 0) or 0
                
                return UserProfileSnapshot(
                    user_id=user_id,
                    big_five=big_five,
                    extended_traits=extended_traits,
                    extended_trait_confidence=extended_confidence,
                    total_decisions=total_decisions,
                    total_conversions=total_conversions,
                    overall_conversion_rate=total_conversions / max(1, total_decisions),
                    profile_completeness=profile_data.get("profile_completeness", 0.1) or 0.1,
                    is_cold_start=total_decisions < 5,
                )
                
        except Exception as e:
            logger.error(f"Failed to pull user profile: {e}")
            return UserProfileSnapshot(
                user_id=user_id,
                is_cold_start=True,
                profile_completeness=0.0,
            )
    
    async def pull_mechanism_history(self, user_id: str) -> MechanismHistory:
        """Pull mechanism effectiveness history from Neo4j."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(QUERY_MECHANISM_HISTORY, user_id=user_id)
                record = await result.single()
                
                if not record:
                    return MechanismHistory(user_id=user_id)
                
                history_data = record["mechanism_history"]
                
                # Build mechanism effectiveness list
                mechanisms = []
                total_trials = 0
                
                for mech in history_data:
                    if mech.get("mechanism_id"):
                        effectiveness = MechanismEffectiveness(
                            mechanism_id=mech["mechanism_id"],
                            mechanism_name=mech.get("mechanism_name", ""),
                            success_rate=mech.get("success_rate", 0.5) or 0.5,
                            effect_size=mech.get("effect_size", 0.0) or 0.0,
                            trial_count=mech.get("trial_count", 0) or 0,
                            confidence=mech.get("confidence", 0.5) or 0.5,
                            trend_direction=mech.get("trend_direction", "stable") or "stable",
                        )
                        mechanisms.append(effectiveness)
                        total_trials += effectiveness.trial_count
                
                # Rank mechanisms
                ranked = sorted(mechanisms, key=lambda m: m.success_rate, reverse=True)
                top_mechanisms = [m.mechanism_id for m in ranked[:3] if m.success_rate > 0.5]
                underperforming = [m.mechanism_id for m in ranked if m.success_rate < 0.3]
                
                return MechanismHistory(
                    user_id=user_id,
                    mechanism_effectiveness=mechanisms,
                    top_mechanisms=top_mechanisms,
                    underperforming_mechanisms=underperforming,
                    total_mechanism_trials=total_trials,
                )
                
        except Exception as e:
            logger.error(f"Failed to pull mechanism history: {e}")
            return MechanismHistory(user_id=user_id)
    
    async def pull_state_history(
        self,
        user_id: str,
        hours_lookback: int = 24,
    ) -> StateHistory:
        """Pull recent state trajectory from Neo4j."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_STATE_HISTORY,
                    user_id=user_id,
                    hours_lookback=hours_lookback,
                )
                record = await result.single()
                
                if not record or not record["states"]:
                    return StateHistory(user_id=user_id)
                
                states_data = record["states"]
                
                # Build state list
                states = []
                for s in states_data:
                    state = TemporalUserState(
                        state_id=s.get("state_id", f"state_{len(states)}"),
                        user_id=user_id,
                        arousal=s.get("arousal", 0.5) or 0.5,
                        valence=s.get("valence", 0.5) or 0.5,
                        current_regulatory_focus=s.get("current_regulatory_focus", "balanced") or "balanced",
                        current_construal_level=s.get("current_construal_level", 0.5) or 0.5,
                        session_id=s.get("session_id"),
                    )
                    states.append(state)
                
                # Compute aggregates
                if states:
                    avg_arousal = sum(s.arousal for s in states) / len(states)
                    avg_valence = sum(s.valence for s in states) / len(states)
                else:
                    avg_arousal = 0.5
                    avg_valence = 0.5
                
                return StateHistory(
                    user_id=user_id,
                    recent_states=states,
                    current_state=states[0] if states else None,
                    avg_arousal=avg_arousal,
                    avg_valence=avg_valence,
                )
                
        except Exception as e:
            logger.error(f"Failed to pull state history: {e}")
            return StateHistory(user_id=user_id)
    
    async def pull_archetype_match(self, user_id: str) -> Optional[ArchetypeMatch]:
        """Pull best matching archetype for cold-start."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(QUERY_ARCHETYPE_MATCH, user_id=user_id)
                record = await result.single()
                
                if not record or not record["archetype"]:
                    return None
                
                arch_data = record["archetype"]
                
                # Build mechanism priors dict
                priors = {}
                for mp in arch_data.get("mechanism_priors", []):
                    if mp.get("mechanism_id"):
                        priors[mp["mechanism_id"]] = mp.get("prior", 0.5)
                
                # Build Big Five centroid
                big_five = BigFiveProfile(
                    openness=arch_data.get("openness_centroid", 0.5) or 0.5,
                    conscientiousness=arch_data.get("conscientiousness_centroid", 0.5) or 0.5,
                    extraversion=arch_data.get("extraversion_centroid", 0.5) or 0.5,
                    agreeableness=arch_data.get("agreeableness_centroid", 0.5) or 0.5,
                    neuroticism=arch_data.get("neuroticism_centroid", 0.5) or 0.5,
                )
                
                return ArchetypeMatch(
                    archetype_id=arch_data.get("archetype_id", ""),
                    archetype_name=arch_data.get("name", ""),
                    match_confidence=arch_data.get("match_confidence", 0.5) or 0.5,
                    distance_to_centroid=arch_data.get("distance", 0.0) or 0.0,
                    archetype_big_five=big_five,
                    mechanism_priors=priors,
                )
                
        except Exception as e:
            logger.error(f"Failed to pull archetype match: {e}")
            return None
    
    async def pull_category_priors(
        self,
        category_name: str,
    ) -> Optional[CategoryPriors]:
        """Pull category-level mechanism priors."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_CATEGORY_PRIORS,
                    category_name=category_name,
                )
                record = await result.single()
                
                if not record or not record["category"]:
                    return None
                
                cat_data = record["category"]
                
                # Build mechanism priors
                priors = []
                for mp in cat_data.get("mechanism_priors", []):
                    if mp.get("mechanism_id"):
                        prior = CategoryMechanismPrior(
                            category_id=category_name,
                            category_name=category_name,
                            mechanism_id=mp["mechanism_id"],
                            mechanism_name=mp.get("mechanism_name", ""),
                            prior_mean=mp.get("prior_mean", 0.5) or 0.5,
                            prior_variance=mp.get("prior_variance", 0.1) or 0.1,
                            sample_size=mp.get("sample_size", 0) or 0,
                            prior_confidence=mp.get("confidence", 0.5) or 0.5,
                        )
                        priors.append(prior)
                
                # Rank by prior mean
                top_mechanisms = [
                    p.mechanism_id
                    for p in sorted(priors, key=lambda p: p.prior_mean, reverse=True)[:3]
                ]
                
                return CategoryPriors(
                    category_id=category_name,
                    category_name=category_name,
                    mechanism_priors=priors,
                    top_mechanisms=top_mechanisms,
                )
                
        except Exception as e:
            logger.error(f"Failed to pull category priors: {e}")
            return None
    
    # -------------------------------------------------------------------------
    # PATTERN DISCOVERY
    # -------------------------------------------------------------------------
    
    async def discover_mechanism_interactions(
        self,
        min_trials: int = 5,
        min_co_occurrences: int = 10,
        min_interaction_strength: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Discover mechanism interactions from graph patterns.
        
        Returns pairs of mechanisms that synergize or suppress each other.
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_DISCOVER_MECHANISM_INTERACTIONS,
                    min_trials=min_trials,
                    min_co_occurrences=min_co_occurrences,
                    min_interaction_strength=min_interaction_strength,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to discover mechanism interactions: {e}")
            return []
    
    async def discover_behavioral_patterns(
        self,
        lookback_days: int = 30,
        min_pattern_occurrences: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Discover behavioral patterns that correlate with outcomes.
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_DISCOVER_BEHAVIORAL_PATTERNS,
                    lookback_days=lookback_days,
                    min_pattern_occurrences=min_pattern_occurrences,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to discover behavioral patterns: {e}")
            return []
    
    async def find_users_with_pattern(
        self,
        signal_types: List[str],
        threshold: float = 0.7,
        lookback_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Find users who exhibit a specific behavioral pattern.
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_FIND_USERS_EXHIBITING_PATTERN,
                    signal_types=signal_types,
                    threshold=threshold,
                    lookback_days=lookback_days,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to find users with pattern: {e}")
            return []
    
    async def discover_cohorts(
        self,
        min_trials: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Discover natural user cohorts based on mechanism response.
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_DISCOVER_COHORTS,
                    min_trials=min_trials,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to discover cohorts: {e}")
            return []
    
    async def discover_temporal_patterns(
        self,
        lookback_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Discover temporal patterns in user state trajectories.
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_TEMPORAL_PATTERNS,
                    lookback_days=lookback_days,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to discover temporal patterns: {e}")
            return []
    
    async def discover_cross_domain_patterns(
        self,
        min_trials: int = 5,
        min_users: int = 10,
        max_success_diff: float = 0.15,
    ) -> List[Dict[str, Any]]:
        """
        Find mechanism patterns that transfer across categories.
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_CROSS_DOMAIN_PATTERNS,
                    min_trials=min_trials,
                    min_users=min_users,
                    max_success_diff=max_success_diff,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to discover cross-domain patterns: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # HYPOTHESIS MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def create_hypothesis(
        self,
        hypothesis_id: str,
        hypothesis_type: str,
        statement: str,
        expected_effect_size: float,
        created_by: str = "system",
        source: str = "pattern_discovery",
        related_pattern_id: Optional[str] = None,
    ) -> bool:
        """Create a new hypothesis for testing."""
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_CREATE_HYPOTHESIS,
                    hypothesis_id=hypothesis_id,
                    hypothesis_type=hypothesis_type,
                    statement=statement,
                    expected_effect_size=expected_effect_size,
                    created_by=created_by,
                    source=source,
                    related_pattern_id=related_pattern_id,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to create hypothesis: {e}")
            return False
    
    async def update_hypothesis(
        self,
        hypothesis_id: str,
        success: bool,
        min_tests_for_validation: int = 20,
        validation_threshold: float = 0.7,
        rejection_threshold: float = 0.3,
    ) -> bool:
        """Update hypothesis after a test."""
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_UPDATE_HYPOTHESIS,
                    hypothesis_id=hypothesis_id,
                    success=1.0 if success else 0.0,
                    min_tests_for_validation=min_tests_for_validation,
                    validation_threshold=validation_threshold,
                    rejection_threshold=rejection_threshold,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update hypothesis: {e}")
            return False
    
    async def get_testable_hypotheses(
        self,
        cooldown_hours: int = 1,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get hypotheses ready for testing."""
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    QUERY_GET_TESTABLE_HYPOTHESES,
                    cooldown_hours=cooldown_hours,
                    limit=limit,
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Failed to get testable hypotheses: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # BEHAVIORAL PATTERN MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def create_behavioral_pattern(
        self,
        pattern_id: str,
        pattern_name: str,
        description: str,
        signal_pattern: List[str],
        predicted_outcome: str,
        sample_size: int,
        effect_size: float,
        p_value: float,
        lift: float,
        discovered_by: str = "system",
        construct_id: Optional[str] = None,
        mechanism_ids: Optional[List[str]] = None,
    ) -> bool:
        """Create a discovered behavioral pattern."""
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_CREATE_BEHAVIORAL_PATTERN,
                    pattern_id=pattern_id,
                    pattern_name=pattern_name,
                    description=description,
                    signal_pattern=signal_pattern,
                    predicted_outcome=predicted_outcome,
                    sample_size=sample_size,
                    effect_size=effect_size,
                    p_value=p_value,
                    lift=lift,
                    discovered_by=discovered_by,
                    construct_id=construct_id,
                    mechanism_ids=mechanism_ids or [],
                )
                return True
        except Exception as e:
            logger.error(f"Failed to create behavioral pattern: {e}")
            return False
    
    async def link_user_to_pattern(
        self,
        user_id: str,
        pattern_id: str,
        confidence: float = 0.5,
    ) -> bool:
        """Create EXHIBITS relationship between user and pattern."""
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_LINK_USER_TO_PATTERN,
                    user_id=user_id,
                    pattern_id=pattern_id,
                    confidence=confidence,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to link user to pattern: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # ADVERTISING KNOWLEDGE MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def store_advertising_knowledge(
        self,
        knowledge_id: str,
        predictor_category: str,
        predictor_name: str,
        predictor_value: str,
        ad_element: str,
        element_specification: str,
        outcome_metric: str,
        outcome_direction: str,
        effect_size: float,
        effect_type: str,
        robustness_tier: int,
        study_count: int = 1,
        related_mechanisms: Optional[List[str]] = None,
    ) -> bool:
        """Store advertising knowledge from consumer psychology research."""
        query = """
        MERGE (ak:AdvertisingKnowledge {knowledge_id: $knowledge_id})
        SET ak.predictor_category = $predictor_category,
            ak.predictor_name = $predictor_name,
            ak.predictor_value = $predictor_value,
            ak.ad_element = $ad_element,
            ak.element_specification = $element_specification,
            ak.outcome_metric = $outcome_metric,
            ak.outcome_direction = $outcome_direction,
            ak.effect_size = $effect_size,
            ak.effect_type = $effect_type,
            ak.robustness_tier = $robustness_tier,
            ak.study_count = $study_count,
            ak.updated_at = datetime()
        
        // Link to related mechanisms
        WITH ak
        UNWIND $related_mechanisms AS mech_id
        MATCH (m:CognitiveMechanism {mechanism_id: mech_id})
        MERGE (ak)-[:ACTIVATES]->(m)
        
        RETURN ak.knowledge_id
        """
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    query,
                    knowledge_id=knowledge_id,
                    predictor_category=predictor_category,
                    predictor_name=predictor_name,
                    predictor_value=predictor_value or "",
                    ad_element=ad_element,
                    element_specification=element_specification,
                    outcome_metric=outcome_metric,
                    outcome_direction=outcome_direction,
                    effect_size=effect_size,
                    effect_type=effect_type,
                    robustness_tier=robustness_tier,
                    study_count=study_count,
                    related_mechanisms=related_mechanisms or [],
                )
                return True
        except Exception as e:
            logger.error(f"Failed to store advertising knowledge: {e}")
            return False
    
    async def get_advertising_knowledge_for_user(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get relevant advertising knowledge for a user based on their profile.
        
        Returns knowledge items that match the user's personality traits,
        psychological state, and demographics.
        """
        query = """
        // Get user's personality traits
        MATCH (u:User {user_id: $user_id})-[ht:HAS_TRAIT]->(t:PersonalityDimension)
        
        // Find matching advertising knowledge
        MATCH (ak:AdvertisingKnowledge)
        WHERE ak.predictor_category = 'personality'
          AND ak.predictor_name = toLower(t.name)
          AND (
            (ak.predictor_value = 'high' AND ht.value >= 0.6) OR
            (ak.predictor_value = 'low' AND ht.value <= 0.4)
          )
        
        RETURN ak {
            .knowledge_id,
            .predictor_category,
            .predictor_name,
            .predictor_value,
            .ad_element,
            .element_specification,
            .outcome_metric,
            .outcome_direction,
            .effect_size,
            .effect_type,
            .robustness_tier,
            matched_trait_value: ht.value
        } AS knowledge
        ORDER BY ak.robustness_tier, ak.effect_size DESC
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(query, user_id=user_id)
                records = await result.data()
                return [r["knowledge"] for r in records]
        except Exception as e:
            logger.error(f"Failed to get advertising knowledge for user: {e}")
            return []
    
    async def get_advertising_knowledge_for_predictor(
        self,
        predictor_name: str,
        robustness_tier: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get all advertising knowledge for a predictor variable."""
        query = """
        MATCH (ak:AdvertisingKnowledge {predictor_name: $predictor_name})
        WHERE $robustness_tier IS NULL OR ak.robustness_tier = $robustness_tier
        RETURN ak {
            .knowledge_id,
            .predictor_category,
            .predictor_name,
            .predictor_value,
            .ad_element,
            .element_specification,
            .outcome_metric,
            .outcome_direction,
            .effect_size,
            .effect_type,
            .robustness_tier
        } AS knowledge
        ORDER BY ak.robustness_tier, ak.effect_size DESC
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(
                    query,
                    predictor_name=predictor_name,
                    robustness_tier=robustness_tier,
                )
                records = await result.data()
                return [r["knowledge"] for r in records]
        except Exception as e:
            logger.error(f"Failed to get advertising knowledge for predictor: {e}")
            return []
    
    async def get_meta_analyzed_knowledge(self) -> List[Dict[str, Any]]:
        """Get all Tier 1 (meta-analyzed) advertising knowledge."""
        query = """
        MATCH (ak:AdvertisingKnowledge {robustness_tier: 1})
        RETURN ak {
            .knowledge_id,
            .predictor_category,
            .predictor_name,
            .predictor_value,
            .ad_element,
            .element_specification,
            .outcome_metric,
            .outcome_direction,
            .effect_size,
            .effect_type,
            .study_count
        } AS knowledge
        ORDER BY ak.effect_size DESC
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(query)
                records = await result.data()
                return [r["knowledge"] for r in records]
        except Exception as e:
            logger.error(f"Failed to get meta-analyzed knowledge: {e}")
            return []
    
    async def store_advertising_interaction(
        self,
        interaction_id: str,
        primary_variable: str,
        moderating_variable: str,
        interaction_type: str,
        effect_when_present: float,
        effect_when_absent: float,
    ) -> bool:
        """Store advertising interaction effect."""
        query = """
        MERGE (ai:AdvertisingInteraction {interaction_id: $interaction_id})
        SET ai.primary_variable = $primary_variable,
            ai.moderating_variable = $moderating_variable,
            ai.interaction_type = $interaction_type,
            ai.effect_when_present = $effect_when_present,
            ai.effect_when_absent = $effect_when_absent,
            ai.updated_at = datetime()
        RETURN ai.interaction_id
        """
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    query,
                    interaction_id=interaction_id,
                    primary_variable=primary_variable,
                    moderating_variable=moderating_variable,
                    interaction_type=interaction_type,
                    effect_when_present=effect_when_present,
                    effect_when_absent=effect_when_absent,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to store advertising interaction: {e}")
            return False
    
    async def get_interactions_for_variable(
        self,
        variable: str,
    ) -> List[Dict[str, Any]]:
        """Get all interactions involving a variable."""
        query = """
        MATCH (ai:AdvertisingInteraction)
        WHERE ai.primary_variable = $variable
           OR ai.moderating_variable = $variable
        RETURN ai {
            .interaction_id,
            .primary_variable,
            .moderating_variable,
            .interaction_type,
            .effect_when_present,
            .effect_when_absent
        } AS interaction
        """
        try:
            async with self.neo4j.session() as session:
                result = await session.run(query, variable=variable)
                records = await result.data()
                return [r["interaction"] for r in records]
        except Exception as e:
            logger.error(f"Failed to get interactions for variable: {e}")
            return []
