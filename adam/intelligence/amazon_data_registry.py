#!/usr/bin/env python3
"""
AMAZON DATA REGISTRY
====================

Complete registry of Amazon review and product data.

DATA STRUCTURE:
- 33 Review files: {Category}.jsonl - Customer reviews with parent_asin
- 33 Meta files: meta_{Category}.jsonl - Product metadata with parent_asin
- Co-purchase graph: amazon-meta.txt, amazon0302.txt, etc.

LINKING:
- parent_asin is THE KEY that links reviews to metadata
- Products with different colors/sizes share the same parent_asin

FILE LOCATIONS:
- Primary: /Volumes/Sped/Nocera Models/Review Data/Amazon/
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os


# =============================================================================
# CONFIGURATION
# =============================================================================

AMAZON_DATA_DIR = Path("/Volumes/Sped/Nocera Models/Review Data/Amazon")


# =============================================================================
# CATEGORY REGISTRY
# =============================================================================

class AmazonCategory(str, Enum):
    """All 33 Amazon product categories."""
    
    ALL_BEAUTY = "All_Beauty"
    AMAZON_FASHION = "Amazon_Fashion"
    APPLIANCES = "Appliances"
    ARTS_CRAFTS_AND_SEWING = "Arts_Crafts_and_Sewing"
    AUTOMOTIVE = "Automotive"
    BABY_PRODUCTS = "Baby_Products"
    BEAUTY_AND_PERSONAL_CARE = "Beauty_and_Personal_Care"
    BOOKS = "Books"
    CDS_AND_VINYL = "CDs_and_Vinyl"
    CELL_PHONES_AND_ACCESSORIES = "Cell_Phones_and_Accessories"
    CLOTHING_SHOES_AND_JEWELRY = "Clothing_Shoes_and_Jewelry"
    DIGITAL_MUSIC = "Digital_Music"
    ELECTRONICS = "Electronics"
    GIFT_CARDS = "Gift_Cards"
    GROCERY_AND_GOURMET_FOOD = "Grocery_and_Gourmet_Food"
    HANDMADE_PRODUCTS = "Handmade_Products"
    HEALTH_AND_HOUSEHOLD = "Health_and_Household"
    HEALTH_AND_PERSONAL_CARE = "Health_and_Personal_Care"
    HOME_AND_KITCHEN = "Home_and_Kitchen"
    INDUSTRIAL_AND_SCIENTIFIC = "Industrial_and_Scientific"
    KINDLE_STORE = "Kindle_Store"
    MAGAZINE_SUBSCRIPTIONS = "Magazine_Subscriptions"
    MOVIES_AND_TV = "Movies_and_TV"
    MUSICAL_INSTRUMENTS = "Musical_Instruments"
    OFFICE_PRODUCTS = "Office_Products"
    PATIO_LAWN_AND_GARDEN = "Patio_Lawn_and_Garden"
    PET_SUPPLIES = "Pet_Supplies"
    SOFTWARE = "Software"
    SPORTS_AND_OUTDOORS = "Sports_and_Outdoors"
    SUBSCRIPTION_BOXES = "Subscription_Boxes"
    TOOLS_AND_HOME_IMPROVEMENT = "Tools_and_Home_Improvement"
    TOYS_AND_GAMES = "Toys_and_Games"
    UNKNOWN = "Unknown"


# Category metadata
CATEGORY_INFO = {
    AmazonCategory.ALL_BEAUTY: {
        "display_name": "All Beauty",
        "keywords": ["beauty", "cosmetic", "makeup", "skincare"],
        "typical_archetypes": ["explorer", "caregiver", "lover"],
    },
    AmazonCategory.AMAZON_FASHION: {
        "display_name": "Amazon Fashion",
        "keywords": ["fashion", "clothing", "apparel", "style"],
        "typical_archetypes": ["explorer", "creator", "lover"],
    },
    AmazonCategory.APPLIANCES: {
        "display_name": "Appliances",
        "keywords": ["appliance", "kitchen", "home", "washer", "dryer"],
        "typical_archetypes": ["ruler", "caregiver", "everyman"],
    },
    AmazonCategory.ARTS_CRAFTS_AND_SEWING: {
        "display_name": "Arts, Crafts & Sewing",
        "keywords": ["craft", "art", "sewing", "diy", "creative"],
        "typical_archetypes": ["creator", "explorer", "innocent"],
    },
    AmazonCategory.AUTOMOTIVE: {
        "display_name": "Automotive",
        "keywords": ["car", "auto", "vehicle", "truck", "motor"],
        "typical_archetypes": ["hero", "outlaw", "ruler"],
    },
    AmazonCategory.BABY_PRODUCTS: {
        "display_name": "Baby Products",
        "keywords": ["baby", "infant", "newborn", "toddler", "child"],
        "typical_archetypes": ["caregiver", "innocent", "everyman"],
    },
    AmazonCategory.BEAUTY_AND_PERSONAL_CARE: {
        "display_name": "Beauty & Personal Care",
        "keywords": ["beauty", "personal", "care", "skin", "hair"],
        "typical_archetypes": ["lover", "caregiver", "magician"],
    },
    AmazonCategory.BOOKS: {
        "display_name": "Books",
        "keywords": ["book", "novel", "reading", "literature"],
        "typical_archetypes": ["sage", "explorer", "creator"],
    },
    AmazonCategory.CDS_AND_VINYL: {
        "display_name": "CDs & Vinyl",
        "keywords": ["music", "cd", "vinyl", "album", "record"],
        "typical_archetypes": ["creator", "explorer", "outlaw"],
    },
    AmazonCategory.CELL_PHONES_AND_ACCESSORIES: {
        "display_name": "Cell Phones & Accessories",
        "keywords": ["phone", "cell", "mobile", "smartphone", "case"],
        "typical_archetypes": ["magician", "explorer", "ruler"],
    },
    AmazonCategory.CLOTHING_SHOES_AND_JEWELRY: {
        "display_name": "Clothing, Shoes & Jewelry",
        "keywords": ["clothing", "shoes", "jewelry", "fashion", "wear"],
        "typical_archetypes": ["lover", "creator", "ruler"],
    },
    AmazonCategory.DIGITAL_MUSIC: {
        "display_name": "Digital Music",
        "keywords": ["digital", "music", "mp3", "streaming", "download"],
        "typical_archetypes": ["explorer", "creator", "outlaw"],
    },
    AmazonCategory.ELECTRONICS: {
        "display_name": "Electronics",
        "keywords": ["electronic", "tech", "gadget", "device"],
        "typical_archetypes": ["magician", "sage", "ruler"],
    },
    AmazonCategory.GIFT_CARDS: {
        "display_name": "Gift Cards",
        "keywords": ["gift", "card", "present"],
        "typical_archetypes": ["caregiver", "everyman", "jester"],
    },
    AmazonCategory.GROCERY_AND_GOURMET_FOOD: {
        "display_name": "Grocery & Gourmet Food",
        "keywords": ["food", "grocery", "gourmet", "snack", "organic"],
        "typical_archetypes": ["caregiver", "explorer", "innocent"],
    },
    AmazonCategory.HANDMADE_PRODUCTS: {
        "display_name": "Handmade Products",
        "keywords": ["handmade", "artisan", "craft", "custom"],
        "typical_archetypes": ["creator", "innocent", "explorer"],
    },
    AmazonCategory.HEALTH_AND_HOUSEHOLD: {
        "display_name": "Health & Household",
        "keywords": ["health", "household", "vitamin", "supplement"],
        "typical_archetypes": ["caregiver", "sage", "everyman"],
    },
    AmazonCategory.HEALTH_AND_PERSONAL_CARE: {
        "display_name": "Health & Personal Care",
        "keywords": ["health", "personal", "care", "wellness"],
        "typical_archetypes": ["caregiver", "sage", "lover"],
    },
    AmazonCategory.HOME_AND_KITCHEN: {
        "display_name": "Home & Kitchen",
        "keywords": ["home", "kitchen", "house", "cooking", "decor"],
        "typical_archetypes": ["caregiver", "creator", "ruler"],
    },
    AmazonCategory.INDUSTRIAL_AND_SCIENTIFIC: {
        "display_name": "Industrial & Scientific",
        "keywords": ["industrial", "scientific", "lab", "equipment"],
        "typical_archetypes": ["sage", "ruler", "magician"],
    },
    AmazonCategory.KINDLE_STORE: {
        "display_name": "Kindle Store",
        "keywords": ["kindle", "ebook", "digital", "reading"],
        "typical_archetypes": ["sage", "explorer", "creator"],
    },
    AmazonCategory.MAGAZINE_SUBSCRIPTIONS: {
        "display_name": "Magazine Subscriptions",
        "keywords": ["magazine", "subscription", "periodical"],
        "typical_archetypes": ["explorer", "sage", "lover"],
    },
    AmazonCategory.MOVIES_AND_TV: {
        "display_name": "Movies & TV",
        "keywords": ["movie", "tv", "film", "video", "dvd"],
        "typical_archetypes": ["explorer", "jester", "outlaw"],
    },
    AmazonCategory.MUSICAL_INSTRUMENTS: {
        "display_name": "Musical Instruments",
        "keywords": ["instrument", "music", "guitar", "piano", "drum"],
        "typical_archetypes": ["creator", "magician", "explorer"],
    },
    AmazonCategory.OFFICE_PRODUCTS: {
        "display_name": "Office Products",
        "keywords": ["office", "desk", "stationery", "supplies"],
        "typical_archetypes": ["ruler", "sage", "everyman"],
    },
    AmazonCategory.PATIO_LAWN_AND_GARDEN: {
        "display_name": "Patio, Lawn & Garden",
        "keywords": ["patio", "lawn", "garden", "outdoor", "plant"],
        "typical_archetypes": ["creator", "caregiver", "innocent"],
    },
    AmazonCategory.PET_SUPPLIES: {
        "display_name": "Pet Supplies",
        "keywords": ["pet", "dog", "cat", "animal", "supplies"],
        "typical_archetypes": ["caregiver", "innocent", "lover"],
    },
    AmazonCategory.SOFTWARE: {
        "display_name": "Software",
        "keywords": ["software", "program", "app", "computer"],
        "typical_archetypes": ["magician", "sage", "ruler"],
    },
    AmazonCategory.SPORTS_AND_OUTDOORS: {
        "display_name": "Sports & Outdoors",
        "keywords": ["sports", "outdoor", "fitness", "exercise", "athletic"],
        "typical_archetypes": ["hero", "explorer", "outlaw"],
    },
    AmazonCategory.SUBSCRIPTION_BOXES: {
        "display_name": "Subscription Boxes",
        "keywords": ["subscription", "box", "monthly", "curated"],
        "typical_archetypes": ["explorer", "jester", "magician"],
    },
    AmazonCategory.TOOLS_AND_HOME_IMPROVEMENT: {
        "display_name": "Tools & Home Improvement",
        "keywords": ["tools", "home", "improvement", "diy", "repair"],
        "typical_archetypes": ["creator", "hero", "ruler"],
    },
    AmazonCategory.TOYS_AND_GAMES: {
        "display_name": "Toys & Games",
        "keywords": ["toy", "game", "play", "fun", "kids"],
        "typical_archetypes": ["jester", "innocent", "creator"],
    },
    AmazonCategory.UNKNOWN: {
        "display_name": "Unknown",
        "keywords": [],
        "typical_archetypes": ["everyman"],
    },
}


# =============================================================================
# FILE PATH HELPERS
# =============================================================================

@dataclass
class CategoryFiles:
    """File paths for a category."""
    
    category: AmazonCategory
    review_file: Path
    meta_file: Path
    review_file_gz: Path
    meta_file_gz: Path
    
    @property
    def review_path(self) -> Path:
        """Get the review file path (prefer uncompressed)."""
        if self.review_file.exists():
            return self.review_file
        return self.review_file_gz
    
    @property
    def meta_path(self) -> Path:
        """Get the meta file path (prefer uncompressed)."""
        if self.meta_file.exists():
            return self.meta_file
        return self.meta_file_gz
    
    @property
    def review_exists(self) -> bool:
        return self.review_file.exists() or self.review_file_gz.exists()
    
    @property
    def meta_exists(self) -> bool:
        return self.meta_file.exists() or self.meta_file_gz.exists()
    
    @property
    def both_exist(self) -> bool:
        return self.review_exists and self.meta_exists


def get_category_files(
    category: AmazonCategory,
    data_dir: Optional[Path] = None,
) -> CategoryFiles:
    """Get file paths for a category."""
    data_dir = data_dir or AMAZON_DATA_DIR
    
    return CategoryFiles(
        category=category,
        review_file=data_dir / f"{category.value}.jsonl",
        meta_file=data_dir / f"meta_{category.value}.jsonl",
        review_file_gz=data_dir / f"{category.value}.jsonl.gz",
        meta_file_gz=data_dir / f"meta_{category.value}.jsonl.gz",
    )


def get_all_category_files(
    data_dir: Optional[Path] = None,
) -> Dict[AmazonCategory, CategoryFiles]:
    """Get file paths for all categories."""
    return {
        cat: get_category_files(cat, data_dir)
        for cat in AmazonCategory
    }


def get_available_categories(
    data_dir: Optional[Path] = None,
) -> List[AmazonCategory]:
    """Get categories that have both review and meta files."""
    all_files = get_all_category_files(data_dir)
    return [
        cat for cat, files in all_files.items()
        if files.both_exist
    ]


# =============================================================================
# CO-PURCHASE GRAPH FILES
# =============================================================================

@dataclass
class CoPurchaseFiles:
    """Amazon co-purchase graph files (SNAP dataset)."""
    
    meta_file: Path  # amazon-meta.txt - Product info with 'similar' products
    graph_files: List[Path]  # amazon0302.txt, etc. - Edge lists
    
    @property
    def meta_exists(self) -> bool:
        return self.meta_file.exists()


def get_copurchase_files(
    data_dir: Optional[Path] = None,
) -> CoPurchaseFiles:
    """Get co-purchase graph file paths."""
    data_dir = data_dir or AMAZON_DATA_DIR
    
    # Check both possible locations
    meta_paths = [
        data_dir / "amazon-meta.txt",
        data_dir / "Amazon Co-Purchase Models" / "amazon-meta.txt",
    ]
    
    meta_file = None
    for p in meta_paths:
        if p.exists():
            meta_file = p
            break
    
    # Graph edge files
    graph_patterns = ["amazon0302.txt", "amazon0312.txt", "amazon0505.txt", "amazon0601.txt"]
    graph_files = []
    for pattern in graph_patterns:
        for parent in [data_dir, data_dir / "Amazon Co-Purchase Models"]:
            path = parent / pattern
            if path.exists():
                graph_files.append(path)
    
    return CoPurchaseFiles(
        meta_file=meta_file or data_dir / "amazon-meta.txt",
        graph_files=graph_files,
    )


# =============================================================================
# CATEGORY INFERENCE
# =============================================================================

def infer_category(
    product_name: str,
    brand: str = "",
) -> AmazonCategory:
    """Infer the most likely category from product name and brand."""
    text = f"{product_name} {brand}".lower()
    
    # Score each category by keyword matches
    scores = {}
    for cat, info in CATEGORY_INFO.items():
        keywords = info.get("keywords", [])
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    
    # Default fallbacks based on common patterns
    if any(w in text for w in ["shoe", "boot", "sneaker", "sandal", "heel", "dress", "shirt", "pant"]):
        return AmazonCategory.CLOTHING_SHOES_AND_JEWELRY
    elif any(w in text for w in ["phone", "tablet", "laptop", "computer", "headphone"]):
        return AmazonCategory.ELECTRONICS
    elif any(w in text for w in ["serum", "cream", "moisturizer", "shampoo"]):
        return AmazonCategory.BEAUTY_AND_PERSONAL_CARE
    elif any(w in text for w in ["vitamin", "supplement", "medicine"]):
        return AmazonCategory.HEALTH_AND_HOUSEHOLD
    
    return AmazonCategory.UNKNOWN


# =============================================================================
# DATA STATISTICS
# =============================================================================

def get_data_statistics(
    data_dir: Optional[Path] = None,
) -> Dict[str, any]:
    """Get statistics about available Amazon data."""
    data_dir = data_dir or AMAZON_DATA_DIR
    
    categories = get_all_category_files(data_dir)
    available = get_available_categories(data_dir)
    copurchase = get_copurchase_files(data_dir)
    
    # Calculate total sizes
    total_review_size = 0
    total_meta_size = 0
    
    for cat, files in categories.items():
        if files.review_path.exists():
            total_review_size += files.review_path.stat().st_size
        if files.meta_path.exists():
            total_meta_size += files.meta_path.stat().st_size
    
    return {
        "data_dir": str(data_dir),
        "total_categories": len(AmazonCategory),
        "available_categories": len(available),
        "available_category_names": [c.value for c in available],
        "total_review_size_gb": total_review_size / (1024**3),
        "total_meta_size_gb": total_meta_size / (1024**3),
        "copurchase_meta_available": copurchase.meta_exists,
        "copurchase_graph_files": len(copurchase.graph_files),
    }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AMAZON DATA REGISTRY")
    print("=" * 70)
    
    stats = get_data_statistics()
    
    print(f"\n📂 Data Directory: {stats['data_dir']}")
    print(f"\n📊 Categories:")
    print(f"   Total defined: {stats['total_categories']}")
    print(f"   Available (with both files): {stats['available_categories']}")
    
    print(f"\n💾 Data Size:")
    print(f"   Review files: {stats['total_review_size_gb']:.2f} GB")
    print(f"   Meta files: {stats['total_meta_size_gb']:.2f} GB")
    print(f"   Total: {stats['total_review_size_gb'] + stats['total_meta_size_gb']:.2f} GB")
    
    print(f"\n🔗 Co-Purchase Data:")
    print(f"   Meta file available: {stats['copurchase_meta_available']}")
    print(f"   Graph edge files: {stats['copurchase_graph_files']}")
    
    print(f"\n📋 Available Categories:")
    for cat in stats['available_category_names']:
        print(f"   - {cat}")
    
    print(f"\n🔍 Category Inference Test:")
    test_products = [
        ("Nike Air Max", "Nike"),
        ("Vitamin D3 Supplement", "Nature Made"),
        ("iPhone 15 Pro Case", "Apple"),
        ("Face Moisturizer", "CeraVe"),
        ("Yoga Mat", "Gaiam"),
    ]
    for product, brand in test_products:
        cat = infer_category(product, brand)
        print(f"   '{product}' ({brand}) → {cat.value}")
