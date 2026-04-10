"""
Blueprint Registry — defines the component composition for each Blueprint type.

Each entry specifies:
  - Which ADAM intelligence components are always active
  - Which connectors are supported
  - Which delivery adapters are supported
  - Which optional components activate based on tenant config
  - The intelligence pipeline flow

This is the "recipe" that the BlueprintEngine uses to wire up a tenant.
"""

from __future__ import annotations

from typing import Any, Dict, List

from adam.platform.tenants.models import BlueprintType


class BlueprintSpec:
    """Specification for a single Blueprint type."""

    def __init__(
        self,
        blueprint_type: BlueprintType,
        description: str,
        intelligence_components: List[str],
        optional_components: Dict[str, str],
        supported_connectors: List[str],
        supported_delivery: List[str],
        pipeline_stages: List[str],
        latency_budget_ms: int = 200,
        requires_audio_pipeline: bool = False,
    ):
        self.blueprint_type = blueprint_type
        self.description = description
        self.intelligence_components = intelligence_components
        self.optional_components = optional_components
        self.supported_connectors = supported_connectors
        self.supported_delivery = supported_delivery
        self.pipeline_stages = pipeline_stages
        self.latency_budget_ms = latency_budget_ms
        self.requires_audio_pipeline = requires_audio_pipeline

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_type": self.blueprint_type.value,
            "description": self.description,
            "intelligence_components": self.intelligence_components,
            "optional_components": self.optional_components,
            "supported_connectors": self.supported_connectors,
            "supported_delivery": self.supported_delivery,
            "pipeline_stages": self.pipeline_stages,
            "latency_budget_ms": self.latency_budget_ms,
            "requires_audio_pipeline": self.requires_audio_pipeline,
        }


BLUEPRINT_SPECS: Dict[BlueprintType, BlueprintSpec] = {

    BlueprintType.PUB_ENR: BlueprintSpec(
        blueprint_type=BlueprintType.PUB_ENR,
        description="Publisher Audience Segment Enrichment",
        intelligence_components=[
            "unified_intelligence_service",  # 3-layer Bayesian fusion
            "cold_start_service",            # Prior computation
            "feature_store_service",         # User feature serving
            "graph_intelligence_service",    # Neo4j graph queries
        ],
        optional_components={
            "journey_tracking_active": "journey_tracking_service",
            "ab_testing_active": "bandit_service",
        },
        supported_connectors=["rss", "sitemap", "cms_webhook"],
        supported_delivery=["magnite", "prebid", "index_exchange", "pubmatic", "openx"],
        pipeline_stages=[
            "ingest_content",        # Connector → raw content
            "ndf_profile",           # 7+1 NDF dimension extraction
            "segment_build",         # 12-domain psychological segmentation
            "taxonomy_map",          # ADAM constructs → IAB taxonomy
            "deliver_segments",      # Push to SSP
        ],
        latency_budget_ms=500,
    ),

    BlueprintType.DSP_TGT: BlueprintSpec(
        blueprint_type=BlueprintType.DSP_TGT,
        description="DSP Psychological Audience Targeting",
        intelligence_components=[
            "unified_intelligence_service",
            "dsp_enrichment_pipeline",       # Real-time impression enrichment
            "inference_engine",              # 5-tier inference
            "cold_start_service",
            "mechanism_activation_atom",     # Mechanism selection
        ],
        optional_components={
            "ab_testing_active": "bandit_service",
        },
        supported_connectors=["bidstream", "audience_feed"],
        supported_delivery=["stackadapt", "ttd", "dv360", "amazon_dsp"],
        pipeline_stages=[
            "receive_impression",    # Bidstream connector
            "extract_signals",       # 42 behavioral signals
            "infer_state",           # Psychological state vector
            "score_alignment",       # 27-dimension alignment scoring
            "select_mechanisms",     # Persuasion mechanism selection
            "generate_guidance",     # Creative + targeting guidance
            "deliver_enrichment",    # Push to DSP
        ],
        latency_budget_ms=100,
    ),

    BlueprintType.AUD_LST: BlueprintSpec(
        blueprint_type=BlueprintType.AUD_LST,
        description="Audio Listener Intelligence",
        intelligence_components=[
            "unified_intelligence_service",
            "cold_start_service",
            "graph_intelligence_service",
            "feature_store_service",
        ],
        optional_components={
            "journey_tracking_active": "journey_tracking_service",
        },
        supported_connectors=["s3_audio", "rss", "transcript_db"],
        supported_delivery=["megaphone", "triton", "spotify_ad_studio"],
        pipeline_stages=[
            "ingest_audio",          # S3/RSS → audio metadata + transcript
            "ndf_profile",           # Content NDF profiling
            "listener_model",        # Temporal listener state model
            "segment_build",
            "host_briefing",         # Host-read ad guidance generation
            "deliver_segments",
        ],
        latency_budget_ms=500,
        requires_audio_pipeline=True,
    ),

    BlueprintType.DSP_CRE: BlueprintSpec(
        blueprint_type=BlueprintType.DSP_CRE,
        description="DSP Creative Optimization",
        intelligence_components=[
            "unified_intelligence_service",
            "dsp_enrichment_pipeline",
            "gradient_bridge_service",       # Shapley attribution for creative testing
        ],
        optional_components={
            "ab_testing_active": "bandit_service",
        },
        supported_connectors=["creative_api", "asset_feed"],
        supported_delivery=["stackadapt", "ttd"],
        pipeline_stages=[
            "ingest_creatives",      # Creative assets
            "ndf_profile_creative",  # NDF analysis of creative content
            "score_alignment",       # Creative ↔ audience alignment
            "run_ab_test",           # Multi-arm bandit testing
            "optimize_creative",     # Gradient-based creative optimization
            "deliver_guidance",
        ],
        latency_budget_ms=200,
    ),

    BlueprintType.PUB_YLD: BlueprintSpec(
        blueprint_type=BlueprintType.PUB_YLD,
        description="Publisher Yield Optimization",
        intelligence_components=[
            "unified_intelligence_service",
            "feature_store_service",
            "performance_service",           # Latency + cache optimization
        ],
        optional_components={},
        supported_connectors=["rss", "sitemap", "real_time_content"],
        supported_delivery=["magnite", "pubmatic", "openx"],
        pipeline_stages=[
            "ingest_content",
            "score_attention",       # Psychological attention → floor price
            "enrich_context",        # Content moment → ad context signal
            "score_demand",          # Score demand partners per slot
            "optimize_floor",        # Floor price optimization
            "deliver_enrichment",
        ],
        latency_budget_ms=100,
    ),

    BlueprintType.BRD_INT: BlueprintSpec(
        blueprint_type=BlueprintType.BRD_INT,
        description="Brand Intelligence Suite",
        intelligence_components=[
            "unified_intelligence_service",
            "graph_intelligence_service",
        ],
        optional_components={},
        supported_connectors=["brand_feed", "creative_api"],
        supported_delivery=["analytics_dashboard"],
        pipeline_stages=[
            "ingest_brand",          # Brand assets and copy
            "analyze_cialdini",      # Cialdini principle analysis
            "analyze_aaker",         # Aaker brand personality
            "map_competitive",       # Competitive mechanism landscape
            "predict_effectiveness", # Copy effectiveness prediction
            "deliver_report",
        ],
        latency_budget_ms=2000,
    ),

    BlueprintType.AGY_PLN: BlueprintSpec(
        blueprint_type=BlueprintType.AGY_PLN,
        description="Agency Planning Tools",
        intelligence_components=[
            "unified_intelligence_service",
            "cold_start_service",
            "graph_intelligence_service",
        ],
        optional_components={},
        supported_connectors=["audience_feed", "media_plan_feed"],
        supported_delivery=["planning_api"],
        pipeline_stages=[
            "size_audience",         # Psychological audience sizing
            "match_media",           # Media ↔ audience alignment
            "predict_outcomes",      # Campaign outcome prediction
            "optimize_plan",
            "deliver_plan",
        ],
        latency_budget_ms=5000,
    ),

    BlueprintType.CTV_AUD: BlueprintSpec(
        blueprint_type=BlueprintType.CTV_AUD,
        description="CTV Audience Intelligence",
        intelligence_components=[
            "unified_intelligence_service",
            "feature_store_service",
        ],
        optional_components={},
        supported_connectors=["content_api", "acr_feed"],
        supported_delivery=["freewheel", "springserve"],
        pipeline_stages=[
            "ingest_content",
            "ndf_profile",
            "model_household",       # Household-level psychology
            "optimize_moment",       # Content moment targeting
            "deliver_segments",
        ],
        latency_budget_ms=200,
    ),

    BlueprintType.RET_PSY: BlueprintSpec(
        blueprint_type=BlueprintType.RET_PSY,
        description="Retail Psychological Targeting",
        intelligence_components=[
            "unified_intelligence_service",
            "cold_start_service",
            "mechanism_activation_atom",
        ],
        optional_components={
            "journey_tracking_active": "journey_tracking_service",
        },
        supported_connectors=["product_feed", "purchase_feed"],
        supported_delivery=["retail_media_api"],
        pipeline_stages=[
            "ingest_products",       # Product catalog
            "ndf_profile_product",   # 80-construct product NDF
            "model_shopper",         # Purchase psychology model
            "select_mechanisms",
            "deliver_targeting",
        ],
        latency_budget_ms=200,
    ),

    BlueprintType.SOC_AUD: BlueprintSpec(
        blueprint_type=BlueprintType.SOC_AUD,
        description="Social Audience Enrichment",
        intelligence_components=[
            "unified_intelligence_service",
            "feature_store_service",
        ],
        optional_components={},
        supported_connectors=["social_api"],
        supported_delivery=["meta_api", "tiktok_api", "snap_api"],
        pipeline_stages=[
            "ingest_social",
            "ndf_profile_social",    # Social signal → NDF
            "model_engagement",      # Engagement prediction
            "advise_creative",       # Social creative guidance
            "deliver_segments",
        ],
        latency_budget_ms=300,
    ),

    BlueprintType.EXC_DAT: BlueprintSpec(
        blueprint_type=BlueprintType.EXC_DAT,
        description="Exchange Data Enrichment",
        intelligence_components=[
            "unified_intelligence_service",
            "dsp_enrichment_pipeline",
        ],
        optional_components={},
        supported_connectors=["exchange_feed"],
        supported_delivery=["seat_api"],
        pipeline_stages=[
            "receive_exchange_data",
            "score_contextual",      # URL → NDF context scoring
            "enrich_bidstream",
            "build_segments",
            "deliver_enrichment",
        ],
        latency_budget_ms=100,
    ),
}


class BlueprintRegistry:
    """Registry of all available Blueprint specifications."""

    @staticmethod
    def get(blueprint_type: BlueprintType) -> BlueprintSpec:
        spec = BLUEPRINT_SPECS.get(blueprint_type)
        if spec is None:
            raise ValueError(f"Unknown blueprint type: {blueprint_type}")
        return spec

    @staticmethod
    def list_all() -> Dict[str, Dict[str, Any]]:
        return {bp.value: spec.to_dict() for bp, spec in BLUEPRINT_SPECS.items()}

    @staticmethod
    def get_for_connector(connector_type: str) -> List[BlueprintType]:
        """Find which Blueprints support a given connector."""
        return [
            bp for bp, spec in BLUEPRINT_SPECS.items()
            if connector_type in spec.supported_connectors
        ]

    @staticmethod
    def get_for_delivery(adapter_type: str) -> List[BlueprintType]:
        """Find which Blueprints support a given delivery adapter."""
        return [
            bp for bp, spec in BLUEPRINT_SPECS.items()
            if adapter_type in spec.supported_delivery
        ]
