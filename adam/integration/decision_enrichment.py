# =============================================================================
# ADAM Decision Enrichment Integration
# Location: adam/integration/decision_enrichment.py
# =============================================================================

"""
DECISION ENRICHMENT SERVICE

Integrates previously unwired services into the decision flow:

1. Identity Resolution
   - Resolves identifiers to unified identity
   - Enables cross-device tracking
   - Enriches decisions with identity context

2. Explanation Generation
   - Generates human-readable explanations
   - Multi-audience support (user, advertiser, engineer, regulator)
   - Compliance documentation

3. Competitive Intelligence
   - Detects competitor strategies
   - Recommends counter-mechanisms

ARCHITECTURE:
                    ┌─────────────────────┐
                    │  Decision Request   │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │ Identity        │ │ Competitive │ │ Intelligence    │
    │ Resolution      │ │ Context     │ │ Gathering       │
    └────────┬────────┘ └──────┬──────┘ └────────┬────────┘
             │                 │                  │
             └─────────────────┼──────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Enriched Context   │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Decision Engine    │
                    │  (SynergyOrch)      │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Explanation        │
                    │  Generation         │
                    └─────────────────────┘
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class IdentifierData:
    """Identifier from request."""
    type: str  # email_hash, device_id, ip_hash, etc.
    value: str
    source: str = "direct"  # direct, cookie, header


@dataclass
class EnrichedContext:
    """Context enriched with identity and competitive intelligence."""
    
    # Original request data
    user_id: str
    original_identifiers: List[IdentifierData] = field(default_factory=list)
    
    # Identity resolution
    unified_identity_id: Optional[str] = None
    identity_match_type: str = "new"  # deterministic, probabilistic, new
    identity_confidence: float = 0.0
    household_id: Optional[str] = None
    cross_device_count: int = 1
    
    # Competitive context (if competitor ads provided)
    competitor_mechanisms: Dict[str, float] = field(default_factory=dict)
    underutilized_mechanisms: List[str] = field(default_factory=list)
    recommended_counter_strategy: Optional[str] = None
    
    # Intelligence data
    detected_archetype: Optional[str] = None
    brand_cialdini_scores: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "user_id": self.user_id,
            "unified_identity_id": self.unified_identity_id,
            "identity_match_type": self.identity_match_type,
            "identity_confidence": self.identity_confidence,
            "household_id": self.household_id,
            "cross_device_count": self.cross_device_count,
            "competitor_mechanisms": self.competitor_mechanisms,
            "underutilized_mechanisms": self.underutilized_mechanisms,
            "detected_archetype": self.detected_archetype,
        }


@dataclass
class EnrichedDecision:
    """Decision enriched with explanation."""
    
    # Core decision
    decision_id: str
    selected_ad_id: str
    mechanisms: List[Dict[str, Any]]
    confidence: float
    
    # Enrichment
    context: EnrichedContext
    
    # Explanation (optional, based on request)
    explanation_summary: Optional[str] = None
    explanation_reasoning: Optional[str] = None
    explanation_mechanisms: List[Dict[str, Any]] = field(default_factory=list)
    
    # Compliance
    compliance_documented: bool = False


# =============================================================================
# DECISION ENRICHMENT SERVICE
# =============================================================================

class DecisionEnrichmentService:
    """
    Enriches decisions with identity, competitive intelligence, and explanations.
    
    Usage:
        service = get_decision_enrichment()
        
        # Pre-decision enrichment
        context = await service.enrich_context(
            user_id="user123",
            identifiers=[
                IdentifierData(type="device_id", value="abc123"),
                IdentifierData(type="ip_hash", value="xyz789"),
            ],
            brand_name="Nike",
            competitor_ads=[("Adidas", "Impossible is Nothing...")],
        )
        
        # Post-decision explanation
        enriched = await service.add_explanation(
            decision=decision,
            context=context,
            audience="advertiser",
        )
    """
    
    def __init__(self):
        """Initialize the service."""
        self._identity_resolver = None
        self._explanation_service = None
        self._competitive_service = None
    
    @property
    def identity_resolver(self):
        """Lazy load identity resolver."""
        if self._identity_resolver is None:
            try:
                from adam.identity.service import get_identity_resolver
                self._identity_resolver = get_identity_resolver()
            except ImportError:
                logger.warning("Identity resolver not available")
        return self._identity_resolver
    
    @property
    def explanation_service(self):
        """Lazy load explanation service."""
        if self._explanation_service is None:
            try:
                from adam.explanation.service import ExplanationService
                self._explanation_service = ExplanationService()
            except ImportError:
                logger.warning("Explanation service not available")
        return self._explanation_service
    
    @property
    def competitive_service(self):
        """Lazy load competitive intelligence service."""
        if self._competitive_service is None:
            try:
                from adam.competitive.intelligence import get_competitive_intelligence_service
                self._competitive_service = get_competitive_intelligence_service()
            except ImportError:
                logger.warning("Competitive intelligence service not available")
        return self._competitive_service
    
    # -------------------------------------------------------------------------
    # PRE-DECISION ENRICHMENT
    # -------------------------------------------------------------------------
    
    async def enrich_context(
        self,
        user_id: str,
        identifiers: Optional[List[IdentifierData]] = None,
        brand_name: Optional[str] = None,
        competitor_ads: Optional[List[tuple]] = None,  # [(name, text), ...]
    ) -> EnrichedContext:
        """
        Enrich context before decision making.
        
        Args:
            user_id: User ID from request
            identifiers: Additional identifiers (device, email hash, etc.)
            brand_name: Brand for competitive analysis
            competitor_ads: Competitor ads for counter-strategy
            
        Returns:
            EnrichedContext with identity and competitive intelligence
        """
        context = EnrichedContext(
            user_id=user_id,
            original_identifiers=identifiers or [],
        )
        
        # Step 1: Resolve identity
        if identifiers and self.identity_resolver:
            await self._resolve_identity(context, identifiers)
        
        # Step 2: Competitive intelligence
        if competitor_ads and brand_name and self.competitive_service:
            self._add_competitive_context(context, brand_name, competitor_ads)
        
        return context
    
    async def _resolve_identity(
        self,
        context: EnrichedContext,
        identifiers: List[IdentifierData],
    ) -> None:
        """Resolve identifiers to unified identity."""
        try:
            from adam.identity.models.identifiers import (
                Identifier, IdentifierType, IdentifierSource
            )
            
            # Convert to identity service format
            id_objects = []
            for id_data in identifiers:
                id_type = {
                    "email_hash": IdentifierType.EMAIL_HASH,
                    "device_id": IdentifierType.DEVICE_ID,
                    "ip_hash": IdentifierType.IP_HASH,
                    "phone_hash": IdentifierType.PHONE_HASH,
                    "cookie": IdentifierType.COOKIE,
                }.get(id_data.type)
                
                if id_type:
                    id_objects.append(Identifier(
                        identifier_type=id_type,
                        identifier_value=id_data.value,
                        source=IdentifierSource.FIRST_PARTY,
                    ))
            
            if id_objects:
                result = await self.identity_resolver.resolve(
                    identifiers=id_objects,
                    create_if_new=True,
                )
                
                if result.matched_identity:
                    context.unified_identity_id = result.matched_identity.identity_id
                    context.identity_match_type = result.match_type
                    context.identity_confidence = result.match_score
                    context.household_id = result.matched_identity.household_id
                    context.cross_device_count = result.matched_identity.total_devices
                    
                    logger.debug(
                        f"Resolved identity: {context.unified_identity_id} "
                        f"({context.identity_match_type}, {context.identity_confidence:.1%})"
                    )
                    
        except Exception as e:
            logger.warning(f"Identity resolution failed: {e}")
    
    def _add_competitive_context(
        self,
        context: EnrichedContext,
        brand_name: str,
        competitor_ads: List[tuple],
    ) -> None:
        """Add competitive intelligence to context."""
        try:
            # Analyze competitors
            analyses = [
                self.competitive_service.analyze_competitor_ad(name, text)
                for name, text in competitor_ads
            ]
            
            # Build intelligence
            intel = self.competitive_service.build_competitive_intelligence(
                our_brand=brand_name,
                competitor_analyses=analyses,
            )
            
            context.competitor_mechanisms = intel.market_mechanism_saturation
            context.underutilized_mechanisms = intel.underutilized_mechanisms[:3]
            
            if intel.counter_strategies:
                context.recommended_counter_strategy = intel.counter_strategies[0].strategy_name
                
            logger.debug(
                f"Competitive context: {len(analyses)} competitors, "
                f"underutilized: {context.underutilized_mechanisms}"
            )
            
        except Exception as e:
            logger.warning(f"Competitive analysis failed: {e}")
    
    # -------------------------------------------------------------------------
    # POST-DECISION ENRICHMENT
    # -------------------------------------------------------------------------
    
    async def add_explanation(
        self,
        decision_id: str,
        selected_ad_id: str,
        mechanisms: List[Dict[str, Any]],
        confidence: float,
        context: EnrichedContext,
        audience: str = "advertiser",
        include_explanation: bool = True,
    ) -> EnrichedDecision:
        """
        Add explanation to decision.
        
        Args:
            decision_id: The decision ID
            selected_ad_id: Selected ad
            mechanisms: Mechanisms applied
            confidence: Decision confidence
            context: Enriched context from pre-decision
            audience: Explanation audience (user, advertiser, engineer, regulator)
            include_explanation: Whether to generate explanation
            
        Returns:
            EnrichedDecision with explanation
        """
        enriched = EnrichedDecision(
            decision_id=decision_id,
            selected_ad_id=selected_ad_id,
            mechanisms=mechanisms,
            confidence=confidence,
            context=context,
        )
        
        if include_explanation and self.explanation_service:
            try:
                from adam.explanation.models import ExplanationAudience
                
                audience_map = {
                    "user": ExplanationAudience.USER,
                    "advertiser": ExplanationAudience.ADVERTISER,
                    "engineer": ExplanationAudience.ENGINEER,
                    "regulator": ExplanationAudience.REGULATOR,
                }
                
                explanation = self.explanation_service.explain_decision(
                    decision_id=decision_id,
                    audience=audience_map.get(audience, ExplanationAudience.ADVERTISER),
                    decision_data={
                        "decision_id": decision_id,
                        "mechanisms": [m.get("mechanism_id") or m.get("name") for m in mechanisms],
                        "mechanism_scores": {
                            m.get("mechanism_id") or m.get("name"): m.get("intensity", m.get("score", 0.5))
                            for m in mechanisms
                        },
                        "archetype": context.detected_archetype or "unknown",
                        "framing": "gain",  # Would come from actual decision
                        "confidence": confidence,
                    },
                )
                
                enriched.explanation_summary = explanation.summary
                enriched.explanation_reasoning = explanation.reasoning
                enriched.explanation_mechanisms = [
                    {
                        "mechanism": m.mechanism,
                        "description": m.human_description,
                        "rationale": m.rationale,
                        "score": m.score,
                    }
                    for m in explanation.mechanisms
                ]
                enriched.compliance_documented = True
                
                logger.debug(f"Added {audience} explanation to decision {decision_id}")
                
            except Exception as e:
                logger.warning(f"Explanation generation failed: {e}")
        
        return enriched


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[DecisionEnrichmentService] = None


def get_decision_enrichment() -> DecisionEnrichmentService:
    """Get singleton decision enrichment service."""
    global _service
    if _service is None:
        _service = DecisionEnrichmentService()
    return _service
