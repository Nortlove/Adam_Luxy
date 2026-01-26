# =============================================================================
# ADAM LLM Service
# Location: adam/llm/service.py
# =============================================================================

"""
LLM SERVICE

Unified service for LLM-powered reasoning.
"""

import logging
from typing import Any, Dict, List, Optional

from adam.llm.client import ClaudeClient, ClaudeConfig
from adam.llm.prompts import PsychologicalPromptBuilder
from adam.llm.fusion import ClaudeFusionEngine
from adam.atoms.models.evidence import MultiSourceEvidence, EvidenceConflict, FusionResult
from adam.performance.circuit_breaker import CircuitBreaker
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class LLMService:
    """
    Unified LLM service for ADAM.
    
    Provides:
    - Evidence fusion via Claude
    - Psychological reasoning
    - Copy enhancement
    - Explanation generation
    """
    
    def __init__(
        self,
        config: Optional[ClaudeConfig] = None,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.config = config or ClaudeConfig()
        self.cache = cache
        
        self.client = ClaudeClient(config=self.config)
        self.circuit_breaker = CircuitBreaker(
            "llm_service",
            failure_threshold=3,
            recovery_timeout=60,
        )
        self.fusion_engine = ClaudeFusionEngine(
            client=self.client,
            circuit_breaker=self.circuit_breaker,
        )
    
    async def close(self) -> None:
        """Close the service."""
        await self.client.close()
    
    # =========================================================================
    # FUSION
    # =========================================================================
    
    async def fuse_evidence(
        self,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
        context: Optional[Dict[str, Any]] = None,
    ) -> FusionResult:
        """Fuse conflicting evidence using Claude."""
        return await self.fusion_engine.fuse_evidence(
            evidence, conflicts, context
        )
    
    async def fuse_for_atom(
        self,
        atom_name: str,
        evidence: MultiSourceEvidence,
        conflicts: List[EvidenceConflict],
        user_context: Optional[Dict[str, Any]] = None,
        raw_evidence: Optional[List[Dict[str, Any]]] = None,
        raw_conflicts: Optional[List[Dict[str, Any]]] = None,
        **context,
    ) -> Dict[str, Any]:
        """Fuse evidence for a specific atom."""
        # Merge all context
        full_context = context.copy()
        if user_context:
            full_context["user_context"] = user_context
        if raw_evidence:
            full_context["raw_evidence"] = raw_evidence
        if raw_conflicts:
            full_context["raw_conflicts"] = raw_conflicts
            
        return await self.fusion_engine.fuse_for_atom(
            atom_name, evidence, conflicts, **full_context
        )
    
    # =========================================================================
    # PSYCHOLOGICAL REASONING
    # =========================================================================
    
    async def assess_regulatory_focus(
        self,
        user_context: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assess regulatory focus using Claude."""
        
        result = PsychologicalPromptBuilder.build_atom_prompt(
            "regulatory_focus",
            user_context=user_context,
            evidence=evidence,
            conflicts=conflicts or [],
        )
        
        if not result:
            return {}
        
        system, prompt, schema = result
        
        return await self.client.complete_structured(
            prompt=prompt,
            output_schema=schema,
            system=system,
        )
    
    async def assess_construal_level(
        self,
        user_context: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assess construal level using Claude."""
        
        result = PsychologicalPromptBuilder.build_atom_prompt(
            "construal_level",
            user_context=user_context,
            evidence=evidence,
            conflicts=conflicts or [],
        )
        
        if not result:
            return {}
        
        system, prompt, schema = result
        
        return await self.client.complete_structured(
            prompt=prompt,
            output_schema=schema,
            system=system,
        )
    
    async def recommend_mechanisms(
        self,
        user_profile: Dict[str, Any],
        current_state: Dict[str, Any],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Recommend cognitive mechanisms using Claude."""
        
        result = PsychologicalPromptBuilder.build_atom_prompt(
            "mechanism_activation",
            user_profile=user_profile,
            current_state=current_state,
            evidence=evidence,
        )
        
        if not result:
            return {}
        
        system, prompt, schema = result
        
        return await self.client.complete_structured(
            prompt=prompt,
            output_schema=schema,
            system=system,
        )
    
    # =========================================================================
    # COPY ENHANCEMENT
    # =========================================================================
    
    async def enhance_copy(
        self,
        base_copy: str,
        user_profile: Dict[str, Any],
        framing: Dict[str, Any],
        brand_voice: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enhance copy based on psychological profile."""
        
        system = """You are an expert copywriter with deep knowledge of consumer psychology.
Your task is to adapt marketing copy to resonate with a specific psychological profile.
Maintain brand voice while personalizing for the target psychology."""
        
        prompt = f"""Enhance the following copy for this user:

Base Copy:
{base_copy}

User Profile:
{user_profile}

Framing Requirements:
{framing}

Brand Voice:
{brand_voice or 'Neutral'}

Please provide:
1. Enhanced headline
2. Enhanced body copy
3. Enhanced CTA
4. Explanation of changes made

Respond in JSON format."""
        
        return await self.client.complete_structured(
            prompt=prompt,
            output_schema={
                "headline": "string",
                "body": "string",
                "cta": "string",
                "changes_explained": "string",
            },
            system=system,
        )
    
    # =========================================================================
    # EXPLANATION GENERATION
    # =========================================================================
    
    async def explain_decision(
        self,
        decision: Dict[str, Any],
        user_profile: Dict[str, Any],
        audience: str = "internal",
    ) -> str:
        """Generate explanation for a decision."""
        
        if audience == "internal":
            system = """You are explaining ADAM's decision-making process to internal stakeholders.
Be technical and detailed about the psychological reasoning."""
        else:
            system = """You are explaining why a recommendation was made to an end user.
Be clear and accessible, avoiding technical jargon."""
        
        prompt = f"""Explain this decision:

Decision:
{decision}

User Profile:
{user_profile}

Provide a clear explanation of why this decision was made and what psychological
factors influenced it."""
        
        response = await self.client.complete(
            prompt=prompt,
            system=system,
            max_tokens=512,
        )
        
        return response.content
    
    # =========================================================================
    # HEALTH
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get LLM service status."""
        return {
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_stats": self.circuit_breaker.get_stats(),
            "client_configured": self.client.api_key is not None,
        }
