# =============================================================================
# ADAM Demo - Brands Router
# Brand analysis endpoints
# =============================================================================

"""
Brand analysis API endpoints for the ADAM demo platform.

Includes:
- Brand category lookup
- Brand reviews analysis
- Brand psychology profiles
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Brands"])


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/brands/{brand_name}/categories")
async def get_brand_categories(brand_name: str) -> Dict[str, Any]:
    """
    Get categories where a brand has products.
    
    Useful for understanding brand scope and selecting appropriate categories.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        categories = service.get_brand_categories(brand_name)
        
        if categories and len(categories) > 0:
            return {
                "brand": brand_name,
                "categories": categories,
                "count": len(categories),
                "total_products": sum(c.get("product_count", 0) for c in categories),
            }
    except Exception as e:
        logger.warning(f"Could not fetch brand categories for {brand_name}: {e}")
    
    try:
        from neo4j import GraphDatabase
        import os
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "atomofthought")),
        )
        with driver.session() as s:
            data = s.run("""
                MATCH (pd:ProductDescription)
                WHERE pd.main_category IS NOT NULL
                WITH pd.main_category AS cat, count(pd) AS cnt
                ORDER BY cnt DESC
                RETURN cat, cnt
            """).data()
        driver.close()
        db_categories = [
            {"main_category": r["cat"].replace(" ", "_"), "subcategory": None,
             "product_count": r["cnt"], "display_name": r["cat"]}
            for r in data
        ]
        return {
            "brand": brand_name,
            "categories": db_categories,
            "count": len(db_categories),
            "total_products": sum(r["cnt"] for r in data),
            "source": "Neo4j ProductDescription categories",
            "note": f"Brand '{brand_name}' not found in learned priors; showing all available categories",
        }
    except Exception:
        raise HTTPException(status_code=503, detail=f"Brand '{brand_name}' not found and Neo4j unavailable")


@router.get("/brands/{brand_name}/reviews")
async def get_brand_reviews_intelligence(
    brand_name: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Max reviews to analyze"),
) -> Dict[str, Any]:
    """
    Get psychological intelligence from brand reviews.
    
    Analyzes review corpus to extract:
    - Customer archetypes
    - Effective mechanisms
    - Sentiment patterns
    - Purchase motivations
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        intelligence = service.get_brand_review_intelligence(
            brand_name=brand_name,
            category=category,
            limit=limit,
        )
        
        return {
            "brand": brand_name,
            "category": category,
            "review_count": intelligence.get("review_count", 0),
            "archetypes": intelligence.get("archetypes", []),
            "mechanism_effectiveness": intelligence.get("mechanisms", {}),
            "sentiment": intelligence.get("sentiment", {}),
            "key_themes": intelligence.get("key_themes", []),
            "purchase_motivations": intelligence.get("motivations", []),
        }
    except Exception as e:
        logger.error(f"Error fetching brand review intelligence for {brand_name}: {e}")
        return {
            "brand": brand_name,
            "category": category,
            "review_count": 0,
            "error": str(e),
        }


@router.get("/brands/{brand_name}/psychology")
async def get_brand_psychology(brand_name: str) -> Dict[str, Any]:
    """
    Get comprehensive psychological profile for a brand.
    
    Combines:
    - Review-derived insights
    - Brand copy analysis (Cialdini)
    - Customer archetype distribution
    - Effective mechanisms
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        brand_data = priors.get_brand_priors(brand_name)
        
        if not brand_data:
            return {
                "brand": brand_name,
                "found": False,
                "message": f"No learned priors found for brand: {brand_name}",
            }
        
        return {
            "brand": brand_name,
            "found": True,
            "cialdini_scores": brand_data.get("cialdini_scores", {}),
            "aaker_personality": brand_data.get("aaker_personality", {}),
            "target_archetypes": brand_data.get("target_archetypes", []),
            "mechanism_effectiveness": brand_data.get("mechanisms", {}),
            "brand_tone": brand_data.get("tone", "neutral"),
            "review_count": brand_data.get("review_count", 0),
            "confidence": brand_data.get("confidence", 0.0),
        }
    except Exception as e:
        logger.error(f"Error fetching brand psychology for {brand_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brands/search")
async def search_brands(
    query: str = Query(..., min_length=2, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> Dict[str, Any]:
    """
    Search for brands in the database.
    
    Returns brands matching the query with basic statistics.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        results = service.search_brands(
            query=query,
            category=category,
            limit=limit,
        )
        
        return {
            "query": query,
            "category": category,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Error searching brands with query '{query}': {e}")
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": str(e),
        }


@router.get("/brands/{brand_name}/competitors")
async def get_brand_competitors(
    brand_name: str,
    category: Optional[str] = Query(None, description="Category to find competitors in"),
    limit: int = Query(10, ge=1, le=50, description="Max competitors to return"),
) -> Dict[str, Any]:
    """
    Find competitors for a brand in a category.
    
    Useful for competitive intelligence analysis.
    """
    try:
        from adam.competitive.intelligence import get_competitive_intelligence_service
        
        service = get_competitive_intelligence_service()
        
        # This would use Neo4j to find brands in same category
        # For now, return a placeholder
        return {
            "brand": brand_name,
            "category": category,
            "competitors": [],
            "note": "Competitor detection requires category context",
        }
    except Exception as e:
        logger.error(f"Error finding competitors for {brand_name}: {e}")
        return {
            "brand": brand_name,
            "competitors": [],
            "error": str(e),
        }
