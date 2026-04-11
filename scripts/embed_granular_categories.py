#!/usr/bin/env python3
"""
Granular Category Embedder

Embeds the ACTUAL category granularity from our data:
- 3,552 Google Maps business categories (per state)
- 1,267 Yelp business categories  
- 315 Steam games (individual products)
- 142 Sephora brands
- 32 Sephora demographic segments
- 33 Amazon product categories

Creates hierarchical relationships:
  Domain > SubDomain > Category > SubCategory

Plus preserves 252 dimension-level data per category.
"""

import asyncio
import json
import logging
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "learning"
MULTI_DOMAIN_DIR = DATA_DIR / "multi_domain"
GOOGLE_MAPS_DIR = DATA_DIR / "google_maps"


# Category hierarchy mappings
CATEGORY_HIERARCHY = {
    # Google Maps / Yelp category patterns -> domain hierarchy
    "restaurant": ("local_business", "food", "restaurant"),
    "cafe": ("local_business", "food", "cafe"),
    "bar": ("local_business", "food", "bar"),
    "food": ("local_business", "food", "general"),
    
    "doctor": ("local_business", "health", "medical"),
    "dentist": ("local_business", "health", "dental"),
    "hospital": ("local_business", "health", "hospital"),
    "clinic": ("local_business", "health", "clinic"),
    "therapist": ("local_business", "health", "therapy"),
    
    "auto": ("local_business", "automotive", "general"),
    "car": ("local_business", "automotive", "vehicle"),
    "mechanic": ("local_business", "automotive", "repair"),
    "dealer": ("local_business", "automotive", "sales"),
    
    "salon": ("local_business", "beauty", "salon"),
    "spa": ("local_business", "beauty", "spa"),
    "nail": ("local_business", "beauty", "nail"),
    
    "store": ("local_business", "retail", "store"),
    "shop": ("local_business", "retail", "shop"),
    "market": ("local_business", "retail", "market"),
    
    "hotel": ("local_business", "travel", "lodging"),
    "lodge": ("local_business", "travel", "lodging"),
    
    "gym": ("local_business", "fitness", "gym"),
    "fitness": ("local_business", "fitness", "general"),
    
    "church": ("local_business", "religious", "church"),
    "temple": ("local_business", "religious", "temple"),
    "mosque": ("local_business", "religious", "mosque"),
    
    "school": ("local_business", "education", "school"),
    "university": ("local_business", "education", "university"),
    
    "attorney": ("local_business", "professional", "legal"),
    "lawyer": ("local_business", "professional", "legal"),
    "accountant": ("local_business", "professional", "financial"),
    "consultant": ("local_business", "professional", "consulting"),
}

# Amazon category -> domain hierarchy
AMAZON_HIERARCHY = {
    "All_Beauty": ("ecommerce", "beauty", "general"),
    "Beauty_and_Personal_Care": ("ecommerce", "beauty", "personal_care"),
    "Electronics": ("ecommerce", "technology", "electronics"),
    "Cell_Phones_and_Accessories": ("ecommerce", "technology", "mobile"),
    "Home_and_Kitchen": ("ecommerce", "home", "general"),
    "Appliances": ("ecommerce", "home", "appliances"),
    "Clothing_Shoes_and_Jewelry": ("ecommerce", "fashion", "general"),
    "Amazon_Fashion": ("ecommerce", "fashion", "amazon_fashion"),
    "Books": ("ecommerce", "media", "books"),
    "Movies_and_TV": ("ecommerce", "media", "video"),
    "Digital_Music": ("ecommerce", "media", "music"),
    "CDs_and_Vinyl": ("ecommerce", "media", "music_physical"),
    "Kindle_Store": ("ecommerce", "media", "digital_books"),
    "Toys_and_Games": ("ecommerce", "entertainment", "toys"),
    "Sports_and_Outdoors": ("ecommerce", "lifestyle", "sports"),
    "Pet_Supplies": ("ecommerce", "lifestyle", "pets"),
    "Baby_Products": ("ecommerce", "family", "baby"),
    "Grocery_and_Gourmet_Food": ("ecommerce", "food", "grocery"),
    "Health_and_Household": ("ecommerce", "health", "general"),
    "Health_and_Personal_Care": ("ecommerce", "health", "personal_care"),
    "Tools_and_Home_Improvement": ("ecommerce", "home", "tools"),
    "Patio_Lawn_and_Garden": ("ecommerce", "home", "outdoor"),
    "Automotive": ("ecommerce", "automotive", "general"),
    "Office_Products": ("ecommerce", "business", "office"),
    "Industrial_and_Scientific": ("ecommerce", "business", "industrial"),
    "Musical_Instruments": ("ecommerce", "entertainment", "music"),
    "Arts_Crafts_and_Sewing": ("ecommerce", "hobby", "crafts"),
    "Handmade_Products": ("ecommerce", "hobby", "handmade"),
    "Software": ("ecommerce", "technology", "software"),
    "Gift_Cards": ("ecommerce", "general", "gift_cards"),
    "Magazine_Subscriptions": ("ecommerce", "media", "magazines"),
    "Subscription_Boxes": ("ecommerce", "general", "subscriptions"),
}


@dataclass
class CategoryNode:
    """A granular category with full psychological profile"""
    category_id: str
    name: str
    source: str  # google_maps, yelp, amazon, steam, sephora
    
    # Hierarchy
    domain: str
    subdomain: str
    category_type: str
    
    # Psychological profile (252 dimensions)
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    review_count: int = 0
    state: str = None  # For location-based categories
    
    def to_neo4j_props(self) -> Dict[str, Any]:
        props = {
            "category_id": self.category_id,
            "name": self.name,
            "source": self.source,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "category_type": self.category_type,
            "review_count": self.review_count,
        }
        if self.state:
            props["state"] = self.state
            
        # Add archetype scores
        for arch, score in self.archetype_scores.items():
            props[f"arch_{arch}"] = score
            
        # Add top 30 dimension scores
        top_dims = sorted(self.dimension_scores.items(), key=lambda x: -x[1])[:30]
        for dim, score in top_dims:
            safe_dim = dim.replace(".", "_")[:50]
            props[f"dim_{safe_dim}"] = score
            
        return props


@dataclass  
class ProductNode:
    """An individual product/brand with psychological profile"""
    product_id: str
    name: str
    source: str
    category: str
    
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    
    # Domain-specific attributes
    domain_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_neo4j_props(self) -> Dict[str, Any]:
        props = {
            "product_id": self.product_id,
            "name": self.name,
            "source": self.source,
            "category": self.category,
        }
        for arch, score in self.archetype_scores.items():
            props[f"arch_{arch}"] = score
        for k, v in self.domain_attributes.items():
            if isinstance(v, (int, float, str, bool)):
                props[k] = v
        return props


@dataclass
class DemographicSegment:
    """A demographic segment (from Sephora)"""
    segment_id: str
    segment_type: str  # skin_type, eye_color, hair_color, skin_tone
    value: str  # dry, brown, black, etc.
    
    archetype_distribution: Dict[str, float] = field(default_factory=dict)
    dimension_scores: Dict[str, float] = field(default_factory=dict)


class GranularEmbedder:
    """Embeds actual category granularity to Neo4j"""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j", 
                 neo4j_password: str = "atomofthought"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        
        # Data stores
        self.categories: Dict[str, CategoryNode] = {}
        self.products: Dict[str, ProductNode] = {}
        self.demographics: Dict[str, DemographicSegment] = {}
        self.dimension_totals: Dict[str, float] = {}
        
    async def connect(self) -> bool:
        try:
            from neo4j import AsyncGraphDatabase
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info(f"Connected to Neo4j")
            return True
        except Exception as e:
            logger.warning(f"Could not connect: {e}")
            return False
    
    async def close(self):
        if self.driver:
            await self.driver.close()
    
    # =========================================================================
    # LOADING
    # =========================================================================
    
    def load_all_sources(self) -> Dict[str, int]:
        """Load all sources with full granularity"""
        stats = {"categories": 0, "products": 0, "demographics": 0}
        
        # Load Google Maps categories (per state)
        stats["categories"] += self._load_google_maps_categories()
        
        # Load Yelp categories
        stats["categories"] += self._load_yelp_categories()
        
        # Load Steam games as products
        stats["products"] += self._load_steam_products()
        
        # Load Sephora brands and demographics
        brand_count, demo_count = self._load_sephora()
        stats["products"] += brand_count
        stats["demographics"] = demo_count
        
        # Load Amazon category profiles
        stats["categories"] += self._load_amazon_categories()
        
        return stats
    
    def _load_google_maps_categories(self) -> int:
        """Load all Google Maps categories with state context"""
        count = 0
        
        if not GOOGLE_MAPS_DIR.exists():
            return 0
        
        for checkpoint in GOOGLE_MAPS_DIR.glob("checkpoint_google_*.json"):
            state = checkpoint.stem.replace("checkpoint_google_", "")
            
            with open(checkpoint) as f:
                data = json.load(f)
            
            cat_profiles = data.get("category_customer_profiles", {})
            dim_totals = data.get("dimension_totals", {})
            
            for cat_name, profile in cat_profiles.items():
                # Determine hierarchy
                hierarchy = self._classify_category(cat_name)
                
                cat_id = f"gm_{state}_{self._safe_id(cat_name)}"
                
                self.categories[cat_id] = CategoryNode(
                    category_id=cat_id,
                    name=cat_name,
                    source="google_maps",
                    domain=hierarchy[0],
                    subdomain=hierarchy[1],
                    category_type=hierarchy[2],
                    archetype_scores=profile if isinstance(profile, dict) else {},
                    state=state,
                )
                count += 1
            
            # Aggregate dimension totals
            for dim, val in dim_totals.items():
                self.dimension_totals[dim] = self.dimension_totals.get(dim, 0) + val
        
        logger.info(f"Loaded {count} Google Maps categories")
        return count
    
    def _load_yelp_categories(self) -> int:
        """Load Yelp business categories"""
        filepath = MULTI_DOMAIN_DIR / "checkpoint_yelp_reviews.json"
        if not filepath.exists():
            return 0
        
        with open(filepath) as f:
            data = json.load(f)
        
        count = 0
        cat_profiles = data.get("category_profiles", {})
        dim_totals = data.get("dimension_totals", {})
        
        for cat_name, profile in cat_profiles.items():
            hierarchy = self._classify_category(cat_name)
            cat_id = f"yelp_{self._safe_id(cat_name)}"
            
            self.categories[cat_id] = CategoryNode(
                category_id=cat_id,
                name=cat_name,
                source="yelp",
                domain=hierarchy[0],
                subdomain=hierarchy[1],
                category_type=hierarchy[2],
                archetype_scores=profile if isinstance(profile, dict) else {},
            )
            count += 1
        
        # Aggregate dimensions
        for dim, val in dim_totals.items():
            self.dimension_totals[dim] = self.dimension_totals.get(dim, 0) + val
        
        logger.info(f"Loaded {count} Yelp categories")
        return count
    
    def _load_steam_products(self) -> int:
        """Load individual Steam games as products"""
        filepath = MULTI_DOMAIN_DIR / "checkpoint_steam_gaming.json"
        if not filepath.exists():
            return 0
        
        with open(filepath) as f:
            data = json.load(f)
        
        count = 0
        games = data.get("brand_customer_profiles", {})
        domain_specific = data.get("domain_specific", {})
        dim_totals = data.get("dimension_totals", {})
        
        # Extract gamer archetypes
        gamer_archetypes = domain_specific.get("gamer_archetypes", {})
        
        for game_name, profile in games.items():
            game_id = f"steam_{self._safe_id(game_name)}"
            
            self.products[game_id] = ProductNode(
                product_id=game_id,
                name=game_name,
                source="steam",
                category="video_games",
                archetype_scores=profile if isinstance(profile, dict) else {},
                domain_attributes={
                    "platform": "pc",
                    "domain": "gaming",
                }
            )
            count += 1
        
        # Aggregate dimensions
        for dim, val in dim_totals.items():
            self.dimension_totals[dim] = self.dimension_totals.get(dim, 0) + val
        
        logger.info(f"Loaded {count} Steam games")
        return count
    
    def _load_sephora(self) -> Tuple[int, int]:
        """Load Sephora brands and demographic segments"""
        filepath = MULTI_DOMAIN_DIR / "checkpoint_sephora_beauty.json"
        if not filepath.exists():
            return 0, 0
        
        with open(filepath) as f:
            data = json.load(f)
        
        brand_count = 0
        demo_count = 0
        
        # Load brands
        brands = data.get("brand_customer_profiles", {})
        for brand_name, profile in brands.items():
            brand_id = f"sephora_{self._safe_id(brand_name)}"
            
            self.products[brand_id] = ProductNode(
                product_id=brand_id,
                name=brand_name,
                source="sephora",
                category="beauty",
                archetype_scores=profile if isinstance(profile, dict) else {},
                domain_attributes={"domain": "beauty"}
            )
            brand_count += 1
        
        # Load demographics
        domain_specific = data.get("domain_specific", {})
        for seg_key, seg_data in domain_specific.items():
            if seg_key.startswith("demo_"):
                # Parse segment type and value
                parts = seg_key.replace("demo_", "").split("_")
                seg_type = parts[0] + "_" + parts[1] if len(parts) > 1 else parts[0]
                value = "_".join(parts[2:]) if len(parts) > 2 else parts[-1]
                
                self.demographics[seg_key] = DemographicSegment(
                    segment_id=seg_key,
                    segment_type=seg_type,
                    value=value,
                    archetype_distribution=seg_data if isinstance(seg_data, dict) else {},
                )
                demo_count += 1
        
        # Aggregate dimensions
        for dim, val in data.get("dimension_totals", {}).items():
            self.dimension_totals[dim] = self.dimension_totals.get(dim, 0) + val
        
        logger.info(f"Loaded {brand_count} Sephora brands, {demo_count} demographics")
        return brand_count, demo_count
    
    def _load_amazon_categories(self) -> int:
        """Load Amazon category profiles"""
        count = 0
        
        for checkpoint in DATA_DIR.glob("checkpoint_*.json"):
            if "google" in checkpoint.name.lower() or "multi_domain" in str(checkpoint):
                continue
            
            try:
                # Read just first 1000 chars to get category name (avoid loading huge files)
                with open(checkpoint) as f:
                    header = f.read(5000)
                
                # Parse category
                if '"category":' in header:
                    start = header.find('"category":') + 12
                    end = header.find('"', start + 1)
                    cat_name = header[start:end].strip('"')
                else:
                    cat_name = checkpoint.stem.replace("checkpoint_", "")
                
                hierarchy = AMAZON_HIERARCHY.get(cat_name, ("ecommerce", "general", cat_name.lower()))
                cat_id = f"amazon_{self._safe_id(cat_name)}"
                
                self.categories[cat_id] = CategoryNode(
                    category_id=cat_id,
                    name=cat_name,
                    source="amazon",
                    domain=hierarchy[0],
                    subdomain=hierarchy[1],
                    category_type=hierarchy[2],
                )
                count += 1
                
            except Exception as e:
                logger.warning(f"Error loading {checkpoint}: {e}")
        
        logger.info(f"Loaded {count} Amazon categories")
        return count
    
    def _classify_category(self, category_name: str) -> Tuple[str, str, str]:
        """Classify a category name into hierarchy"""
        name_lower = category_name.lower()
        
        for pattern, hierarchy in CATEGORY_HIERARCHY.items():
            if pattern in name_lower:
                return hierarchy
        
        # Default classification based on common words
        if any(x in name_lower for x in ["restaurant", "food", "cafe", "bar", "pizza", "burger", "sushi"]):
            return ("local_business", "food", "restaurant")
        elif any(x in name_lower for x in ["doctor", "medical", "health", "clinic"]):
            return ("local_business", "health", "medical")
        elif any(x in name_lower for x in ["store", "shop", "retail"]):
            return ("local_business", "retail", "store")
        else:
            return ("local_business", "other", "general")
    
    def _safe_id(self, name: str) -> str:
        """Create safe ID from name"""
        return re.sub(r'[^a-z0-9]', '_', name.lower())[:50]
    
    # =========================================================================
    # NEO4J EMBEDDING
    # =========================================================================
    
    async def embed_to_neo4j(self) -> Dict[str, int]:
        """Embed all granular data to Neo4j"""
        if not self.driver:
            return self._save_to_json()
        
        stats = {"categories": 0, "products": 0, "demographics": 0, "dimensions": 0, "relationships": 0}
        
        async with self.driver.session() as session:
            # Create schema
            await self._create_schema(session)
            
            # Create category nodes
            stats["categories"] = await self._create_categories(session)
            
            # Create product nodes
            stats["products"] = await self._create_products(session)
            
            # Create demographic nodes
            stats["demographics"] = await self._create_demographics(session)
            
            # Create dimension nodes
            stats["dimensions"] = await self._create_dimensions(session)
            
            # Create hierarchy relationships
            stats["relationships"] = await self._create_relationships(session)
        
        logger.info(f"Embedded: {stats}")
        return stats
    
    async def _create_schema(self, session):
        """Create Neo4j schema"""
        constraints = [
            "CREATE CONSTRAINT cat_granular_id IF NOT EXISTS FOR (c:CategoryGranular) REQUIRE c.category_id IS UNIQUE",
            "CREATE CONSTRAINT product_granular_id IF NOT EXISTS FOR (p:ProductGranular) REQUIRE p.product_id IS UNIQUE",
            "CREATE CONSTRAINT demo_segment_id IF NOT EXISTS FOR (d:DemographicSegment) REQUIRE d.segment_id IS UNIQUE",
            "CREATE CONSTRAINT psych_dim_id IF NOT EXISTS FOR (pd:PsychDimension) REQUIRE pd.dimension_id IS UNIQUE",
            "CREATE CONSTRAINT domain_hierarchy_id IF NOT EXISTS FOR (dh:DomainHierarchy) REQUIRE dh.hierarchy_id IS UNIQUE",
            
            "CREATE INDEX cat_source IF NOT EXISTS FOR (c:CategoryGranular) ON (c.source)",
            "CREATE INDEX cat_domain IF NOT EXISTS FOR (c:CategoryGranular) ON (c.domain)",
            "CREATE INDEX cat_subdomain IF NOT EXISTS FOR (c:CategoryGranular) ON (c.subdomain)",
            "CREATE INDEX cat_state IF NOT EXISTS FOR (c:CategoryGranular) ON (c.state)",
            "CREATE INDEX prod_source IF NOT EXISTS FOR (p:ProductGranular) ON (p.source)",
        ]
        
        for c in constraints:
            try:
                await session.run(c)
            except:
                pass
    
    async def _create_categories(self, session) -> int:
        """Create category nodes"""
        count = 0
        batch_size = 500
        
        categories_list = list(self.categories.values())
        
        for i in range(0, len(categories_list), batch_size):
            batch = categories_list[i:i + batch_size]
            
            query = """
            UNWIND $categories AS cat
            MERGE (c:CategoryGranular {category_id: cat.category_id})
            SET c.name = cat.name,
                c.source = cat.source,
                c.domain = cat.domain,
                c.subdomain = cat.subdomain,
                c.category_type = cat.category_type,
                c.state = cat.state,
                c.arch_achiever = cat.arch_achiever,
                c.arch_explorer = cat.arch_explorer,
                c.arch_connector = cat.arch_connector,
                c.arch_guardian = cat.arch_guardian,
                c.arch_pragmatist = cat.arch_pragmatist
            """
            
            cat_data = []
            for cat in batch:
                props = cat.to_neo4j_props()
                # Ensure archetype scores exist
                for arch in ['achiever', 'explorer', 'connector', 'guardian', 'pragmatist']:
                    if f'arch_{arch}' not in props:
                        props[f'arch_{arch}'] = cat.archetype_scores.get(arch, 0.0)
                cat_data.append(props)
            
            await session.run(query, {"categories": cat_data})
            count += len(batch)
            
            if count % 5000 == 0:
                logger.info(f"Created {count} categories...")
        
        return count
    
    async def _create_products(self, session) -> int:
        """Create product nodes"""
        count = 0
        batch_size = 500
        
        products_list = list(self.products.values())
        
        for i in range(0, len(products_list), batch_size):
            batch = products_list[i:i + batch_size]
            
            query = """
            UNWIND $products AS prod
            MERGE (p:ProductGranular {product_id: prod.product_id})
            SET p.name = prod.name,
                p.source = prod.source,
                p.category = prod.category,
                p.arch_achiever = prod.arch_achiever,
                p.arch_explorer = prod.arch_explorer,
                p.arch_connector = prod.arch_connector,
                p.arch_guardian = prod.arch_guardian,
                p.arch_pragmatist = prod.arch_pragmatist
            """
            
            prod_data = []
            for prod in batch:
                props = prod.to_neo4j_props()
                for arch in ['achiever', 'explorer', 'connector', 'guardian', 'pragmatist']:
                    if f'arch_{arch}' not in props:
                        props[f'arch_{arch}'] = prod.archetype_scores.get(arch, 0.0)
                prod_data.append(props)
            
            await session.run(query, {"products": prod_data})
            count += len(batch)
        
        return count
    
    async def _create_demographics(self, session) -> int:
        """Create demographic segment nodes"""
        count = 0
        
        for demo in self.demographics.values():
            query = """
            MERGE (d:DemographicSegment {segment_id: $segment_id})
            SET d.segment_type = $segment_type,
                d.value = $value
            """
            
            await session.run(query, {
                "segment_id": demo.segment_id,
                "segment_type": demo.segment_type,
                "value": demo.value,
            })
            count += 1
        
        return count
    
    async def _create_dimensions(self, session) -> int:
        """Create psychological dimension nodes"""
        count = 0
        
        # Group dimensions by framework
        for dim, total in self.dimension_totals.items():
            if total < 1000:  # Skip low-signal dimensions
                continue
            
            parts = dim.split(".")
            framework = parts[0] if parts else dim
            
            query = """
            MERGE (pd:PsychDimension {dimension_id: $dim_id})
            SET pd.framework = $framework,
                pd.full_name = $full_name,
                pd.total_signal = $total
            """
            
            await session.run(query, {
                "dim_id": dim,
                "framework": framework,
                "full_name": dim,
                "total": total,
            })
            count += 1
        
        return count
    
    async def _create_relationships(self, session) -> int:
        """Create hierarchy relationships"""
        count = 0
        
        # Create domain hierarchy nodes
        domains = set()
        subdomains = set()
        
        for cat in self.categories.values():
            domains.add(cat.domain)
            subdomains.add((cat.domain, cat.subdomain))
        
        # Create domain nodes
        for domain in domains:
            await session.run("""
                MERGE (dh:DomainHierarchy {hierarchy_id: $id})
                SET dh.level = 'domain', dh.name = $name
            """, {"id": f"domain_{domain}", "name": domain})
            count += 1
        
        # Create subdomain nodes and link to domains
        for domain, subdomain in subdomains:
            await session.run("""
                MERGE (dh:DomainHierarchy {hierarchy_id: $id})
                SET dh.level = 'subdomain', dh.name = $name
            """, {"id": f"subdomain_{domain}_{subdomain}", "name": subdomain})
            
            await session.run("""
                MATCH (d:DomainHierarchy {hierarchy_id: $domain_id})
                MATCH (sd:DomainHierarchy {hierarchy_id: $subdomain_id})
                MERGE (sd)-[:PART_OF]->(d)
            """, {
                "domain_id": f"domain_{domain}",
                "subdomain_id": f"subdomain_{domain}_{subdomain}"
            })
            count += 2
        
        # Link categories to subdomains
        for cat in self.categories.values():
            await session.run("""
                MATCH (c:CategoryGranular {category_id: $cat_id})
                MATCH (sd:DomainHierarchy {hierarchy_id: $subdomain_id})
                MERGE (c)-[:IN_SUBDOMAIN]->(sd)
            """, {
                "cat_id": cat.category_id,
                "subdomain_id": f"subdomain_{cat.domain}_{cat.subdomain}"
            })
            count += 1
        
        return count
    
    def _save_to_json(self) -> Dict[str, int]:
        """Save to JSON if Neo4j not available"""
        output_dir = DATA_DIR / "granular_export"
        output_dir.mkdir(exist_ok=True)
        
        with open(output_dir / "categories.json", 'w') as f:
            json.dump(
                {c.category_id: c.to_neo4j_props() for c in self.categories.values()},
                f, indent=2
            )
        
        with open(output_dir / "products.json", 'w') as f:
            json.dump(
                {p.product_id: p.to_neo4j_props() for p in self.products.values()},
                f, indent=2
            )
        
        logger.info(f"Saved to {output_dir}")
        return {
            "categories": len(self.categories),
            "products": len(self.products),
            "demographics": len(self.demographics),
        }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="atomofthought")
    args = parser.parse_args()
    
    embedder = GranularEmbedder(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )
    
    print("=" * 70)
    print("GRANULAR CATEGORY EMBEDDER")
    print("=" * 70)
    
    print("\n1. Loading all sources with full granularity...")
    stats = embedder.load_all_sources()
    
    print(f"\n   Categories loaded: {stats['categories']:,}")
    print(f"   Products loaded: {stats['products']:,}")
    print(f"   Demographics loaded: {stats['demographics']}")
    print(f"   Dimensions tracked: {len(embedder.dimension_totals)}")
    
    print("\n2. Connecting to Neo4j...")
    connected = await embedder.connect()
    
    print("\n3. Embedding to Neo4j...")
    embed_stats = await embedder.embed_to_neo4j()
    
    await embedder.close()
    
    print("\n" + "=" * 70)
    print("EMBEDDING COMPLETE")
    print("=" * 70)
    print(f"\nCategories: {embed_stats['categories']:,}")
    print(f"Products: {embed_stats['products']:,}")
    print(f"Demographics: {embed_stats['demographics']}")
    print(f"Dimensions: {embed_stats['dimensions']}")
    print(f"Relationships: {embed_stats['relationships']:,}")


if __name__ == "__main__":
    asyncio.run(main())
