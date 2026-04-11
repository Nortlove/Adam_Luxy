#!/usr/bin/env python3
"""
Embed Review Learnings to Neo4j

This script embeds the deep learning extractions from customer reviews into
Neo4j for use by the ADAM system. It focuses on:

1. Multi-domain data (Steam, Sephora, Yelp) - richest psychological profiles
2. Key Amazon categories (not all 63 - too large)
3. Creating thousands of customer types from dimension combinations

Usage:
    python scripts/embed_review_learnings.py [--neo4j-uri URI] [--categories all|essential]
"""

import asyncio
import json
import logging
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field, asdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "learning"
MULTI_DOMAIN_DIR = DATA_DIR / "multi_domain"

# Essential Amazon categories for demo (smaller files with good coverage)
ESSENTIAL_CATEGORIES = [
    "All_Beauty",
    "Appliances", 
    "Baby_Products",
    "Electronics",
    "Grocery_and_Gourmet_Food",
    "Health_and_Personal_Care",
    "Home_and_Kitchen",
    "Sports_and_Outdoors",
    "Toys_and_Games",
]


@dataclass
class ProductProfile:
    """Psychological profile for a product"""
    product_id: str
    brand: str
    product_name: str
    category: str
    domain: str
    
    # Archetypes
    achiever: float = 0.0
    explorer: float = 0.0
    connector: float = 0.0
    guardian: float = 0.0
    pragmatist: float = 0.0
    analyst: float = 0.0
    
    # Framework scores (100+ psychological dimensions) - CRITICAL DATA
    framework_scores: Dict[str, float] = field(default_factory=dict)
    
    # Category scores (19 psychological categories)
    category_scores: Dict[str, float] = field(default_factory=dict)
    
    # Archetype scores (detailed breakdown)
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    review_count: int = 0


@dataclass
class CustomerTypeGranular:
    """
    Granular customer type derived from psychological dimensions.
    This enables THOUSANDS of types instead of just 5-6 archetypes.
    """
    type_id: str
    name: str
    description: str
    
    # Defining characteristics
    primary_framework: str = ""
    primary_dimension: str = ""
    secondary_dimension: str = ""
    
    # Base archetype it's derived from
    base_archetype: str = ""
    
    # Psychological profile
    profile_vector: Dict[str, float] = field(default_factory=dict)
    
    # Which products attract this type
    attracted_to_count: int = 0


class ReviewLearningsEmbedder:
    """Embeds review learnings into Neo4j"""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", 
                 neo4j_password: str = "atomofthought"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        
        self.products: Dict[str, ProductProfile] = {}
        self.customer_types: Dict[str, CustomerTypeGranular] = {}
        self.framework_dimensions: Dict[str, List[str]] = {}
        self.dimension_totals: Dict[str, float] = {}
        
    async def connect(self):
        """Connect to Neo4j"""
        try:
            from neo4j import AsyncGraphDatabase
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.neo4j_uri}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")
            logger.info("Will save learnings to JSON for later embedding")
            return False
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    def load_multi_domain(self) -> Dict[str, Any]:
        """Load multi-domain checkpoints (Steam, Sephora, Yelp, etc.)"""
        stats = {"files": 0, "products": 0, "dimensions": 0}
        
        if not MULTI_DOMAIN_DIR.exists():
            logger.warning(f"Multi-domain dir not found: {MULTI_DOMAIN_DIR}")
            return stats
        
        for checkpoint_file in MULTI_DOMAIN_DIR.glob("checkpoint_*.json"):
            try:
                self._load_checkpoint(checkpoint_file, "multi_domain")
                stats["files"] += 1
                logger.info(f"Loaded {checkpoint_file.name}")
            except Exception as e:
                logger.error(f"Error loading {checkpoint_file}: {e}")
        
        stats["products"] = len(self.products)
        stats["dimensions"] = len(self.dimension_totals)
        return stats
    
    def load_amazon_essential(self) -> Dict[str, Any]:
        """Load essential Amazon categories (not all 63)"""
        stats = {"files": 0, "products": 0}
        
        for category in ESSENTIAL_CATEGORIES:
            checkpoint_file = DATA_DIR / f"checkpoint_{category}.json"
            if checkpoint_file.exists():
                try:
                    self._load_checkpoint(checkpoint_file, "amazon")
                    stats["files"] += 1
                    logger.info(f"Loaded {checkpoint_file.name}")
                except Exception as e:
                    logger.error(f"Error loading {checkpoint_file}: {e}")
        
        stats["products"] = len(self.products)
        return stats
    
    def _load_checkpoint(self, filepath: Path, source: str):
        """Load a single checkpoint file"""
        with open(filepath) as f:
            data = json.load(f)
        
        # Determine domain/category
        if source == "multi_domain":
            domain = data.get("domain", filepath.stem.replace("checkpoint_", ""))
            category = domain
        else:
            category = data.get("category", filepath.stem.replace("checkpoint_", ""))
            domain = "amazon"
        
        domain_key = domain.lower().replace(" ", "_")
        
        # Load dimension totals
        dim_totals = data.get("dimension_totals", {})
        for dim, count in dim_totals.items():
            self.dimension_totals[dim] = self.dimension_totals.get(dim, 0) + count
            # Track framework -> dimensions
            framework = dim.split(".")[0] if "." in dim else "general"
            if framework not in self.framework_dimensions:
                self.framework_dimensions[framework] = []
            if dim not in self.framework_dimensions[framework]:
                self.framework_dimensions[framework].append(dim)
        
        # Load brand/product profiles
        brand_profiles = data.get("brand_customer_profiles", {})
        brand_ad_profiles = data.get("brand_ad_profiles", {})
        
        for brand_name, profile in brand_profiles.items():
            product_id = f"{domain_key}_{category}_{brand_name}".replace(" ", "_").replace(":", "").lower()[:100]
            
            # Get rich psychological data from ad profile - CRITICAL: Don't lose this!
            ad_profile = brand_ad_profiles.get(brand_name, {})
            framework_scores = ad_profile.get("framework_scores", {})
            category_scores = ad_profile.get("category_scores", {})
            archetype_scores = ad_profile.get("archetype_scores", {})
            
            # Create product profile with ALL psychological dimensions
            product = ProductProfile(
                product_id=product_id,
                brand=brand_name,
                product_name=brand_name,
                category=category,
                domain=domain_key,
                # Basic archetypes (backward compatibility)
                achiever=profile.get("achiever", 0),
                explorer=profile.get("explorer", 0),
                connector=profile.get("connector", 0),
                guardian=profile.get("guardian", 0),
                pragmatist=profile.get("pragmatist", 0),
                analyst=profile.get("analyst", 0),
                # RICH DATA: 100+ framework scores per brand
                framework_scores=framework_scores,
                # RICH DATA: 19 psychological category scores
                category_scores=category_scores,
                # RICH DATA: Detailed archetype breakdown
                archetype_scores=archetype_scores,
                review_count=ad_profile.get("product_count", 1),
            )
            
            self.products[product_id] = product
    
    def derive_customer_types(self) -> int:
        """
        Derive thousands of customer types from dimension combinations.
        
        Strategy:
        1. For each framework, identify top dimensions
        2. For each archetype, create subtypes based on dimension emphasis
        3. This gives us: 5 archetypes × 40 frameworks × ~5 dimensions = 1000+ types
        """
        type_count = 0
        
        # Get top dimensions per framework
        framework_top_dims = {}
        for framework, dims in self.framework_dimensions.items():
            dim_scores = [(d, self.dimension_totals.get(d, 0)) for d in dims]
            dim_scores.sort(key=lambda x: -x[1])
            framework_top_dims[framework] = dim_scores[:5]  # Top 5 per framework
        
        archetypes = ["achiever", "explorer", "connector", "guardian", "pragmatist"]
        
        # Create granular types
        for archetype in archetypes:
            for framework, top_dims in framework_top_dims.items():
                for dim, score in top_dims:
                    if score <= 0:
                        continue
                    
                    type_id = f"ct_{archetype[:3]}_{framework[:8]}_{dim.split('.')[-1][:10]}"
                    type_id = type_id.replace(".", "_").replace(" ", "_").lower()[:50]
                    
                    dim_name = dim.split(".")[-1] if "." in dim else dim
                    
                    name = f"{archetype.title()} - {dim_name.replace('_', ' ').title()}"
                    description = f"{archetype.title()} customer type with emphasis on {framework} {dim_name}"
                    
                    customer_type = CustomerTypeGranular(
                        type_id=type_id,
                        name=name,
                        description=description,
                        primary_framework=framework,
                        primary_dimension=dim,
                        base_archetype=archetype,
                    )
                    
                    self.customer_types[type_id] = customer_type
                    type_count += 1
        
        logger.info(f"Derived {type_count} granular customer types")
        return type_count
    
    async def embed_to_neo4j(self) -> Dict[str, int]:
        """Embed all learnings to Neo4j"""
        if not self.driver:
            logger.warning("No Neo4j connection - saving to JSON instead")
            return await self._save_to_json()
        
        stats = {"products": 0, "types": 0, "dimensions": 0, "relationships": 0}
        
        async with self.driver.session() as session:
            # Create schema
            await self._create_schema(session)
            
            # Create dimension nodes
            stats["dimensions"] = await self._create_dimensions(session)
            
            # Create product nodes
            stats["products"] = await self._create_products(session)
            
            # Create customer type nodes
            stats["types"] = await self._create_customer_types(session)
            
            # Create relationships
            stats["relationships"] = await self._create_relationships(session)
        
        logger.info(f"Embedded to Neo4j: {stats}")
        return stats
    
    async def _create_schema(self, session):
        """Create Neo4j schema with full psychological data support"""
        constraints = [
            # Core constraints
            "CREATE CONSTRAINT product_psych_id IF NOT EXISTS FOR (p:ProductPsychProfile) REQUIRE p.product_id IS UNIQUE",
            "CREATE CONSTRAINT customer_type_granular_id IF NOT EXISTS FOR (ct:CustomerTypeGranular) REQUIRE ct.type_id IS UNIQUE",
            "CREATE CONSTRAINT psych_dim_id IF NOT EXISTS FOR (d:PsychDimension) REQUIRE d.dimension_id IS UNIQUE",
            "CREATE CONSTRAINT framework_score_id IF NOT EXISTS FOR (f:FrameworkScore) REQUIRE f.score_id IS UNIQUE",
            # Basic indexes
            "CREATE INDEX product_brand_idx IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.brand)",
            "CREATE INDEX product_category_idx IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.category)",
            "CREATE INDEX product_domain_idx IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.domain)",
            "CREATE INDEX customer_type_archetype_idx IF NOT EXISTS FOR (ct:CustomerTypeGranular) ON (ct.base_archetype)",
            "CREATE INDEX psych_dim_framework_idx IF NOT EXISTS FOR (d:PsychDimension) ON (d.framework)",
            # NEW: Framework score indexes for fast lookup
            "CREATE INDEX framework_score_framework_idx IF NOT EXISTS FOR (f:FrameworkScore) ON (f.framework)",
            "CREATE INDEX framework_score_dimension_idx IF NOT EXISTS FOR (f:FrameworkScore) ON (f.dimension)",
            # NEW: Composite index for brand + category queries
            "CREATE INDEX product_brand_category_idx IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.brand, p.category)",
        ]
        
        for constraint in constraints:
            try:
                await session.run(constraint)
            except Exception as e:
                if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                    logger.warning(f"Schema: {e}")
    
    async def _create_dimensions(self, session) -> int:
        """Create psychological dimension nodes"""
        count = 0
        
        for dim, total in self.dimension_totals.items():
            framework = dim.split(".")[0] if "." in dim else "general"
            dim_name = dim.split(".")[-1] if "." in dim else dim
            
            query = """
            MERGE (d:PsychDimension {dimension_id: $dim_id})
            SET d.name = $name,
                d.framework = $framework,
                d.total_occurrences = $total
            """
            
            await session.run(query, {
                "dim_id": dim,
                "name": dim_name,
                "framework": framework,
                "total": total,
            })
            count += 1
        
        return count
    
    async def _create_products(self, session) -> int:
        """Create product profile nodes with FULL psychological data"""
        count = 0
        framework_rel_count = 0
        batch_size = 500
        
        products_list = list(self.products.values())
        
        for i in range(0, len(products_list), batch_size):
            batch = products_list[i:i + batch_size]
            
            # Create product nodes with all psychological data
            query = """
            UNWIND $products AS p
            MERGE (prod:ProductPsychProfile {product_id: p.product_id})
            SET prod.brand = p.brand,
                prod.product_name = p.product_name,
                prod.category = p.category,
                prod.domain = p.domain,
                // Basic archetypes
                prod.achiever = p.achiever,
                prod.explorer = p.explorer,
                prod.connector = p.connector,
                prod.guardian = p.guardian,
                prod.pragmatist = p.pragmatist,
                prod.analyst = p.analyst,
                prod.review_count = p.review_count,
                // CRITICAL: Store rich psychological data as JSON strings for complex queries
                prod.framework_scores_json = p.framework_scores_json,
                prod.category_scores_json = p.category_scores_json,
                prod.archetype_scores_json = p.archetype_scores_json,
                // Store key framework dimensions as direct properties for fast queries
                prod.need_for_cognition = p.need_for_cognition,
                prod.regulatory_focus_promotion = p.regulatory_focus_promotion,
                prod.regulatory_focus_prevention = p.regulatory_focus_prevention,
                prod.construal_level = p.construal_level,
                prod.temporal_focus = p.temporal_focus,
                prod.social_proof_sensitivity = p.social_proof_sensitivity,
                prod.authority_sensitivity = p.authority_sensitivity,
                prod.scarcity_sensitivity = p.scarcity_sensitivity,
                prod.commitment_consistency = p.commitment_consistency,
                prod.reciprocity_norm = p.reciprocity_norm,
                // Metadata
                prod.has_framework_scores = p.has_framework_scores,
                prod.framework_score_count = p.framework_score_count
            """
            
            await session.run(query, {
                "products": [
                    {
                        "product_id": p.product_id,
                        "brand": p.brand,
                        "product_name": p.product_name,
                        "category": p.category,
                        "domain": p.domain,
                        "achiever": p.achiever,
                        "explorer": p.explorer,
                        "connector": p.connector,
                        "guardian": p.guardian,
                        "pragmatist": p.pragmatist,
                        "analyst": p.analyst,
                        "review_count": p.review_count,
                        # Store full scores as JSON for complex queries
                        "framework_scores_json": json.dumps(p.framework_scores) if p.framework_scores else "{}",
                        "category_scores_json": json.dumps(p.category_scores) if p.category_scores else "{}",
                        "archetype_scores_json": json.dumps(p.archetype_scores) if p.archetype_scores else "{}",
                        # Extract key dimensions for direct property access
                        "need_for_cognition": p.framework_scores.get("need_for_cognition", p.framework_scores.get("cognitive.need_for_cognition", 0.0)),
                        "regulatory_focus_promotion": p.framework_scores.get("regulatory_focus.promotion", p.framework_scores.get("promotion_focus", 0.0)),
                        "regulatory_focus_prevention": p.framework_scores.get("regulatory_focus.prevention", p.framework_scores.get("prevention_focus", 0.0)),
                        "construal_level": p.framework_scores.get("construal_level", p.framework_scores.get("construal.level", 0.0)),
                        "temporal_focus": p.framework_scores.get("temporal_focus", p.framework_scores.get("temporal.focus", 0.0)),
                        "social_proof_sensitivity": p.framework_scores.get("social_proof", p.framework_scores.get("cialdini.social_proof", 0.0)),
                        "authority_sensitivity": p.framework_scores.get("authority", p.framework_scores.get("cialdini.authority", 0.0)),
                        "scarcity_sensitivity": p.framework_scores.get("scarcity", p.framework_scores.get("cialdini.scarcity", 0.0)),
                        "commitment_consistency": p.framework_scores.get("commitment", p.framework_scores.get("cialdini.commitment", 0.0)),
                        "reciprocity_norm": p.framework_scores.get("reciprocity", p.framework_scores.get("cialdini.reciprocity", 0.0)),
                        "has_framework_scores": len(p.framework_scores) > 0,
                        "framework_score_count": len(p.framework_scores),
                    }
                    for p in batch
                ]
            })
            
            count += len(batch)
            
            if count % 2000 == 0:
                logger.info(f"Created {count} product nodes...")
        
        # Create framework score relationships for products with rich data
        logger.info("Creating framework score relationships...")
        for p in products_list:
            if not p.framework_scores:
                continue
                
            # Create relationships to top framework dimensions (top 20 per product)
            top_frameworks = sorted(
                p.framework_scores.items(), 
                key=lambda x: abs(x[1]), 
                reverse=True
            )[:20]
            
            for fw_name, fw_score in top_frameworks:
                if abs(fw_score) < 0.1:  # Skip very low scores
                    continue
                    
                rel_query = """
                MATCH (prod:ProductPsychProfile {product_id: $product_id})
                MERGE (fw:FrameworkScore {score_id: $fw_id})
                SET fw.framework = $framework,
                    fw.dimension = $dimension
                MERGE (prod)-[r:HAS_FRAMEWORK_SCORE]->(fw)
                SET r.score = $score,
                    r.normalized_score = $normalized_score
                """
                
                framework = fw_name.split(".")[0] if "." in fw_name else "general"
                dimension = fw_name.split(".")[-1] if "." in fw_name else fw_name
                
                await session.run(rel_query, {
                    "product_id": p.product_id,
                    "fw_id": f"fw_{fw_name}",
                    "framework": framework,
                    "dimension": dimension,
                    "score": fw_score,
                    "normalized_score": min(1.0, max(-1.0, fw_score)),
                })
                framework_rel_count += 1
        
        logger.info(f"Created {framework_rel_count} framework score relationships")
        return count
    
    async def _create_customer_types(self, session) -> int:
        """Create granular customer type nodes"""
        count = 0
        batch_size = 500
        
        types_list = list(self.customer_types.values())
        
        for i in range(0, len(types_list), batch_size):
            batch = types_list[i:i + batch_size]
            
            query = """
            UNWIND $types AS t
            MERGE (ct:CustomerTypeGranular {type_id: t.type_id})
            SET ct.name = t.name,
                ct.description = t.description,
                ct.primary_framework = t.primary_framework,
                ct.primary_dimension = t.primary_dimension,
                ct.base_archetype = t.base_archetype
            """
            
            await session.run(query, {
                "types": [
                    {
                        "type_id": ct.type_id,
                        "name": ct.name,
                        "description": ct.description,
                        "primary_framework": ct.primary_framework,
                        "primary_dimension": ct.primary_dimension,
                        "base_archetype": ct.base_archetype,
                    }
                    for ct in batch
                ]
            })
            
            count += len(batch)
        
        return count
    
    async def _create_relationships(self, session) -> int:
        """Create relationships between nodes"""
        count = 0
        
        # Link customer types to their primary dimension
        for ct in self.customer_types.values():
            query = """
            MATCH (ct:CustomerTypeGranular {type_id: $type_id})
            MATCH (d:PsychDimension {dimension_id: $dim_id})
            MERGE (ct)-[r:DEFINED_BY]->(d)
            SET r.importance = 1.0
            """
            
            await session.run(query, {
                "type_id": ct.type_id,
                "dim_id": ct.primary_dimension,
            })
            count += 1
        
        # Link customer types to base archetype (via existing CustomerArchetype nodes if they exist)
        for ct in self.customer_types.values():
            query = """
            MATCH (ct:CustomerTypeGranular {type_id: $type_id})
            MATCH (a:CustomerArchetype)
            WHERE toLower(a.archetype_id) CONTAINS $archetype
               OR toLower(a.name) CONTAINS $archetype
            MERGE (ct)-[r:SPECIALIZES]->(a)
            """
            
            await session.run(query, {
                "type_id": ct.type_id,
                "archetype": ct.base_archetype,
            })
            count += 1
        
        logger.info(f"Created {count} relationships")
        return count
    
    async def _save_to_json(self) -> Dict[str, int]:
        """Save learnings to JSON if Neo4j not available"""
        output_dir = DATA_DIR / "neo4j_export"
        output_dir.mkdir(exist_ok=True)
        
        # Save products
        products_file = output_dir / "products_psych_profiles.json"
        with open(products_file, 'w') as f:
            json.dump(
                {pid: asdict(p) for pid, p in self.products.items()},
                f, indent=2
            )
        
        # Save customer types
        types_file = output_dir / "customer_types_granular.json"
        with open(types_file, 'w') as f:
            json.dump(
                {tid: asdict(t) for tid, t in self.customer_types.items()},
                f, indent=2
            )
        
        # Save dimensions
        dims_file = output_dir / "psych_dimensions.json"
        with open(dims_file, 'w') as f:
            json.dump({
                "dimension_totals": self.dimension_totals,
                "framework_dimensions": self.framework_dimensions,
            }, f, indent=2)
        
        logger.info(f"Saved learnings to {output_dir}")
        
        return {
            "products": len(self.products),
            "types": len(self.customer_types),
            "dimensions": len(self.dimension_totals),
            "relationships": 0,
        }


async def main():
    parser = argparse.ArgumentParser(description="Embed review learnings to Neo4j")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="atomofthought")
    parser.add_argument("--categories", choices=["essential", "all"], default="essential",
                       help="Which Amazon categories to load (essential=9 key categories, all=all 63)")
    parser.add_argument("--skip-amazon", action="store_true", 
                       help="Skip Amazon categories (multi-domain only)")
    args = parser.parse_args()
    
    embedder = ReviewLearningsEmbedder(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
    )
    
    print("=" * 60)
    print("REVIEW LEARNINGS EMBEDDER")
    print("=" * 60)
    
    # Load multi-domain first (smaller, richer)
    print("\n1. Loading multi-domain learnings (Steam, Sephora, Yelp, etc.)...")
    multi_stats = embedder.load_multi_domain()
    print(f"   Loaded: {multi_stats}")
    
    # Load Amazon categories
    if not args.skip_amazon:
        print(f"\n2. Loading Amazon {args.categories} categories...")
        if args.categories == "essential":
            amazon_stats = embedder.load_amazon_essential()
        else:
            # Load all - this will be slow!
            print("   WARNING: Loading all Amazon categories - this may take several minutes...")
            amazon_stats = {"files": 0, "products": len(embedder.products)}
            for checkpoint in DATA_DIR.glob("checkpoint_*.json"):
                if "google" not in checkpoint.name.lower() and "multi_domain" not in str(checkpoint):
                    embedder._load_checkpoint(checkpoint, "amazon")
                    amazon_stats["files"] += 1
            amazon_stats["products"] = len(embedder.products)
        print(f"   Loaded: {amazon_stats}")
    
    print(f"\n   Total products: {len(embedder.products)}")
    print(f"   Total dimensions: {len(embedder.dimension_totals)}")
    
    # Derive customer types
    print("\n3. Deriving granular customer types...")
    type_count = embedder.derive_customer_types()
    print(f"   Created {type_count} customer types!")
    
    # Connect and embed
    print("\n4. Connecting to Neo4j...")
    connected = await embedder.connect()
    
    print("\n5. Embedding to Neo4j...")
    stats = await embedder.embed_to_neo4j()
    print(f"   Embedded: {stats}")
    
    await embedder.close()
    
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\nProducts embedded: {stats['products']}")
    print(f"Customer types created: {stats['types']}")
    print(f"Psychological dimensions: {stats['dimensions']}")
    print(f"Relationships: {stats['relationships']}")
    
    if not connected:
        print(f"\nNote: Neo4j was not available. Learnings saved to:")
        print(f"  {DATA_DIR / 'neo4j_export'}")
        print("\nTo embed later, start Neo4j and run this script again.")


if __name__ == "__main__":
    asyncio.run(main())
