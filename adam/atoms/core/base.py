# =============================================================================
# ADAM Base Atom with Multi-Source Fusion
# Location: adam/atoms/core/base.py
# =============================================================================

"""
BASE ATOM

Abstract base class for all atoms with multi-source intelligence fusion.

Each atom:
1. Queries all relevant intelligence sources in parallel
2. Detects conflicts between sources
3. Optionally uses Claude for synthesis
4. Emits learning signals
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    EvidenceConflict,
    EvidenceStrength,
    FusionResult,
    ConflictSeverity,
)
from adam.atoms.models.atom_io import (
    AtomInput,
    AtomOutput,
    AtomConfig,
    AtomTier,
    AtomExecutionResult,
    AtomExecutionStatus,
)
from adam.blackboard.models.zone2_reasoning import AtomType, AtomReasoningSpace
from adam.blackboard.service import BlackboardService
from adam.blackboard.models.core import ComponentRole
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)
from adam.graph_reasoning.bridge import InteractionBridge
from adam.infrastructure.prometheus import get_metrics
from adam.core.learning.universal_learning_interface import (
    LearningSignal,
    LearningSignalType,
    LearningContribution,
    LearningQualityMetrics,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONTRIBUTION CACHE
# =============================================================================
# Thread-safe cache for tracking atom contributions to decisions
# This enables credit attribution in the Gradient Bridge

_contribution_cache: Dict[str, Dict[str, Any]] = {}


class BaseAtom(ABC):
    """
    Abstract base class for all Atom of Thought nodes.
    
    Provides:
    - Multi-source evidence gathering
    - Conflict detection
    - Fusion orchestration
    - Learning signal emission
    """
    
    # Class attributes to be overridden by subclasses
    ATOM_TYPE: AtomType = AtomType.CUSTOM
    ATOM_NAME: str = "base_atom"
    TARGET_CONSTRUCT: str = "unknown"
    
    # Which sources this atom queries
    REQUIRED_SOURCES: List[IntelligenceSourceType] = []
    OPTIONAL_SOURCES: List[IntelligenceSourceType] = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]
    
    # All 10 intelligence sources available in ADAM
    ALL_INTELLIGENCE_SOURCES: List[IntelligenceSourceType] = [
        IntelligenceSourceType.CLAUDE_REASONING,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.META_LEARNER,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.TEMPORAL_PATTERNS,
        IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
        IntelligenceSourceType.COHORT_ORGANIZATION,
    ]
    
    def __init__(
        self,
        blackboard: BlackboardService,
        bridge: InteractionBridge,
        config: Optional[AtomConfig] = None,
    ):
        self.blackboard = blackboard
        self.bridge = bridge
        self.config = config or self._default_config()
        self.metrics = get_metrics()
    
    def _default_config(self) -> AtomConfig:
        """Create default configuration."""
        return AtomConfig(
            atom_id=f"atom_{self.ATOM_NAME}",
            atom_type=self.ATOM_TYPE,
            atom_name=self.ATOM_NAME,
            tier=AtomTier.STANDARD,
            max_latency_ms=500,
            required_sources=[s.value for s in self.REQUIRED_SOURCES],
            optional_sources=[s.value for s in self.OPTIONAL_SOURCES],
        )
    
    # -------------------------------------------------------------------------
    # MAIN EXECUTION FLOW
    # -------------------------------------------------------------------------
    
    async def execute(self, atom_input: AtomInput) -> AtomExecutionResult:
        """
        Execute the atom with full multi-source fusion.
        
        Flow:
        1. Initialize reasoning space in blackboard
        2. Gather evidence from all sources (parallel)
        3. Detect conflicts between sources
        4. Fuse evidence (with or without Claude)
        5. Build output
        6. Update reasoning space
        7. Emit learning signals
        """
        start_time = datetime.now(timezone.utc)
        request_id = atom_input.request_id
        
        try:
            # Step 1: Initialize reasoning space
            reasoning_space = AtomReasoningSpace(
                request_id=request_id,
                atom_id=self.config.atom_id,
                atom_type=self.ATOM_TYPE,
            )
            reasoning_space.start()
            
            # Step 2: Gather evidence from all sources
            evidence_package = await self._gather_evidence(atom_input)
            
            # Step 3: Detect conflicts
            conflicts = self._detect_conflicts(evidence_package)
            
            # Step 4: Fuse evidence
            if self.config.tier == AtomTier.FAST or atom_input.skip_claude:
                fusion_result = await self._fuse_without_claude(
                    evidence_package, conflicts
                )
            else:
                fusion_result = await self._fuse_with_claude(
                    evidence_package, conflicts, atom_input
                )
            
            # Step 5: Build atom-specific output
            output = await self._build_output(
                atom_input, evidence_package, fusion_result
            )
            
            # Step 5b: Cache contribution for credit attribution
            self._cache_contribution(request_id, output, evidence_package, fusion_result)
            
            # Step 6: Update reasoning space
            reasoning_space.complete(
                self._to_legacy_output(output)
            )
            await self.blackboard.write_zone2_atom(
                request_id,
                self.config.atom_id,
                reasoning_space,
                role=ComponentRole.ATOM,
            )
            
            # Step 7: Emit learning signals
            await self._emit_learning_signals(output, evidence_package)
            
            # Build execution result
            end_time = datetime.now(timezone.utc)
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            self._record_metrics(output, duration_ms)
            
            return AtomExecutionResult(
                status=AtomExecutionStatus.SUCCESS,
                output=output,
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                claude_tokens_in=fusion_result.claude_tokens_in,
                claude_tokens_out=fusion_result.claude_tokens_out,
                neo4j_queries=len(evidence_package.sources_queried),
            )
            
        except Exception as e:
            logger.error(f"Atom {self.config.atom_id} failed: {e}")
            end_time = datetime.now(timezone.utc)
            
            return AtomExecutionResult(
                status=AtomExecutionStatus.FAILED,
                error_message=str(e),
                error_type=type(e).__name__,
                started_at=start_time,
                completed_at=end_time,
                duration_ms=(end_time - start_time).total_seconds() * 1000,
            )
    
    # -------------------------------------------------------------------------
    # EVIDENCE GATHERING
    # -------------------------------------------------------------------------
    
    async def _gather_evidence(
        self,
        atom_input: AtomInput,
    ) -> MultiSourceEvidence:
        """
        Gather evidence from all relevant intelligence sources in parallel.
        """
        evidence_package = MultiSourceEvidence(
            construct=self.TARGET_CONSTRUCT,
            sources_queried=[],
        )
        
        start_time = datetime.now(timezone.utc)
        
        # Create tasks for each source
        tasks = []
        sources = []
        
        for source in self.REQUIRED_SOURCES + self.OPTIONAL_SOURCES:
            task = self._query_source(source, atom_input)
            tasks.append(task)
            sources.append(source)
            evidence_package.sources_queried.append(source)
        
        # Execute all queries in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                logger.warning(f"Source {source.value} query failed: {result}")
                evidence_package.sources_without_evidence.append(source)
            elif result is not None:
                evidence_package.add_evidence(result)
            else:
                evidence_package.sources_without_evidence.append(source)
        
        end_time = datetime.now(timezone.utc)
        evidence_package.query_latency_ms = (
            (end_time - start_time).total_seconds() * 1000
        )
        
        return evidence_package
    
    async def _query_source(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query a single intelligence source for evidence.
        
        Routes to the appropriate query method for each of the 10 sources.
        Subclasses can override specific source queries for construct-specific logic.
        """
        user_id = atom_input.user_id
        request_id = atom_input.request_id
        
        # Route to appropriate query method based on source type
        query_methods = {
            IntelligenceSourceType.CLAUDE_REASONING: lambda: self._query_claude_reasoning(user_id, atom_input),
            IntelligenceSourceType.EMPIRICAL_PATTERNS: lambda: self._query_empirical_patterns(user_id),
            IntelligenceSourceType.NONCONSCIOUS_SIGNALS: lambda: self._query_nonconscious_signals(user_id),
            IntelligenceSourceType.GRAPH_EMERGENCE: lambda: self._query_graph_patterns(user_id),
            IntelligenceSourceType.BANDIT_POSTERIORS: lambda: self._query_bandit_posteriors(user_id),
            IntelligenceSourceType.META_LEARNER: lambda: self._query_meta_learner_routing(request_id),
            IntelligenceSourceType.MECHANISM_TRAJECTORIES: lambda: self._query_mechanism_history(user_id),
            IntelligenceSourceType.TEMPORAL_PATTERNS: lambda: self._query_temporal_patterns(user_id),
            IntelligenceSourceType.CROSS_DOMAIN_TRANSFER: lambda: self._query_cross_domain_transfer(user_id),
            IntelligenceSourceType.COHORT_ORGANIZATION: lambda: self._query_cohort_patterns(user_id),
        }
        
        query_method = query_methods.get(source)
        if query_method:
            return await query_method()
        
        # Subclasses implement construct-specific queries
        return await self._query_construct_specific(source, atom_input)
    
    async def _query_mechanism_history(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query mechanism effectiveness history from graph."""
        try:
            # Use the bridge to get mechanism history
            context = await self.bridge.query_executor.get_mechanism_history(user_id)
            
            if context and context.mechanisms:
                # Find best performing mechanisms
                best_mech = max(
                    context.mechanisms.values(),
                    key=lambda m: m.success_rate,
                    default=None,
                )
                
                if best_mech:
                    return IntelligenceEvidence(
                        source_type=IntelligenceSourceType.MECHANISM_TRAJECTORIES,
                        construct=self.TARGET_CONSTRUCT,
                        assessment=best_mech.mechanism_id,
                        assessment_value=best_mech.success_rate,
                        confidence=min(0.9, best_mech.trial_count / 50),
                        confidence_semantics=ConfidenceSemantics.FREQUENTIST,
                        strength=self._trial_count_to_strength(best_mech.trial_count),
                        support_count=best_mech.trial_count,
                        reasoning=f"Best mechanism {best_mech.mechanism_id} has {best_mech.success_rate:.1%} success rate",
                    )
        except Exception as e:
            logger.debug(f"Mechanism history query failed: {e}")
        return None
    
    async def _query_bandit_posteriors(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query bandit posterior distributions."""
        # Subclasses implement based on construct
        return None
    
    async def _query_graph_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query emergent patterns from graph structure."""
        # Subclasses implement based on construct
        return None
    
    async def _query_empirical_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """Query empirically discovered patterns."""
        # Subclasses implement based on construct
        return None
    
    async def _query_claude_reasoning(
        self,
        user_id: str,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query Claude for construct-specific reasoning.
        
        Note: Claude reasoning typically happens in fusion, not as a separate
        evidence source. This is for retrieving cached Claude insights.
        """
        # Claude reasoning is integrated into fusion, not queried separately
        # Subclasses can override if they have cached Claude insights
        return None
    
    async def _query_nonconscious_signals(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query nonconscious behavioral signals for this user.
        
        Returns implicit behavioral signatures that reveal hidden psychological states.
        """
        try:
            # Try to get signals from behavioral analytics
            from adam.behavioral_analytics.engine import get_behavioral_analytics_engine
            
            engine = get_behavioral_analytics_engine()
            if not engine:
                return None
            
            # Get latest psychological state inference
            state = await engine.get_latest_psychological_state(user_id)
            if state:
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=state.primary_state,
                    assessment_value=state.confidence,
                    confidence=state.confidence,
                    confidence_semantics=ConfidenceSemantics.SIGNAL_STRENGTH,
                    strength=EvidenceStrength.MODERATE if state.confidence > 0.5 else EvidenceStrength.WEAK,
                    reasoning=f"Inferred from {state.signal_count} behavioral signals",
                )
        except (ImportError, Exception) as e:
            logger.debug(f"Nonconscious signals query failed: {e}")
        return None
    
    async def _query_meta_learner_routing(
        self,
        request_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query meta-learner routing context for this request.
        
        Returns information about which execution path was selected and why.
        """
        try:
            # Get current routing decision from blackboard
            routing_zone = await self.blackboard.read_zone3(request_id)
            if routing_zone and routing_zone.meta_learner_routing:
                routing = routing_zone.meta_learner_routing
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.META_LEARNER,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=routing.selected_path,
                    assessment_value=routing.confidence,
                    confidence=routing.confidence,
                    confidence_semantics=ConfidenceSemantics.POSTERIOR_DISTRIBUTION,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=f"Meta-learner selected {routing.selected_path} path",
                )
        except Exception as e:
            logger.debug(f"Meta-learner routing query failed: {e}")
        return None
    
    async def _query_temporal_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query temporal patterns for this user.
        
        Returns time-based effectiveness patterns (day of week, time of day, decay).
        """
        try:
            # Query temporal patterns from graph
            context = await self.bridge.query_executor.get_temporal_patterns(user_id)
            if context and context.patterns:
                # Find most relevant pattern for current time
                from datetime import datetime
                current_hour = datetime.now().hour
                
                best_pattern = None
                best_confidence = 0.0
                
                for pattern in context.patterns:
                    if pattern.applicable_hours and current_hour in pattern.applicable_hours:
                        if pattern.confidence > best_confidence:
                            best_pattern = pattern
                            best_confidence = pattern.confidence
                
                if best_pattern:
                    return IntelligenceEvidence(
                        source_type=IntelligenceSourceType.TEMPORAL_PATTERNS,
                        construct=self.TARGET_CONSTRUCT,
                        assessment=best_pattern.pattern_type,
                        assessment_value=best_pattern.effectiveness_multiplier,
                        confidence=best_pattern.confidence,
                        confidence_semantics=ConfidenceSemantics.TEMPORAL_ADJUSTED,
                        strength=self._trial_count_to_strength(best_pattern.observation_count),
                        support_count=best_pattern.observation_count,
                        reasoning=f"Temporal pattern: {best_pattern.description}",
                    )
        except Exception as e:
            logger.debug(f"Temporal patterns query failed: {e}")
        return None
    
    async def _query_cross_domain_transfer(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query cross-domain transfer patterns.
        
        Returns patterns that transfer across product categories/domains.
        """
        try:
            # Query transfer patterns from graph
            context = await self.bridge.query_executor.get_transfer_patterns(user_id)
            if context and context.transfers:
                # Find strongest transfer relevant to this construct
                for transfer in sorted(context.transfers, key=lambda t: t.transfer_lift, reverse=True):
                    if transfer.underlying_construct == self.TARGET_CONSTRUCT:
                        return IntelligenceEvidence(
                            source_type=IntelligenceSourceType.CROSS_DOMAIN_TRANSFER,
                            construct=self.TARGET_CONSTRUCT,
                            assessment=transfer.pattern_description,
                            assessment_value=transfer.transfer_lift,
                            confidence=min(0.9, transfer.validation_count / 10),
                            confidence_semantics=ConfidenceSemantics.EFFECT_SIZE,
                            strength=EvidenceStrength.STRONG if transfer.transfer_lift > 0.2 else EvidenceStrength.MODERATE,
                            reasoning=f"Pattern transfers from {transfer.source_domain} to {transfer.target_domain}",
                        )
        except Exception as e:
            logger.debug(f"Cross-domain transfer query failed: {e}")
        return None
    
    async def _query_cohort_patterns(
        self,
        user_id: str,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query cohort self-organization patterns.
        
        Returns information about emergent user segments this user belongs to.
        """
        try:
            # Query cohort membership from graph
            context = await self.bridge.query_executor.get_user_cohort(user_id)
            if context and context.cohort:
                cohort = context.cohort
                
                # Get mechanism effectiveness for this cohort
                mechanism_pref = None
                if cohort.mechanism_effectiveness:
                    best_mech = max(
                        cohort.mechanism_effectiveness.items(),
                        key=lambda x: x[1],
                        default=None,
                    )
                    if best_mech:
                        mechanism_pref = best_mech[0]
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.COHORT_ORGANIZATION,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=cohort.cohort_name,
                    assessment_value=cohort.cluster_purity,
                    confidence=cohort.cluster_purity,
                    confidence_semantics=ConfidenceSemantics.CLUSTER_PURITY,
                    strength=EvidenceStrength.MODERATE if cohort.cluster_size > 100 else EvidenceStrength.WEAK,
                    support_count=cohort.cluster_size,
                    reasoning=f"User in cohort '{cohort.cohort_name}' (size={cohort.cluster_size}), prefers {mechanism_pref}",
                )
        except Exception as e:
            logger.debug(f"Cohort patterns query failed: {e}")
        return None
    
    @abstractmethod
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources. Must be implemented by subclasses."""
        pass
    
    def _trial_count_to_strength(self, count: int) -> EvidenceStrength:
        """Convert trial count to evidence strength."""
        if count < 5:
            return EvidenceStrength.WEAK
        elif count < 20:
            return EvidenceStrength.MODERATE
        elif count < 50:
            return EvidenceStrength.STRONG
        else:
            return EvidenceStrength.VERY_STRONG
    
    # -------------------------------------------------------------------------
    # CONFLICT DETECTION
    # -------------------------------------------------------------------------
    
    def _detect_conflicts(
        self,
        evidence: MultiSourceEvidence,
    ) -> List[EvidenceConflict]:
        """
        Detect conflicts between intelligence sources.
        """
        conflicts = []
        sources = list(evidence.evidence.keys())
        
        # Compare each pair of sources
        for i, source_a in enumerate(sources):
            for source_b in sources[i+1:]:
                evi_a = evidence.evidence[source_a]
                evi_b = evidence.evidence[source_b]
                
                conflict = self._check_conflict(evi_a, evi_b)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _check_conflict(
        self,
        evi_a: IntelligenceEvidence,
        evi_b: IntelligenceEvidence,
    ) -> Optional[EvidenceConflict]:
        """Check if two evidence items conflict."""
        # Simple conflict detection: different assessments with high confidence
        if evi_a.assessment != evi_b.assessment:
            if evi_a.confidence > 0.6 and evi_b.confidence > 0.6:
                severity = ConflictSeverity.MAJOR
            elif evi_a.confidence > 0.4 and evi_b.confidence > 0.4:
                severity = ConflictSeverity.MODERATE
            else:
                severity = ConflictSeverity.MINOR
            
            return EvidenceConflict(
                source_a=evi_a.source_type,
                source_b=evi_b.source_type,
                construct=self.TARGET_CONSTRUCT,
                assessment_a=evi_a.assessment,
                assessment_b=evi_b.assessment,
                confidence_a=evi_a.confidence,
                confidence_b=evi_b.confidence,
                severity=severity,
            )
        
        return None
    
    # -------------------------------------------------------------------------
    # FUSION
    # -------------------------------------------------------------------------
    
    async def _fuse_without_claude(
        self,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
    ) -> FusionResult:
        """
        Fuse evidence without Claude (fast path).
        
        Uses confidence-weighted voting.
        """
        if not evidence.evidence:
            return FusionResult(
                construct=self.TARGET_CONSTRUCT,
                assessment="unknown",
                confidence=0.3,
            )
        
        # Confidence-weighted voting
        assessment_scores: Dict[str, float] = {}
        for evi in evidence.evidence.values():
            score = assessment_scores.get(evi.assessment, 0.0)
            assessment_scores[evi.assessment] = score + evi.weighted_confidence
        
        best_assessment = max(assessment_scores.keys(), key=lambda a: assessment_scores[a])
        best_score = assessment_scores[best_assessment]
        total_score = sum(assessment_scores.values())
        
        # Calculate fused confidence
        confidence = best_score / total_score if total_score > 0 else 0.5
        
        # Penalize for conflicts
        if conflicts:
            conflict_penalty = 0.1 * len([c for c in conflicts if c.severity == ConflictSeverity.MAJOR])
            confidence = max(0.3, confidence - conflict_penalty)
        
        return FusionResult(
            construct=self.TARGET_CONSTRUCT,
            assessment=best_assessment,
            confidence=confidence,
            sources_used=list(evidence.evidence.keys()),
            conflicts_detected=conflicts,
            conflicts_unresolved=len(conflicts),
            claude_used=False,
        )
    
    async def _fuse_with_claude(
        self,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
        atom_input: AtomInput,
    ) -> FusionResult:
        """
        Fuse evidence using Claude for synthesis.
        
        Claude's role: Integrate conflicting evidence, explain patterns,
        validate against psychological theory.
        """
        try:
            # =================================================================
            # IMPORT CYCLE PREVENTION: Dynamic import of LLMService
            # 
            # LLMService imports CircuitBreaker and FusionResult which may
            # reference atom types. Importing here at runtime (not module load)
            # ensures all dependencies are fully initialized first.
            # See: adam/core/IMPORT_PATTERNS.md
            # =================================================================
            from adam.llm.service import LLMService
            
            # Only use Claude if there are conflicts to resolve
            if not conflicts or len(conflicts) == 0:
                result = await self._fuse_without_claude(evidence, conflicts)
                return result
            
            # Initialize LLM service
            llm_service = LLMService()
            
            try:
                # Convert evidence to format for LLM
                evidence_list = []
                for source_type, evi in evidence.evidence.items():
                    evidence_list.append({
                        "source": source_type.value if hasattr(source_type, 'value') else str(source_type),
                        "assessment": evi.assessment,
                        "confidence": evi.confidence,
                        "reasoning": evi.reasoning,
                        "values": {
                            "assessment_value": evi.assessment_value,
                            "strength": evi.strength.value if hasattr(evi.strength, 'value') else str(evi.strength),
                        },
                    })
                
                # Convert conflicts
                conflict_list = []
                for c in conflicts:
                    conflict_list.append({
                        "source_a": c.source_a.value if hasattr(c.source_a, 'value') else str(c.source_a),
                        "source_b": c.source_b.value if hasattr(c.source_b, 'value') else str(c.source_b),
                        "assessment_a": c.assessment_a,
                        "assessment_b": c.assessment_b,
                        "severity": c.severity.value if hasattr(c.severity, 'value') else str(c.severity),
                    })
                
                # Call LLM for fusion
                llm_result = await llm_service.fuse_for_atom(
                    atom_name=self.ATOM_NAME,
                    evidence=MultiSourceEvidence(
                        construct=self.TARGET_CONSTRUCT,
                        sources_queried=list(evidence.evidence.keys()),
                    ),
                    conflicts=conflicts,
                    user_context={"user_id": atom_input.user_id},
                    raw_evidence=evidence_list,
                    raw_conflicts=conflict_list,
                )
                
                if llm_result:
                    # Extract assessment from LLM response
                    assessment = llm_result.get("assessment", llm_result.get("dominant_focus", "unknown"))
                    confidence = llm_result.get("confidence", llm_result.get("overall_confidence", 0.6))
                    reasoning = llm_result.get("reasoning", "Claude synthesis")
                    
                    return FusionResult(
                        construct=self.TARGET_CONSTRUCT,
                        assessment=assessment,
                        confidence=confidence,
                        sources_used=list(evidence.evidence.keys()),
                        conflicts_detected=conflicts,
                        conflicts_unresolved=0,  # Claude resolved them
                        claude_used=True,
                        claude_synthesis=reasoning,
                    )
                
            finally:
                await llm_service.close()
                
        except ImportError:
            logger.debug("LLM service not available, using fast fusion")
        except Exception as e:
            logger.warning(f"Claude fusion failed, falling back to fast fusion: {e}")
        
        # Fallback to fast fusion
        result = await self._fuse_without_claude(evidence, conflicts)
        result.claude_used = False
        result.claude_synthesis = None
        
        return result
    
    # -------------------------------------------------------------------------
    # OUTPUT BUILDING
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build atom-specific output. Must be implemented by subclasses."""
        pass
    
    def _to_legacy_output(self, output: AtomOutput) -> Any:
        """Convert to legacy AtomOutput format for blackboard."""
        # IMPORT CYCLE PREVENTION: Zone2 models reference AtomType
        # See: adam/core/IMPORT_PATTERNS.md
        from adam.blackboard.models.zone2_reasoning import AtomOutput as LegacyOutput
        return LegacyOutput(
            atom_id=output.atom_id,
            atom_type=output.atom_type,
            primary_result={"assessment": output.primary_assessment},
            confidence=output.overall_confidence,
            recommended_mechanisms=output.recommended_mechanisms,
            mechanism_scores=output.mechanism_weights,
        )
    
    # -------------------------------------------------------------------------
    # LEARNING SIGNALS
    # -------------------------------------------------------------------------
    
    async def _emit_learning_signals(
        self,
        output: AtomOutput,
        evidence: MultiSourceEvidence,
    ) -> None:
        """Emit learning signals for the gradient bridge."""
        # IMPORT CYCLE PREVENTION: Zone5 models reference component types
        # See: adam/core/IMPORT_PATTERNS.md
        from adam.blackboard.models.zone5_learning import (
            ComponentSignal,
            SignalSource,
            SignalPriority,
        )
        
        signal = ComponentSignal(
            source=SignalSource.ATOM,
            source_component_id=self.config.atom_id,
            source_component_type=self.ATOM_NAME,
            target_construct=self.TARGET_CONSTRUCT,
            signal_type="atom_output",
            signal_value=output.overall_confidence,
            user_id=None,  # Set from output if available
            request_id=output.request_id,
            priority=SignalPriority.MEDIUM,
        )
        
        await self.blackboard.write_zone5_signal(
            output.request_id,
            signal,
            role=ComponentRole.ATOM,
        )
    
    # -------------------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------------------
    
    def _record_metrics(self, output: AtomOutput, duration_ms: float) -> None:
        """Record execution metrics."""
        self.metrics.inference_latency.labels(
            component=self.ATOM_NAME,
            operation="execute",
        ).observe(duration_ms / 1000)
    
    # -------------------------------------------------------------------------
    # LEARNING INTERFACE (Partial LearningCapableComponent implementation)
    # -------------------------------------------------------------------------
    
    @property
    def component_name(self) -> str:
        """Component name for learning signal routing."""
        return f"atom_{self.ATOM_NAME}"
    
    @property
    def component_version(self) -> str:
        """Component version."""
        return "1.0"
    
    def _cache_contribution(
        self,
        request_id: str,
        output: AtomOutput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> None:
        """
        Cache this atom's contribution to a decision for credit attribution.
        
        Called automatically during execute() - enables Gradient Bridge to
        properly attribute credit when outcomes arrive.
        """
        contribution = {
            "atom_id": self.config.atom_id,
            "atom_name": self.ATOM_NAME,
            "atom_type": self.ATOM_TYPE.value if hasattr(self.ATOM_TYPE, 'value') else str(self.ATOM_TYPE),
            "target_construct": self.TARGET_CONSTRUCT,
            "primary_assessment": output.primary_assessment,
            "confidence": output.overall_confidence,
            "sources_used": [s.value if hasattr(s, 'value') else str(s) for s in evidence.sources_queried],
            "sources_with_evidence": list(evidence.evidence.keys()),
            "recommended_mechanisms": output.recommended_mechanisms,
            "mechanism_weights": output.mechanism_weights,
            "fusion_method": "claude" if fusion_result.claude_used else "confidence_weighted",
            "reasoning_summary": fusion_result.claude_synthesis or "Confidence-weighted evidence fusion",
        }
        
        # Store in module-level cache
        if request_id not in _contribution_cache:
            _contribution_cache[request_id] = {}
        _contribution_cache[request_id][self.config.atom_id] = contribution
        
        logger.debug(f"Cached contribution for {self.config.atom_id} in request {request_id}")
    
    @classmethod
    def get_contribution(cls, request_id: str, atom_id: str) -> Optional[LearningContribution]:
        """
        Get a cached contribution for credit attribution.
        
        Called by Gradient Bridge during outcome processing.
        """
        if request_id not in _contribution_cache:
            return None
        
        contrib_data = _contribution_cache[request_id].get(atom_id)
        if not contrib_data:
            return None
        
        return LearningContribution(
            component_name=f"atom_{contrib_data['atom_name']}",
            decision_id=request_id,
            contribution_type="psychological_assessment",
            contribution_value=contrib_data["primary_assessment"],
            confidence=contrib_data["confidence"],
            reasoning_summary=contrib_data["reasoning_summary"],
            evidence_sources=contrib_data["sources_used"],
            weight=contrib_data["confidence"],  # Use confidence as weight
        )
    
    @classmethod
    def get_all_contributions(cls, request_id: str) -> List[LearningContribution]:
        """Get all atom contributions for a request."""
        if request_id not in _contribution_cache:
            return []
        
        contributions = []
        for atom_id, contrib_data in _contribution_cache[request_id].items():
            contrib = cls.get_contribution(request_id, atom_id)
            if contrib:
                contributions.append(contrib)
        
        return contributions
    
    @classmethod
    def clear_contribution_cache(cls, request_id: str) -> None:
        """Clear cached contributions for a completed request."""
        if request_id in _contribution_cache:
            del _contribution_cache[request_id]
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """
        Process an outcome and generate learning signals.
        
        Default implementation - subclasses can override for
        construct-specific learning.
        """
        signals = []
        
        # Get our contribution to this decision
        contrib_data = _contribution_cache.get(decision_id, {}).get(self.config.atom_id)
        if not contrib_data:
            return signals
        
        # Determine if our assessment was correct
        # This requires construct-specific logic - subclasses should override
        assessment_validated = context.get("assessment_validated", None)
        
        if assessment_validated is not None:
            signal = LearningSignal(
                signal_type=(
                    LearningSignalType.PREDICTION_VALIDATED 
                    if assessment_validated 
                    else LearningSignalType.PREDICTION_FAILED
                ),
                source_component=self.component_name,
                source_version=self.component_version,
                decision_id=decision_id,
                payload={
                    "atom_id": self.config.atom_id,
                    "construct": self.TARGET_CONSTRUCT,
                    "assessment": contrib_data.get("primary_assessment"),
                    "confidence": contrib_data.get("confidence"),
                    "outcome_value": outcome_value,
                    "validated": assessment_validated,
                },
                confidence=outcome_value if assessment_validated else 1.0 - outcome_value,
            )
            signals.append(signal)
        
        return signals
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get metrics about this atom's learning quality."""
        # Default implementation - returns basic metrics
        return LearningQualityMetrics(
            component_name=self.component_name,
            measurement_period_hours=24,
            signals_emitted=0,  # Would track over time
            signals_consumed=0,
            outcomes_processed=0,
            prediction_accuracy=0.5,  # Would compute from history
            prediction_accuracy_trend="stable",
            attribution_coverage=1.0,  # Atoms always contribute
        )