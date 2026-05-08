# =============================================================================
# ADAM Cohort Discovery Service
# Location: adam/intelligence/cohort_discovery.py
# =============================================================================

"""
COHORT DISCOVERY SERVICE

Uses Neo4j Graph Data Science to discover psychologically similar user cohorts.

Key capabilities:
1. Project user-mechanism graph for GDS algorithms
2. Run Louvain community detection for cohort discovery
3. Cache cohort assignments for fast lookup
4. Enable cohort-level learning signal sharing

Cohorts enable:
- Transfer learning between similar users
- Faster cold start via cohort priors
- Cohort-level A/B testing
- Privacy-preserving aggregation
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import asyncio

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UserCohort:
    """A discovered user cohort."""
    cohort_id: str
    size: int
    sample_members: List[str]
    dominant_mechanisms: List[str] = field(default_factory=list)
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    psychological_centroid: Dict[str, float] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # ── E / S6-prep.4 — compensatory_consumption_pattern schema slot ──
    # SCHEMA SLOT ONLY. Detection logic and offline-pipeline + bid-time-
    # wiring deferred to F / S6.1 (the consumer slice — cells condition
    # on the flag). Default values apply on every existing UserCohort
    # instance until F populates real values; Cypher persistence
    # extension is also F's responsibility (current cypher in
    # persist_cohort_assignments writes only size +
    # mechanism_effectiveness_json — new fields silently drop until F
    # extends the write path).
    #
    # Reference: Mead, N. L., Baumeister, R. F., Stillman, T. F.,
    # Rawn, C. D., & Vohs, K. D. (2010). Social exclusion causes
    # people to spend and consume strategically in the service of
    # affiliation. Journal of Consumer Research 37(5), 902-919.
    # Loh, H. C. et al. (2021). Compensatory consumption: A systematic
    # review. Journal of Consumer Behavior 20(5), 1144-1156.
    compensatory_consumption_pattern: bool = False
    compensatory_detection_confidence: float = 0.5


# =============================================================================
# F.2 / S6.1 (2 of 2) — compensatory_consumption_pattern detection
# =============================================================================
#
# Two-criterion heuristic detection from cohort.dominant_mechanisms +
# cohort.mechanism_effectiveness (the actual cohort_discovery outputs per
# Q13 finding). The original spec's per-session telemetry inputs (posture
# concentration / browsing_momentum / hour-of-day variance) don't have a
# per-cohort aggregation surface in this codebase; F.2 uses what the
# Louvain-over-RESPONDS_TO pipeline actually produces — the Cialdini-
# mechanism vocabulary is the canonical cohort-aggregated signal.
#
# Mapping rationale (Mead et al. 2010; Loh et al. 2021):
#   AFFILIATIVE mechanisms (social_proof, liking, unity) ≈ in-group
#     identification + social-bond proxy + conformity-with-others ≈
#     compensatory-consumption-as-social-substitute literature.
#   TRANSACTIONAL NEGATIVES (anchoring, scarcity, loss_aversion) ≈
#     utilitarian / risk-management response; LOW effectiveness on these
#     in a cohort indicates the cohort is NOT primarily transactional.
#
# REPLICATION + EMPIRICAL CAVEAT — Cialdini-mechanism mapping to
# compensatory-consumption literature is THEORETICALLY MOTIVATED, NOT
# EMPIRICALLY VALIDATED on this platform's data. Pilot data through
# cohort outcome tracking will tighten thresholds and may revise the
# mechanism-set selection. Heuristic substrate, NOT load-bearing
# academic citation.

COMPENSATORY_MECHANISM_INDICATORS: tuple = (
    "social_proof",   # affiliative — conformity-with-others
    "liking",         # affiliative — peer / celebrity bond proxy
    "unity",          # affiliative — in-group / shared-identity priming
)

COMPENSATORY_TRANSACTIONAL_NEGATIVES: tuple = (
    "anchoring",      # comparison-shopping / price-rationalization
    "scarcity",       # urgency / utilitarian loss-aversion
    "loss_aversion",  # transactional risk-management
)

COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD: float = 0.50
COMPENSATORY_TRANSACTIONAL_WEAKNESS_THRESHOLD: float = 0.40
COMPENSATORY_MIN_COHORT_SIZE_FOR_HIGH_CONFIDENCE: int = 200


def detect_compensatory_consumption_pattern(
    cohort: UserCohort,
) -> tuple:
    """Detect compensatory-consumption pattern in a UserCohort using its
    dominant_mechanisms and mechanism_effectiveness.

    HEURISTIC SUBSTRATE — Cialdini-mechanism vocabulary as proxy for
    compensatory-consumption literature constructs. NOT load-bearing
    academic citation. Pilot data through cohort outcome tracking will
    tighten thresholds and may revise the mechanism-set selection.

    Algorithm (two-criterion):
        (1) AFFILIATIVE-MECHANISM DOMINANCE:
            fraction of cohort.dominant_mechanisms in
            COMPENSATORY_MECHANISM_INDICATORS must be ≥
            COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD (default 0.50).

        (2) TRANSACTIONAL-MECHANISM WEAKNESS:
            mean cohort.mechanism_effectiveness across
            COMPENSATORY_TRANSACTIONAL_NEGATIVES must be <
            COMPENSATORY_TRANSACTIONAL_WEAKNESS_THRESHOLD (default 0.40).

        Both criteria required for flag = True.

    Confidence calibration:
        0.85 — both criteria met AND cohort.size ≥
               COMPENSATORY_MIN_COHORT_SIZE_FOR_HIGH_CONFIDENCE (200).
        0.65 — exactly one criterion met OR (both met but undersample).
        0.50 — neither criterion met (uninformative neutral default;
               also returned for cohorts with empty dominant_mechanisms).

    References (theoretical motivation, NOT empirical validation):
        Mead, N. L., Baumeister, R. F., Stillman, T. F., Rawn, C. D., &
            Vohs, K. D. (2010). Social exclusion causes people to spend
            and consume strategically in the service of affiliation.
            JCR 37(5), 902-919.
        Loh, H. C. et al. (2021). Compensatory consumption: A systematic
            review. JCB 20(5), 1144-1156.
        Cialdini, R. B. (2009/2016). Influence: Science and Practice
            (mechanism vocabulary mapping).
    """
    if not cohort.dominant_mechanisms:
        return (False, 0.50)

    affiliative_count = sum(
        1 for m in cohort.dominant_mechanisms
        if m in COMPENSATORY_MECHANISM_INDICATORS
    )
    affiliative_fraction = (
        affiliative_count / len(cohort.dominant_mechanisms)
    )
    criterion_1 = (
        affiliative_fraction
        >= COMPENSATORY_AFFILIATIVE_DOMINANCE_THRESHOLD
    )

    transactional_values = [
        cohort.mechanism_effectiveness.get(m, 0.5)
        for m in COMPENSATORY_TRANSACTIONAL_NEGATIVES
    ]
    mean_transactional = (
        sum(transactional_values) / len(transactional_values)
    )
    criterion_2 = (
        mean_transactional
        < COMPENSATORY_TRANSACTIONAL_WEAKNESS_THRESHOLD
    )

    flag = criterion_1 and criterion_2
    sufficient_sample = (
        cohort.size
        >= COMPENSATORY_MIN_COHORT_SIZE_FOR_HIGH_CONFIDENCE
    )

    if flag and sufficient_sample:
        confidence = 0.85
    elif (criterion_1 != criterion_2) or (flag and not sufficient_sample):
        confidence = 0.65
    else:
        confidence = 0.50

    return (flag, confidence)


@dataclass
class CohortMembership:
    """A user's cohort membership."""
    user_id: str
    cohort_id: str
    membership_score: float  # 0-1, strength of membership
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CohortLearningSignal:
    """Learning signal aggregated at cohort level."""
    cohort_id: str
    mechanism_id: str
    signal_type: str
    aggregated_value: float
    sample_size: int
    confidence: float


# =============================================================================
# COHORT DISCOVERY SERVICE
# =============================================================================

class CohortDiscoveryService:
    """
    Service for discovering and managing user cohorts.
    
    Uses Neo4j GDS Louvain algorithm to find communities of
    psychologically similar users based on their mechanism responses.
    
    The insight: Users who respond similarly to mechanisms form
    natural cohorts that can share learning signals.
    """
    
    PROJECTION_NAME = "user-mechanism-cohort-graph"
    
    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver
        self._cohorts: Dict[str, UserCohort] = {}
        self._user_cohorts: Dict[str, CohortMembership] = {}
        self._projection_active = False
        self._last_discovery: Optional[datetime] = None
    
    # =========================================================================
    # GRAPH PROJECTION
    # =========================================================================
    
    async def ensure_projection(self) -> bool:
        """Ensure the user-mechanism graph is projected for GDS."""
        if self._projection_active:
            return True
        
        if not self._driver:
            logger.warning("No Neo4j driver available for projection")
            return False
        
        # Drop existing projection if any
        await self._drop_projection()
        
        # Create new projection
        query = """
        CALL gds.graph.project(
            $projection_name,
            {
                User: {properties: []},
                CognitiveMechanism: {properties: ['population_base_rate']}
            },
            {
                RESPONDS_TO: {
                    type: 'RESPONDS_TO',
                    orientation: 'UNDIRECTED',
                    properties: ['success_rate', 'trial_count']
                }
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    projection_name=self.PROJECTION_NAME,
                )
                record = await result.single()
                
                if record:
                    self._projection_active = True
                    logger.info(
                        f"Created cohort projection: "
                        f"{record['nodeCount']} nodes, "
                        f"{record['relationshipCount']} relationships"
                    )
                    return True
                    
        except Exception as e:
            if "already exists" in str(e):
                self._projection_active = True
                return True
            logger.error(f"Failed to create projection: {e}")
        
        return False
    
    async def _drop_projection(self) -> None:
        """Drop the existing projection if any."""
        if not self._driver:
            return
        
        query = f"CALL gds.graph.drop('{self.PROJECTION_NAME}', false)"
        
        try:
            async with self._driver.session() as session:
                await session.run(query)
                self._projection_active = False
        except Exception:
            pass  # Projection may not exist
    
    # =========================================================================
    # COHORT DISCOVERY
    # =========================================================================
    
    async def discover_cohorts(
        self,
        min_community_size: int = 10,
        resolution: float = 1.0,
    ) -> List[UserCohort]:
        """
        Discover user cohorts using Louvain community detection.
        
        Args:
            min_community_size: Minimum users per cohort
            resolution: Louvain resolution (higher = more communities)
            
        Returns:
            List of discovered cohorts
        """
        if not await self.ensure_projection():
            return self._get_default_cohorts()
        
        query = """
        CALL gds.louvain.stream($projection_name, {
            includeIntermediateCommunities: false,
            maxLevels: 10,
            maxIterations: 10,
            tolerance: 0.0001,
            concurrency: 4
        })
        YIELD nodeId, communityId
        WITH gds.util.asNode(nodeId) AS node, communityId
        WHERE 'User' IN labels(node)
        WITH communityId, collect(node.user_id) AS members
        WHERE size(members) >= $min_size
        RETURN 
            communityId,
            size(members) AS size,
            members[..10] AS sample_members
        ORDER BY size DESC
        LIMIT 50
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    projection_name=self.PROJECTION_NAME,
                    min_size=min_community_size,
                )
                records = await result.data()
                
                cohorts = []
                for record in records:
                    cohort_id = f"cohort_{record['communityId']}"
                    
                    cohort = UserCohort(
                        cohort_id=cohort_id,
                        size=record["size"],
                        sample_members=record["sample_members"],
                    )
                    
                    # Store membership for each user
                    for user_id in record["sample_members"]:
                        self._user_cohorts[user_id] = CohortMembership(
                            user_id=user_id,
                            cohort_id=cohort_id,
                            membership_score=1.0,
                        )
                    
                    # Get cohort mechanism profile
                    mechanism_profile = await self._get_cohort_mechanism_profile(
                        record["sample_members"]
                    )
                    cohort.dominant_mechanisms = mechanism_profile.get("dominant", [])
                    cohort.mechanism_effectiveness = mechanism_profile.get("effectiveness", {})

                    # F.2 / S6.1 (2 of 2) — populate E's deferred slot.
                    flag, confidence = detect_compensatory_consumption_pattern(cohort)
                    cohort.compensatory_consumption_pattern = flag
                    cohort.compensatory_detection_confidence = confidence

                    cohorts.append(cohort)
                    self._cohorts[cohort_id] = cohort
                
                self._last_discovery = datetime.now(timezone.utc)
                logger.info(f"Discovered {len(cohorts)} cohorts")
                
                return cohorts
                
        except Exception as e:
            logger.error(f"Cohort discovery failed: {e}")
            return self._get_default_cohorts()
    
    async def _get_cohort_mechanism_profile(
        self,
        user_ids: List[str],
    ) -> Dict[str, Any]:
        """Get aggregated mechanism profile for a cohort."""
        if not self._driver or not user_ids:
            return {"dominant": [], "effectiveness": {}}
        
        query = """
        MATCH (u:User)-[r:RESPONDS_TO]->(m:CognitiveMechanism)
        WHERE u.user_id IN $user_ids
        WITH m.name AS mechanism,
             avg(r.success_rate) AS avg_success,
             sum(r.trial_count) AS total_trials
        WHERE total_trials > 5
        RETURN mechanism, avg_success, total_trials
        ORDER BY avg_success DESC
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query, user_ids=user_ids)
                records = await result.data()
                
                effectiveness = {}
                dominant = []
                
                for record in records:
                    mechanism = record["mechanism"]
                    effectiveness[mechanism] = record["avg_success"]
                    
                    if record["avg_success"] > 0.6:
                        dominant.append(mechanism)
                
                return {
                    "dominant": dominant[:3],
                    "effectiveness": effectiveness,
                }
                
        except Exception as e:
            logger.debug(f"Failed to get cohort profile: {e}")
            return {"dominant": [], "effectiveness": {}}
    
    def _get_default_cohorts(self) -> List[UserCohort]:
        """Return default cohorts when Neo4j unavailable."""
        defaults = [
            UserCohort(
                cohort_id="cohort_analytical",
                size=100,
                sample_members=[],
                dominant_mechanisms=["temporal_construal", "anchoring"],
                mechanism_effectiveness={"temporal_construal": 0.65, "anchoring": 0.6},
            ),
            UserCohort(
                cohort_id="cohort_social",
                size=150,
                sample_members=[],
                dominant_mechanisms=["social_proof", "mimetic_desire"],
                mechanism_effectiveness={"social_proof": 0.7, "mimetic_desire": 0.65},
            ),
            UserCohort(
                cohort_id="cohort_identity",
                size=80,
                sample_members=[],
                dominant_mechanisms=["identity_construction", "mimetic_desire"],
                mechanism_effectiveness={"identity_construction": 0.75, "mimetic_desire": 0.6},
            ),
        ]
        for cohort in defaults:
            # F.2 / S6.1 (2 of 2) — populate E's deferred slot on
            # default cohorts too, so the no-Neo4j fallback path
            # carries realistic flag values rather than silent defaults.
            flag, confidence = detect_compensatory_consumption_pattern(cohort)
            cohort.compensatory_consumption_pattern = flag
            cohort.compensatory_detection_confidence = confidence
            self._cohorts[cohort.cohort_id] = cohort
        return defaults
    
    # =========================================================================
    # COHORT LOOKUP
    # =========================================================================
    
    async def get_user_cohort(
        self,
        user_id: str,
    ) -> Optional[CohortMembership]:
        """Get a user's cohort membership."""
        # Check cache first
        if user_id in self._user_cohorts:
            return self._user_cohorts[user_id]
        
        # Query graph if available
        if self._driver:
            membership = await self._query_user_cohort(user_id)
            if membership:
                self._user_cohorts[user_id] = membership
                return membership
        
        return None
    
    async def _query_user_cohort(
        self,
        user_id: str,
    ) -> Optional[CohortMembership]:
        """Query user's cohort from graph."""
        if not self._driver:
            return None
        
        query = """
        MATCH (u:User {user_id: $user_id})
        WHERE u.cohort_id IS NOT NULL
        RETURN u.cohort_id AS cohort_id, u.cohort_score AS score
        """
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query, user_id=user_id)
                record = await result.single()
                
                if record:
                    return CohortMembership(
                        user_id=user_id,
                        cohort_id=record["cohort_id"],
                        membership_score=record.get("score", 1.0),
                    )
                    
        except Exception as e:
            logger.debug(f"Failed to query user cohort: {e}")
        
        return None
    
    async def get_cohort(
        self,
        cohort_id: str,
    ) -> Optional[UserCohort]:
        """Get a cohort by ID."""
        return self._cohorts.get(cohort_id)
    
    async def get_cohort_mechanism_priors(
        self,
        cohort_id: str,
    ) -> Dict[str, float]:
        """
        Get mechanism priors from cohort aggregated learning.
        
        This enables transfer learning within a cohort.
        """
        cohort = self._cohorts.get(cohort_id)
        if cohort:
            return cohort.mechanism_effectiveness
        return {}
    
    # =========================================================================
    # COHORT-LEVEL LEARNING
    # =========================================================================
    
    async def aggregate_learning_signal(
        self,
        user_id: str,
        mechanism_id: str,
        outcome_value: float,
    ) -> Optional[CohortLearningSignal]:
        """
        Aggregate a learning signal at cohort level.
        
        This enables learning to propagate across cohort members.
        """
        membership = await self.get_user_cohort(user_id)
        if not membership:
            return None
        
        cohort = self._cohorts.get(membership.cohort_id)
        if not cohort:
            return None
        
        # Update cohort's mechanism effectiveness (running average)
        current = cohort.mechanism_effectiveness.get(mechanism_id, 0.5)
        weight = 0.1  # Learning rate
        new_value = current * (1 - weight) + outcome_value * weight
        cohort.mechanism_effectiveness[mechanism_id] = new_value
        
        return CohortLearningSignal(
            cohort_id=cohort.cohort_id,
            mechanism_id=mechanism_id,
            signal_type="effectiveness_update",
            aggregated_value=new_value,
            sample_size=cohort.size,
            confidence=min(0.9, cohort.size / 100),
        )
    
    async def get_cohort_boost(
        self,
        user_id: str,
        mechanism_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Apply cohort-based boosting to mechanism scores.
        
        Mechanisms that work well for the user's cohort get boosted.
        """
        membership = await self.get_user_cohort(user_id)
        if not membership:
            return mechanism_scores
        
        cohort_priors = await self.get_cohort_mechanism_priors(membership.cohort_id)
        if not cohort_priors:
            return mechanism_scores
        
        boosted = mechanism_scores.copy()
        
        for mechanism, score in mechanism_scores.items():
            cohort_effectiveness = cohort_priors.get(mechanism)
            if cohort_effectiveness and cohort_effectiveness > 0.5:
                # Boost by cohort's observed effectiveness
                boost = (cohort_effectiveness - 0.5) * membership.membership_score * 0.2
                boosted[mechanism] = min(1.0, score + boost)
        
        return boosted
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    async def persist_cohort_assignments(self) -> int:
        """Persist cohort assignments and cohort metadata back to Neo4j.

        Two writes per call:
            1. User.cohort_id / cohort_score (per-user assignment)
            2. UserCohort node with mechanism_effectiveness as a JSON
               string property (per-cohort metadata, queryable from
               sync paths like graph_cache.get_cohort_priors)

        Without (2) the cascade has no way to read cohort-level
        mechanism priors at decision time — the per-user assignment
        alone is just a label.
        """
        if not self._driver:
            return 0

        assignments = [
            {
                "user_id": m.user_id,
                "cohort_id": m.cohort_id,
                "score": m.membership_score,
            }
            for m in self._user_cohorts.values()
        ]

        if not assignments:
            return 0

        # Per-cohort metadata: write each known cohort's
        # mechanism_effectiveness as a JSON-string property on a
        # UserCohort node. JSON keeps the query simple (no fan-out
        # over a Mechanism relationship) and round-trips cleanly to
        # the sync reader.
        import json
        cohort_metadata = [
            {
                "cohort_id": c.cohort_id,
                "size": c.size,
                "mechanism_effectiveness_json": json.dumps(
                    c.mechanism_effectiveness or {},
                ),
                # F.2 / S6.1 (2 of 2) — persist E's slot.
                "compensatory_consumption_pattern":
                    c.compensatory_consumption_pattern,
                "compensatory_detection_confidence":
                    c.compensatory_detection_confidence,
            }
            for c in self._cohorts.values()
        ]

        user_query = """
        UNWIND $assignments AS a
        MATCH (u:User {user_id: a.user_id})
        SET u.cohort_id = a.cohort_id,
            u.cohort_score = a.score,
            u.cohort_assigned_at = datetime()
        RETURN count(*) AS updated
        """

        cohort_query = """
        UNWIND $cohort_metadata AS c
        MERGE (uc:UserCohort {id: c.cohort_id})
        SET uc.size = c.size,
            uc.mechanism_effectiveness_json = c.mechanism_effectiveness_json,
            uc.compensatory_consumption_pattern = c.compensatory_consumption_pattern,
            uc.compensatory_detection_confidence = c.compensatory_detection_confidence,
            uc.updated_at = datetime()
        RETURN count(*) AS persisted
        """

        # Atomic per Weakness #2 (audit Item 14): user assignments and
        # cohort metadata MUST commit together. Partial failure (user
        # assignment commits, cohort metadata does not) leaves
        # User.cohort_id pointing at a UserCohort node that doesn't
        # exist, which silently breaks
        # graph_cache.get_cohort_priors → cascade boost reads {} as
        # "no cohort data" rather than as an error.
        async def _persist_tx(tx) -> int:
            result = await tx.run(user_query, assignments=assignments)
            record = await result.single()
            updated = record["updated"] if record else 0
            if cohort_metadata:
                await tx.run(cohort_query, cohort_metadata=cohort_metadata)
            return updated

        try:
            async with self._driver.session() as session:
                updated = await session.execute_write(_persist_tx)
                logger.info(
                    f"Persisted {updated} cohort assignments + "
                    f"{len(cohort_metadata)} cohort metadata nodes (atomic)"
                )
                return updated
        except Exception as e:
            logger.error(f"Failed to persist cohort assignments: {e}")
            return 0
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "cohorts_discovered": len(self._cohorts),
            "users_assigned": len(self._user_cohorts),
            "projection_active": self._projection_active,
            "last_discovery": self._last_discovery.isoformat() if self._last_discovery else None,
            "cohort_sizes": {
                c.cohort_id: c.size for c in self._cohorts.values()
            },
        }


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[CohortDiscoveryService] = None


def get_cohort_discovery_service(neo4j_driver=None) -> CohortDiscoveryService:
    """Get singleton Cohort Discovery Service."""
    global _service
    if _service is None:
        _service = CohortDiscoveryService(neo4j_driver)
    return _service
