#!/usr/bin/env python3
"""
Strategic Review Learnings Embedder

This implements the multi-dimensional customer type strategy:
- 3,750+ granular customer types (not 5 archetypes)
- Domain-specific intelligence preservation
- Regional psychology integration
- Mechanism effectiveness per customer type

Usage:
    python3 scripts/embed_strategic_learnings.py [--neo4j-uri URI]
"""

import asyncio
import json
import logging
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "learning"
MULTI_DOMAIN_DIR = DATA_DIR / "multi_domain"
GOOGLE_MAPS_DIR = DATA_DIR / "google_maps"

# Core archetypes
BASE_ARCHETYPES = ["achiever", "explorer", "connector", "guardian", "pragmatist"]

# Top frameworks (by signal strength across all sources)
TOP_FRAMEWORKS = [
    "regulatory_focus", "construal_level", "temporal_orientation",
    "big_five", "self_determination", "need_for_cognition",
    "approach_avoidance", "emotional_intensity", "decision_style",
    "self_monitoring", "uncertainty_tolerance", "dual_process",
    "elm", "loss_aversion", "social_proof"
]

# Domains
DOMAINS = [
    "gaming", "beauty", "local_business", "product_general",
    "entertainment", "automotive", "food", "travel", "technology", "health"
]

# Regional clusters (from cultural values analysis)
REGIONAL_CLUSTERS = [
    "traditional_south", "progressive_coast", "midwest_practical",
    "mountain_west", "northeast_urban", "southwest_blend",
    "pacific_northwest", "great_plains", "mid_atlantic", "national_average"
]

# Cognitive mechanisms
MECHANISMS = [
    "social_proof", "scarcity", "authority", "reciprocity",
    "commitment", "liking", "loss_aversion", "anchoring", "framing"
]


@dataclass
class CustomerTypeGranular:
    """A granular customer type from dimension combinations"""
    type_id: str
    base_archetype: str
    primary_framework: str
    primary_dimension: str
    domain: str
    regional_cluster: str = "national_average"
    
    # Mechanism effectiveness scores
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Evidence
    evidence_count: int = 0
    confidence: float = 0.0
    
    def to_neo4j_props(self) -> Dict[str, Any]:
        props = {
            "type_id": self.type_id,
            "base_archetype": self.base_archetype,
            "primary_framework": self.primary_framework,
            "primary_dimension": self.primary_dimension,
            "domain": self.domain,
            "regional_cluster": self.regional_cluster,
            "evidence_count": self.evidence_count,
            "confidence": self.confidence,
        }
        # Add mechanism effectiveness as properties
        for mech, eff in self.mechanism_effectiveness.items():
            props[f"mech_{mech}"] = eff
        return props


@dataclass
class DomainProfile:
    """Domain-specific profile"""
    domain: str
    domain_types: List[str]  # e.g., gamer archetypes, beauty types
    framework_weights: Dict[str, float]  # Which frameworks matter most
    mechanism_modifiers: Dict[str, float]  # Domain adjustments to mechanisms


@dataclass
class RegionalProfile:
    """Regional psychology profile"""
    state: str
    cluster: str
    traditionalism: float
    individualism: float
    need_for_closure: float
    uncertainty_tolerance: float
    moral_foundations: Dict[str, float]
    advertising_implications: Dict[str, List[str]]


class StrategicEmbedder:
    """
    Creates 3,750+ customer types with domain and regional intelligence.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "atomofthought"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        
        # Data stores
        self.customer_types: Dict[str, CustomerTypeGranular] = {}
        self.domain_profiles: Dict[str, DomainProfile] = {}
        self.regional_profiles: Dict[str, RegionalProfile] = {}
        self.dimension_stats: Dict[str, float] = {}  # dimension -> total signal
        self.framework_dimensions: Dict[str, List[str]] = {}  # framework -> top dimensions
        
        # Mechanism-archetype base effectiveness (from research)
        self.base_mechanism_effectiveness = self._init_base_effectiveness()
    
    def _init_base_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """Initialize research-based mechanism effectiveness by archetype"""
        return {
            "achiever": {
                "scarcity": 0.85, "authority": 0.80, "social_proof": 0.75,
                "commitment": 0.70, "anchoring": 0.75, "framing": 0.70,
                "loss_aversion": 0.80, "reciprocity": 0.60, "liking": 0.55
            },
            "explorer": {
                "scarcity": 0.70, "authority": 0.55, "social_proof": 0.60,
                "commitment": 0.50, "anchoring": 0.55, "framing": 0.75,
                "loss_aversion": 0.50, "reciprocity": 0.65, "liking": 0.80
            },
            "connector": {
                "scarcity": 0.55, "authority": 0.60, "social_proof": 0.90,
                "commitment": 0.75, "anchoring": 0.50, "framing": 0.65,
                "loss_aversion": 0.60, "reciprocity": 0.85, "liking": 0.90
            },
            "guardian": {
                "scarcity": 0.80, "authority": 0.85, "social_proof": 0.80,
                "commitment": 0.85, "anchoring": 0.70, "framing": 0.60,
                "loss_aversion": 0.90, "reciprocity": 0.70, "liking": 0.60
            },
            "pragmatist": {
                "scarcity": 0.65, "authority": 0.75, "social_proof": 0.70,
                "commitment": 0.65, "anchoring": 0.85, "framing": 0.80,
                "loss_aversion": 0.75, "reciprocity": 0.65, "liking": 0.55
            }
        }
    
    async def connect(self) -> bool:
        """Connect to Neo4j"""
        try:
            from neo4j import AsyncGraphDatabase
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.neo4j_uri}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")
            return False
    
    async def close(self):
        if self.driver:
            await self.driver.close()
    
    # =========================================================================
    # PHASE 1: Load and Analyze All Sources
    # =========================================================================
    
    def load_all_sources(self) -> Dict[str, Any]:
        """Load all data sources and extract dimensional statistics"""
        stats = {"sources": 0, "dimensions": 0, "products": 0}
        
        # Load multi-domain
        self._load_multi_domain_stats()
        
        # Load Google Maps with regional data
        self._load_google_maps_stats()
        
        # Load Amazon categories
        self._load_amazon_stats()
        
        # Compute top dimensions per framework
        self._compute_top_dimensions()
        
        stats["dimensions"] = len(self.dimension_stats)
        stats["sources"] = len(self.domain_profiles)
        
        logger.info(f"Loaded stats: {stats}")
        return stats
    
    def _load_multi_domain_stats(self):
        """Load Steam, Sephora, Yelp, etc."""
        domain_configs = {
            "checkpoint_steam_gaming.json": ("gaming", ["gamer_archetypes", "playtime_segments"]),
            "checkpoint_sephora_beauty.json": ("beauty", ["beauty_demographics", "ingredient_focus"]),
            "checkpoint_yelp_reviews.json": ("local_business", ["elite_reviewers", "rating_psychology"]),
            "checkpoint_podcast_reviews.json": ("entertainment", ["content_engagement"]),
            "checkpoint_airline_reviews.json": ("travel", ["service_expectations"]),
            "checkpoint_edmunds_car_reviews.json": ("automotive", ["purchase_psychology"]),
        }
        
        for filename, (domain, domain_types) in domain_configs.items():
            filepath = MULTI_DOMAIN_DIR / filename
            if not filepath.exists():
                continue
            
            with open(filepath) as f:
                data = json.load(f)
            
            # Aggregate dimension stats
            for dim, count in data.get("dimension_totals", {}).items():
                self.dimension_stats[dim] = self.dimension_stats.get(dim, 0) + count
            
            # Extract framework weights from actual data
            framework_totals = data.get("framework_totals", {})
            total = sum(framework_totals.values()) or 1
            framework_weights = {k: v/total for k, v in framework_totals.items()}
            
            # Create domain profile
            self.domain_profiles[domain] = DomainProfile(
                domain=domain,
                domain_types=domain_types,
                framework_weights=framework_weights,
                mechanism_modifiers=self._compute_domain_mechanism_modifiers(domain, data)
            )
            
            logger.info(f"Loaded {domain}: {data.get('total_reviews', 0):,} reviews")
    
    def _load_google_maps_stats(self):
        """Load Google Maps with regional profiles"""
        if not GOOGLE_MAPS_DIR.exists():
            return
        
        # Load enhanced summary for regional data
        summary_file = GOOGLE_MAPS_DIR / "google_maps_enhanced_summary.json"
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)
        
        # Load individual state checkpoints
        for checkpoint in GOOGLE_MAPS_DIR.glob("enhanced_checkpoint_google_*.json"):
            state = checkpoint.stem.replace("enhanced_checkpoint_google_", "")
            
            with open(checkpoint) as f:
                data = json.load(f)
            
            ea = data.get("enhanced_analysis", {})
            cv = ea.get("cultural_values", {})
            
            if not cv.get("available"):
                continue
            
            # Determine regional cluster
            cluster = self._classify_regional_cluster(cv)
            
            self.regional_profiles[state] = RegionalProfile(
                state=state,
                cluster=cluster,
                traditionalism=cv.get("summary", {}).get("traditionalism_score", 0.5),
                individualism=cv.get("summary", {}).get("individualism_score", 0.5),
                need_for_closure=cv.get("decision_style", {}).get("need_for_closure", 0.5),
                uncertainty_tolerance=cv.get("decision_style", {}).get("uncertainty_tolerance", 0.5),
                moral_foundations=cv.get("moral_foundations", {}),
                advertising_implications=cv.get("advertising_implications", {})
            )
        
        # Add local_business domain profile
        self.domain_profiles["local_business"] = DomainProfile(
            domain="local_business",
            domain_types=["restaurant", "retail", "service", "entertainment"],
            framework_weights={"social_proof": 0.2, "trust": 0.2, "convenience": 0.15},
            mechanism_modifiers={"social_proof": 1.3, "liking": 1.2, "authority": 0.9}
        )
        
        logger.info(f"Loaded Google Maps: {len(self.regional_profiles)} state profiles")
    
    def _load_amazon_stats(self):
        """Load Amazon category statistics - SKIP for now (files too large)"""
        # Amazon files are 10GB+ each - skip loading to avoid memory issues
        # The multi-domain + Google Maps data is sufficient for customer type generation
        
        # Add product_general domain with default settings
        self.domain_profiles["product_general"] = DomainProfile(
            domain="product_general",
            domain_types=["consumer_goods", "electronics", "home", "fashion"],
            framework_weights={"quality": 0.2, "value": 0.2, "brand": 0.15},
            mechanism_modifiers={"anchoring": 1.2, "scarcity": 1.1, "social_proof": 1.1}
        )
        
        # Add other product domains
        for domain in ["technology", "health", "food"]:
            if domain not in self.domain_profiles:
                self.domain_profiles[domain] = DomainProfile(
                    domain=domain,
                    domain_types=[domain],
                    framework_weights={},
                    mechanism_modifiers={}
                )
        
        logger.info(f"Skipped Amazon (too large) - using multi-domain data")
    
    def _classify_regional_cluster(self, cultural_values: Dict) -> str:
        """Classify a state into regional cluster based on cultural values"""
        trad = cultural_values.get("summary", {}).get("traditionalism_score", 0.5)
        indiv = cultural_values.get("summary", {}).get("individualism_score", 0.5)
        
        if trad > 0.7:
            return "traditional_south"
        elif trad < 0.3:
            if indiv > 0.7:
                return "progressive_coast"
            else:
                return "northeast_urban"
        elif 0.4 < trad < 0.6:
            if indiv > 0.6:
                return "mountain_west"
            else:
                return "midwest_practical"
        else:
            return "national_average"
    
    def _compute_domain_mechanism_modifiers(self, domain: str, data: Dict) -> Dict[str, float]:
        """Compute how domain modifies mechanism effectiveness"""
        modifiers = {m: 1.0 for m in MECHANISMS}
        
        # Domain-specific adjustments based on framework emphasis
        fw_totals = data.get("framework_totals", {})
        total = sum(fw_totals.values()) or 1
        
        # Social proof emphasis
        social_signals = fw_totals.get("social_comparison", 0) + fw_totals.get("belongingness", 0)
        if social_signals / total > 0.05:
            modifiers["social_proof"] *= 1.3
            modifiers["liking"] *= 1.2
        
        # Achievement emphasis
        achievement_signals = fw_totals.get("self_determination", 0)
        if achievement_signals / total > 0.05:
            modifiers["scarcity"] *= 1.2
            modifiers["authority"] *= 1.1
        
        # Analytical emphasis
        analytical_signals = fw_totals.get("need_for_cognition", 0) + fw_totals.get("elm", 0)
        if analytical_signals / total > 0.05:
            modifiers["anchoring"] *= 1.2
            modifiers["framing"] *= 1.15
        
        return modifiers
    
    def _compute_top_dimensions(self):
        """Compute top 5 dimensions per framework"""
        # Group dimensions by framework
        framework_dims = defaultdict(list)
        for dim, count in self.dimension_stats.items():
            if "." in dim:
                fw = dim.split(".")[0]
                framework_dims[fw].append((dim, count))
        
        # Get top 5 per framework
        for fw, dims in framework_dims.items():
            sorted_dims = sorted(dims, key=lambda x: -x[1])[:5]
            self.framework_dimensions[fw] = [d[0] for d in sorted_dims]
        
        logger.info(f"Computed top dimensions for {len(self.framework_dimensions)} frameworks")
    
    # =========================================================================
    # PHASE 2: Generate Customer Types
    # =========================================================================
    
    def generate_customer_types(self) -> int:
        """Generate 3,750+ granular customer types"""
        count = 0
        
        for archetype in BASE_ARCHETYPES:
            for framework in TOP_FRAMEWORKS:
                # Get top dimensions for this framework
                dimensions = self.framework_dimensions.get(framework, [f"{framework}.default"])[:5]
                
                for dimension in dimensions:
                    for domain in DOMAINS:
                        # Create type without regional cluster (will be added per-query)
                        type_id = f"{archetype}_{framework}_{self._short_dim(dimension)}_{domain}"
                        
                        # Compute mechanism effectiveness for this type
                        mech_eff = self._compute_type_mechanism_effectiveness(
                            archetype, framework, dimension, domain
                        )
                        
                        self.customer_types[type_id] = CustomerTypeGranular(
                            type_id=type_id,
                            base_archetype=archetype,
                            primary_framework=framework,
                            primary_dimension=dimension,
                            domain=domain,
                            mechanism_effectiveness=mech_eff,
                            confidence=0.7  # Base confidence
                        )
                        count += 1
        
        logger.info(f"Generated {count} customer types")
        return count
    
    def _short_dim(self, dimension: str) -> str:
        """Shorten dimension name for type ID"""
        parts = dimension.split(".")
        return parts[-1][:15] if parts else dimension[:15]
    
    def _compute_type_mechanism_effectiveness(
        self, 
        archetype: str, 
        framework: str, 
        dimension: str, 
        domain: str
    ) -> Dict[str, float]:
        """
        Compute mechanism effectiveness for a specific customer type.
        
        Combines:
        1. Base archetype effectiveness (40%)
        2. Framework-mechanism alignment (30%)
        3. Domain modifier (20%)
        4. Dimension-specific adjustment (10%)
        """
        effectiveness = {}
        
        # Get base effectiveness for archetype
        base = self.base_mechanism_effectiveness.get(archetype, {})
        
        # Get framework-mechanism alignment
        framework_alignment = self._get_framework_mechanism_alignment(framework)
        
        # Get domain modifier
        domain_profile = self.domain_profiles.get(domain)
        domain_modifier = domain_profile.mechanism_modifiers if domain_profile else {}
        
        # Get dimension-specific adjustment
        dim_adjustment = self._get_dimension_adjustment(dimension)
        
        for mechanism in MECHANISMS:
            eff = (
                base.get(mechanism, 0.5) * 0.4 +
                framework_alignment.get(mechanism, 0.5) * 0.3 +
                (domain_modifier.get(mechanism, 1.0) - 1.0 + 0.5) * 0.2 +
                dim_adjustment.get(mechanism, 0.5) * 0.1
            )
            effectiveness[mechanism] = min(1.0, max(0.0, eff))
        
        return effectiveness
    
    def _get_framework_mechanism_alignment(self, framework: str) -> Dict[str, float]:
        """Get mechanism alignment for a framework"""
        alignments = {
            "regulatory_focus": {
                "scarcity": 0.8, "loss_aversion": 0.85, "framing": 0.9,
                "social_proof": 0.6, "authority": 0.7
            },
            "construal_level": {
                "framing": 0.9, "anchoring": 0.75, "authority": 0.7,
                "social_proof": 0.6, "scarcity": 0.5
            },
            "temporal_orientation": {
                "scarcity": 0.8, "loss_aversion": 0.7, "commitment": 0.75,
                "framing": 0.7, "anchoring": 0.65
            },
            "big_five": {
                "liking": 0.8, "social_proof": 0.75, "authority": 0.7,
                "reciprocity": 0.7, "commitment": 0.65
            },
            "self_determination": {
                "commitment": 0.85, "reciprocity": 0.8, "liking": 0.75,
                "authority": 0.6, "framing": 0.65
            },
            "need_for_cognition": {
                "authority": 0.85, "anchoring": 0.8, "framing": 0.8,
                "social_proof": 0.5, "scarcity": 0.4
            },
            "approach_avoidance": {
                "loss_aversion": 0.9, "scarcity": 0.85, "framing": 0.8,
                "social_proof": 0.65, "authority": 0.6
            },
            "emotional_intensity": {
                "scarcity": 0.85, "liking": 0.8, "social_proof": 0.8,
                "loss_aversion": 0.75, "reciprocity": 0.7
            },
            "social_proof": {
                "social_proof": 0.95, "liking": 0.85, "authority": 0.75,
                "commitment": 0.65, "reciprocity": 0.7
            }
        }
        
        return alignments.get(framework, {m: 0.5 for m in MECHANISMS})
    
    def _get_dimension_adjustment(self, dimension: str) -> Dict[str, float]:
        """Get mechanism adjustments for specific dimension"""
        # Extract dimension type
        if "promotion" in dimension.lower():
            return {"framing": 0.7, "scarcity": 0.6, "loss_aversion": 0.3}
        elif "prevention" in dimension.lower():
            return {"loss_aversion": 0.8, "authority": 0.7, "commitment": 0.7}
        elif "high" in dimension.lower() and "extraversion" in dimension.lower():
            return {"social_proof": 0.8, "liking": 0.8, "reciprocity": 0.7}
        elif "future" in dimension.lower():
            return {"commitment": 0.7, "framing": 0.7, "anchoring": 0.6}
        elif "past" in dimension.lower():
            return {"authority": 0.7, "commitment": 0.8, "social_proof": 0.7}
        else:
            return {m: 0.5 for m in MECHANISMS}
    
    # =========================================================================
    # PHASE 3: Embed to Neo4j
    # =========================================================================
    
    async def embed_to_neo4j(self) -> Dict[str, int]:
        """Embed all learnings to Neo4j"""
        if not self.driver:
            logger.warning("No Neo4j connection")
            return await self._save_to_json()
        
        stats = {"customer_types": 0, "regional_profiles": 0, "mechanisms": 0, "relationships": 0}
        
        async with self.driver.session() as session:
            # Create schema
            await self._create_schema(session)
            
            # Create customer type nodes
            stats["customer_types"] = await self._create_customer_types(session)
            
            # Create regional profile nodes
            stats["regional_profiles"] = await self._create_regional_profiles(session)
            
            # Create mechanism nodes
            stats["mechanisms"] = await self._create_mechanisms(session)
            
            # Create relationships
            stats["relationships"] = await self._create_relationships(session)
        
        logger.info(f"Embedded: {stats}")
        return stats
    
    async def _create_schema(self, session):
        """Create Neo4j schema"""
        constraints = [
            "CREATE CONSTRAINT customer_type_granular_id IF NOT EXISTS FOR (ct:CustomerTypeGranular) REQUIRE ct.type_id IS UNIQUE",
            "CREATE CONSTRAINT regional_profile_state IF NOT EXISTS FOR (rp:RegionalProfile) REQUIRE rp.state IS UNIQUE",
            "CREATE CONSTRAINT cognitive_mechanism_id IF NOT EXISTS FOR (m:CognitiveMechanism) REQUIRE m.mechanism_id IS UNIQUE",
            "CREATE INDEX ct_archetype IF NOT EXISTS FOR (ct:CustomerTypeGranular) ON (ct.base_archetype)",
            "CREATE INDEX ct_domain IF NOT EXISTS FOR (ct:CustomerTypeGranular) ON (ct.domain)",
            "CREATE INDEX ct_framework IF NOT EXISTS FOR (ct:CustomerTypeGranular) ON (ct.primary_framework)",
            "CREATE INDEX rp_cluster IF NOT EXISTS FOR (rp:RegionalProfile) ON (rp.cluster)",
        ]
        
        for c in constraints:
            try:
                await session.run(c)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Schema: {e}")
    
    async def _create_customer_types(self, session) -> int:
        """Create customer type nodes"""
        count = 0
        batch_size = 500
        
        types_list = list(self.customer_types.values())
        
        for i in range(0, len(types_list), batch_size):
            batch = types_list[i:i + batch_size]
            
            query = """
            UNWIND $types AS t
            MERGE (ct:CustomerTypeGranular {type_id: t.type_id})
            SET ct.base_archetype = t.base_archetype,
                ct.primary_framework = t.primary_framework,
                ct.primary_dimension = t.primary_dimension,
                ct.domain = t.domain,
                ct.confidence = t.confidence,
                ct.mech_social_proof = t.mech_social_proof,
                ct.mech_scarcity = t.mech_scarcity,
                ct.mech_authority = t.mech_authority,
                ct.mech_reciprocity = t.mech_reciprocity,
                ct.mech_commitment = t.mech_commitment,
                ct.mech_liking = t.mech_liking,
                ct.mech_loss_aversion = t.mech_loss_aversion,
                ct.mech_anchoring = t.mech_anchoring,
                ct.mech_framing = t.mech_framing
            """
            
            await session.run(query, {
                "types": [ct.to_neo4j_props() for ct in batch]
            })
            
            count += len(batch)
            
            if count % 1000 == 0:
                logger.info(f"Created {count} customer types...")
        
        return count
    
    async def _create_regional_profiles(self, session) -> int:
        """Create regional profile nodes"""
        count = 0
        
        for state, profile in self.regional_profiles.items():
            query = """
            MERGE (rp:RegionalProfile {state: $state})
            SET rp.cluster = $cluster,
                rp.traditionalism = $traditionalism,
                rp.individualism = $individualism,
                rp.need_for_closure = $need_for_closure,
                rp.uncertainty_tolerance = $uncertainty_tolerance,
                rp.mf_care = $mf_care,
                rp.mf_fairness = $mf_fairness,
                rp.mf_loyalty = $mf_loyalty,
                rp.mf_authority = $mf_authority,
                rp.mf_sanctity = $mf_sanctity
            """
            
            mf = profile.moral_foundations
            await session.run(query, {
                "state": state,
                "cluster": profile.cluster,
                "traditionalism": profile.traditionalism,
                "individualism": profile.individualism,
                "need_for_closure": profile.need_for_closure,
                "uncertainty_tolerance": profile.uncertainty_tolerance,
                "mf_care": mf.get("care", 0.5),
                "mf_fairness": mf.get("fairness", 0.5),
                "mf_loyalty": mf.get("loyalty", 0.5),
                "mf_authority": mf.get("authority", 0.5),
                "mf_sanctity": mf.get("sanctity", 0.5),
            })
            count += 1
        
        return count
    
    async def _create_mechanisms(self, session) -> int:
        """Create cognitive mechanism nodes"""
        count = 0
        
        for mechanism in MECHANISMS:
            query = """
            MERGE (m:CognitiveMechanism {mechanism_id: $mechanism_id})
            SET m.name = $name
            """
            
            await session.run(query, {
                "mechanism_id": mechanism,
                "name": mechanism.replace("_", " ").title()
            })
            count += 1
        
        return count
    
    async def _create_relationships(self, session) -> int:
        """Create relationships"""
        count = 0
        
        # Customer types to mechanisms (effectiveness relationships)
        for ct in self.customer_types.values():
            for mechanism, effectiveness in ct.mechanism_effectiveness.items():
                query = """
                MATCH (ct:CustomerTypeGranular {type_id: $type_id})
                MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
                MERGE (ct)-[r:RESPONDS_TO]->(m)
                SET r.effectiveness = $effectiveness,
                    r.confidence = $confidence
                """
                
                await session.run(query, {
                    "type_id": ct.type_id,
                    "mechanism_id": mechanism,
                    "effectiveness": effectiveness,
                    "confidence": ct.confidence
                })
                count += 1
        
        logger.info(f"Created {count} relationships")
        return count
    
    async def _save_to_json(self) -> Dict[str, int]:
        """Save to JSON if Neo4j not available"""
        output_dir = DATA_DIR / "strategic_export"
        output_dir.mkdir(exist_ok=True)
        
        # Save customer types
        with open(output_dir / "customer_types_granular.json", 'w') as f:
            json.dump(
                {ct.type_id: ct.to_neo4j_props() for ct in self.customer_types.values()},
                f, indent=2
            )
        
        # Save regional profiles
        with open(output_dir / "regional_profiles.json", 'w') as f:
            json.dump(
                {s: {"state": p.state, "cluster": p.cluster, "traditionalism": p.traditionalism}
                 for s, p in self.regional_profiles.items()},
                f, indent=2
            )
        
        logger.info(f"Saved to {output_dir}")
        return {
            "customer_types": len(self.customer_types),
            "regional_profiles": len(self.regional_profiles),
            "mechanisms": len(MECHANISMS),
            "relationships": 0
        }


async def main():
    parser = argparse.ArgumentParser(description="Strategic Review Learnings Embedder")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="atomofthought")
    args = parser.parse_args()
    
    embedder = StrategicEmbedder(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )
    
    print("=" * 70)
    print("STRATEGIC REVIEW LEARNINGS EMBEDDER")
    print("=" * 70)
    
    # Phase 1: Load all sources
    print("\n1. Loading and analyzing all data sources...")
    stats = embedder.load_all_sources()
    print(f"   Dimensions tracked: {len(embedder.dimension_stats)}")
    print(f"   Domain profiles: {len(embedder.domain_profiles)}")
    print(f"   Regional profiles: {len(embedder.regional_profiles)}")
    
    # Phase 2: Generate customer types
    print("\n2. Generating granular customer types...")
    type_count = embedder.generate_customer_types()
    print(f"   Created {type_count:,} customer types!")
    
    # Phase 3: Connect and embed
    print("\n3. Connecting to Neo4j...")
    connected = await embedder.connect()
    
    print("\n4. Embedding to Neo4j...")
    embed_stats = await embedder.embed_to_neo4j()
    
    await embedder.close()
    
    print("\n" + "=" * 70)
    print("EMBEDDING COMPLETE")
    print("=" * 70)
    print(f"\nCustomer Types: {embed_stats['customer_types']:,}")
    print(f"Regional Profiles: {embed_stats['regional_profiles']}")
    print(f"Mechanisms: {embed_stats['mechanisms']}")
    print(f"Relationships: {embed_stats['relationships']:,}")
    
    if not connected:
        print(f"\nData saved to: {DATA_DIR / 'strategic_export'}")


if __name__ == "__main__":
    asyncio.run(main())
