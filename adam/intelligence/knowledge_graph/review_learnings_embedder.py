"""
Review Learnings Embedder for Neo4j

This module embeds the deep learning extractions from customer reviews into
the Neo4j knowledge graph, enabling:
1. Thousands of customer types (not just 5-6 archetypes)
2. Full 252+ psychological dimension storage per product
3. Similarity-based product lookups for fuzzy matching
4. Brand-to-psychological-profile relationships

The key insight is that we have 40+ psychological frameworks with 252+ dimensions,
but the system was collapsing this into just 5-6 archetypes. This embedder preserves
the full granularity.
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class ProductPsychProfile:
    """Full psychological profile for a product/brand"""
    product_id: str
    brand: str
    product_name: str
    category: str
    domain: str  # amazon, steam, sephora, yelp, etc.
    
    # High-level archetypes (for quick matching)
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    
    # Full framework scores (78+ dimensions)
    framework_scores: Dict[str, float] = field(default_factory=dict)
    
    # Granular dimension totals (252+ dimensions)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    review_count: int = 0
    avg_rating: float = 0.0
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j-compatible properties"""
        return {
            "product_id": self.product_id,
            "brand": self.brand,
            "product_name": self.product_name,
            "category": self.category,
            "domain": self.domain,
            "review_count": self.review_count,
            "avg_rating": self.avg_rating,
            # Store archetype scores as individual properties for querying
            **{f"arch_{k}": v for k, v in self.archetype_scores.items()},
            # Store top framework scores (Neo4j has property limits)
            **{f"fw_{k}": v for k, v in sorted(
                self.framework_scores.items(), 
                key=lambda x: -x[1]
            )[:30]},
        }


@dataclass  
class CustomerType:
    """
    A unique customer type derived from psychological dimension combinations.
    This enables THOUSANDS of customer types instead of just 5-6 archetypes.
    """
    type_id: str
    name: str
    description: str
    
    # Dominant dimensions that define this type
    primary_dimensions: List[Tuple[str, float]]  # [(dimension, strength), ...]
    
    # Framework breakdown
    framework_profile: Dict[str, float] = field(default_factory=dict)
    
    # Which products attract this type
    attracted_to_products: List[str] = field(default_factory=list)
    
    # Persuasion effectiveness
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        return {
            "type_id": self.type_id,
            "name": self.name,
            "description": self.description,
            "primary_dimension_1": self.primary_dimensions[0][0] if len(self.primary_dimensions) > 0 else None,
            "primary_dimension_2": self.primary_dimensions[1][0] if len(self.primary_dimensions) > 1 else None,
            "primary_dimension_3": self.primary_dimensions[2][0] if len(self.primary_dimensions) > 2 else None,
        }


class ReviewLearningsEmbedder:
    """
    Embeds review learnings into Neo4j for the ADAM system.
    
    Key capabilities:
    1. Store full psychological profiles (252+ dimensions) per product
    2. Create thousands of customer types from dimension combinations
    3. Enable similarity-based product lookups
    4. Link products to psychological mechanisms
    """
    
    # Paths to learning data
    LEARNING_DIR = Path(__file__).parent.parent.parent.parent / "data" / "learning"
    MULTI_DOMAIN_DIR = LEARNING_DIR / "multi_domain"
    
    def __init__(self, neo4j_client=None):
        self.neo4j_client = neo4j_client
        self.products: Dict[str, ProductPsychProfile] = {}
        self.customer_types: Dict[str, CustomerType] = {}
        self.framework_dimensions: Dict[str, List[str]] = {}  # framework -> dimensions
        
    async def load_all_learnings(self) -> Dict[str, Any]:
        """Load all learning checkpoints from disk"""
        stats = {
            "amazon_categories": 0,
            "multi_domain_sources": 0,
            "total_products": 0,
            "total_brands": 0,
            "frameworks_loaded": set(),
            "dimensions_loaded": 0,
        }
        
        # Load Amazon category checkpoints
        amazon_files = list(self.LEARNING_DIR.glob("checkpoint_*.json"))
        amazon_files = [f for f in amazon_files if "google" not in f.name.lower()]
        
        for checkpoint_file in amazon_files:
            if "multi_domain" in str(checkpoint_file):
                continue
            try:
                await self._load_amazon_checkpoint(checkpoint_file, stats)
                stats["amazon_categories"] += 1
            except Exception as e:
                logger.warning(f"Error loading {checkpoint_file}: {e}")
        
        # Load multi-domain checkpoints (Steam, Sephora, Yelp, etc.)
        if self.MULTI_DOMAIN_DIR.exists():
            for checkpoint_file in self.MULTI_DOMAIN_DIR.glob("checkpoint_*.json"):
                try:
                    await self._load_multi_domain_checkpoint(checkpoint_file, stats)
                    stats["multi_domain_sources"] += 1
                except Exception as e:
                    logger.warning(f"Error loading {checkpoint_file}: {e}")
        
        stats["total_products"] = len(self.products)
        stats["frameworks_loaded"] = list(stats["frameworks_loaded"])
        stats["dimensions_loaded"] = sum(len(dims) for dims in self.framework_dimensions.values())
        
        logger.info(f"Loaded learnings: {stats}")
        return stats
    
    async def _load_amazon_checkpoint(self, filepath: Path, stats: Dict):
        """Load an Amazon category checkpoint"""
        with open(filepath) as f:
            data = json.load(f)
        
        category = data.get("category", filepath.stem.replace("checkpoint_", ""))
        
        # Load framework scores (category-level)
        framework_scores = data.get("framework_scores", {})
        stats["frameworks_loaded"].update(framework_scores.keys())
        
        # Load dimension totals
        dimension_totals = data.get("dimension_totals", {})
        for dim in dimension_totals.keys():
            framework = dim.split(".")[0] if "." in dim else "general"
            if framework not in self.framework_dimensions:
                self.framework_dimensions[framework] = []
            if dim not in self.framework_dimensions[framework]:
                self.framework_dimensions[framework].append(dim)
        
        # Load brand/product profiles
        brand_profiles = data.get("brand_customer_profiles", {})
        brand_ad_profiles = data.get("brand_ad_profiles", {})
        
        for brand_name, profile in brand_profiles.items():
            product_id = f"amazon_{category}_{brand_name}".replace(" ", "_").lower()
            
            # Get ad profile for framework scores
            ad_profile = brand_ad_profiles.get(brand_name, {})
            
            product = ProductPsychProfile(
                product_id=product_id,
                brand=brand_name,
                product_name=brand_name,  # For Amazon, brand often is product
                category=category,
                domain="amazon",
                archetype_scores={
                    k: v for k, v in profile.items() 
                    if k in ["achiever", "explorer", "connector", "guardian", "pragmatist", "analyst"]
                },
                framework_scores=ad_profile.get("framework_scores", {}),
                review_count=ad_profile.get("product_count", 1),
            )
            
            self.products[product_id] = product
            stats["total_brands"] = len(set(p.brand for p in self.products.values()))
    
    async def _load_multi_domain_checkpoint(self, filepath: Path, stats: Dict):
        """Load a multi-domain checkpoint (Steam, Sephora, Yelp, etc.)"""
        with open(filepath) as f:
            data = json.load(f)
        
        domain = data.get("domain", filepath.stem.replace("checkpoint_", ""))
        domain_key = domain.lower().replace(" ", "_")
        
        # Load framework totals
        framework_totals = data.get("framework_totals", {})
        stats["frameworks_loaded"].update(framework_totals.keys())
        
        # Load dimension totals (the 252+ granular dimensions)
        dimension_totals = data.get("dimension_totals", {})
        for dim in dimension_totals.keys():
            framework = dim.split(".")[0] if "." in dim else "general"
            if framework not in self.framework_dimensions:
                self.framework_dimensions[framework] = []
            if dim not in self.framework_dimensions[framework]:
                self.framework_dimensions[framework].append(dim)
        
        # Compute normalized dimension scores
        total_matches = data.get("total_matches", 1)
        normalized_dimensions = {
            dim: count / total_matches 
            for dim, count in dimension_totals.items()
        }
        
        # Load brand/product profiles
        brand_profiles = data.get("brand_customer_profiles", {})
        
        for product_name, profile in brand_profiles.items():
            product_id = f"{domain_key}_{product_name}".replace(" ", "_").replace(":", "").lower()
            
            # Extract archetype scores
            archetype_scores = {
                k: v for k, v in profile.items()
                if k in ["achiever", "explorer", "connector", "guardian", "pragmatist", "analyst"]
            }
            
            # Normalize archetype scores
            total = sum(archetype_scores.values()) or 1
            archetype_scores = {k: v / total for k, v in archetype_scores.items()}
            
            product = ProductPsychProfile(
                product_id=product_id,
                brand=product_name.split(":")[0] if ":" in product_name else product_name,
                product_name=product_name,
                category=domain,
                domain=domain_key,
                archetype_scores=archetype_scores,
                dimension_scores=normalized_dimensions,  # All products share domain dimensions
            )
            
            self.products[product_id] = product
    
    def derive_customer_types(self, min_products: int = 10) -> List[CustomerType]:
        """
        Derive thousands of customer types from dimension combinations.
        
        Instead of just 5-6 archetypes, we create types based on:
        - Dominant psychological dimensions
        - Framework combinations
        - Behavioral patterns
        
        This gives us THOUSANDS of unique customer types.
        """
        customer_types = []
        
        # Group products by their dominant dimensions
        dimension_products = defaultdict(list)
        
        for product in self.products.values():
            # Get top 3 dimensions for this product
            all_dims = {**product.dimension_scores, **product.framework_scores}
            if not all_dims:
                continue
            
            top_dims = sorted(all_dims.items(), key=lambda x: -x[1])[:3]
            if not top_dims:
                continue
            
            # Create dimension signature (top 3 dims)
            dim_sig = tuple(d[0] for d in top_dims)
            dimension_products[dim_sig].append(product.product_id)
        
        # Create customer types for dimension combinations with enough products
        type_counter = 0
        for dim_sig, product_ids in dimension_products.items():
            if len(product_ids) < min_products:
                continue
            
            type_id = f"customer_type_{type_counter:04d}"
            
            # Generate descriptive name from dimensions
            dim_names = [d.split(".")[-1] if "." in d else d for d in dim_sig]
            name = f"{dim_names[0]}_{dim_names[1] if len(dim_names) > 1 else 'focused'}"
            
            # Generate description
            description = f"Customer type characterized by high {', '.join(dim_names[:3])}"
            
            customer_type = CustomerType(
                type_id=type_id,
                name=name,
                description=description,
                primary_dimensions=[(d, 1.0 / (i + 1)) for i, d in enumerate(dim_sig)],
                attracted_to_products=product_ids[:100],  # Limit stored products
            )
            
            customer_types.append(customer_type)
            self.customer_types[type_id] = customer_type
            type_counter += 1
        
        logger.info(f"Derived {len(customer_types)} customer types from dimension combinations")
        return customer_types
    
    async def embed_to_neo4j(self) -> Dict[str, int]:
        """Embed all learnings to Neo4j graph database"""
        if not self.neo4j_client:
            raise ValueError("Neo4j client not configured")
        
        stats = {
            "products_created": 0,
            "customer_types_created": 0,
            "relationships_created": 0,
            "dimensions_created": 0,
        }
        
        driver = self.neo4j_client.driver
        
        async with driver.session() as session:
            # Create constraints and indexes
            await self._create_schema(session)
            
            # Create psychological dimension nodes
            stats["dimensions_created"] = await self._create_dimension_nodes(session)
            
            # Create product nodes with full psychological profiles
            stats["products_created"] = await self._create_product_nodes(session)
            
            # Create customer type nodes
            stats["customer_types_created"] = await self._create_customer_type_nodes(session)
            
            # Create relationships
            stats["relationships_created"] = await self._create_relationships(session)
        
        logger.info(f"Embedded to Neo4j: {stats}")
        return stats
    
    async def _create_schema(self, session):
        """Create Neo4j schema for review learnings"""
        constraints = [
            "CREATE CONSTRAINT product_psych_id IF NOT EXISTS FOR (p:ProductPsychProfile) REQUIRE p.product_id IS UNIQUE",
            "CREATE CONSTRAINT customer_type_id IF NOT EXISTS FOR (ct:CustomerTypeGranular) REQUIRE ct.type_id IS UNIQUE",
            "CREATE CONSTRAINT psych_dimension_id IF NOT EXISTS FOR (d:PsychDimension) REQUIRE d.dimension_id IS UNIQUE",
            "CREATE INDEX product_brand IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.brand)",
            "CREATE INDEX product_category IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.category)",
            "CREATE INDEX product_domain IF NOT EXISTS FOR (p:ProductPsychProfile) ON (p.domain)",
            "CREATE INDEX dimension_framework IF NOT EXISTS FOR (d:PsychDimension) ON (d.framework)",
        ]
        
        for constraint in constraints:
            try:
                await session.run(constraint)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Schema error: {e}")
    
    async def _create_dimension_nodes(self, session) -> int:
        """Create nodes for all 252+ psychological dimensions"""
        count = 0
        
        for framework, dimensions in self.framework_dimensions.items():
            for dim in dimensions:
                query = """
                MERGE (d:PsychDimension {dimension_id: $dim_id})
                SET d.name = $name,
                    d.framework = $framework,
                    d.full_path = $full_path
                """
                await session.run(query, {
                    "dim_id": dim,
                    "name": dim.split(".")[-1] if "." in dim else dim,
                    "framework": framework,
                    "full_path": dim,
                })
                count += 1
        
        return count
    
    async def _create_product_nodes(self, session) -> int:
        """Create product nodes with full psychological profiles"""
        count = 0
        batch_size = 500
        
        products_list = list(self.products.values())
        
        for i in range(0, len(products_list), batch_size):
            batch = products_list[i:i + batch_size]
            
            query = """
            UNWIND $products AS prod
            MERGE (p:ProductPsychProfile {product_id: prod.product_id})
            SET p += prod
            """
            
            await session.run(query, {
                "products": [p.to_neo4j_properties() for p in batch]
            })
            
            count += len(batch)
            
            if count % 5000 == 0:
                logger.info(f"Created {count} product nodes...")
        
        return count
    
    async def _create_customer_type_nodes(self, session) -> int:
        """Create granular customer type nodes"""
        count = 0
        
        for ct in self.customer_types.values():
            query = """
            MERGE (ct:CustomerTypeGranular {type_id: $type_id})
            SET ct.name = $name,
                ct.description = $description,
                ct.primary_dimension_1 = $pd1,
                ct.primary_dimension_2 = $pd2,
                ct.primary_dimension_3 = $pd3
            """
            
            await session.run(query, {
                "type_id": ct.type_id,
                "name": ct.name,
                "description": ct.description,
                "pd1": ct.primary_dimensions[0][0] if len(ct.primary_dimensions) > 0 else None,
                "pd2": ct.primary_dimensions[1][0] if len(ct.primary_dimensions) > 1 else None,
                "pd3": ct.primary_dimensions[2][0] if len(ct.primary_dimensions) > 2 else None,
            })
            count += 1
        
        return count
    
    async def _create_relationships(self, session) -> int:
        """Create relationships between products, types, and dimensions"""
        count = 0
        
        # Link products to their dominant dimensions
        for product in self.products.values():
            all_dims = {**product.dimension_scores, **product.framework_scores}
            top_dims = sorted(all_dims.items(), key=lambda x: -x[1])[:5]
            
            for dim, score in top_dims:
                query = """
                MATCH (p:ProductPsychProfile {product_id: $product_id})
                MATCH (d:PsychDimension {dimension_id: $dim_id})
                MERGE (p)-[r:HAS_DIMENSION]->(d)
                SET r.strength = $strength
                """
                await session.run(query, {
                    "product_id": product.product_id,
                    "dim_id": dim,
                    "strength": score,
                })
                count += 1
        
        # Link customer types to their primary dimensions
        for ct in self.customer_types.values():
            for dim, strength in ct.primary_dimensions:
                query = """
                MATCH (ct:CustomerTypeGranular {type_id: $type_id})
                MATCH (d:PsychDimension {dimension_id: $dim_id})
                MERGE (ct)-[r:DEFINED_BY]->(d)
                SET r.importance = $importance
                """
                await session.run(query, {
                    "type_id": ct.type_id,
                    "dim_id": dim,
                    "importance": strength,
                })
                count += 1
            
            # Link customer types to products they're attracted to
            for product_id in ct.attracted_to_products[:20]:  # Limit connections
                query = """
                MATCH (ct:CustomerTypeGranular {type_id: $type_id})
                MATCH (p:ProductPsychProfile {product_id: $product_id})
                MERGE (ct)-[r:ATTRACTED_TO]->(p)
                """
                await session.run(query, {
                    "type_id": ct.type_id,
                    "product_id": product_id,
                })
                count += 1
        
        return count
    
    def find_similar_products(
        self, 
        brand: str, 
        product_name: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 20
    ) -> List[Tuple[ProductPsychProfile, float]]:
        """
        Find similar products using relaxed matching.
        
        This is the key function for "when someone enters a brand and a product,
        the system searches for learnings" with relaxed matching.
        """
        results = []
        
        brand_lower = brand.lower()
        product_lower = product_name.lower() if product_name else ""
        
        for product in self.products.values():
            score = 0.0
            
            # Brand match (highest weight)
            if brand_lower in product.brand.lower():
                score += 0.5
            elif any(word in product.brand.lower() for word in brand_lower.split()):
                score += 0.3
            
            # Product name match
            if product_lower and product_lower in product.product_name.lower():
                score += 0.3
            elif product_lower and any(word in product.product_name.lower() for word in product_lower.split()):
                score += 0.2
            
            # Category match
            if category and category.lower() in product.category.lower():
                score += 0.2
            
            if score > 0:
                results.append((product, score))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: -x[1])
        return results[:top_k]
    
    def get_aggregated_profile(
        self, 
        products: List[ProductPsychProfile]
    ) -> Dict[str, Any]:
        """
        Aggregate psychological profiles across multiple similar products.
        
        This combines the learnings from similar products to create a
        comprehensive psychological profile for persuasion.
        """
        if not products:
            return {}
        
        # Aggregate archetype scores
        archetype_totals = defaultdict(float)
        framework_totals = defaultdict(float)
        dimension_totals = defaultdict(float)
        
        total_reviews = 0
        
        for product in products:
            weight = product.review_count or 1
            total_reviews += weight
            
            for arch, score in product.archetype_scores.items():
                archetype_totals[arch] += score * weight
            
            for fw, score in product.framework_scores.items():
                framework_totals[fw] += score * weight
            
            for dim, score in product.dimension_scores.items():
                dimension_totals[dim] += score * weight
        
        # Normalize
        if total_reviews > 0:
            archetype_totals = {k: v / total_reviews for k, v in archetype_totals.items()}
            framework_totals = {k: v / total_reviews for k, v in framework_totals.items()}
            dimension_totals = {k: v / total_reviews for k, v in dimension_totals.items()}
        
        return {
            "archetype_distribution": dict(archetype_totals),
            "framework_profile": dict(sorted(framework_totals.items(), key=lambda x: -x[1])[:30]),
            "dimension_profile": dict(sorted(dimension_totals.items(), key=lambda x: -x[1])[:50]),
            "products_aggregated": len(products),
            "total_reviews": total_reviews,
        }


async def main():
    """Test the embedder"""
    embedder = ReviewLearningsEmbedder()
    
    # Load all learnings
    print("Loading learnings...")
    stats = await embedder.load_all_learnings()
    print(f"Loaded: {stats}")
    
    # Derive customer types
    print("\nDeriving customer types...")
    types = embedder.derive_customer_types(min_products=5)
    print(f"Derived {len(types)} customer types")
    
    # Test similarity search
    print("\nTesting similarity search for 'Nike'...")
    similar = embedder.find_similar_products("Nike", category="Sports")
    for product, score in similar[:5]:
        print(f"  {product.product_name} ({product.category}): {score:.2f}")
    
    # Get aggregated profile
    if similar:
        products = [p for p, _ in similar[:10]]
        profile = embedder.get_aggregated_profile(products)
        print(f"\nAggregated profile from {profile['products_aggregated']} products:")
        print(f"  Archetypes: {profile['archetype_distribution']}")
        print(f"  Top frameworks: {list(profile['framework_profile'].keys())[:5]}")


if __name__ == "__main__":
    asyncio.run(main())
