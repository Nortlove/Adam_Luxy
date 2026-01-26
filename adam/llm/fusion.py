# =============================================================================
# ADAM Claude Fusion Engine
# Location: adam/llm/fusion.py
# =============================================================================

"""
CLAUDE FUSION ENGINE

Use Claude to fuse conflicting evidence from multiple intelligence sources.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from adam.llm.client import ClaudeClient, ClaudeConfig
from adam.llm.prompts import PsychologicalPromptBuilder
from adam.atoms.models.evidence import (
    MultiSourceEvidence,
    EvidenceConflict,
    FusionResult,
)
from adam.performance.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class ClaudeFusionEngine:
    """
    Engine for fusing evidence using Claude.
    """
    
    def __init__(
        self,
        client: Optional[ClaudeClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.client = client or ClaudeClient()
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            "claude_fusion",
            failure_threshold=3,
            recovery_timeout=60,
        )
    
    async def fuse_evidence(
        self,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
        context: Optional[Dict[str, Any]] = None,
    ) -> FusionResult:
        """
        Fuse evidence using Claude.
        
        Called when algorithmic fusion cannot resolve conflicts.
        """
        
        # Check circuit breaker
        if self.circuit_breaker.is_open:
            logger.warning("Claude fusion circuit is open, using fallback")
            return self._fallback_fusion(evidence, conflicts)
        
        try:
            # Build prompt from evidence dict
            sources = [
                {
                    "name": source_type.value if hasattr(source_type, 'value') else str(source_type),
                    "confidence": ev.confidence,
                    "assessment": ev.assessment,
                    "assessment_value": ev.assessment_value,
                    "strength": ev.strength.value if hasattr(ev.strength, 'value') else str(ev.strength),
                }
                for source_type, ev in evidence.evidence.items()
            ]
            
            conflict_dicts = [
                {
                    "construct": c.construct,
                    "source_a": c.source_a.value if hasattr(c.source_a, 'value') else str(c.source_a),
                    "assessment_a": c.assessment_a,
                    "source_b": c.source_b.value if hasattr(c.source_b, 'value') else str(c.source_b),
                    "assessment_b": c.assessment_b,
                    "severity": c.severity.value if hasattr(c.severity, 'value') else str(c.severity),
                }
                for c in conflicts
            ]
            
            system, prompt, schema = PsychologicalPromptBuilder.build_fusion_prompt(
                sources=sources,
                conflicts=conflict_dicts,
                context=context or {},
            )
            
            # Call Claude
            response = await self.client.complete_structured(
                prompt=prompt,
                output_schema=schema,
                system=system,
            )
            
            # Parse response
            resolved_values = response.get("resolved_values", {})
            overall_confidence = response.get("overall_confidence", 0.5)
            
            # Record success
            await self.circuit_breaker._record_success()
            
            return FusionResult(
                construct=evidence.construct,
                assessment=resolved_values.get("assessment", "unknown"),
                assessment_value=resolved_values.get("assessment_value"),
                confidence=overall_confidence,
                claude_used=True,
                claude_synthesis=resolved_values.get("reasoning", ""),
                sources_used=list(evidence.evidence.keys()),
                conflicts_detected=conflicts,
                conflicts_resolved=len(conflicts),
            )
            
        except Exception as e:
            logger.error(f"Claude fusion failed: {e}")
            await self.circuit_breaker._record_failure()
            return self._fallback_fusion(evidence, conflicts)
    
    async def fuse_for_atom(
        self,
        atom_name: str,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
        **context,
    ) -> Dict[str, Any]:
        """
        Fuse evidence for a specific atom.
        """
        
        # Check circuit breaker
        if self.circuit_breaker.is_open:
            return {}
        
        try:
            # Get atom-specific template
            result = PsychologicalPromptBuilder.build_atom_prompt(
                atom_name,
                evidence=self._format_evidence(evidence),
                conflicts=self._format_conflicts(conflicts),
                **context,
            )
            
            if not result:
                return {}
            
            system, prompt, schema = result
            
            # Call Claude
            response = await self.client.complete_structured(
                prompt=prompt,
                output_schema=schema,
                system=system,
            )
            
            await self.circuit_breaker._record_success()
            return response
            
        except Exception as e:
            logger.error(f"Atom fusion failed for {atom_name}: {e}")
            await self.circuit_breaker._record_failure()
            return {}
    
    def _fallback_fusion(
        self,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
    ) -> FusionResult:
        """
        Fallback fusion when Claude is unavailable.
        
        Uses weighted averaging based on source confidence.
        """
        
        # Collect assessments with weights
        assessment_scores: Dict[str, float] = {}
        for source_type, ev in evidence.evidence.items():
            score = assessment_scores.get(ev.assessment, 0.0)
            assessment_scores[ev.assessment] = score + ev.weighted_confidence
        
        # Find best assessment
        if assessment_scores:
            best_assessment = max(assessment_scores.keys(), key=lambda a: assessment_scores[a])
            best_score = assessment_scores[best_assessment]
            total_score = sum(assessment_scores.values())
            confidence = best_score / total_score if total_score > 0 else 0.5
        else:
            best_assessment = "unknown"
            confidence = 0.3
        
        return FusionResult(
            construct=evidence.construct,
            assessment=best_assessment,
            confidence=confidence,
            claude_used=False,
            sources_used=list(evidence.evidence.keys()),
            conflicts_detected=conflicts,
            conflicts_resolved=len(conflicts),
        )
    
    def _format_evidence(self, evidence: MultiSourceEvidence) -> str:
        """Format evidence for prompt."""
        lines = []
        for source_type, ev in evidence.evidence.items():
            source_name = source_type.value if hasattr(source_type, 'value') else str(source_type)
            lines.append(f"Source: {source_name} (confidence: {ev.confidence})")
            lines.append(f"  Assessment: {ev.assessment}")
            if ev.assessment_value is not None:
                lines.append(f"  Value: {ev.assessment_value}")
            if ev.reasoning:
                lines.append(f"  Reasoning: {ev.reasoning}")
            lines.append("")
        return "\n".join(lines)
    
    def _format_conflicts(self, conflicts: List[EvidenceConflict]) -> str:
        """Format conflicts for prompt."""
        if not conflicts:
            return "No conflicts detected."
        
        lines = []
        for c in conflicts:
            source_a = c.source_a.value if hasattr(c.source_a, 'value') else str(c.source_a)
            source_b = c.source_b.value if hasattr(c.source_b, 'value') else str(c.source_b)
            lines.append(f"- {c.construct}: {source_a}={c.assessment_a} vs {source_b}={c.assessment_b}")
        return "\n".join(lines)
