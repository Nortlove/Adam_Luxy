"""
MAXIMUM IMPACT INTELLIGENCE INTEGRATION SERVICE
=================================================

Central orchestration service that integrates all intelligence modules
and data sources into a unified API for ADAM's cognitive ecosystem.

This service:
1. Loads all processed priors from data pipelines
2. Combines intelligence from all modules
3. Provides unified query interface
4. Feeds the LangGraph prefetch nodes
5. Updates cold-start configurations
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import all intelligence modules
try:
    from .context_intelligence import ContextIntelligenceService, export_context_priors
    from .persuadability_intelligence import (
        PersuadabilityCalculator, 
        export_persuadability_priors,
        PERSUADABILITY_BY_MOTIVATION as PERS_BY_MOT,
    )
    from .temporal_psychology import TemporalPsychologyService, export_temporal_priors
    from .attribution_intelligence import AttributionIntelligenceService, export_attribution_priors
    from .cross_platform_validation import CrossPlatformValidationService, export_cross_platform_priors
    from .granular_type_enrichment import (
        GranularTypeEnrichmentService, 
        export_enrichment_priors,
        PERSUADABILITY_BY_MOTIVATION,
    )
except ImportError:
    # Allow running standalone
    ContextIntelligenceService = None
    PersuadabilityCalculator = None
    TemporalPsychologyService = None
    AttributionIntelligenceService = None
    CrossPlatformValidationService = None
    GranularTypeEnrichmentService = None
    PERSUADABILITY_BY_MOTIVATION = {}
    PERS_BY_MOT = {}


@dataclass
class UnifiedIntelligence:
    """Combined intelligence from all sources for a request."""
    
    # Target identification
    motivation: str
    decision_style: str
    archetype: str
    
    # Persuadability intelligence
    persuadability_score: float
    optimal_treatment_intensity: str
    uplift_potential: float
    
    # Mechanism recommendations
    optimal_mechanisms: List[str]
    mechanism_sequence: List[str]
    mechanism_effectiveness: Dict[str, float]
    
    # Context adjustments
    domain_adjustments: Dict[str, float]
    mindset_modifiers: Dict[str, float]
    
    # Temporal intelligence
    temporal_stability: float
    authenticity_baseline: float
    pattern_evolution: str
    
    # Attribution intelligence
    recommended_touchpoints: int
    first_touch_mechanisms: List[str]
    last_touch_mechanisms: List[str]
    
    # Confidence metrics
    overall_confidence: float
    data_sources_used: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target": {
                "motivation": self.motivation,
                "decision_style": self.decision_style,
                "archetype": self.archetype,
            },
            "persuadability": {
                "score": self.persuadability_score,
                "optimal_intensity": self.optimal_treatment_intensity,
                "uplift_potential": self.uplift_potential,
            },
            "mechanisms": {
                "optimal": self.optimal_mechanisms,
                "sequence": self.mechanism_sequence,
                "effectiveness": self.mechanism_effectiveness,
            },
            "context": {
                "domain_adjustments": self.domain_adjustments,
                "mindset_modifiers": self.mindset_modifiers,
            },
            "temporal": {
                "stability": self.temporal_stability,
                "authenticity_baseline": self.authenticity_baseline,
                "evolution": self.pattern_evolution,
            },
            "attribution": {
                "recommended_touchpoints": self.recommended_touchpoints,
                "first_touch": self.first_touch_mechanisms,
                "last_touch": self.last_touch_mechanisms,
            },
            "meta": {
                "confidence": self.overall_confidence,
                "sources": self.data_sources_used,
            },
        }


class MaximumImpactIntegrationService:
    """
    Central service integrating all intelligence modules for maximum impact.
    """
    
    def __init__(self, priors_dir: Optional[Path] = None):
        """
        Initialize with optional priors directory.
        
        Args:
            priors_dir: Path to processed priors from data pipelines
        """
        self.priors_dir = priors_dir or Path("/Volumes/Sped/new_reviews_and_data/processed_priors")
        
        # Initialize sub-services
        self.context_service = ContextIntelligenceService() if ContextIntelligenceService else None
        self.persuadability_calc = PersuadabilityCalculator() if PersuadabilityCalculator else None
        self.temporal_service = TemporalPsychologyService() if TemporalPsychologyService else None
        self.attribution_service = AttributionIntelligenceService() if AttributionIntelligenceService else None
        self.cross_platform_service = CrossPlatformValidationService() if CrossPlatformValidationService else None
        self.enrichment_service = GranularTypeEnrichmentService(priors_dir) if GranularTypeEnrichmentService else None
        
        # Load processed priors
        self.priors = {}
        self._load_priors()
    
    def _load_priors(self) -> None:
        """Load all processed priors from data pipelines."""
        prior_files = [
            "amazon2015_priors.json",
            "amazon2015_full_priors.json",
            "criteo_priors.json",
            "combined_maximum_impact_priors.json",
        ]
        
        for filename in prior_files:
            filepath = self.priors_dir / filename
            if filepath.exists():
                try:
                    with open(filepath) as f:
                        self.priors[filename.replace("_priors.json", "").replace(".json", "")] = json.load(f)
                except Exception as e:
                    print(f"Warning: Failed to load {filepath}: {e}")
    
    def get_unified_intelligence(
        self,
        motivation: str,
        decision_style: str,
        archetype: str,
        domain: Optional[str] = None,
        category: Optional[str] = None,
    ) -> UnifiedIntelligence:
        """
        Get unified intelligence for targeting.
        
        Args:
            motivation: Customer motivation (15 types)
            decision_style: Decision style (fast/moderate/deliberate)
            archetype: Customer archetype (8 types)
            domain: Optional domain/context (e.g., ecommerce, finance)
            category: Optional product category
        
        Returns:
            UnifiedIntelligence with all combined recommendations
        """
        sources_used = []
        
        # === PERSUADABILITY INTELLIGENCE ===
        # Get from granular type enrichment data first (more complete)
        pers_data = PERSUADABILITY_BY_MOTIVATION.get(motivation, {
            "score": 0.5, "optimal_intensity": "moderate", "uplift": 0.05
        })
        persuadability_score = pers_data.get("score", 0.5)
        optimal_intensity = pers_data.get("optimal_intensity", "moderate")
        uplift_potential = pers_data.get("uplift", 0.05)
        
        # Adjust for decision style
        if decision_style == "fast":
            persuadability_score = min(0.95, persuadability_score + 0.15)
        elif decision_style == "deliberate":
            persuadability_score = max(0.1, persuadability_score - 0.15)
        
        # Use calculator for refined score if available
        if self.persuadability_calc:
            calc_score = self.persuadability_calc.calculate_persuadability(
                motivation=motivation,
                decision_style=decision_style,
                emotional_intensity="moderate",  # Default
                regulatory_focus="promotion",
            )
            # Blend with data-driven score
            persuadability_score = (persuadability_score + calc_score) / 2
            sources_used.append("persuadability")
        
        # === MECHANISM EFFECTIVENESS ===
        mechanism_effectiveness = self._get_mechanism_effectiveness(archetype)
        
        optimal_mechanisms = sorted(
            mechanism_effectiveness.keys(),
            key=lambda k: mechanism_effectiveness[k],
            reverse=True
        )[:3]
        
        # === ATTRIBUTION INTELLIGENCE ===
        touchpoints = 3
        first_touch = ["authority", "social_proof"]
        last_touch = ["reciprocity", "commitment"]
        mechanism_sequence = []
        
        if self.attribution_service:
            try:
                attr_intel = self.attribution_service.get_optimal_sequence(
                    motivation=motivation,
                    decision_style=decision_style,
                    emotional_intensity="moderate",  # Default to moderate
                    persuadability=persuadability_score,
                )
                touchpoints = attr_intel.touchpoints_needed
                mechanism_sequence = attr_intel.sequence
                first_touch = [attr_intel.first_touch_best]
                last_touch = [attr_intel.last_touch_best]
                sources_used.append("attribution")
            except Exception:
                # Fall back to default sequences
                pass
        
        if not mechanism_sequence:
            # Default sequences by decision style
            sequences = {
                "fast": ["scarcity", "social_proof", "liking"],
                "moderate": ["authority", "social_proof", "commitment", "reciprocity"],
                "deliberate": ["authority", "commitment", "social_proof", "reciprocity", "unity"],
            }
            mechanism_sequence = sequences.get(decision_style, sequences["moderate"])
            touchpoints = {"fast": 2, "moderate": 4, "deliberate": 6}.get(decision_style, 4)
        
        # === CONTEXT ADJUSTMENTS ===
        domain_adjustments = {}
        mindset_modifiers = {}
        
        if domain and self.context_service:
            try:
                ctx_intel = self.context_service.get_context_recommendation(domain)
                domain_adjustments = ctx_intel.get("mechanism_adjustments", {})
                mindset_profile = ctx_intel.get("mindset_profile", {})
                mindset_modifiers = {
                    "openness": mindset_profile.get("openness", 0.5),
                    "engagement": mindset_profile.get("engagement", 0.5),
                    "receptivity": mindset_profile.get("receptivity", 0.5),
                }
                sources_used.append("context")
            except Exception:
                pass
        
        # === TEMPORAL INTELLIGENCE ===
        temporal_stability = 0.6
        authenticity_baseline = 0.5
        pattern_evolution = "stable"
        
        if category and self.temporal_service:
            temp_intel = self.temporal_service.get_temporal_baseline(category)
            temporal_stability = temp_intel.temporal_stability
            authenticity_baseline = temp_intel.authenticity_baseline
            pattern_evolution = temp_intel.evolution_trend
            sources_used.append("temporal")
        
        # Load from processed priors if available
        if "amazon2015_full" in self.priors or "amazon2015" in self.priors:
            amazon_priors = self.priors.get("amazon2015_full") or self.priors.get("amazon2015")
            if category and "category_baselines" in amazon_priors:
                cat_baseline = amazon_priors["category_baselines"].get(category)
                if cat_baseline:
                    temporal_stability = 0.7  # Historical data provides stability
                    sources_used.append("amazon2015")
        
        # === CROSS-PLATFORM VALIDATION ===
        overall_confidence = 0.5
        
        if self.cross_platform_service:
            try:
                confidence_boost = self.cross_platform_service.get_confidence_boost(
                    motivation=motivation,
                    decision_style=decision_style,
                )
                overall_confidence = confidence_boost
                sources_used.append("cross_platform")
            except Exception:
                # Base confidence from number of sources
                overall_confidence = min(0.5 + (len(sources_used) * 0.1), 0.9)
        else:
            # Base confidence from number of sources
            overall_confidence = min(0.5 + (len(sources_used) * 0.1), 0.9)
        
        # === ENRICHMENT FROM GRANULAR TYPES ===
        if self.enrichment_service:
            enriched = self.enrichment_service.enrich_type(
                motivation=motivation,
                decision_style=decision_style,
                regulatory_focus="promotion",  # Default
                emotional_intensity="moderate",
                price_sensitivity="moderate",
                archetype=archetype,
            )
            # Override with enriched data
            persuadability_score = enriched.persuadability_score
            temporal_stability = enriched.temporal_stability
            mechanism_effectiveness = enriched.mechanism_effectiveness
            mechanism_sequence = enriched.optimal_mechanism_sequence
            touchpoints = int(enriched.avg_touchpoints_to_convert)
            first_touch = enriched.first_touch_mechanisms
            last_touch = enriched.last_touch_mechanisms
            sources_used.append("enrichment")
        
        return UnifiedIntelligence(
            motivation=motivation,
            decision_style=decision_style,
            archetype=archetype,
            persuadability_score=persuadability_score,
            optimal_treatment_intensity=optimal_intensity,
            uplift_potential=uplift_potential,
            optimal_mechanisms=optimal_mechanisms,
            mechanism_sequence=mechanism_sequence,
            mechanism_effectiveness=mechanism_effectiveness,
            domain_adjustments=domain_adjustments,
            mindset_modifiers=mindset_modifiers,
            temporal_stability=temporal_stability,
            authenticity_baseline=authenticity_baseline,
            pattern_evolution=pattern_evolution,
            recommended_touchpoints=touchpoints,
            first_touch_mechanisms=first_touch,
            last_touch_mechanisms=last_touch,
            overall_confidence=overall_confidence,
            data_sources_used=sources_used,
        )
    
    def _get_mechanism_effectiveness(self, archetype: str) -> Dict[str, float]:
        """Get mechanism effectiveness for archetype."""
        effectiveness_by_archetype = {
            "explorer": {
                "scarcity": 0.85, "social_proof": 0.70, "authority": 0.55,
                "reciprocity": 0.60, "commitment": 0.45, "liking": 0.65, "unity": 0.50
            },
            "achiever": {
                "authority": 0.85, "social_proof": 0.80, "commitment": 0.75,
                "scarcity": 0.65, "reciprocity": 0.50, "liking": 0.55, "unity": 0.60
            },
            "connector": {
                "unity": 0.90, "social_proof": 0.85, "liking": 0.80,
                "reciprocity": 0.70, "commitment": 0.65, "authority": 0.45, "scarcity": 0.40
            },
            "guardian": {
                "authority": 0.90, "commitment": 0.85, "social_proof": 0.75,
                "unity": 0.70, "reciprocity": 0.55, "liking": 0.50, "scarcity": 0.35
            },
            "analyst": {
                "authority": 0.95, "commitment": 0.70, "social_proof": 0.60,
                "reciprocity": 0.45, "scarcity": 0.30, "liking": 0.35, "unity": 0.40
            },
            "creator": {
                "scarcity": 0.80, "authority": 0.65, "social_proof": 0.55,
                "liking": 0.75, "reciprocity": 0.70, "unity": 0.60, "commitment": 0.50
            },
            "nurturer": {
                "reciprocity": 0.90, "liking": 0.85, "unity": 0.80,
                "social_proof": 0.65, "commitment": 0.60, "authority": 0.50, "scarcity": 0.35
            },
            "pragmatist": {
                "authority": 0.70, "social_proof": 0.70, "reciprocity": 0.65,
                "commitment": 0.60, "scarcity": 0.55, "liking": 0.50, "unity": 0.45
            },
        }
        return effectiveness_by_archetype.get(archetype, effectiveness_by_archetype["pragmatist"])
    
    def export_all_priors(self, output_path: Path) -> None:
        """Export all combined priors for cold-start."""
        priors = {
            "version": "2.0",
            "integration_service": "MaximumImpactIntegrationService",
        }
        
        # Collect from all modules
        if ContextIntelligenceService:
            priors["context"] = export_context_priors()
        
        if PersuadabilityCalculator:
            priors["persuadability"] = export_persuadability_priors()
        
        if TemporalPsychologyService:
            priors["temporal"] = export_temporal_priors()
        
        if AttributionIntelligenceService:
            priors["attribution"] = export_attribution_priors()
        
        if CrossPlatformValidationService:
            priors["cross_platform"] = export_cross_platform_priors()
        
        if GranularTypeEnrichmentService:
            priors["enrichment"] = export_enrichment_priors()
        
        # Add loaded priors
        priors["processed_data"] = self.priors
        
        with open(output_path, 'w') as f:
            json.dump(priors, f, indent=2)
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            "priors_loaded": list(self.priors.keys()),
            "services_active": {
                "context": self.context_service is not None,
                "persuadability": self.persuadability_calc is not None,
                "temporal": self.temporal_service is not None,
                "attribution": self.attribution_service is not None,
                "cross_platform": self.cross_platform_service is not None,
                "enrichment": self.enrichment_service is not None,
            },
            "data_sources": {
                name: {
                    "total_reviews": data.get("total_reviews", "N/A"),
                    "categories": data.get("total_categories", "N/A"),
                }
                for name, data in self.priors.items()
                if isinstance(data, dict)
            },
        }


# Convenience function for quick access
def get_intelligence(
    motivation: str,
    decision_style: str,
    archetype: str,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Quick access to unified intelligence.
    
    Example:
        intel = get_intelligence("quality_seeking", "deliberate", "analyst")
        print(intel["mechanisms"]["optimal"])
    """
    service = MaximumImpactIntegrationService()
    unified = service.get_unified_intelligence(
        motivation=motivation,
        decision_style=decision_style,
        archetype=archetype,
        domain=domain,
    )
    return unified.to_dict()
