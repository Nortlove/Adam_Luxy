# =============================================================================
# ADAM Atom Unit Tests
# Location: tests/unit/test_atoms.py
# =============================================================================

"""
ATOM UNIT TESTS

Tests for individual atoms and the DAG execution.
"""

import pytest
from unittest.mock import AsyncMock, patch

from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    EvidenceConflict,
    EvidenceStrength,
    ConflictSeverity,
)
from adam.atoms.models.atom_io import AtomExecutionStatus
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)


# =============================================================================
# EVIDENCE MODEL TESTS
# =============================================================================

class TestEvidenceModels:
    """Tests for evidence models."""
    
    def test_intelligence_evidence_weighted_confidence(self):
        """Test weighted confidence calculation."""
        evidence = IntelligenceEvidence(
            source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
            construct="regulatory_focus",
            assessment="promotion",
            confidence=0.8,
            strength=EvidenceStrength.STRONG,
            staleness_hours=0,
        )
        
        # Strong, fresh, high confidence should give high weighted confidence
        assert evidence.weighted_confidence > 0.6
    
    def test_intelligence_evidence_stale(self):
        """Test that stale evidence has lower weight."""
        fresh = IntelligenceEvidence(
            source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
            construct="regulatory_focus",
            assessment="promotion",
            confidence=0.8,
            strength=EvidenceStrength.STRONG,
            staleness_hours=0,
        )
        
        stale = IntelligenceEvidence(
            source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
            construct="regulatory_focus",
            assessment="promotion",
            confidence=0.8,
            strength=EvidenceStrength.STRONG,
            staleness_hours=100,  # Stale
        )
        
        assert stale.weighted_confidence < fresh.weighted_confidence
    
    def test_multi_source_evidence_aggregation(self):
        """Test adding and aggregating evidence."""
        mse = MultiSourceEvidence(construct="regulatory_focus")
        
        mse.add_evidence(IntelligenceEvidence(
            source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
            construct="regulatory_focus",
            assessment="promotion",
            confidence=0.7,
        ))
        
        mse.add_evidence(IntelligenceEvidence(
            source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
            construct="regulatory_focus",
            assessment="promotion",
            confidence=0.8,
        ))
        
        assert mse.total_sources == 2
        assert mse.average_confidence == 0.75
        assert mse.max_confidence == 0.8
    
    def test_conflict_detection(self):
        """Test conflict model properties."""
        conflict = EvidenceConflict(
            source_a=IntelligenceSourceType.CLAUDE_REASONING,
            source_b=IntelligenceSourceType.EMPIRICAL_PATTERNS,
            construct="regulatory_focus",
            assessment_a="promotion",
            assessment_b="prevention",
            confidence_a=0.8,
            confidence_b=0.7,
            severity=ConflictSeverity.MAJOR,
        )
        
        assert conflict.is_theory_vs_data  # Claude vs Empirical


# =============================================================================
# REGULATORY FOCUS ATOM TESTS
# =============================================================================

class TestRegulatoryFocusAtom:
    """Tests for RegulatoryFocusAtom."""
    
    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, regulatory_focus_atom, atom_input_factory
    ):
        """Test that atom execution returns valid result."""
        atom_input = atom_input_factory(user_id="test_user_001")
        
        result = await regulatory_focus_atom.execute(atom_input)
        
        assert result.status in [
            AtomExecutionStatus.SUCCESS,
            AtomExecutionStatus.PARTIAL,
        ]
        assert result.duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_skips_claude_when_requested(
        self, regulatory_focus_atom, atom_input_factory
    ):
        """Test that Claude is skipped when skip_claude=True."""
        atom_input = atom_input_factory(skip_claude=True)
        
        result = await regulatory_focus_atom.execute(atom_input)
        
        # Claude should not be used
        assert result.claude_tokens_in == 0
        assert result.claude_tokens_out == 0


# =============================================================================
# CONSTRUAL LEVEL ATOM TESTS
# =============================================================================

class TestConstrualLevelAtom:
    """Tests for ConstrualLevelAtom."""
    
    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, construal_level_atom, atom_input_factory
    ):
        """Test that atom execution returns valid result."""
        atom_input = atom_input_factory(user_id="test_user_002")
        
        result = await construal_level_atom.execute(atom_input)
        
        assert result.status in [
            AtomExecutionStatus.SUCCESS,
            AtomExecutionStatus.PARTIAL,
        ]


# =============================================================================
# ATOM DAG TESTS
# =============================================================================

class TestAtomDAG:
    """Tests for AtomDAG execution."""
    
    @pytest.mark.asyncio
    async def test_dag_executes_all_atoms(
        self, atom_dag, blackboard, request_id, user_id, request_context_factory
    ):
        """Test that DAG executes all registered atoms."""
        # Create blackboard
        await blackboard.create_blackboard(request_id, user_id)
        
        # Use factory to create context with required fields
        context = request_context_factory(request_id=request_id, user_id=user_id)
        
        result = await atom_dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        # Should have executed multiple atoms
        assert len(result.atom_results) > 0
        assert result.total_duration_ms >= 0
    
    @pytest.mark.asyncio
    async def test_dag_handles_failures_gracefully(
        self, atom_dag, blackboard, request_id, user_id, request_context_factory
    ):
        """Test that DAG continues despite individual atom failures."""
        await blackboard.create_blackboard(request_id, user_id)
        
        # Use factory to create context with required fields
        context = request_context_factory(request_id=request_id, user_id=user_id)
        
        # Even with potential failures, DAG should complete
        result = await atom_dag.execute(
            request_id=request_id,
            request_context=context,
        )
        
        # DAG should complete even if some atoms fail
        assert result is not None
