# =============================================================================
# ADAM Demo - Categories Router
# Category management and psychology endpoints
# =============================================================================

"""
Category API endpoints for the ADAM demo platform.

Includes:
- Top-level category listing
- Subcategory navigation
- Category psychology profiles
- Brand/category context analysis
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Categories"])


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/categories/top-level")
async def get_top_level_categories() -> Dict[str, Any]:
    """
    Get top-level Amazon categories for dropdown selection.
    
    Returns the main categories with product counts for the demo UI.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        categories = service.get_category_hierarchy()
        
        return {
            "categories": categories,
            "count": len(categories),
            "source": "Neo4j AmazonCategoryLevel nodes"
        }
    except Exception as e:
        logger.error(f"Error fetching top-level categories: {e}")
        # Return comprehensive fallback categories covering all product types
        return {
            "categories": [
                {"name": "Tools & Home Improvement", "level": 0, "product_count": 7041234, "main_category": "Tools_and_Home_Improvement"},
                {"name": "Electronics", "level": 0, "product_count": 1481570, "main_category": "Electronics"},
                {"name": "Home & Kitchen", "level": 0, "product_count": 3344847, "main_category": "Home_and_Kitchen"},
                {"name": "Automotive", "level": 0, "product_count": 1897346, "main_category": "Automotive"},
                {"name": "Sports & Outdoors", "level": 0, "product_count": 1497591, "main_category": "Sports_and_Outdoors"},
                {"name": "Clothing, Shoes & Jewelry", "level": 0, "product_count": 7218481, "main_category": "Clothing_Shoes_and_Jewelry"},
                {"name": "Beauty & Personal Care", "level": 0, "product_count": 1028914, "main_category": "Beauty_and_Personal_Care"},
                {"name": "Health & Household", "level": 0, "product_count": 797560, "main_category": "Health_and_Household"},
                {"name": "Industrial & Scientific", "level": 0, "product_count": 2156789, "main_category": "Industrial_and_Scientific"},
                {"name": "Patio, Lawn & Garden", "level": 0, "product_count": 1234567, "main_category": "Patio_Lawn_and_Garden"},
                {"name": "Office Products", "level": 0, "product_count": 987654, "main_category": "Office_Products"},
                {"name": "Appliances", "level": 0, "product_count": 654321, "main_category": "Appliances"},
                {"name": "Cell Phones & Accessories", "level": 0, "product_count": 876543, "main_category": "Cell_Phones_and_Accessories"},
                {"name": "Toys & Games", "level": 0, "product_count": 801922, "main_category": "Toys_and_Games"},
                {"name": "Pet Supplies", "level": 0, "product_count": 439915, "main_category": "Pet_Supplies"},
                {"name": "Baby Products", "level": 0, "product_count": 567890, "main_category": "Baby_Products"},
                {"name": "Books", "level": 0, "product_count": 3919508, "main_category": "Books"},
                {"name": "Grocery & Gourmet Food", "level": 0, "product_count": 1234567, "main_category": "Grocery_and_Gourmet_Food"},
                {"name": "Arts, Crafts & Sewing", "level": 0, "product_count": 456789, "main_category": "Arts_Crafts_and_Sewing"},
                {"name": "Musical Instruments", "level": 0, "product_count": 234567, "main_category": "Musical_Instruments"},
                {"name": "Movies & TV", "level": 0, "product_count": 345678, "main_category": "Movies_and_TV"},
                {"name": "Video Games", "level": 0, "product_count": 456789, "main_category": "Video_Games"},
                {"name": "Software", "level": 0, "product_count": 123456, "main_category": "Software"},
                {"name": "CDs & Vinyl", "level": 0, "product_count": 234567, "main_category": "CDs_and_Vinyl"},
                {"name": "Kindle Store", "level": 0, "product_count": 345678, "main_category": "Kindle_Store"},
                {"name": "Amazon Fashion", "level": 0, "product_count": 567890, "main_category": "Amazon_Fashion"},
                {"name": "All Beauty", "level": 0, "product_count": 234567, "main_category": "All_Beauty"},
                {"name": "Handmade Products", "level": 0, "product_count": 123456, "main_category": "Handmade_Products"},
            ],
            "count": 28,
            "source": "fallback"
        }


@router.get("/categories/{parent_category}/subcategories")
async def get_subcategories(parent_category: str) -> Dict[str, Any]:
    """
    Get subcategories of a parent category.
    
    Used for cascading dropdown selection in the demo UI.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        subcategories = service.get_subcategories(parent_category)
        
        return {
            "parent": parent_category,
            "subcategories": subcategories,
            "count": len(subcategories)
        }
    except Exception as e:
        logger.error(f"Error fetching subcategories for {parent_category}: {e}")
        return {
            "parent": parent_category,
            "subcategories": [],
            "count": 0,
            "error": str(e)
        }


@router.get("/categories/psychology/{category_path:path}")
async def get_category_psychology(category_path: str) -> Dict[str, Any]:
    """
    Get psychological profile for a category path.
    
    Implements relaxed matching:
    1. Exact match
    2. Parent category fallback
    3. Similar category fallback
    4. Domain-level fallback
    5. Global priors
    
    Args:
        category_path: Full category path (e.g., "Electronics > Computers > Laptops")
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        profile = service.get_category_psychology(category_path)
        
        # Get best mechanisms
        mechanisms = service.get_best_mechanisms_for_category(category_path, top_n=5)
        
        return {
            "category_path": profile.category_path,
            "match_type": profile.match_type,
            "match_confidence": profile.match_confidence,
            "review_count": profile.review_count,
            "archetypes": profile.archetypes,
            "mechanism_effectiveness": profile.mechanism_effectiveness,
            "recommended_mechanisms": [
                {
                    "mechanism": m.mechanism,
                    "effectiveness": m.effectiveness,
                    "confidence": m.confidence,
                    "reasoning": m.reasoning
                }
                for m in mechanisms
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching category psychology for {category_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching category psychology: {str(e)}"
        )


@router.post("/categories/analyze-context")
async def analyze_brand_category_context(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze psychological context for a brand + category + location combination.
    
    This is the main endpoint for the demo's intelligent targeting.
    
    Args:
        brand: Brand name (e.g., "Nike")
        category: Main category (e.g., "Sports & Outdoors")
        subcategory: Specific subcategory (e.g., "Running Shoes")
        state: US state for regional psychology (e.g., "California")
    
    Returns comprehensive targeting intelligence.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        review_service = get_review_learnings_service()
        priors_service = get_learned_priors()
        
        result = {
            "input": {
                "brand": brand,
                "category": category,
                "subcategory": subcategory,
                "state": state
            },
            "category_intelligence": None,
            "brand_intelligence": None,
            "regional_intelligence": None,
            "recommended_mechanisms": [],
            "target_archetypes": [],
            "confidence": 0.0,
        }
        
        # Get category psychology if provided
        if category:
            category_path = category
            if subcategory:
                category_path = f"{category} > {subcategory}"
            
            try:
                profile = review_service.get_category_psychology(category_path)
                result["category_intelligence"] = {
                    "path": profile.category_path,
                    "match_type": profile.match_type,
                    "archetypes": profile.archetypes,
                    "mechanisms": profile.mechanism_effectiveness,
                }
            except Exception as e:
                logger.warning(f"Could not get category psychology: {e}")
        
        # Get brand intelligence if provided
        if brand:
            try:
                brand_priors = priors_service.get_brand_priors(brand)
                if brand_priors:
                    result["brand_intelligence"] = {
                        "brand": brand,
                        "mechanisms": brand_priors.get("mechanisms", {}),
                        "archetypes": brand_priors.get("archetypes", []),
                        "tone": brand_priors.get("tone", "neutral"),
                    }
            except Exception as e:
                logger.warning(f"Could not get brand intelligence: {e}")
        
        # Get regional intelligence if state provided
        if state:
            try:
                regional_priors = priors_service.get_regional_priors(state)
                if regional_priors:
                    result["regional_intelligence"] = {
                        "state": state,
                        "cultural_traits": regional_priors.get("cultural_traits", []),
                        "mechanism_preferences": regional_priors.get("mechanisms", {}),
                    }
            except Exception as e:
                logger.warning(f"Could not get regional intelligence: {e}")
        
        # Calculate combined recommendations
        mechanisms_scores = {}
        
        if result["category_intelligence"]:
            for mech, score in result["category_intelligence"].get("mechanisms", {}).items():
                mechanisms_scores[mech] = mechanisms_scores.get(mech, 0) + score * 0.4
        
        if result["brand_intelligence"]:
            for mech, score in result["brand_intelligence"].get("mechanisms", {}).items():
                mechanisms_scores[mech] = mechanisms_scores.get(mech, 0) + score * 0.35
        
        if result["regional_intelligence"]:
            for mech, score in result["regional_intelligence"].get("mechanism_preferences", {}).items():
                mechanisms_scores[mech] = mechanisms_scores.get(mech, 0) + score * 0.25
        
        # Sort and take top mechanisms
        sorted_mechanisms = sorted(
            mechanisms_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        result["recommended_mechanisms"] = [
            {"mechanism": m, "score": round(s, 3)}
            for m, s in sorted_mechanisms
        ]
        
        # Calculate confidence based on available data
        confidence = 0.0
        if result["category_intelligence"]:
            confidence += 0.4
        if result["brand_intelligence"]:
            confidence += 0.35
        if result["regional_intelligence"]:
            confidence += 0.25
        result["confidence"] = confidence
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing brand/category context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/stats")
async def get_category_stats() -> Dict[str, Any]:
    """
    Get statistics about loaded category data.
    
    Shows how much category intelligence is available.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        stats = service.get_statistics()
        
        return {
            "total_categories": stats.get("total_categories", 0),
            "categories_with_psychology": stats.get("categories_with_psychology", 0),
            "average_review_count": stats.get("average_review_count", 0),
            "top_categories": stats.get("top_categories", []),
            "last_updated": stats.get("last_updated"),
        }
    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        return {
            "total_categories": 0,
            "error": str(e),
        }
