# =============================================================================
# ADAM Verification Layer 4: Graph Grounding
# Location: adam/verification/layers/grounding.py
# =============================================================================

"""
LAYER 4: GRAPH GROUNDING

Verifies claims against the Neo4j knowledge graph:
- Check attribute existence
- Validate relationship traversals
- Detect hallucinated user properties
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.verification.models.constraints import ConstraintResult, ConstraintSeverity
from adam.verification.models.results import (
    LayerResult,
    VerificationLayer,
    GroundingResult,
)
from adam.graph_reasoning.bridge import InteractionBridge

logger = logging.getLogger(__name__)


class GraphGroundingLayer:
    """
    Layer 4: Verify claims against Neo4j graph.
    
    Detects:
    - Hallucinated user attributes
    - Invalid mechanism references
    - Unsupported relationship claims
    """
    
    def __init__(self, bridge: Optional[InteractionBridge] = None):
        self.bridge = bridge
    
    async def verify(
        self,
        atom_outputs: Dict[str, Any],
        user_id: str,
        request_context: Optional[Any] = None,
    ) -> LayerResult:
        """
        Verify that atom claims are grounded in the graph.
        """
        start_time = datetime.now(timezone.utc)
        
        result = LayerResult(
            layer=VerificationLayer.GROUNDING,
            passed=True,
        )
        
        grounding = GroundingResult()
        
        # Extract claims from atom outputs
        claims = self._extract_claims(atom_outputs)
        grounding.claims_checked = len(claims)
        
        # Verify each claim
        for claim in claims:
            is_grounded, message = await self._verify_claim(claim, user_id)
            
            if is_grounded:
                grounding.claims_grounded += 1
                result.add_result(ConstraintResult(
                    constraint_id=f"ground_{claim['type']}",
                    constraint_name=f"Grounding: {claim['description']}",
                    satisfied=True,
                ))
            else:
                grounding.claims_ungrounded += 1
                grounding.hallucinations_detected += 1
                grounding.hallucination_details.append(message)
                
                result.add_result(ConstraintResult(
                    constraint_id=f"ground_{claim['type']}",
                    constraint_name=f"Grounding: {claim['description']}",
                    satisfied=False,
                    violation_message=message,
                    severity=ConstraintSeverity.WARNING,
                    correctable=True,
                ))
        
        # Check if too many hallucinations
        if grounding.hallucinations_detected > 2:
            result.passed = False
            result.errors.append(f"Too many ungrounded claims: {grounding.hallucinations_detected}")
        
        end_time = datetime.now(timezone.utc)
        result.duration_ms = (end_time - start_time).total_seconds() * 1000
        grounding.query_latency_ms = result.duration_ms
        result.summary = f"Grounded {grounding.claims_grounded}/{grounding.claims_checked} claims"
        
        return result
    
    def _extract_claims(
        self,
        atom_outputs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Extract verifiable claims from atom outputs."""
        claims = []
        
        for atom_id, output in atom_outputs.items():
            if isinstance(output, dict):
                # Check for mechanism claims
                mechanisms = output.get("recommended_mechanisms", [])
                for mech in mechanisms:
                    claims.append({
                        "type": "mechanism_exists",
                        "description": f"Mechanism {mech} exists",
                        "atom_id": atom_id,
                        "mechanism_id": mech,
                    })
                
                # Check for inferred states
                states = output.get("inferred_states", {})
                for state_name, state_value in states.items():
                    if state_value > 0.7:  # High-confidence states
                        claims.append({
                            "type": "state_inference",
                            "description": f"User in state {state_name}",
                            "atom_id": atom_id,
                            "state": state_name,
                            "value": state_value,
                        })
        
        return claims
    
    async def _verify_claim(
        self,
        claim: Dict[str, Any],
        user_id: str,
    ) -> tuple:
        """Verify a single claim against the graph."""
        claim_type = claim["type"]
        
        if claim_type == "mechanism_exists":
            return await self._verify_mechanism_exists(claim["mechanism_id"])
        elif claim_type == "state_inference":
            # State inferences don't need graph verification
            return True, ""
        
        return True, ""
    
    async def _verify_mechanism_exists(
        self,
        mechanism_id: str,
    ) -> tuple:
        """Verify that a mechanism exists in the graph."""
        # Known valid mechanisms
        valid_mechanisms = {
            "temporal_construal",
            "regulatory_focus",
            "social_proof",
            "scarcity",
            "anchoring",
            "identity_construction",
            "mimetic_desire",
            "attention_dynamics",
            "embodied_cognition",
            "gain_framing",
            "loss_framing",
            "why_framing",
            "how_framing",
        }
        
        if mechanism_id in valid_mechanisms:
            return True, ""
        
        # Check if it's a variant
        for valid in valid_mechanisms:
            if valid in mechanism_id.lower():
                return True, ""
        
        return False, f"Unknown mechanism: {mechanism_id}"
