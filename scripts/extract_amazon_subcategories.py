#!/usr/bin/env python3
"""
Amazon Sub-Category Extractor

Extracts the FULL 6-level category hierarchy from Amazon meta files.
Creates:
- Category nodes at each level
- Category paths (full hierarchy)
- Links between levels

Example hierarchy:
  Electronics > Computers & Accessories > Computer Components > 
  Internal Components > Memory > Memory Card Readers

Usage:
    python3 scripts/extract_amazon_subcategories.py
"""

import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass, field
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
AMAZON_DIR = BASE_DIR / "amazon"
DATA_DIR = BASE_DIR / "data" / "learning"


@dataclass
class CategoryLevel:
    """A category at a specific level in the hierarchy"""
    name: str
    level: int
    parent_path: str  # Path to parent (e.g., "Electronics > Computers")
    full_path: str    # Full path including this category
    product_count: int = 0
    child_categories: Set[str] = field(default_factory=set)
    
    def to_neo4j_props(self) -> Dict[str, Any]:
        return {
            "category_id": f"amazon_{self.full_path.replace(' > ', '_').replace(' ', '_')[:100]}",
            "name": self.name,
            "level": self.level,
            "full_path": self.full_path,
            "parent_path": self.parent_path,
            "product_count": self.product_count,
        }


@dataclass
class CategoryPath:
    """A complete category path from root to leaf"""
    path: str         # "Electronics > Computers > Components > Memory"
    levels: List[str] # ["Electronics", "Computers", "Components", "Memory"]
    depth: int
    product_count: int = 0
    main_category: str = ""  # Top-level Amazon category file
    
    def to_neo4j_props(self) -> Dict[str, Any]:
        return {
            "path_id": f"amazon_path_{self.path.replace(' > ', '_').replace(' ', '_')[:100]}",
            "full_path": self.path,
            "depth": self.depth,
            "product_count": self.product_count,
            "main_category": self.main_category,
            "level_0": self.levels[0] if len(self.levels) > 0 else "",
            "level_1": self.levels[1] if len(self.levels) > 1 else "",
            "level_2": self.levels[2] if len(self.levels) > 2 else "",
            "level_3": self.levels[3] if len(self.levels) > 3 else "",
            "level_4": self.levels[4] if len(self.levels) > 4 else "",
            "level_5": self.levels[5] if len(self.levels) > 5 else "",
        }


class AmazonSubcategoryExtractor:
    """Extracts and embeds Amazon's full category hierarchy"""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "atomofthought"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        
        # Data stores
        self.category_levels: Dict[str, CategoryLevel] = {}  # full_path -> CategoryLevel
        self.category_paths: Dict[str, CategoryPath] = {}    # path -> CategoryPath
        self.level_stats: Dict[int, int] = defaultdict(int)  # level -> count
        
    async def connect(self) -> bool:
        try:
            from neo4j import AsyncGraphDatabase
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            logger.info("Connected to Neo4j")
            return True
        except Exception as e:
            logger.warning(f"Could not connect: {e}")
            return False
    
    async def close(self):
        if self.driver:
            await self.driver.close()
    
    def extract_from_all_meta_files(self) -> Dict[str, int]:
        """Extract categories from all Amazon meta files"""
        stats = {"files": 0, "products": 0, "paths": 0, "levels": 0}
        
        meta_files = list(AMAZON_DIR.glob("meta_*.jsonl"))
        logger.info(f"Found {len(meta_files)} meta files")
        
        for meta_file in meta_files:
            main_category = meta_file.stem.replace("meta_", "")
            logger.info(f"Processing {main_category}...")
            
            file_products = self._extract_from_file(meta_file, main_category)
            stats["products"] += file_products
            stats["files"] += 1
            
            logger.info(f"  {main_category}: {file_products:,} products, "
                       f"{len(self.category_paths):,} total paths")
        
        stats["paths"] = len(self.category_paths)
        stats["levels"] = len(self.category_levels)
        
        # Log level distribution
        logger.info("\nCategory distribution by level:")
        for level in sorted(self.level_stats.keys()):
            logger.info(f"  Level {level}: {self.level_stats[level]:,} unique categories")
        
        return stats
    
    def _extract_from_file(self, meta_file: Path, main_category: str) -> int:
        """Extract categories from a single meta file"""
        product_count = 0
        
        with open(meta_file) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    categories = data.get("categories", [])
                    
                    if categories:
                        self._process_category_hierarchy(categories, main_category)
                        product_count += 1
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    continue
        
        return product_count
    
    def _process_category_hierarchy(self, categories: List[str], main_category: str):
        """Process a single product's category hierarchy"""
        if not categories:
            return
        
        # Create the full path
        full_path = " > ".join(categories)
        
        # Track the path
        if full_path not in self.category_paths:
            self.category_paths[full_path] = CategoryPath(
                path=full_path,
                levels=categories,
                depth=len(categories),
                product_count=0,
                main_category=main_category
            )
        self.category_paths[full_path].product_count += 1
        
        # Track each level
        for level, cat_name in enumerate(categories):
            parent_path = " > ".join(categories[:level]) if level > 0 else ""
            level_path = " > ".join(categories[:level + 1])
            
            if level_path not in self.category_levels:
                self.category_levels[level_path] = CategoryLevel(
                    name=cat_name,
                    level=level,
                    parent_path=parent_path,
                    full_path=level_path,
                    product_count=0
                )
                self.level_stats[level] += 1
            
            self.category_levels[level_path].product_count += 1
            
            # Track child relationship
            if level > 0 and parent_path in self.category_levels:
                self.category_levels[parent_path].child_categories.add(cat_name)
    
    async def embed_to_neo4j(self) -> Dict[str, int]:
        """Embed extracted categories to Neo4j"""
        if not self.driver:
            return self._save_to_json()
        
        stats = {"category_levels": 0, "category_paths": 0, "relationships": 0}
        
        async with self.driver.session() as session:
            # Create schema
            await self._create_schema(session)
            
            # Create category level nodes
            stats["category_levels"] = await self._create_category_levels(session)
            
            # Create category path nodes
            stats["category_paths"] = await self._create_category_paths(session)
            
            # Create hierarchy relationships
            stats["relationships"] = await self._create_hierarchy_relationships(session)
        
        return stats
    
    async def _create_schema(self, session):
        """Create Neo4j schema for Amazon categories"""
        constraints = [
            "CREATE CONSTRAINT amazon_cat_level_id IF NOT EXISTS FOR (c:AmazonCategoryLevel) REQUIRE c.category_id IS UNIQUE",
            "CREATE CONSTRAINT amazon_cat_path_id IF NOT EXISTS FOR (p:AmazonCategoryPath) REQUIRE p.path_id IS UNIQUE",
            "CREATE INDEX amazon_cat_level IF NOT EXISTS FOR (c:AmazonCategoryLevel) ON (c.level)",
            "CREATE INDEX amazon_cat_name IF NOT EXISTS FOR (c:AmazonCategoryLevel) ON (c.name)",
            "CREATE INDEX amazon_path_main_cat IF NOT EXISTS FOR (p:AmazonCategoryPath) ON (p.main_category)",
            "CREATE INDEX amazon_path_depth IF NOT EXISTS FOR (p:AmazonCategoryPath) ON (p.depth)",
        ]
        
        for c in constraints:
            try:
                await session.run(c)
            except:
                pass
    
    async def _create_category_levels(self, session) -> int:
        """Create category level nodes"""
        count = 0
        batch_size = 1000
        
        levels_list = list(self.category_levels.values())
        
        for i in range(0, len(levels_list), batch_size):
            batch = levels_list[i:i + batch_size]
            
            query = """
            UNWIND $categories AS cat
            MERGE (c:AmazonCategoryLevel {category_id: cat.category_id})
            SET c.name = cat.name,
                c.level = cat.level,
                c.full_path = cat.full_path,
                c.parent_path = cat.parent_path,
                c.product_count = cat.product_count
            """
            
            await session.run(query, {
                "categories": [c.to_neo4j_props() for c in batch]
            })
            count += len(batch)
            
            if count % 5000 == 0:
                logger.info(f"Created {count} category levels...")
        
        return count
    
    async def _create_category_paths(self, session) -> int:
        """Create category path nodes"""
        count = 0
        batch_size = 1000
        
        paths_list = list(self.category_paths.values())
        
        for i in range(0, len(paths_list), batch_size):
            batch = paths_list[i:i + batch_size]
            
            query = """
            UNWIND $paths AS p
            MERGE (cp:AmazonCategoryPath {path_id: p.path_id})
            SET cp.full_path = p.full_path,
                cp.depth = p.depth,
                cp.product_count = p.product_count,
                cp.main_category = p.main_category,
                cp.level_0 = p.level_0,
                cp.level_1 = p.level_1,
                cp.level_2 = p.level_2,
                cp.level_3 = p.level_3,
                cp.level_4 = p.level_4,
                cp.level_5 = p.level_5
            """
            
            await session.run(query, {
                "paths": [p.to_neo4j_props() for p in batch]
            })
            count += len(batch)
            
            if count % 5000 == 0:
                logger.info(f"Created {count} category paths...")
        
        return count
    
    async def _create_hierarchy_relationships(self, session) -> int:
        """Create parent-child relationships between category levels"""
        count = 0
        
        # Only create relationships for categories with parents
        for level_path, cat_level in self.category_levels.items():
            if cat_level.parent_path and cat_level.parent_path in self.category_levels:
                parent = self.category_levels[cat_level.parent_path]
                
                query = """
                MATCH (child:AmazonCategoryLevel {category_id: $child_id})
                MATCH (parent:AmazonCategoryLevel {category_id: $parent_id})
                MERGE (child)-[:CHILD_OF]->(parent)
                """
                
                await session.run(query, {
                    "child_id": cat_level.to_neo4j_props()["category_id"],
                    "parent_id": parent.to_neo4j_props()["category_id"]
                })
                count += 1
                
                if count % 5000 == 0:
                    logger.info(f"Created {count} relationships...")
        
        return count
    
    def _save_to_json(self) -> Dict[str, int]:
        """Save to JSON if Neo4j unavailable"""
        output_dir = DATA_DIR / "amazon_subcategories"
        output_dir.mkdir(exist_ok=True)
        
        # Save category levels
        with open(output_dir / "category_levels.json", 'w') as f:
            json.dump(
                {k: v.to_neo4j_props() for k, v in self.category_levels.items()},
                f, indent=2
            )
        
        # Save category paths
        with open(output_dir / "category_paths.json", 'w') as f:
            json.dump(
                {k: v.to_neo4j_props() for k, v in self.category_paths.items()},
                f, indent=2
            )
        
        # Save summary stats
        with open(output_dir / "extraction_stats.json", 'w') as f:
            json.dump({
                "total_paths": len(self.category_paths),
                "total_levels": len(self.category_levels),
                "level_distribution": dict(self.level_stats),
                "top_paths_by_products": sorted(
                    [(p.path, p.product_count) for p in self.category_paths.values()],
                    key=lambda x: -x[1]
                )[:100]
            }, f, indent=2)
        
        logger.info(f"Saved to {output_dir}")
        return {
            "category_levels": len(self.category_levels),
            "category_paths": len(self.category_paths),
            "relationships": 0
        }
    
    def print_summary(self):
        """Print extraction summary"""
        print("\n" + "=" * 70)
        print("AMAZON SUB-CATEGORY EXTRACTION SUMMARY")
        print("=" * 70)
        
        print(f"\nTotal unique category paths: {len(self.category_paths):,}")
        print(f"Total category nodes (all levels): {len(self.category_levels):,}")
        
        print("\n### DISTRIBUTION BY LEVEL ###")
        for level in sorted(self.level_stats.keys()):
            print(f"  Level {level}: {self.level_stats[level]:,} unique categories")
        
        print("\n### TOP 20 CATEGORY PATHS BY PRODUCT COUNT ###")
        top_paths = sorted(
            self.category_paths.values(),
            key=lambda x: -x.product_count
        )[:20]
        for p in top_paths:
            print(f"  ({p.product_count:,}) {p.path}")
        
        print("\n### SAMPLE HIERARCHY (Electronics) ###")
        electronics_paths = [p for p in self.category_paths.values() 
                           if p.levels[0] == "Electronics"][:10]
        for p in electronics_paths:
            indent = "  " * (p.depth - 1)
            print(f"{indent}└── {p.levels[-1]} ({p.product_count:,})")


async def main():
    extractor = AmazonSubcategoryExtractor()
    
    print("=" * 70)
    print("AMAZON SUB-CATEGORY EXTRACTOR")
    print("=" * 70)
    
    print("\n1. Extracting categories from all meta files...")
    stats = extractor.extract_from_all_meta_files()
    
    print(f"\n   Files processed: {stats['files']}")
    print(f"   Products scanned: {stats['products']:,}")
    print(f"   Unique category paths: {stats['paths']:,}")
    print(f"   Total category nodes: {stats['levels']:,}")
    
    extractor.print_summary()
    
    print("\n2. Connecting to Neo4j...")
    connected = await extractor.connect()
    
    print("\n3. Embedding to Neo4j...")
    embed_stats = await extractor.embed_to_neo4j()
    
    await extractor.close()
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"\nCategory Levels: {embed_stats['category_levels']:,}")
    print(f"Category Paths: {embed_stats['category_paths']:,}")
    print(f"Hierarchy Relationships: {embed_stats['relationships']:,}")


if __name__ == "__main__":
    asyncio.run(main())
