# =============================================================================
# ADAM Graph Intelligence Layer
# Location: adam/orchestrator/graph_intelligence.py
# =============================================================================

"""
Graph Intelligence Layer

Queries Neo4j for psychological intelligence:
- Cognitive mechanisms and their effectiveness
- Buyer archetypes and their characteristics
- Mechanism synergies and antagonisms
- Personality dimension relationships

This is the "brain" that provides ADAM with its psychological knowledge.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from adam.orchestrator.models import (
    ArchetypeIntelligence,
    GraphQueryResult,
    MechanismEdge,
    MechanismIntelligence,
)

logger = logging.getLogger(__name__)


class GraphIntelligenceService:
    """
    Service for querying Neo4j graph for psychological intelligence.
    
    This is where ADAM's knowledge lives - the relationships between
    mechanisms, archetypes, personality dimensions, and persuasion strategies.
    """
    
    def __init__(self, neo4j_driver=None):
        """
        Initialize the graph intelligence service.
        
        Args:
            neo4j_driver: Neo4j driver instance (will attempt to get from infra if None)
        """
        self._driver = neo4j_driver
        self._connected = False
    
    async def _get_driver(self):
        """Get Neo4j driver, attempting to connect if needed."""
        if self._driver is not None and self._connected:
            return self._driver
        
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            
            # Ensure client is connected
            if not client.is_connected:
                connected = await client.connect()
                if not connected:
                    logger.warning("Could not connect to Neo4j")
                    self._connected = False
                    return None
            
            self._driver = client.driver
            self._connected = True
            logger.info("Neo4j driver acquired for GraphIntelligenceService")
            return self._driver
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")
            self._connected = False
            return None
    
    async def is_available(self) -> bool:
        """Check if Neo4j is available."""
        driver = await self._get_driver()
        return driver is not None
    
    # =========================================================================
    # MECHANISM QUERIES
    # =========================================================================
    
    async def get_all_mechanisms(self) -> GraphQueryResult:
        """
        Get all cognitive mechanisms from the graph.
        
        Returns mechanisms with their descriptions and optimal conditions.
        """
        start_time = time.time()
        result = GraphQueryResult(
            query_name="get_all_mechanisms",
            query_type="mechanism",
        )
        
        driver = await self._get_driver()
        if not driver:
            # Return fallback data if Neo4j not available
            return self._get_fallback_mechanisms()
        
        query = """
        MATCH (m:CognitiveMechanism)
        OPTIONAL MATCH (m)-[s:SYNERGIZES_WITH]->(m2:CognitiveMechanism)
        OPTIONAL MATCH (m)-[a:ANTAGONIZES]->(m3:CognitiveMechanism)
        RETURN m.name as name, 
               m.id as id,
               m.description as description,
               m.optimal_construal as construal,
               m.optimal_focus as focus,
               collect(DISTINCT {target: m2.name, strength: s.strength}) as synergies,
               collect(DISTINCT {target: m3.name, strength: a.strength}) as antagonisms
        """
        
        result.cypher_query = query
        
        try:
            async with driver.session() as session:
                records = await session.run(query)
                data = await records.data()
                
                for record in data:
                    if record.get("name"):
                        mechanism = MechanismIntelligence(
                            mechanism_name=record["name"],
                            mechanism_id=record.get("id", record["name"].lower()),
                            description=record.get("description"),
                            optimal_construal_level=record.get("construal"),
                            optimal_regulatory_focus=record.get("focus"),
                        )
                        
                        # Add synergies
                        for syn in record.get("synergies", []):
                            if syn.get("target"):
                                mechanism.synergies.append(MechanismEdge(
                                    target_mechanism=syn["target"],
                                    relationship_type="SYNERGIZES_WITH",
                                    strength=syn.get("strength", 0.5),
                                ))
                        
                        # Add antagonisms
                        for ant in record.get("antagonisms", []):
                            if ant.get("target"):
                                mechanism.antagonisms.append(MechanismEdge(
                                    target_mechanism=ant["target"],
                                    relationship_type="ANTAGONIZES",
                                    strength=ant.get("strength", 0.5),
                                ))
                        
                        result.mechanisms.append(mechanism)
                        result.nodes_returned += 1
                
                result.edges_returned = sum(
                    len(m.synergies) + len(m.antagonisms) 
                    for m in result.mechanisms
                )
                
        except Exception as e:
            logger.error(f"Error querying mechanisms: {e}")
            return self._get_fallback_mechanisms()
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
    
    async def get_mechanism_for_archetype(
        self, 
        archetype: str
    ) -> GraphQueryResult:
        """
        Get mechanism effectiveness for a specific archetype.
        
        This is the key query: "What mechanisms work best for Achievers?"
        
        Note: Mechanism effectiveness is stored as properties on BuyerArchetype nodes
        (mech_authority, mech_social_proof, etc.) rather than as relationships.
        """
        start_time = time.time()
        result = GraphQueryResult(
            query_name=f"get_mechanisms_for_{archetype}",
            query_type="archetype_mechanism",
        )
        
        driver = await self._get_driver()
        if not driver:
            return self._get_fallback_archetype_mechanisms(archetype)
        
        # Query archetype for mechanism effectiveness properties
        query = """
        MATCH (a:BuyerArchetype {name: $archetype})
        RETURN a.mech_authority as authority,
               a.mech_social_proof as social_proof,
               a.mech_scarcity as scarcity,
               a.mech_reciprocity as reciprocity,
               a.mech_commitment as commitment,
               a.regulatory_focus as regulatory_focus
        """
        
        result.cypher_query = query
        
        try:
            async with driver.session() as session:
                records = await session.run(query, archetype=archetype)
                data = await records.data()
                
                if not data:
                    logger.warning(f"Archetype {archetype} not found in graph")
                    return self._get_fallback_archetype_mechanisms(archetype)
                
                arch_data = data[0]
                
                # Map mechanism properties to MechanismIntelligence objects
                mech_map = {
                    "authority": arch_data.get("authority", 0.5),
                    "social_proof": arch_data.get("social_proof", 0.5),
                    "scarcity": arch_data.get("scarcity", 0.5),
                    "reciprocity": arch_data.get("reciprocity", 0.5),
                    "commitment": arch_data.get("commitment", 0.5),
                }
                
                # Now get the full mechanism details from CognitiveMechanism nodes
                mech_query = """
                MATCH (m:CognitiveMechanism)
                OPTIONAL MATCH (m)-[s:SYNERGIZES_WITH]->(m2:CognitiveMechanism)
                RETURN m.name as name, m.description as description,
                       collect(DISTINCT m2.name) as synergy_targets
                """
                mech_records = await session.run(mech_query)
                mech_data = await mech_records.data()
                
                for mech in mech_data:
                    mech_name = mech.get("name", "")
                    # Map mechanism name to our effectiveness keys
                    effectiveness_key = mech_name.lower().replace(" ", "_")
                    effectiveness = mech_map.get(effectiveness_key, 0.5)
                    
                    mechanism = MechanismIntelligence(
                        mechanism_name=mech_name,
                        mechanism_id=effectiveness_key,
                        description=mech.get("description"),
                        archetype_effectiveness={
                            archetype: effectiveness
                        },
                    )
                    
                    # Add synergies
                    for target in mech.get("synergy_targets", []):
                        if target:
                            mechanism.synergies.append(MechanismEdge(
                                target_mechanism=target,
                                relationship_type="SYNERGIZES_WITH",
                                strength=0.6,
                            ))
                    
                    result.mechanisms.append(mechanism)
                    result.nodes_returned += 1
                
                # Sort by effectiveness
                result.mechanisms.sort(
                    key=lambda m: m.archetype_effectiveness.get(archetype, 0),
                    reverse=True
                )
                
        except Exception as e:
            logger.error(f"Error querying mechanisms for {archetype}: {e}")
            return self._get_fallback_archetype_mechanisms(archetype)
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
    
    # =========================================================================
    # ARCHETYPE QUERIES
    # =========================================================================
    
    async def get_all_archetypes(self) -> GraphQueryResult:
        """Get all buyer archetypes from the graph."""
        start_time = time.time()
        result = GraphQueryResult(
            query_name="get_all_archetypes",
            query_type="archetype",
        )
        
        driver = await self._get_driver()
        if not driver:
            return self._get_fallback_archetypes()
        
        # Query archetypes with their properties (mechanism effectiveness stored as properties)
        query = """
        MATCH (a:BuyerArchetype)
        RETURN a.name as name,
               a.archetype_id as id,
               a.description as description,
               a.regulatory_focus as focus,
               a.openness as openness,
               a.conscientiousness as conscientiousness,
               a.extraversion as extraversion,
               a.agreeableness as agreeableness,
               a.neuroticism as neuroticism,
               a.mech_authority as authority,
               a.mech_social_proof as social_proof,
               a.mech_scarcity as scarcity,
               a.mech_reciprocity as reciprocity,
               a.mech_commitment as commitment
        """
        
        result.cypher_query = query
        
        try:
            async with driver.session() as session:
                records = await session.run(query)
                data = await records.data()
                
                for record in data:
                    if record.get("name"):
                        archetype = ArchetypeIntelligence(
                            archetype_name=record["name"],
                            archetype_id=record.get("id", record["name"].lower()),
                            description=record.get("description"),
                            regulatory_focus=record.get("focus", "balanced"),
                            personality_profile={
                                "openness": record.get("openness", 0.5),
                                "conscientiousness": record.get("conscientiousness", 0.5),
                                "extraversion": record.get("extraversion", 0.5),
                                "agreeableness": record.get("agreeableness", 0.5),
                                "neuroticism": record.get("neuroticism", 0.5),
                            },
                        )
                        
                        # Add mechanism responses from individual properties
                        archetype.mechanism_responses = {
                            "Authority": record.get("authority", 0.5),
                            "Social Proof": record.get("social_proof", 0.5),
                            "Scarcity": record.get("scarcity", 0.5),
                            "Reciprocity": record.get("reciprocity", 0.5),
                            "Commitment": record.get("commitment", 0.5),
                        }
                        
                        result.archetypes.append(archetype)
                        result.nodes_returned += 1
                
        except Exception as e:
            logger.error(f"Error querying archetypes: {e}")
            return self._get_fallback_archetypes()
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
    
    async def get_archetype_by_name(self, name: str) -> Optional[ArchetypeIntelligence]:
        """Get a specific archetype by name."""
        result = await self.get_all_archetypes()
        for arch in result.archetypes:
            if arch.archetype_name.lower() == name.lower():
                return arch
        return None
    
    # =========================================================================
    # SYNERGY QUERIES
    # =========================================================================
    
    async def get_mechanism_synergies(
        self, 
        mechanism: str
    ) -> List[MechanismEdge]:
        """Get mechanisms that synergize with the given mechanism."""
        driver = await self._get_driver()
        if not driver:
            return self._get_fallback_synergies(mechanism)
        
        query = """
        MATCH (m1:CognitiveMechanism {name: $mechanism})
        MATCH (m1)-[r:SYNERGIZES_WITH]->(m2:CognitiveMechanism)
        RETURN m2.name as target, r.strength as strength, r.context as context
        ORDER BY r.strength DESC
        """
        
        synergies = []
        
        try:
            async with driver.session() as session:
                records = await session.run(query, mechanism=mechanism)
                data = await records.data()
                
                for record in data:
                    synergies.append(MechanismEdge(
                        target_mechanism=record["target"],
                        relationship_type="SYNERGIZES_WITH",
                        strength=record.get("strength", 0.5),
                        context=record.get("context"),
                    ))
                    
        except Exception as e:
            logger.error(f"Error querying synergies for {mechanism}: {e}")
            return self._get_fallback_synergies(mechanism)
        
        return synergies
    
    async def find_optimal_mechanism_combination(
        self,
        archetype: str,
        max_mechanisms: int = 3,
    ) -> List[MechanismIntelligence]:
        """
        Find the optimal combination of mechanisms for an archetype.
        
        This considers:
        1. Individual mechanism effectiveness for the archetype
        2. Synergies between mechanisms
        3. Avoiding antagonisms
        """
        # Get mechanisms for archetype
        mech_result = await self.get_mechanism_for_archetype(archetype)
        mechanisms = mech_result.mechanisms
        
        if not mechanisms:
            return []
        
        # Score each mechanism considering synergies
        scored = []
        for mech in mechanisms:
            base_score = mech.archetype_effectiveness.get(archetype, 0.5)
            
            # Boost score based on synergies with other high-scoring mechanisms
            synergy_bonus = 0.0
            for other in mechanisms:
                if other.mechanism_name != mech.mechanism_name:
                    for syn in mech.synergies:
                        if syn.target_mechanism == other.mechanism_name:
                            other_score = other.archetype_effectiveness.get(archetype, 0.5)
                            synergy_bonus += syn.strength * other_score * 0.1
            
            scored.append((mech, base_score + synergy_bonus))
        
        # Sort by combined score and return top N
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:max_mechanisms]]
    
    # =========================================================================
    # FALLBACK DATA (when Neo4j not available)
    # =========================================================================
    
    def _get_fallback_mechanisms(self) -> GraphQueryResult:
        """Fallback mechanism data based on psychological research."""
        result = GraphQueryResult(
            query_name="fallback_mechanisms",
            query_type="mechanism",
        )
        
        mechanisms_data = [
            {
                "name": "Authority",
                "id": "authority",
                "description": "Leveraging expert credibility and authoritative sources",
                "construal": "high",
                "focus": "promotion",
                "synergies": [("Social Proof", 0.7), ("Commitment", 0.6)],
            },
            {
                "name": "Social Proof",
                "id": "social_proof", 
                "description": "Demonstrating that others have chosen this option",
                "construal": "low",
                "focus": "balanced",
                "synergies": [("Authority", 0.7), ("Liking", 0.65)],
            },
            {
                "name": "Scarcity",
                "id": "scarcity",
                "description": "Emphasizing limited availability or time pressure",
                "construal": "low",
                "focus": "prevention",
                "synergies": [("Commitment", 0.6)],
                "antagonisms": [("Reciprocity", 0.4)],
            },
            {
                "name": "Reciprocity",
                "id": "reciprocity",
                "description": "Creating obligation through giving first",
                "construal": "high",
                "focus": "promotion",
                "synergies": [("Liking", 0.7)],
            },
            {
                "name": "Commitment",
                "id": "commitment",
                "description": "Building on prior commitments and consistency",
                "construal": "high",
                "focus": "prevention",
                "synergies": [("Authority", 0.6), ("Social Proof", 0.5)],
            },
            {
                "name": "Liking",
                "id": "liking",
                "description": "Leveraging similarity and rapport",
                "construal": "low",
                "focus": "promotion",
                "synergies": [("Social Proof", 0.65), ("Reciprocity", 0.7)],
            },
            {
                "name": "Novelty",
                "id": "novelty",
                "description": "Emphasizing newness and innovation",
                "construal": "high",
                "focus": "promotion",
                "synergies": [("Authority", 0.5)],
            },
        ]
        
        for data in mechanisms_data:
            mech = MechanismIntelligence(
                mechanism_name=data["name"],
                mechanism_id=data["id"],
                description=data["description"],
                optimal_construal_level=data.get("construal"),
                optimal_regulatory_focus=data.get("focus"),
            )
            
            for target, strength in data.get("synergies", []):
                mech.synergies.append(MechanismEdge(
                    target_mechanism=target,
                    relationship_type="SYNERGIZES_WITH",
                    strength=strength,
                ))
            
            for target, strength in data.get("antagonisms", []):
                mech.antagonisms.append(MechanismEdge(
                    target_mechanism=target,
                    relationship_type="ANTAGONIZES",
                    strength=strength,
                ))
            
            result.mechanisms.append(mech)
        
        result.nodes_returned = len(result.mechanisms)
        return result
    
    def _get_fallback_archetypes(self) -> GraphQueryResult:
        """Fallback archetype data based on psychological research."""
        result = GraphQueryResult(
            query_name="fallback_archetypes",
            query_type="archetype",
        )
        
        archetypes_data = [
            {
                "name": "Achiever",
                "description": "Goal-oriented, status-conscious, values success and recognition",
                "focus": "promotion",
                "personality": {"o": 0.65, "c": 0.8, "e": 0.7, "a": 0.5, "n": 0.4},
                "mechanisms": {"Authority": 0.85, "Social Proof": 0.75, "Scarcity": 0.7, "Commitment": 0.65},
            },
            {
                "name": "Explorer",
                "description": "Curious, open to new experiences, values discovery and novelty",
                "focus": "promotion",
                "personality": {"o": 0.9, "c": 0.5, "e": 0.65, "a": 0.6, "n": 0.45},
                "mechanisms": {"Novelty": 0.9, "Social Proof": 0.65, "Authority": 0.5, "Liking": 0.6},
            },
            {
                "name": "Guardian",
                "description": "Security-focused, values stability and protection",
                "focus": "prevention",
                "personality": {"o": 0.4, "c": 0.85, "e": 0.45, "a": 0.65, "n": 0.6},
                "mechanisms": {"Commitment": 0.85, "Authority": 0.8, "Social Proof": 0.7, "Scarcity": 0.6},
            },
            {
                "name": "Connector",
                "description": "Relationship-focused, values community and belonging",
                "focus": "promotion",
                "personality": {"o": 0.6, "c": 0.55, "e": 0.85, "a": 0.8, "n": 0.5},
                "mechanisms": {"Social Proof": 0.9, "Liking": 0.85, "Reciprocity": 0.8, "Commitment": 0.6},
            },
            {
                "name": "Pragmatist",
                "description": "Value-focused, practical, seeks best ROI",
                "focus": "balanced",
                "personality": {"o": 0.5, "c": 0.75, "e": 0.5, "a": 0.55, "n": 0.45},
                "mechanisms": {"Reciprocity": 0.85, "Commitment": 0.8, "Authority": 0.7, "Social Proof": 0.6},
            },
        ]
        
        for data in archetypes_data:
            arch = ArchetypeIntelligence(
                archetype_name=data["name"],
                archetype_id=data["name"].lower(),
                description=data["description"],
                regulatory_focus=data["focus"],
                personality_profile={
                    "openness": data["personality"]["o"],
                    "conscientiousness": data["personality"]["c"],
                    "extraversion": data["personality"]["e"],
                    "agreeableness": data["personality"]["a"],
                    "neuroticism": data["personality"]["n"],
                },
                mechanism_responses=data["mechanisms"],
            )
            result.archetypes.append(arch)
        
        result.nodes_returned = len(result.archetypes)
        return result
    
    def _get_fallback_archetype_mechanisms(self, archetype: str) -> GraphQueryResult:
        """Get fallback mechanism effectiveness for a specific archetype."""
        all_archetypes = self._get_fallback_archetypes()
        
        result = GraphQueryResult(
            query_name=f"fallback_mechanisms_for_{archetype}",
            query_type="archetype_mechanism",
        )
        
        # Find the archetype
        target_arch = None
        for arch in all_archetypes.archetypes:
            if arch.archetype_name.lower() == archetype.lower():
                target_arch = arch
                break
        
        if not target_arch:
            return result
        
        # Create mechanism intelligence from archetype's mechanism responses
        all_mechanisms = self._get_fallback_mechanisms()
        
        for mech in all_mechanisms.mechanisms:
            effectiveness = target_arch.mechanism_responses.get(mech.mechanism_name, 0.5)
            mech.archetype_effectiveness[archetype] = effectiveness
            result.mechanisms.append(mech)
        
        # Sort by effectiveness
        result.mechanisms.sort(
            key=lambda m: m.archetype_effectiveness.get(archetype, 0),
            reverse=True
        )
        
        result.nodes_returned = len(result.mechanisms)
        return result
    
    def _get_fallback_synergies(self, mechanism: str) -> List[MechanismEdge]:
        """Get fallback synergies for a mechanism."""
        all_mechanisms = self._get_fallback_mechanisms()
        
        for mech in all_mechanisms.mechanisms:
            if mech.mechanism_name.lower() == mechanism.lower():
                return mech.synergies
        
        return []
    
    # =========================================================================
    # iHEART CHANNEL INTELLIGENCE
    # =========================================================================
    
    async def get_matching_shows(
        self,
        target_emotions: List[str],
        target_traits: List[str],
        persuasion_techniques: Optional[List[str]] = None,
        min_score: float = 0.5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find shows/podcasts matching target psychological profile.
        
        Queries Neo4j for shows that:
        1. Evoke the target emotional states
        2. Attract the target personality traits
        3. Are receptive to planned persuasion techniques
        
        Args:
            target_emotions: List of emotion names (e.g., ["excitement", "joy"])
            target_traits: List of personality traits (e.g., ["extraversion_high"])
            persuasion_techniques: Optional list of planned techniques
            min_score: Minimum combined score threshold
            limit: Maximum results to return
            
        Returns:
            List of show matches with scores and reasoning
        """
        start_time = time.time()
        
        driver = await self._get_driver()
        if not driver:
            logger.warning("Neo4j not available for show matching")
            return self._get_fallback_shows(target_emotions, target_traits)
        
        # Build dynamic query based on inputs
        # Note: We collect ALL emotions/traits first, then filter and score in post-processing
        # This is because WHERE inside OPTIONAL MATCH is invalid Cypher
        query = """
        MATCH (s)
        WHERE s:Show OR s:Podcast
        
        // Collect all emotional states
        OPTIONAL MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState)
        
        // Collect all personality traits
        OPTIONAL MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
        
        // Collect all persuasion technique receptivity
        OPTIONAL MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique)
        
        // Get station info for shows
        OPTIONAL MATCH (station:Station)-[:BROADCASTS]->(s)
        
        // Get time slots
        OPTIONAL MATCH (s)-[:AIRS_DURING]->(t:TimeSlot)
        
        WITH s, station,
             COLLECT(DISTINCT {name: e.name, intensity: ev.intensity, valence: e.valence, arousal: e.arousal}) as all_emotions,
             COLLECT(DISTINCT {name: p.name, correlation: at.correlation, dimension: p.dimension}) as all_traits,
             COLLECT(DISTINCT {name: pt.name, effectiveness: rt.effectiveness, principle: pt.principle}) as all_persuasion,
             COLLECT(DISTINCT {name: t.name, hours: t.hours, attention: t.attention_level, mood: t.typical_mood}) as time_slots
        
        // Filter to target emotions and traits, calculate scores
        WITH s, station, all_emotions, all_traits, all_persuasion, time_slots,
             [em IN all_emotions WHERE em.name IN $target_emotions] as matched_emotions,
             [tr IN all_traits WHERE tr.name IN $target_traits] as matched_traits,
             [pr IN all_persuasion WHERE pr.name IN $target_persuasion OR size($target_persuasion) = 0] as matched_persuasion
        
        // Calculate scores based on matched items
        WITH s, station, all_emotions, all_traits, all_persuasion, time_slots,
             matched_emotions, matched_traits, matched_persuasion,
             CASE WHEN size(matched_emotions) > 0 
                  THEN REDUCE(sum = 0.0, em IN matched_emotions | sum + COALESCE(em.intensity, 0.5)) / size(matched_emotions)
                  ELSE 0.0 END as emotion_score,
             CASE WHEN size(matched_traits) > 0
                  THEN REDUCE(sum = 0.0, tr IN matched_traits | sum + COALESCE(tr.correlation, 0.5)) / size(matched_traits)
                  ELSE 0.0 END as trait_score,
             CASE WHEN size(matched_persuasion) > 0
                  THEN REDUCE(sum = 0.0, pr IN matched_persuasion | sum + COALESCE(pr.effectiveness, 0.5)) / size(matched_persuasion)
                  ELSE 0.0 END as persuasion_score
        
        // Only include shows with at least one match
        WHERE size(matched_emotions) > 0 OR size(matched_traits) > 0
        
        RETURN s.name as show_name,
               s.id as show_id,
               s.description as description,
               labels(s)[0] as show_type,
               station.brand_name as station_name,
               station.format as station_format,
               s.air_time as air_time,
               s.days as days,
               matched_emotions as emotions,
               matched_traits as traits,
               matched_persuasion as persuasion,
               time_slots,
               emotion_score,
               trait_score,
               persuasion_score,
               (emotion_score * 0.4 + trait_score * 0.35 + persuasion_score * 0.25) as total_score
        ORDER BY total_score DESC
        LIMIT $limit
        """
        
        try:
            async with driver.session() as session:
                result = await session.run(
                    query,
                    target_emotions=target_emotions or [],
                    target_traits=target_traits or [],
                    target_persuasion=persuasion_techniques or [],
                    limit=limit
                )
                data = await result.data()
                
                shows = []
                for record in data:
                    if record.get("total_score", 0) >= min_score:
                        shows.append({
                            "show_name": record["show_name"],
                            "show_id": record.get("show_id"),
                            "description": record.get("description", ""),
                            "show_type": record.get("show_type", "Show").lower(),
                            "station_name": record.get("station_name"),
                            "station_format": record.get("station_format"),
                            "air_time": record.get("air_time"),
                            "days": record.get("days"),
                            "emotions": [e for e in record.get("emotions", []) if e.get("name")],
                            "traits": [t for t in record.get("traits", []) if t.get("name")],
                            "persuasion": [p for p in record.get("persuasion", []) if p.get("name")],
                            "time_slots": [t for t in record.get("time_slots", []) if t.get("name")],
                            "emotion_score": record.get("emotion_score", 0),
                            "trait_score": record.get("trait_score", 0),
                            "persuasion_score": record.get("persuasion_score", 0),
                            "total_score": record.get("total_score", 0),
                        })
                
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Found {len(shows)} matching shows in {elapsed:.2f}ms")
                return shows
                
        except Exception as e:
            logger.error(f"Error querying shows: {e}")
            return self._get_fallback_shows(target_emotions, target_traits)
    
    async def get_show_psycholinguistic_profile(
        self,
        show_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete psycholinguistic profile for a show.
        
        Returns the full State-Behavior-Traits (SBT) profile including:
        - Emotional states evoked
        - Mindsets created
        - Behavioral tendencies triggered
        - Urges induced
        - Personality traits attracted
        - Persuasion technique receptivity
        - Optimal time slots
        """
        driver = await self._get_driver()
        if not driver:
            return None
        
        query = """
        MATCH (s {name: $show_name})
        WHERE s:Show OR s:Podcast
        
        OPTIONAL MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState)
        OPTIONAL MATCH (s)-[cm:CREATES_MINDSET]->(m:Mindset)
        OPTIONAL MATCH (s)-[tb:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency)
        OPTIONAL MATCH (s)-[iu:INDUCES_URGE]->(u:Urge)
        OPTIONAL MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
        OPTIONAL MATCH (s)-[ec:ENGAGES_COGNITIVE]->(cs:CognitiveStyle)
        OPTIONAL MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique)
        OPTIONAL MATCH (s)-[:AIRS_DURING]->(t:TimeSlot)
        OPTIONAL MATCH (station:Station)-[:BROADCASTS]->(s)
        
        RETURN s.name as name,
               s.description as description,
               station.brand_name as station,
               COLLECT(DISTINCT {name: e.name, intensity: ev.intensity, valence: e.valence, arousal: e.arousal}) as emotions,
               COLLECT(DISTINCT {name: m.name, strength: cm.strength, openness: m.openness, focus: m.focus}) as mindsets,
               COLLECT(DISTINCT {name: b.name, likelihood: tb.likelihood}) as behaviors,
               COLLECT(DISTINCT {name: u.name, potency: iu.potency}) as urges,
               COLLECT(DISTINCT {name: p.name, correlation: at.correlation, dimension: p.dimension}) as traits,
               COLLECT(DISTINCT {name: cs.name, alignment: ec.alignment}) as cognitive_styles,
               COLLECT(DISTINCT {name: pt.name, effectiveness: rt.effectiveness, principle: pt.principle}) as persuasion,
               COLLECT(DISTINCT t.name) as time_slots
        """
        
        try:
            async with driver.session() as session:
                result = await session.run(query, show_name=show_name)
                record = await result.single()
                
                if not record:
                    return None
                
                return {
                    "show_name": record["name"],
                    "description": record.get("description", ""),
                    "station": record.get("station"),
                    "emotions": [e for e in record.get("emotions", []) if e.get("name")],
                    "mindsets": [m for m in record.get("mindsets", []) if m.get("name")],
                    "behaviors": [b for b in record.get("behaviors", []) if b.get("name")],
                    "urges": [u for u in record.get("urges", []) if u.get("name")],
                    "traits": [t for t in record.get("traits", []) if t.get("name")],
                    "cognitive_styles": [c for c in record.get("cognitive_styles", []) if c.get("name")],
                    "persuasion": [p for p in record.get("persuasion", []) if p.get("name")],
                    "time_slots": record.get("time_slots", []),
                }
                
        except Exception as e:
            logger.error(f"Error getting show profile: {e}")
            return None
    
    async def get_optimal_time_slots(
        self,
        target_mindsets: Optional[List[str]] = None,
        target_attention_level: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get optimal time slots based on attention level and mindset.
        """
        driver = await self._get_driver()
        if not driver:
            return self._get_fallback_time_slots()
        
        query = """
        MATCH (t:TimeSlot)
        WHERE t.attention_level >= $min_attention
        RETURN t.name as name,
               t.hours as hours,
               t.attention_level as attention_level,
               t.typical_mood as typical_mood,
               t.context as context
        ORDER BY t.attention_level DESC
        """
        
        try:
            async with driver.session() as session:
                result = await session.run(query, min_attention=target_attention_level)
                data = await result.data()
                return data
        except Exception as e:
            logger.error(f"Error querying time slots: {e}")
            return self._get_fallback_time_slots()
    
    async def get_shows_by_persuasion_technique(
        self,
        technique: str,
        min_effectiveness: float = 0.6,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find shows most receptive to a specific persuasion technique.
        """
        driver = await self._get_driver()
        if not driver:
            return []
        
        query = """
        MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique {name: $technique})
        WHERE (s:Show OR s:Podcast) AND rt.effectiveness >= $min_effectiveness
        OPTIONAL MATCH (station:Station)-[:BROADCASTS]->(s)
        RETURN s.name as show_name,
               s.description as description,
               station.brand_name as station_name,
               rt.effectiveness as effectiveness
        ORDER BY rt.effectiveness DESC
        LIMIT $limit
        """
        
        try:
            async with driver.session() as session:
                result = await session.run(
                    query,
                    technique=technique,
                    min_effectiveness=min_effectiveness,
                    limit=limit
                )
                return await result.data()
        except Exception as e:
            logger.error(f"Error querying shows by technique: {e}")
            return []
    
    def _get_fallback_shows(
        self,
        target_emotions: List[str],
        target_traits: List[str]
    ) -> List[Dict[str, Any]]:
        """Fallback show data when Neo4j unavailable."""
        # Return generic recommendations based on target profile
        shows = []
        
        if "excitement" in target_emotions or "joy" in target_emotions:
            shows.append({
                "show_name": "Elvis Duran and the Morning Show",
                "description": "High-energy morning show with celebrity interviews",
                "show_type": "show",
                "station_format": "Top 40/CHR",
                "emotion_score": 0.8,
                "trait_score": 0.7,
                "total_score": 0.75,
                "match_reasoning": "High energy content matches target emotional profile"
            })
        
        if "extraversion_high" in target_traits:
            shows.append({
                "show_name": "The Breakfast Club",
                "description": "Culture, politics, and entertainment discussions",
                "show_type": "show",
                "station_format": "Urban",
                "emotion_score": 0.7,
                "trait_score": 0.8,
                "total_score": 0.75,
                "match_reasoning": "Social content appeals to extraverted audiences"
            })
        
        if "nostalgia" in target_emotions:
            shows.append({
                "show_name": "The Bobby Bones Show",
                "description": "Country music and storytelling",
                "show_type": "show",
                "station_format": "Country",
                "emotion_score": 0.75,
                "trait_score": 0.65,
                "total_score": 0.7,
                "match_reasoning": "Storytelling format evokes nostalgic emotions"
            })
        
        return shows
    
    def _get_fallback_time_slots(self) -> List[Dict[str, Any]]:
        """Fallback time slot data."""
        return [
            {"name": "morning_drive", "hours": "7-9", "attention_level": 0.6, "typical_mood": "focused"},
            {"name": "evening_drive", "hours": "17-19", "attention_level": 0.5, "typical_mood": "relaxed"},
            {"name": "midday", "hours": "12-14", "attention_level": 0.7, "typical_mood": "open"},
        ]


# =============================================================================
# SINGLETON
# =============================================================================

_graph_intelligence: Optional[GraphIntelligenceService] = None


def get_graph_intelligence() -> GraphIntelligenceService:
    """Get singleton GraphIntelligenceService."""
    global _graph_intelligence
    if _graph_intelligence is None:
        _graph_intelligence = GraphIntelligenceService()
    return _graph_intelligence
