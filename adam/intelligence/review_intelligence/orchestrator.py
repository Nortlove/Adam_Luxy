"""
Review Intelligence Orchestrator
================================

THE COOKIE-LESS TARGETING HUB

This orchestrator:
1. Coordinates all dataset extractors
2. Builds unified intelligence for DSP/SSP/Agency
3. Manages the three machines integration:
   - Neo4j Graph Database
   - LangGraph Orchestration
   - Atom-of-Thought Reasoning
4. Handles cross-dataset intelligence synthesis

The Cookie Crisis Solution:
- No tracking required
- First-party data friendly
- Privacy-preserving inference
- Contextual + psychological targeting
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Type
from dataclasses import dataclass, field
from enum import Enum
import json

from . import (
    DataSource,
    IntelligenceLayer,
    PsychologicalSignal,
    AudienceSegment,
    ContextualSignal,
)
from .base_extractor import (
    BaseReviewExtractor,
    ExtractionResult,
    AggregatedIntelligence,
    PsychologicalConstruct,
    Archetype,
    PersuasionMechanism,
)
from .extractors import EXTRACTORS

logger = logging.getLogger(__name__)


# =============================================================================
# UNIFIED INTELLIGENCE OUTPUT
# =============================================================================

@dataclass
class UnifiedIntelligence:
    """
    Unified intelligence output combining all data sources.
    
    This is what ADAM produces for the ecosystem:
    - DSPs use this for targeting and creative optimization
    - SSPs use this for inventory valuation
    - Agencies use this for strategy and planning
    """
    
    # Scope
    scope_type: str  # "category", "location", "segment", "brand"
    scope_value: str
    
    # Cross-source synthesis
    psychological_profile: Dict[str, float]  # construct -> score
    archetype_profile: Dict[str, float]  # archetype -> probability
    mechanism_effectiveness: Dict[str, float]  # mechanism -> effectiveness
    
    # Persuasive intelligence
    top_templates: List[Dict[str, Any]]
    avoid_patterns: List[Dict[str, Any]]
    
    # Targeting signals
    contextual_signals: List[ContextualSignal]
    audience_segments: List[AudienceSegment]
    
    # Source attribution
    sources_used: List[DataSource]
    confidence_by_source: Dict[DataSource, float]
    total_sample_size: int
    
    # Ecosystem outputs
    dsp_output: Optional[Dict[str, Any]] = None
    ssp_output: Optional[Dict[str, Any]] = None
    agency_output: Optional[Dict[str, Any]] = None
    
    # Machine integration
    graph_updates: Optional[Dict[str, Any]] = None
    langgraph_priors: Optional[Dict[str, Any]] = None
    atom_injections: Optional[Dict[str, Any]] = None


@dataclass
class EcosystemDeliverable:
    """
    The final deliverable for ecosystem partners.
    
    This is what we actually send to:
    - StackAdapt (DSP)
    - iHeart (SSP)
    - WPP (Agency)
    """
    
    # Identity
    deliverable_id: str
    deliverable_type: str  # "segment", "context", "creative_brief"
    
    # Target partner
    target_layer: IntelligenceLayer
    
    # Content
    payload: Dict[str, Any]
    
    # Metadata
    sources: List[DataSource]
    confidence: float
    sample_size: int
    created_at: str
    
    # Integration
    api_format: str  # "stackadapt_v2", "iheart_v1", "wpp_custom"


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class ReviewIntelligenceOrchestrator:
    """
    The central orchestrator for all review intelligence.
    
    This class:
    1. Manages all dataset extractors
    2. Synthesizes cross-dataset intelligence
    3. Produces ecosystem deliverables
    4. Integrates with ADAM's three machines
    """
    
    def __init__(
        self,
        data_root: Path,
        extractors_to_use: Optional[List[DataSource]] = None,
    ):
        self.data_root = data_root
        
        # Initialize extractors
        self.extractors: Dict[DataSource, BaseReviewExtractor] = {}
        self._initialize_extractors(extractors_to_use)
        
        # Intelligence cache
        self._intelligence_cache: Dict[str, UnifiedIntelligence] = {}
        
        # Cross-source mappings
        self._category_mappings: Dict[str, Set[str]] = {}  # our_category -> source categories
        self._location_mappings: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_extractors(
        self,
        extractors_to_use: Optional[List[DataSource]] = None,
    ):
        """Initialize all requested extractors."""
        
        # Data source paths
        source_paths = {
            DataSource.AMAZON: self.data_root / "Amazon",
            DataSource.GOOGLE_LOCAL: self.data_root / "Google",
            DataSource.YELP: self.data_root / "yelp_reviews",
            DataSource.TWITTER_MENTAL_HEALTH: self.data_root / "Twitter",
            DataSource.STEAM_GAMING: self.data_root / "Gaming" / "Steam Gamers Reviews",
            DataSource.SEPHORA_BEAUTY: self.data_root / "sephora_reviews",
            DataSource.MOVIELENS_GENOME: self.data_root / "Movies & Shows" / "Movie - Lens - 25M - 1995 to 2020",
            DataSource.PODCAST: self.data_root / "Music & Podcasts" / "Podcast",
            DataSource.AIRLINE: self.data_root / "airline_reviews",
            DataSource.AUTOMOTIVE: self.data_root / "Auto" / "Edmonds by Car Company - by Make & Model",
        }
        
        sources_to_init = extractors_to_use or list(DataSource)
        
        for source in sources_to_init:
            if source in EXTRACTORS and source in source_paths:
                path = source_paths[source]
                if path.exists():
                    try:
                        self.extractors[source] = EXTRACTORS[source](data_path=path)
                        logger.info(f"Initialized extractor for {source.value}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize {source.value}: {e}")
    
    # =========================================================================
    # INTELLIGENCE BUILDING
    # =========================================================================
    
    def build_unified_intelligence(
        self,
        scope_type: str,
        scope_value: str,
        sources: Optional[List[DataSource]] = None,
    ) -> UnifiedIntelligence:
        """
        Build unified intelligence combining all available sources.
        
        This is the main method that synthesizes intelligence across datasets.
        """
        sources = sources or list(self.extractors.keys())
        
        # Collect intelligence from each source
        source_results: Dict[DataSource, AggregatedIntelligence] = {}
        
        for source in sources:
            if source not in self.extractors:
                continue
            
            extractor = self.extractors[source]
            
            # Extract and aggregate
            results = []
            for review in extractor.iter_reviews():
                result = extractor.extract_psychological_signals(review)
                if result.confidence > 0.3:  # Quality threshold
                    results.append(result)
                
                # Batch processing
                if len(results) >= extractor.batch_size:
                    break
            
            if results:
                agg = extractor.aggregate_intelligence(results, scope_type, scope_value)
                source_results[source] = agg
        
        # Synthesize across sources
        unified = self._synthesize_intelligence(
            source_results, scope_type, scope_value
        )
        
        # Generate ecosystem outputs
        unified.dsp_output = self._generate_dsp_output(unified, source_results)
        unified.ssp_output = self._generate_ssp_output(unified, source_results)
        unified.agency_output = self._generate_agency_output(unified, source_results)
        
        # Generate machine integrations
        unified.graph_updates = self._generate_graph_updates(unified)
        unified.langgraph_priors = self._generate_langgraph_priors(unified)
        unified.atom_injections = self._generate_atom_injections(unified)
        
        # Cache
        cache_key = f"{scope_type}:{scope_value}"
        self._intelligence_cache[cache_key] = unified
        
        return unified
    
    def _synthesize_intelligence(
        self,
        source_results: Dict[DataSource, AggregatedIntelligence],
        scope_type: str,
        scope_value: str,
    ) -> UnifiedIntelligence:
        """Synthesize intelligence across sources."""
        
        # Weighted combination based on sample size and source relevance
        total_samples = sum(r.sample_size for r in source_results.values())
        
        # Aggregate psychological profile
        psychological_profile = self._aggregate_constructs(source_results)
        
        # Aggregate archetypes
        archetype_profile = self._aggregate_archetypes(source_results)
        
        # Aggregate mechanisms
        mechanism_effectiveness = self._aggregate_mechanisms(source_results)
        
        # Collect top templates
        all_templates = []
        for result in source_results.values():
            all_templates.extend(result.top_templates)
        all_templates.sort(key=lambda x: x.get('helpful_score', 0), reverse=True)
        
        # Calculate confidence by source
        confidence_by_source = {
            source: min(1.0, result.sample_size / 1000)
            for source, result in source_results.items()
        }
        
        return UnifiedIntelligence(
            scope_type=scope_type,
            scope_value=scope_value,
            psychological_profile=psychological_profile,
            archetype_profile=archetype_profile,
            mechanism_effectiveness=mechanism_effectiveness,
            top_templates=all_templates[:100],
            avoid_patterns=[],  # Would be populated from negative patterns
            contextual_signals=[],  # Populated in specific methods
            audience_segments=[],  # Populated in specific methods
            sources_used=list(source_results.keys()),
            confidence_by_source=confidence_by_source,
            total_sample_size=total_samples,
        )
    
    def _aggregate_constructs(
        self,
        source_results: Dict[DataSource, AggregatedIntelligence],
    ) -> Dict[str, float]:
        """Aggregate psychological constructs across sources."""
        from collections import defaultdict
        
        construct_sums = defaultdict(float)
        construct_weights = defaultdict(float)
        
        for source, result in source_results.items():
            weight = min(1.0, result.sample_size / 1000)  # Sample size weight
            
            for construct, dist in result.construct_distributions.items():
                key = construct.value if hasattr(construct, 'value') else str(construct)
                if 'mean' in dist:
                    construct_sums[key] += dist['mean'] * weight
                    construct_weights[key] += weight
        
        return {
            k: construct_sums[k] / construct_weights[k]
            for k in construct_sums
            if construct_weights[k] > 0
        }
    
    def _aggregate_archetypes(
        self,
        source_results: Dict[DataSource, AggregatedIntelligence],
    ) -> Dict[str, float]:
        """Aggregate archetypes across sources."""
        from collections import defaultdict
        
        archetype_sums = defaultdict(float)
        total_weight = 0
        
        for source, result in source_results.items():
            weight = min(1.0, result.sample_size / 1000)
            total_weight += weight
            
            for archetype, prob in result.archetype_prevalence.items():
                key = archetype.value if hasattr(archetype, 'value') else str(archetype)
                archetype_sums[key] += prob * weight
        
        if total_weight == 0:
            return {}
        
        return {k: v / total_weight for k, v in archetype_sums.items()}
    
    def _aggregate_mechanisms(
        self,
        source_results: Dict[DataSource, AggregatedIntelligence],
    ) -> Dict[str, float]:
        """Aggregate mechanism effectiveness across sources."""
        from collections import defaultdict
        
        mech_sums = defaultdict(float)
        mech_weights = defaultdict(float)
        
        for source, result in source_results.items():
            weight = min(1.0, result.sample_size / 1000)
            
            for mechanism, effectiveness in result.mechanism_effectiveness.items():
                key = mechanism.value if hasattr(mechanism, 'value') else str(mechanism)
                mech_sums[key] += effectiveness * weight
                mech_weights[key] += weight
        
        return {
            k: mech_sums[k] / mech_weights[k]
            for k in mech_sums
            if mech_weights[k] > 0
        }
    
    # =========================================================================
    # ECOSYSTEM OUTPUTS
    # =========================================================================
    
    def _generate_dsp_output(
        self,
        unified: UnifiedIntelligence,
        source_results: Dict[DataSource, AggregatedIntelligence],
    ) -> Dict[str, Any]:
        """
        Generate DSP-ready output (StackAdapt, The Trade Desk).
        
        DSPs need:
        - Audience segments for targeting
        - Contextual signals for cookie-less
        - Creative optimization recommendations
        """
        return {
            "version": "adam_dsp_v1",
            "scope": {
                "type": unified.scope_type,
                "value": unified.scope_value,
            },
            
            # TARGETING SEGMENTS
            "segments": {
                # Psychological segments
                "psychological_segments": self._build_psychological_segments(unified),
                
                # Archetype segments
                "archetype_segments": self._build_archetype_segments(unified),
                
                # Contextual segments (cookie-less)
                "contextual_segments": self._build_contextual_segments(unified),
            },
            
            # CREATIVE OPTIMIZATION
            "creative_optimization": {
                "recommended_mechanisms": self._get_top_mechanisms(
                    unified.mechanism_effectiveness, 5
                ),
                "avoid_mechanisms": self._get_bottom_mechanisms(
                    unified.mechanism_effectiveness, 2
                ),
                "top_templates": unified.top_templates[:20],
                "tone_guidance": self._recommend_tone(unified.archetype_profile),
            },
            
            # BIDDING SIGNALS
            "bidding_signals": {
                "audience_value_score": self._calculate_audience_value(unified),
                "conversion_propensity": self._estimate_conversion_propensity(unified),
                "recommended_bid_adjustment": self._recommend_bid_adjustment(unified),
            },
            
            # METADATA
            "confidence": min(unified.confidence_by_source.values()) if unified.confidence_by_source else 0,
            "sample_size": unified.total_sample_size,
            "sources": [s.value for s in unified.sources_used],
        }
    
    def _generate_ssp_output(
        self,
        unified: UnifiedIntelligence,
        source_results: Dict[DataSource, AggregatedIntelligence],
    ) -> Dict[str, Any]:
        """
        Generate SSP-ready output (iHeart).
        
        SSPs need:
        - Inventory value signals
        - Audience composition data
        - Yield optimization recommendations
        """
        return {
            "version": "adam_ssp_v1",
            "scope": {
                "type": unified.scope_type,
                "value": unified.scope_value,
            },
            
            # INVENTORY VALUE
            "inventory_value": {
                "psychological_richness": self._calculate_psychological_richness(unified),
                "archetype_diversity": self._calculate_archetype_diversity(unified),
                "premium_segment_presence": self._identify_premium_segments(unified),
            },
            
            # AUDIENCE COMPOSITION
            "audience_composition": {
                "psychological_profile": unified.psychological_profile,
                "archetype_distribution": unified.archetype_profile,
                "mechanism_receptivity": unified.mechanism_effectiveness,
            },
            
            # YIELD OPTIMIZATION
            "yield_optimization": {
                "recommended_floor_multiplier": self._calculate_floor_multiplier(unified),
                "optimal_advertiser_categories": self._recommend_advertiser_categories(unified),
                "premium_deal_opportunities": self._identify_premium_deals(unified),
            },
            
            # CONTENT MATCHING (for iHeart)
            "content_matching": {
                "recommended_formats": self._recommend_audio_formats(unified),
                "show_affinity": self._calculate_show_affinity(unified),
                "podcast_alignment": self._calculate_podcast_alignment(unified),
            },
            
            "confidence": min(unified.confidence_by_source.values()) if unified.confidence_by_source else 0,
            "sample_size": unified.total_sample_size,
        }
    
    def _generate_agency_output(
        self,
        unified: UnifiedIntelligence,
        source_results: Dict[DataSource, AggregatedIntelligence],
    ) -> Dict[str, Any]:
        """
        Generate Agency-ready output (WPP).
        
        Agencies need:
        - Strategic insights
        - Creative briefs
        - Cross-platform recommendations
        """
        return {
            "version": "adam_agency_v1",
            "scope": {
                "type": unified.scope_type,
                "value": unified.scope_value,
            },
            
            # STRATEGIC INSIGHTS
            "strategic_insights": {
                "market_psychology": {
                    "dominant_archetypes": self._get_dominant_archetypes(
                        unified.archetype_profile, 3
                    ),
                    "key_psychological_traits": self._get_key_traits(unified),
                    "behavioral_patterns": self._extract_behavioral_patterns(unified),
                },
                "competitive_landscape": {
                    "mechanism_gaps": self._identify_mechanism_gaps(unified),
                    "differentiation_opportunities": self._identify_opportunities(unified),
                },
            },
            
            # CREATIVE BRIEF
            "creative_brief": {
                "recommended_tone": self._recommend_tone(unified.archetype_profile),
                "key_messages": self._generate_key_messages(unified),
                "visual_direction": self._recommend_visual_direction(unified),
                "persuasive_templates": unified.top_templates[:10],
                "avoid": {
                    "mechanisms": self._get_bottom_mechanisms(
                        unified.mechanism_effectiveness, 3
                    ),
                    "topics": [],  # From safeguards
                },
            },
            
            # CROSS-PLATFORM STRATEGY
            "cross_platform": {
                "audio": {
                    "recommended_formats": ["podcast_host_read", "radio_spot"],
                    "tone_guidance": self._get_audio_tone(unified),
                    "iheart_alignment": self._get_iheart_recommendations(unified),
                },
                "digital": {
                    "recommended_formats": self._get_digital_formats(unified),
                    "retargeting_strategy": self._get_retargeting_strategy(unified),
                },
                "social": {
                    "platform_priorities": self._get_social_priorities(unified),
                    "content_approach": self._get_social_approach(unified),
                },
            },
            
            # MEASUREMENT FRAMEWORK
            "measurement": {
                "kpis": self._recommend_kpis(unified),
                "attribution_approach": "multi_touch_psychological",
                "success_indicators": self._define_success_indicators(unified),
            },
            
            "confidence": min(unified.confidence_by_source.values()) if unified.confidence_by_source else 0,
            "sample_size": unified.total_sample_size,
        }
    
    # =========================================================================
    # THREE MACHINES INTEGRATION
    # =========================================================================
    
    def _generate_graph_updates(
        self,
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Generate updates for Neo4j graph database.
        
        The graph stores:
        - Effectiveness relationships
        - Pattern nodes
        - User/segment profiles
        """
        return {
            "nodes_to_create": [
                {
                    "label": "PsychologicalSegment",
                    "properties": {
                        "scope_type": unified.scope_type,
                        "scope_value": unified.scope_value,
                        "profile": unified.psychological_profile,
                    }
                },
            ],
            "relationships_to_create": [
                {
                    "from": f"Segment:{unified.scope_value}",
                    "to": f"Archetype:{arch}",
                    "type": "HAS_ARCHETYPE",
                    "properties": {"strength": score},
                }
                for arch, score in unified.archetype_profile.items()
            ],
            "effectiveness_updates": [
                {
                    "scope": unified.scope_value,
                    "mechanism": mech,
                    "effectiveness": score,
                    "sample_size": unified.total_sample_size,
                }
                for mech, score in unified.mechanism_effectiveness.items()
            ],
        }
    
    def _generate_langgraph_priors(
        self,
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Generate priors for LangGraph orchestration.
        
        LangGraph uses these to:
        - Pre-fetch relevant intelligence
        - Inject context into atom execution
        - Coordinate cross-system optimization
        """
        return {
            "prior_key": f"{unified.scope_type}:{unified.scope_value}",
            "psychological_priors": unified.psychological_profile,
            "archetype_priors": unified.archetype_profile,
            "mechanism_priors": unified.mechanism_effectiveness,
            "template_priors": [t['text'] for t in unified.top_templates[:10]],
            "context_injection": {
                "sources": [s.value for s in unified.sources_used],
                "confidence": min(unified.confidence_by_source.values()) if unified.confidence_by_source else 0,
            },
        }
    
    def _generate_atom_injections(
        self,
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Generate injections for Atom-of-Thought execution.
        
        Each atom gets relevant intelligence:
        - UserStateAtom: Psychological profile
        - ReviewIntelligenceAtom: Templates and patterns
        - BrandPersonalityAtom: Archetype alignment
        - MechanismActivationAtom: Effectiveness data
        """
        return {
            "UserStateAtom": {
                "psychological_baseline": unified.psychological_profile,
                "archetype_affinities": unified.archetype_profile,
            },
            "ReviewIntelligenceAtom": {
                "persuasive_templates": unified.top_templates[:20],
                "mechanism_effectiveness": unified.mechanism_effectiveness,
            },
            "BrandPersonalityAtom": {
                "audience_archetypes": unified.archetype_profile,
                "alignment_guidance": self._get_brand_alignment_guidance(unified),
            },
            "MechanismActivationAtom": {
                "mechanism_effectiveness": unified.mechanism_effectiveness,
                "context_modifiers": self._get_context_modifiers(unified),
            },
            "ChannelSelectionAtom": {
                "format_affinities": self._get_format_affinities(unified),
                "timing_recommendations": self._get_timing_recommendations(unified),
            },
        }
    
    # =========================================================================
    # ECOSYSTEM DELIVERABLE GENERATION
    # =========================================================================
    
    def generate_deliverable(
        self,
        unified: UnifiedIntelligence,
        target_layer: IntelligenceLayer,
        deliverable_type: str,
    ) -> EcosystemDeliverable:
        """Generate a specific ecosystem deliverable."""
        from datetime import datetime
        import uuid
        
        # Get appropriate output
        if target_layer == IntelligenceLayer.DSP:
            payload = unified.dsp_output
            api_format = "stackadapt_v2"
        elif target_layer == IntelligenceLayer.SSP:
            payload = unified.ssp_output
            api_format = "iheart_v1"
        elif target_layer == IntelligenceLayer.AGENCY:
            payload = unified.agency_output
            api_format = "wpp_custom"
        else:
            payload = {
                "dsp": unified.dsp_output,
                "ssp": unified.ssp_output,
                "agency": unified.agency_output,
            }
            api_format = "adam_unified_v1"
        
        return EcosystemDeliverable(
            deliverable_id=str(uuid.uuid4()),
            deliverable_type=deliverable_type,
            target_layer=target_layer,
            payload=payload,
            sources=unified.sources_used,
            confidence=min(unified.confidence_by_source.values()) if unified.confidence_by_source else 0,
            sample_size=unified.total_sample_size,
            created_at=datetime.utcnow().isoformat(),
            api_format=api_format,
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _build_psychological_segments(
        self,
        unified: UnifiedIntelligence,
    ) -> List[Dict[str, Any]]:
        """Build targetable psychological segments."""
        segments = []
        
        for construct, score in unified.psychological_profile.items():
            if score > 0.6:  # High affinity
                segments.append({
                    "segment_id": f"psych_{construct}_high",
                    "segment_name": f"High {construct.replace('_', ' ').title()}",
                    "targeting_key": construct,
                    "threshold": "high",
                    "score": score,
                })
        
        return segments
    
    def _build_archetype_segments(
        self,
        unified: UnifiedIntelligence,
    ) -> List[Dict[str, Any]]:
        """Build targetable archetype segments."""
        segments = []
        
        for archetype, prob in unified.archetype_profile.items():
            if prob > 0.1:  # Meaningful presence
                segments.append({
                    "segment_id": f"arch_{archetype}",
                    "segment_name": f"{archetype.title()} Archetype",
                    "archetype": archetype,
                    "probability": prob,
                    "recommended_mechanisms": self._get_mechanisms_for_archetype(archetype),
                })
        
        return segments
    
    def _build_contextual_segments(
        self,
        unified: UnifiedIntelligence,
    ) -> List[Dict[str, Any]]:
        """Build contextual targeting segments (cookie-less)."""
        return [
            {
                "segment_id": f"ctx_{unified.scope_type}_{unified.scope_value}",
                "context_type": unified.scope_type,
                "context_value": unified.scope_value,
                "psychological_profile": unified.psychological_profile,
                "mechanism_effectiveness": unified.mechanism_effectiveness,
            }
        ]
    
    def _get_mechanisms_for_archetype(self, archetype: str) -> List[str]:
        """Get recommended mechanisms for an archetype."""
        archetype_mechanisms = {
            "ruler": ["authority", "exclusivity", "aspiration"],
            "hero": ["aspiration", "commitment_consistency", "social_proof"],
            "sage": ["authority", "logical_appeal", "trust"],
            "explorer": ["curiosity", "storytelling", "authenticity"],
            "outlaw": ["exclusivity", "scarcity", "fear_appeal"],
            "magician": ["storytelling", "aspiration", "curiosity"],
            "everyman": ["social_proof", "liking", "unity"],
            "lover": ["emotional_appeal", "liking", "aspiration"],
            "jester": ["humor", "liking", "social_proof"],
            "caregiver": ["trust", "reciprocity", "unity"],
            "creator": ["authenticity", "storytelling", "aspiration"],
            "innocent": ["trust", "unity", "emotional_appeal"],
        }
        return archetype_mechanisms.get(archetype.lower(), ["social_proof", "trust"])
    
    def _get_top_mechanisms(
        self,
        mechanisms: Dict[str, float],
        n: int,
    ) -> List[str]:
        """Get top n mechanisms."""
        sorted_mechs = sorted(mechanisms.items(), key=lambda x: x[1], reverse=True)
        return [m for m, _ in sorted_mechs[:n]]
    
    def _get_bottom_mechanisms(
        self,
        mechanisms: Dict[str, float],
        n: int,
    ) -> List[str]:
        """Get bottom n mechanisms (to avoid)."""
        sorted_mechs = sorted(mechanisms.items(), key=lambda x: x[1])
        return [m for m, _ in sorted_mechs[:n]]
    
    def _get_dominant_archetypes(
        self,
        archetypes: Dict[str, float],
        n: int,
    ) -> List[Dict[str, float]]:
        """Get dominant archetypes."""
        sorted_archs = sorted(archetypes.items(), key=lambda x: x[1], reverse=True)
        return [{"archetype": a, "strength": s} for a, s in sorted_archs[:n]]
    
    def _recommend_tone(self, archetypes: Dict[str, float]) -> str:
        """Recommend creative tone."""
        if not archetypes:
            return "friendly_professional"
        
        dominant = max(archetypes, key=archetypes.get)
        
        tone_map = {
            "ruler": "prestigious_authoritative",
            "hero": "empowering_confident",
            "sage": "informative_wise",
            "explorer": "adventurous_inspiring",
            "outlaw": "bold_provocative",
            "magician": "visionary_transformative",
            "everyman": "relatable_down_to_earth",
            "lover": "sensual_intimate",
            "jester": "playful_humorous",
            "caregiver": "nurturing_supportive",
            "creator": "innovative_expressive",
            "innocent": "warm_optimistic",
        }
        
        return tone_map.get(dominant.lower(), "friendly_professional")
    
    def _calculate_audience_value(self, unified: UnifiedIntelligence) -> float:
        """Calculate overall audience value score."""
        # Premium archetypes contribute to value
        premium_archetypes = {"ruler", "hero", "sage", "creator"}
        premium_score = sum(
            score for arch, score in unified.archetype_profile.items()
            if arch.lower() in premium_archetypes
        )
        
        return min(1.0, 0.5 + premium_score)
    
    def _estimate_conversion_propensity(self, unified: UnifiedIntelligence) -> float:
        """Estimate conversion propensity."""
        # Base on mechanism effectiveness for conversion-related mechanisms
        conversion_mechanisms = ["commitment_consistency", "reciprocity", "scarcity"]
        
        scores = [
            unified.mechanism_effectiveness.get(m, 0.5)
            for m in conversion_mechanisms
        ]
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _recommend_bid_adjustment(self, unified: UnifiedIntelligence) -> float:
        """Recommend bid adjustment multiplier."""
        value = self._calculate_audience_value(unified)
        
        if value > 0.8:
            return 1.5  # 50% increase
        elif value > 0.6:
            return 1.2  # 20% increase
        elif value < 0.4:
            return 0.8  # 20% decrease
        else:
            return 1.0  # No adjustment
    
    def _calculate_psychological_richness(self, unified: UnifiedIntelligence) -> float:
        """Calculate psychological richness score."""
        # More constructs with meaningful scores = richer
        meaningful_constructs = sum(
            1 for score in unified.psychological_profile.values()
            if score > 0.3
        )
        return min(1.0, meaningful_constructs / 10)
    
    def _calculate_archetype_diversity(self, unified: UnifiedIntelligence) -> float:
        """Calculate archetype diversity."""
        # Entropy-like measure
        import math
        
        probs = [p for p in unified.archetype_profile.values() if p > 0]
        if not probs:
            return 0
        
        entropy = -sum(p * math.log(p) for p in probs if p > 0)
        max_entropy = math.log(len(probs)) if probs else 1
        
        return entropy / max_entropy if max_entropy > 0 else 0
    
    def _identify_premium_segments(self, unified: UnifiedIntelligence) -> List[str]:
        """Identify premium segments present."""
        premium = []
        
        for arch, score in unified.archetype_profile.items():
            if arch.lower() in {"ruler", "hero", "sage"} and score > 0.1:
                premium.append(f"{arch}_segment")
        
        return premium
    
    def _calculate_floor_multiplier(self, unified: UnifiedIntelligence) -> float:
        """Calculate recommended floor price multiplier."""
        value = self._calculate_audience_value(unified)
        richness = self._calculate_psychological_richness(unified)
        
        return 1.0 + (value * 0.3) + (richness * 0.2)
    
    def _recommend_advertiser_categories(self, unified: UnifiedIntelligence) -> List[str]:
        """Recommend advertiser categories."""
        categories = []
        
        archetype_advertisers = {
            "ruler": ["luxury", "financial_services", "premium_auto"],
            "hero": ["fitness", "sports", "outdoor"],
            "sage": ["education", "technology", "consulting"],
            "explorer": ["travel", "outdoor", "adventure"],
            "everyman": ["retail", "food", "entertainment"],
            "caregiver": ["healthcare", "insurance", "family"],
        }
        
        for arch, score in unified.archetype_profile.items():
            if score > 0.15:
                cats = archetype_advertisers.get(arch.lower(), [])
                categories.extend(cats)
        
        return list(set(categories))
    
    def _identify_premium_deals(self, unified: UnifiedIntelligence) -> List[Dict[str, Any]]:
        """Identify premium deal opportunities."""
        return [
            {
                "deal_type": "preferred",
                "audience_quality": self._calculate_audience_value(unified),
                "minimum_spend": 10000,
            }
        ]
    
    def _recommend_audio_formats(self, unified: UnifiedIntelligence) -> List[str]:
        """Recommend audio ad formats."""
        formats = []
        
        if unified.mechanism_effectiveness.get("storytelling", 0) > 0.6:
            formats.append("podcast_host_read")
        if unified.mechanism_effectiveness.get("social_proof", 0) > 0.6:
            formats.append("testimonial_spot")
        if unified.mechanism_effectiveness.get("authority", 0) > 0.6:
            formats.append("expert_endorsement")
        
        return formats or ["standard_audio_spot"]
    
    def _calculate_show_affinity(self, unified: UnifiedIntelligence) -> Dict[str, float]:
        """Calculate affinity with iHeart shows."""
        # Would integrate with iHeart data
        return {}
    
    def _calculate_podcast_alignment(self, unified: UnifiedIntelligence) -> Dict[str, float]:
        """Calculate podcast category alignment."""
        # Would integrate with podcast data
        return {}
    
    def _get_key_traits(self, unified: UnifiedIntelligence) -> List[str]:
        """Get key psychological traits."""
        top_traits = sorted(
            unified.psychological_profile.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [t[0] for t in top_traits[:5]]
    
    def _extract_behavioral_patterns(self, unified: UnifiedIntelligence) -> List[str]:
        """Extract behavioral patterns."""
        patterns = []
        
        if unified.mechanism_effectiveness.get("social_proof", 0) > 0.7:
            patterns.append("social_validation_seeking")
        if unified.mechanism_effectiveness.get("scarcity", 0) > 0.7:
            patterns.append("urgency_responsive")
        if unified.mechanism_effectiveness.get("authority", 0) > 0.7:
            patterns.append("expert_trusting")
        
        return patterns
    
    def _identify_mechanism_gaps(self, unified: UnifiedIntelligence) -> List[str]:
        """Identify underutilized mechanisms."""
        return [
            m for m, score in unified.mechanism_effectiveness.items()
            if score < 0.3
        ]
    
    def _identify_opportunities(self, unified: UnifiedIntelligence) -> List[str]:
        """Identify differentiation opportunities."""
        opportunities = []
        
        gaps = self._identify_mechanism_gaps(unified)
        if "humor" in gaps:
            opportunities.append("humor_differentiation")
        if "nostalgia" in gaps:
            opportunities.append("heritage_storytelling")
        if "unity" in gaps:
            opportunities.append("community_building")
        
        return opportunities
    
    def _generate_key_messages(self, unified: UnifiedIntelligence) -> List[str]:
        """Generate key message recommendations."""
        messages = []
        
        top_mechanisms = self._get_top_mechanisms(unified.mechanism_effectiveness, 3)
        
        mechanism_messages = {
            "social_proof": "Highlight popularity and social validation",
            "authority": "Emphasize expertise and credibility",
            "scarcity": "Create urgency with limited availability",
            "storytelling": "Use narrative and emotional connection",
            "trust": "Build confidence through transparency",
        }
        
        for mech in top_mechanisms:
            if mech in mechanism_messages:
                messages.append(mechanism_messages[mech])
        
        return messages
    
    def _recommend_visual_direction(self, unified: UnifiedIntelligence) -> Dict[str, Any]:
        """Recommend visual creative direction."""
        dominant = max(
            unified.archetype_profile.items(),
            key=lambda x: x[1],
            default=("everyman", 1.0)
        )[0]
        
        visual_map = {
            "ruler": {"style": "luxurious", "colors": "gold_black"},
            "hero": {"style": "dynamic", "colors": "bold_red_blue"},
            "sage": {"style": "clean", "colors": "blue_white"},
            "explorer": {"style": "outdoor", "colors": "earth_tones"},
            "everyman": {"style": "friendly", "colors": "warm_neutral"},
        }
        
        return visual_map.get(dominant.lower(), {"style": "clean", "colors": "brand"})
    
    def _get_audio_tone(self, unified: UnifiedIntelligence) -> str:
        """Get recommended audio tone."""
        return self._recommend_tone(unified.archetype_profile)
    
    def _get_iheart_recommendations(self, unified: UnifiedIntelligence) -> Dict[str, Any]:
        """Get iHeart-specific recommendations."""
        return {
            "formats": self._recommend_audio_formats(unified),
            "timing": "drive_time",  # Would be data-driven
            "frequency": "3_7_impressions",
        }
    
    def _get_digital_formats(self, unified: UnifiedIntelligence) -> List[str]:
        """Get recommended digital formats."""
        return ["display", "video", "native"]
    
    def _get_retargeting_strategy(self, unified: UnifiedIntelligence) -> str:
        """Get recommended retargeting strategy."""
        if unified.mechanism_effectiveness.get("reciprocity", 0) > 0.6:
            return "offer_escalation"
        elif unified.mechanism_effectiveness.get("social_proof", 0) > 0.6:
            return "testimonial_sequence"
        else:
            return "benefit_reminder"
    
    def _get_social_priorities(self, unified: UnifiedIntelligence) -> List[str]:
        """Get social platform priorities."""
        # Would be data-driven
        return ["instagram", "facebook", "tiktok"]
    
    def _get_social_approach(self, unified: UnifiedIntelligence) -> str:
        """Get social media approach."""
        if unified.mechanism_effectiveness.get("social_proof", 0) > 0.7:
            return "ugc_focused"
        elif unified.mechanism_effectiveness.get("authority", 0) > 0.7:
            return "influencer_expert"
        else:
            return "brand_storytelling"
    
    def _recommend_kpis(self, unified: UnifiedIntelligence) -> List[str]:
        """Recommend KPIs based on psychological profile."""
        kpis = ["awareness", "engagement"]
        
        if unified.mechanism_effectiveness.get("commitment_consistency", 0) > 0.6:
            kpis.append("repeat_purchase")
        if unified.mechanism_effectiveness.get("social_proof", 0) > 0.6:
            kpis.append("social_sharing")
        
        kpis.append("conversion")
        return kpis
    
    def _define_success_indicators(self, unified: UnifiedIntelligence) -> List[str]:
        """Define success indicators."""
        return [
            "Engagement above benchmark",
            "Positive sentiment shift",
            "Mechanism alignment confirmed",
            "Conversion lift measured",
        ]
    
    def _get_brand_alignment_guidance(self, unified: UnifiedIntelligence) -> Dict[str, Any]:
        """Get brand alignment guidance."""
        return {
            "target_archetypes": self._get_dominant_archetypes(unified.archetype_profile, 3),
            "alignment_score_threshold": 0.7,
        }
    
    def _get_context_modifiers(self, unified: UnifiedIntelligence) -> Dict[str, float]:
        """Get context-based mechanism modifiers."""
        return {
            "scope_type": unified.scope_type,
            "scope_value": unified.scope_value,
            "modifier": 1.0,  # Would be context-dependent
        }
    
    def _get_format_affinities(self, unified: UnifiedIntelligence) -> Dict[str, float]:
        """Get format affinities."""
        affinities = {}
        
        if unified.mechanism_effectiveness.get("storytelling", 0) > 0.6:
            affinities["podcast"] = 0.9
            affinities["video"] = 0.8
        if unified.mechanism_effectiveness.get("social_proof", 0) > 0.6:
            affinities["display_social"] = 0.8
        
        return affinities
    
    def _get_timing_recommendations(self, unified: UnifiedIntelligence) -> Dict[str, Any]:
        """Get timing recommendations."""
        return {
            "optimal_hours": [8, 9, 10, 12, 18, 19, 20],
            "optimal_days": ["tuesday", "wednesday", "thursday"],
        }
    
    # =========================================================================
    # LEARNING LOOP INTEGRATION (Synergistic Brain Architecture)
    # =========================================================================
    
    def update_mechanism_priors(
        self,
        effectiveness_updates: Dict[str, float],
    ) -> None:
        """
        Update mechanism effectiveness priors based on outcome feedback.
        
        This is called by the ReviewIntelligenceMachineBridge when it
        accumulates sufficient outcome data to update predictions.
        
        Args:
            effectiveness_updates: Dict mapping mechanism names to new effectiveness scores
        """
        if not hasattr(self, '_mechanism_priors'):
            self._mechanism_priors: Dict[str, float] = {}
        
        # Update priors with exponential moving average
        alpha = 0.2  # Learning rate
        
        for mechanism, new_score in effectiveness_updates.items():
            if mechanism in self._mechanism_priors:
                # Blend old and new
                self._mechanism_priors[mechanism] = (
                    (1 - alpha) * self._mechanism_priors[mechanism] +
                    alpha * new_score
                )
            else:
                self._mechanism_priors[mechanism] = new_score
        
        # Invalidate cached intelligence that may be stale
        self._intelligence_cache.clear()
        
        logger.info(
            f"Updated mechanism priors: {len(effectiveness_updates)} mechanisms, "
            f"total tracked: {len(self._mechanism_priors)}"
        )
    
    def get_mechanism_prior(self, mechanism: str) -> Optional[float]:
        """Get the prior effectiveness for a mechanism."""
        if hasattr(self, '_mechanism_priors'):
            return self._mechanism_priors.get(mechanism)
        return None
    
    def get_all_priors(self) -> Dict[str, float]:
        """Get all mechanism priors."""
        if hasattr(self, '_mechanism_priors'):
            return dict(self._mechanism_priors)
        return {}
