# =============================================================================
# ADAM Graph Edge Intelligence Service
# Location: adam/intelligence/graph_edge_service.py
# =============================================================================

"""
GRAPH EDGE INTELLIGENCE SERVICE

Provides powerful edge-based queries for ADAM's learning loop:

1. Mechanism Synergy Computation - Query SYNERGIZES_WITH/ANTAGONIZES edges
2. Archetype Transfer - Query ARCHETYPE_RESPONDS_TO for cold start priors
3. Learning Path Attribution - Traverse decision->outcome chains
4. Causal Path Discovery - Find intervention paths
5. Research Domain Transfer - Query INFORMS_MECHANISM for research backing

These transforms graph edges from passive storage into active intelligence.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MechanismSynergy:
    """Synergy relationship between two mechanisms."""
    source_mechanism: str
    target_mechanism: str
    synergy_multiplier: float
    conditions: Dict[str, Any]
    relationship_type: str  # "synergy" or "antagonism"


@dataclass
class ArchetypeMechanismPrior:
    """Mechanism prior from archetype matching."""
    archetype_id: str
    mechanism_name: str
    success_rate: float
    confidence: float
    sample_size: int


@dataclass
class LearningPathAttribution:
    """Attribution path from decision to outcome."""
    decision_id: str
    mechanisms_applied: List[str]
    mechanism_intensities: Dict[str, float]
    outcome_value: float
    outcome_type: str
    attribution_weights: Dict[str, float]


@dataclass
class CausalPath:
    """Causal intervention path."""
    path_nodes: List[str]
    path_strength: float
    controllable_trigger: str
    target_outcome: str


@dataclass
class ResearchDomainBacking:
    """Research backing for mechanism confidence."""
    mechanism_name: str
    research_domain: str
    effect_size: float
    confidence_tier: int
    reference: str


# =============================================================================
# GRAPH EDGE SERVICE
# =============================================================================

class GraphEdgeService:
    """
    Service for leveraging graph edges in ADAM's intelligence layer.
    
    Transforms Neo4j edges into actionable intelligence:
    - Mechanism synergies boost/penalize combinations
    - Archetype priors seed Thompson Sampling
    - Causal paths suggest interventions
    - Research domains validate confidence
    """
    
    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        self._synergy_cache: Dict[str, List[MechanismSynergy]] = {}
        self._archetype_cache: Dict[str, List[ArchetypeMechanismPrior]] = {}
        self._cache_timestamp: Optional[datetime] = None
    
    # =========================================================================
    # 1. MECHANISM SYNERGY QUERIES
    # =========================================================================
    
    async def get_mechanism_synergies(
        self,
        mechanism_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[MechanismSynergy]:
        """
        Get all synergies and antagonisms for a mechanism.
        
        Args:
            mechanism_name: Name of the mechanism to query
            context: Optional context for filtering conditions
            
        Returns:
            List of synergy relationships
        """
        # Check cache first
        if mechanism_name in self._synergy_cache:
            return self._filter_by_context(
                self._synergy_cache[mechanism_name],
                context
            )
        
        if not self._driver:
            # Return hardcoded defaults when no Neo4j connection
            return self._get_default_synergies(mechanism_name)
        
        # Query Neo4j
        query = """
        MATCH (m1:CognitiveMechanism {name: $mechanism_name})
        OPTIONAL MATCH (m1)-[syn:SYNERGIZES_WITH]->(m2:CognitiveMechanism)
        OPTIONAL MATCH (m1)-[ant:ANTAGONIZES]->(m3:CognitiveMechanism)
        RETURN 
            m2.name AS synergy_target,
            syn.synergy_multiplier AS synergy_multiplier,
            syn.conditions AS synergy_conditions,
            m3.name AS antagonism_target,
            ant.antagonism_penalty AS antagonism_penalty,
            ant.conditions AS antagonism_conditions
        """
        
        synergies = []
        try:
            async with self._driver.session() as session:
                result = await session.run(query, mechanism_name=mechanism_name)
                records = await result.data()
                
                for record in records:
                    if record.get("synergy_target"):
                        synergies.append(MechanismSynergy(
                            source_mechanism=mechanism_name,
                            target_mechanism=record["synergy_target"],
                            synergy_multiplier=record.get("synergy_multiplier", 1.0),
                            conditions=record.get("synergy_conditions", {}),
                            relationship_type="synergy",
                        ))
                    
                    if record.get("antagonism_target"):
                        synergies.append(MechanismSynergy(
                            source_mechanism=mechanism_name,
                            target_mechanism=record["antagonism_target"],
                            synergy_multiplier=record.get("antagonism_penalty", 1.0),
                            conditions=record.get("antagonism_conditions", {}),
                            relationship_type="antagonism",
                        ))
                
                # Cache results
                self._synergy_cache[mechanism_name] = synergies
                
        except Exception as e:
            logger.warning(f"Failed to query synergies: {e}")
            return self._get_default_synergies(mechanism_name)
        
        return self._filter_by_context(synergies, context)
    
    async def compute_synergy_adjusted_scores(
        self,
        mechanism_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Adjust mechanism scores based on synergy/antagonism relationships.
        
        This is the key edge leverage: mechanisms that synergize with
        already-strong mechanisms get boosted, antagonistic ones get penalized.
        
        Args:
            mechanism_scores: Base scores for each mechanism
            context: Optional context for conditional synergies
            
        Returns:
            Adjusted scores incorporating synergy effects
        """
        adjusted_scores = mechanism_scores.copy()
        
        # Sort by score to process strongest first
        sorted_mechanisms = sorted(
            mechanism_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # For each strong mechanism, apply synergy effects
        for mechanism, score in sorted_mechanisms[:3]:  # Top 3 influence others
            if score < 0.5:
                continue  # Only strong mechanisms influence
            
            synergies = await self.get_mechanism_synergies(mechanism, context)
            
            for synergy in synergies:
                target = synergy.target_mechanism
                if target not in adjusted_scores:
                    continue
                
                if synergy.relationship_type == "synergy":
                    # Boost synergistic mechanisms
                    boost = (score - 0.5) * (synergy.synergy_multiplier - 1.0) * 0.3
                    adjusted_scores[target] = min(1.0, adjusted_scores[target] + boost)
                    
                    logger.debug(
                        f"Synergy boost: {mechanism} -> {target} (+{boost:.3f})"
                    )
                    
                else:  # antagonism
                    # Penalize antagonistic mechanisms
                    penalty = (score - 0.5) * (1.0 - synergy.synergy_multiplier) * 0.3
                    adjusted_scores[target] = max(0.0, adjusted_scores[target] - penalty)
                    
                    logger.debug(
                        f"Antagonism penalty: {mechanism} -> {target} (-{penalty:.3f})"
                    )
        
        return adjusted_scores
    
    def _get_default_synergies(self, mechanism_name: str) -> List[MechanismSynergy]:
        """Return hardcoded default synergies when Neo4j unavailable."""
        # Based on 004_seed_mechanisms.cypher
        default_synergies = {
            "automatic_evaluation": [
                MechanismSynergy("automatic_evaluation", "attention_dynamics", 1.3, {"context": "initial_exposure"}, "synergy"),
                MechanismSynergy("automatic_evaluation", "embodied_cognition", 1.25, {"context": "mobile_context"}, "synergy"),
                MechanismSynergy("automatic_evaluation", "identity_construction", 0.7, {"context": "deliberative_mode"}, "antagonism"),
            ],
            "wanting_liking_dissociation": [
                MechanismSynergy("wanting_liking_dissociation", "evolutionary_motive_activation", 1.35, {"context": "desire_activation"}, "synergy"),
            ],
            "mimetic_desire": [
                MechanismSynergy("mimetic_desire", "identity_construction", 1.4, {"context": "social_identity"}, "synergy"),
            ],
            "linguistic_framing": [
                MechanismSynergy("linguistic_framing", "temporal_construal", 1.3, {"context": "message_construction"}, "synergy"),
            ],
            "evolutionary_motive_activation": [
                MechanismSynergy("evolutionary_motive_activation", "automatic_evaluation", 0.75, {"context": "conscious_override"}, "antagonism"),
            ],
        }
        return default_synergies.get(mechanism_name, [])
    
    def _filter_by_context(
        self,
        synergies: List[MechanismSynergy],
        context: Optional[Dict[str, Any]],
    ) -> List[MechanismSynergy]:
        """Filter synergies by context conditions."""
        if not context:
            return synergies
        
        filtered = []
        for synergy in synergies:
            if not synergy.conditions:
                filtered.append(synergy)
                continue
            
            # Check if context matches conditions
            matches = True
            for key, value in synergy.conditions.items():
                if key in context and context[key] != value:
                    matches = False
                    break
            
            if matches:
                filtered.append(synergy)
        
        return filtered
    
    # =========================================================================
    # 2. ARCHETYPE TRANSFER QUERIES
    # =========================================================================
    
    async def get_archetype_mechanism_priors(
        self,
        archetype_id: str,
    ) -> List[ArchetypeMechanismPrior]:
        """
        Get mechanism priors from archetype's ARCHETYPE_RESPONDS_TO edges.
        
        This enables cold start users to inherit learned mechanism
        effectiveness from their matched archetype.
        
        Args:
            archetype_id: The archetype to query
            
        Returns:
            List of mechanism priors with success rates
        """
        if archetype_id in self._archetype_cache:
            return self._archetype_cache[archetype_id]
        
        if not self._driver:
            return self._get_default_archetype_priors(archetype_id)
        
        query = """
        MATCH (a:ReviewArchetype {archetype_id: $archetype_id})
        -[r:ARCHETYPE_RESPONDS_TO]->(m:CognitiveMechanism)
        RETURN 
            m.name AS mechanism_name,
            r.success_rate AS success_rate,
            r.confidence AS confidence,
            r.sample_size AS sample_size
        ORDER BY r.success_rate DESC
        """
        
        priors = []
        try:
            async with self._driver.session() as session:
                result = await session.run(query, archetype_id=archetype_id)
                records = await result.data()
                
                for record in records:
                    priors.append(ArchetypeMechanismPrior(
                        archetype_id=archetype_id,
                        mechanism_name=record["mechanism_name"],
                        success_rate=record.get("success_rate", 0.5),
                        confidence=record.get("confidence", 0.5),
                        sample_size=record.get("sample_size", 0),
                    ))
                
                self._archetype_cache[archetype_id] = priors
                
        except Exception as e:
            logger.warning(f"Failed to query archetype priors: {e}")
            return self._get_default_archetype_priors(archetype_id)
        
        return priors
    
    async def get_user_archetype_priors(
        self,
        user_id: str,
    ) -> Optional[List[ArchetypeMechanismPrior]]:
        """
        Get mechanism priors for a user based on their matched archetype.
        
        Queries: User -[:MATCHES_ARCHETYPE]-> Archetype -[:ARCHETYPE_RESPONDS_TO]-> Mechanism
        """
        if not self._driver:
            return None
        
        query = """
        MATCH (u:User {user_id: $user_id})
        -[ma:MATCHES_ARCHETYPE]->(a:ReviewArchetype)
        -[r:ARCHETYPE_RESPONDS_TO]->(m:CognitiveMechanism)
        WHERE ma.match_score > 0.3
        RETURN 
            a.archetype_id AS archetype_id,
            ma.match_score AS match_score,
            m.name AS mechanism_name,
            r.success_rate AS success_rate,
            r.confidence AS confidence,
            r.sample_size AS sample_size
        ORDER BY ma.match_score DESC, r.success_rate DESC
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query, user_id=user_id)
                records = await result.data()
                
                if not records:
                    return None
                
                priors = []
                for record in records:
                    # Weight by archetype match score
                    adjusted_confidence = (
                        record.get("confidence", 0.5) * 
                        record.get("match_score", 0.5)
                    )
                    
                    priors.append(ArchetypeMechanismPrior(
                        archetype_id=record["archetype_id"],
                        mechanism_name=record["mechanism_name"],
                        success_rate=record.get("success_rate", 0.5),
                        confidence=adjusted_confidence,
                        sample_size=record.get("sample_size", 0),
                    ))
                
                return priors
                
        except Exception as e:
            logger.warning(f"Failed to query user archetype priors: {e}")
            return None
    
    def _get_default_archetype_priors(
        self,
        archetype_id: str,
    ) -> List[ArchetypeMechanismPrior]:
        """Return default archetype priors when Neo4j unavailable."""
        # Generic priors based on archetype type
        defaults = {
            "analytical_deliberator": [
                ArchetypeMechanismPrior(archetype_id, "temporal_construal", 0.65, 0.6, 100),
                ArchetypeMechanismPrior(archetype_id, "anchoring", 0.60, 0.5, 80),
            ],
            "impulsive_experiencer": [
                ArchetypeMechanismPrior(archetype_id, "scarcity", 0.70, 0.65, 120),
                ArchetypeMechanismPrior(archetype_id, "social_proof", 0.65, 0.6, 100),
            ],
            "social_validator": [
                ArchetypeMechanismPrior(archetype_id, "mimetic_desire", 0.75, 0.7, 150),
                ArchetypeMechanismPrior(archetype_id, "social_proof", 0.70, 0.65, 130),
            ],
            "identity_seeker": [
                ArchetypeMechanismPrior(archetype_id, "identity_construction", 0.80, 0.75, 180),
                ArchetypeMechanismPrior(archetype_id, "mimetic_desire", 0.65, 0.6, 100),
            ],
        }
        return defaults.get(archetype_id, [])
    
    # =========================================================================
    # 3. LEARNING PATH ATTRIBUTION
    # =========================================================================
    
    async def get_learning_path(
        self,
        decision_id: str,
    ) -> Optional[LearningPathAttribution]:
        """
        Get complete learning path for credit attribution.
        
        Traverses: Decision -[:APPLIED_MECHANISM]-> Mechanism
                   Decision -[:HAD_OUTCOME]-> Outcome
        """
        if not self._driver:
            return None
        
        query = """
        MATCH (d:AdDecision {decision_id: $decision_id})
        OPTIONAL MATCH (d)-[am:APPLIED_MECHANISM]->(m:CognitiveMechanism)
        OPTIONAL MATCH (d)-[ho:HAD_OUTCOME]->(o:AdOutcome)
        RETURN 
            d.decision_id AS decision_id,
            collect(DISTINCT {
                mechanism: m.name, 
                intensity: am.intensity,
                was_primary: am.was_primary
            }) AS mechanisms,
            o.outcome_type AS outcome_type,
            o.outcome_value AS outcome_value
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query, decision_id=decision_id)
                record = await result.single()
                
                if not record:
                    return None
                
                mechanisms = [m for m in record["mechanisms"] if m.get("mechanism")]
                
                return LearningPathAttribution(
                    decision_id=decision_id,
                    mechanisms_applied=[m["mechanism"] for m in mechanisms],
                    mechanism_intensities={
                        m["mechanism"]: m.get("intensity", 1.0) 
                        for m in mechanisms
                    },
                    outcome_value=record.get("outcome_value", 0.0),
                    outcome_type=record.get("outcome_type", "unknown"),
                    attribution_weights=self._compute_attribution_weights(mechanisms),
                )
                
        except Exception as e:
            logger.warning(f"Failed to get learning path: {e}")
            return None
    
    def _compute_attribution_weights(
        self,
        mechanisms: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Compute attribution weights based on mechanism intensity and primacy."""
        if not mechanisms:
            return {}
        
        weights = {}
        total_intensity = sum(m.get("intensity", 1.0) for m in mechanisms)
        
        for mech in mechanisms:
            name = mech.get("mechanism")
            if not name:
                continue
            
            intensity = mech.get("intensity", 1.0)
            is_primary = mech.get("was_primary", False)
            
            # Base weight from intensity
            base_weight = intensity / max(1.0, total_intensity)
            
            # Boost primary mechanism
            if is_primary:
                base_weight *= 1.5
            
            weights[name] = base_weight
        
        # Normalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    # =========================================================================
    # 4. CAUSAL PATH DISCOVERY
    # =========================================================================
    
    async def find_causal_paths(
        self,
        target_outcome: str = "conversion",
        max_depth: int = 3,
        min_strength: float = 0.3,
    ) -> List[CausalPath]:
        """
        Find causal intervention paths to a target outcome.
        
        Traverses: (trigger)-[:CAUSES*1..depth]->(outcome)
        
        Returns paths ordered by total strength (product of edge strengths).
        """
        if not self._driver:
            return self._get_default_causal_paths(target_outcome)
        
        query = f"""
        MATCH p = (trigger:CausalVariable)-[:CAUSES*1..{max_depth}]->(target:CausalVariable {{name: $target}})
        WHERE trigger.controllable = true
        WITH p, trigger, target,
             reduce(s = 1.0, r IN relationships(p) | s * r.strength) AS path_strength
        WHERE path_strength > $min_strength
        RETURN 
            [n IN nodes(p) | n.name] AS path_nodes,
            path_strength,
            trigger.name AS trigger_name
        ORDER BY path_strength DESC
        LIMIT 10
        """
        
        paths = []
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    target=target_outcome,
                    min_strength=min_strength,
                )
                records = await result.data()
                
                for record in records:
                    paths.append(CausalPath(
                        path_nodes=record["path_nodes"],
                        path_strength=record["path_strength"],
                        controllable_trigger=record["trigger_name"],
                        target_outcome=target_outcome,
                    ))
                
        except Exception as e:
            logger.warning(f"Failed to find causal paths: {e}")
            return self._get_default_causal_paths(target_outcome)
        
        return paths
    
    def _get_default_causal_paths(self, target: str) -> List[CausalPath]:
        """Return default causal paths when Neo4j unavailable."""
        defaults = [
            CausalPath(
                path_nodes=["scarcity_signal", "urgency_perception", "conversion"],
                path_strength=0.65,
                controllable_trigger="scarcity_signal",
                target_outcome=target,
            ),
            CausalPath(
                path_nodes=["social_proof_signal", "trust", "conversion"],
                path_strength=0.60,
                controllable_trigger="social_proof_signal",
                target_outcome=target,
            ),
            CausalPath(
                path_nodes=["identity_match", "aspiration", "conversion"],
                path_strength=0.55,
                controllable_trigger="identity_match",
                target_outcome=target,
            ),
        ]
        return defaults
    
    # =========================================================================
    # 5. RESEARCH DOMAIN TRANSFER
    # =========================================================================
    
    async def get_research_backing(
        self,
        mechanism_name: str,
    ) -> List[ResearchDomainBacking]:
        """
        Get research domain backing for mechanism confidence.
        
        Queries: (domain)-[:INFORMS_MECHANISM]->(mechanism)
        
        Returns research findings that validate the mechanism.
        """
        if not self._driver:
            return self._get_default_research_backing(mechanism_name)
        
        query = """
        MATCH (rd:ResearchDomain)-[r:INFORMS_MECHANISM]->(m:CognitiveMechanism {name: $mechanism})
        OPTIONAL MATCH (rd)<-[:BELONGS_TO_DOMAIN]-(scm:SignalConstructMapping)
        WHERE scm.confidence_tier <= 2
        RETURN 
            rd.name AS domain_name,
            rd.key_finding AS key_finding,
            r.strength AS strength,
            scm.effect_size AS effect_size,
            scm.confidence_tier AS tier,
            scm.reference AS reference
        ORDER BY scm.effect_size DESC
        """
        
        backings = []
        try:
            async with self._driver.session() as session:
                result = await session.run(query, mechanism=mechanism_name)
                records = await result.data()
                
                for record in records:
                    backings.append(ResearchDomainBacking(
                        mechanism_name=mechanism_name,
                        research_domain=record["domain_name"],
                        effect_size=record.get("effect_size", 0.0),
                        confidence_tier=record.get("tier", 3),
                        reference=record.get("reference", ""),
                    ))
                
        except Exception as e:
            logger.warning(f"Failed to get research backing: {e}")
            return self._get_default_research_backing(mechanism_name)
        
        return backings
    
    def _get_default_research_backing(
        self,
        mechanism_name: str,
    ) -> List[ResearchDomainBacking]:
        """Return default research backing when Neo4j unavailable."""
        defaults = {
            "regulatory_focus": [
                ResearchDomainBacking("regulatory_focus", "regulatory_focus", 0.475, 1, "Higgins (1997)"),
            ],
            "temporal_construal": [
                ResearchDomainBacking("temporal_construal", "temporal_targeting", 0.475, 1, "Trope & Liberman CLT"),
            ],
            "social_proof": [
                ResearchDomainBacking("social_proof", "social_effects", 0.32, 1, "Cialdini (2001)"),
            ],
        }
        return defaults.get(mechanism_name, [])
    
    # =========================================================================
    # 6. TEMPORAL SEQUENCE MINING
    # =========================================================================
    
    async def find_effective_sequences(
        self,
        target_outcome: str = "conversion",
        max_sequence_length: int = 3,
        min_support: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find mechanism sequences that frequently lead to target outcomes.
        
        Mines temporal patterns from time-ordered decision edges.
        
        Returns sequences like:
        - [social_proof] -> [scarcity] -> conversion (support: 50, lift: 1.8)
        """
        if not self._driver:
            return self._get_default_sequences(target_outcome)
        
        query = """
        MATCH (u:User)-[:MADE_AD_DECISION]->(d1:AdDecision)-[:APPLIED_MECHANISM]->(m1:CognitiveMechanism)
        MATCH (d1)-[:HAD_OUTCOME]->(o:AdOutcome {outcome_type: $target})
        WHERE o.outcome_value > 0.5
        OPTIONAL MATCH (u)-[:MADE_AD_DECISION]->(d0:AdDecision)-[:APPLIED_MECHANISM]->(m0:CognitiveMechanism)
        WHERE d0.created_at < d1.created_at
          AND d0.created_at > datetime() - duration('P7D')  // Within 7 days
        WITH m1.name AS final_mechanism, 
             collect(DISTINCT m0.name) AS preceding_mechanisms,
             count(DISTINCT d1) AS support
        WHERE support >= $min_support
        RETURN final_mechanism, preceding_mechanisms, support
        ORDER BY support DESC
        LIMIT 20
        """
        
        sequences = []
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    target=target_outcome,
                    min_support=min_support,
                )
                records = await result.data()
                
                for record in records:
                    preceding = record.get("preceding_mechanisms", [])
                    final = record["final_mechanism"]
                    
                    sequences.append({
                        "sequence": preceding[:max_sequence_length-1] + [final],
                        "final_mechanism": final,
                        "support": record["support"],
                        "target_outcome": target_outcome,
                    })
                
        except Exception as e:
            logger.warning(f"Failed to find sequences: {e}")
            return self._get_default_sequences(target_outcome)
        
        return sequences
    
    async def get_next_best_mechanism(
        self,
        user_id: str,
        recent_mechanisms: List[str],
        target_outcome: str = "conversion",
    ) -> Optional[str]:
        """
        Suggest next best mechanism based on temporal patterns.
        
        Given what mechanisms were just used, suggest what should come next
        based on sequences that historically led to conversion.
        """
        if not self._driver or not recent_mechanisms:
            return None
        
        query = """
        MATCH (u:User)-[:MADE_AD_DECISION]->(d_prev:AdDecision)-[:APPLIED_MECHANISM]->(m_prev:CognitiveMechanism)
        WHERE m_prev.name IN $recent_mechanisms
        MATCH (u)-[:MADE_AD_DECISION]->(d_next:AdDecision)-[:APPLIED_MECHANISM]->(m_next:CognitiveMechanism)
        WHERE d_next.created_at > d_prev.created_at
        MATCH (d_next)-[:HAD_OUTCOME]->(o:AdOutcome)
        WHERE o.outcome_value > 0.5
        WITH m_next.name AS next_mechanism,
             count(*) AS success_count,
             avg(o.outcome_value) AS avg_outcome
        WHERE success_count >= 5
        RETURN next_mechanism, success_count, avg_outcome
        ORDER BY avg_outcome * success_count DESC
        LIMIT 1
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    recent_mechanisms=recent_mechanisms,
                )
                record = await result.single()
                
                if record:
                    return record["next_mechanism"]
                    
        except Exception as e:
            logger.debug(f"Failed to get next best mechanism: {e}")
        
        return None
    
    def _get_default_sequences(self, target: str) -> List[Dict[str, Any]]:
        """Return default sequences when Neo4j unavailable."""
        return [
            {
                "sequence": ["attention_dynamics", "social_proof", "scarcity"],
                "final_mechanism": "scarcity",
                "support": 50,
                "target_outcome": target,
            },
            {
                "sequence": ["identity_construction", "mimetic_desire"],
                "final_mechanism": "mimetic_desire",
                "support": 35,
                "target_outcome": target,
            },
        ]
    
    # =========================================================================
    # 7. COMPREHENSIVE EDGE ANALYSIS
    # =========================================================================
    
    async def get_comprehensive_edge_insights(
        self,
        user_id: Optional[str] = None,
        mechanism_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive edge-based insights.
        
        Combines:
        - Synergy relationships
        - Archetype priors
        - Causal paths
        - Research backing
        - Temporal sequences
        
        Returns a unified intelligence package.
        """
        insights = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "mechanism": mechanism_name,
        }
        
        # Synergies for mechanism
        if mechanism_name:
            synergies = await self.get_mechanism_synergies(mechanism_name)
            insights["synergies"] = [
                {
                    "target": s.target_mechanism,
                    "multiplier": s.synergy_multiplier,
                    "type": s.relationship_type,
                }
                for s in synergies
            ]
            
            # Research backing
            research = await self.get_research_backing(mechanism_name)
            insights["research_backing"] = [
                {
                    "domain": r.research_domain,
                    "effect_size": r.effect_size,
                    "tier": r.confidence_tier,
                }
                for r in research
            ]
        
        # Archetype priors for user
        if user_id:
            priors = await self.get_user_archetype_priors(user_id)
            if priors:
                insights["archetype_priors"] = [
                    {
                        "mechanism": p.mechanism_name,
                        "success_rate": p.success_rate,
                        "confidence": p.confidence,
                    }
                    for p in priors
                ]
        
        # Causal paths to conversion
        causal = await self.find_causal_paths("conversion", max_depth=2)
        insights["causal_paths"] = [
            {
                "path": p.path_nodes,
                "strength": p.path_strength,
                "trigger": p.controllable_trigger,
            }
            for p in causal[:5]
        ]
        
        # Effective sequences
        sequences = await self.find_effective_sequences("conversion")
        insights["effective_sequences"] = sequences[:5]
        
        return insights
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def clear_caches(self) -> None:
        """Clear all caches."""
        self._synergy_cache.clear()
        self._archetype_cache.clear()
        self._cache_timestamp = None


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[GraphEdgeService] = None


def get_graph_edge_service(neo4j_driver=None) -> GraphEdgeService:
    """Get singleton Graph Edge Service."""
    global _service
    if _service is None:
        _service = GraphEdgeService(neo4j_driver)
    return _service
