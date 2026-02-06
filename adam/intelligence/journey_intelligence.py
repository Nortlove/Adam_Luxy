# =============================================================================
# ADAM Journey Intelligence
# Location: adam/intelligence/journey_intelligence.py
# =============================================================================

"""
JOURNEY INTELLIGENCE

Leverages bought_together data to understand customer purchase journeys.

KEY INSIGHT:
When Amazon shows "Frequently bought together" bundles, they're revealing:
1. Product relationships that WORK (customers actually buy them together)
2. Customer journey patterns (what leads to what)
3. Cross-product influence (how one product affects another purchase)

This intelligence enables:
- **Cross-product recommendations**: "Customers who considered X also loved Y"
- **Journey-based persuasion**: Adapt messaging based on journey stage
- **Bundle effectiveness**: Which product combinations have highest conversion
- **Upgrade paths**: Premium product suggestions based on entry-level purchases

JOURNEY TYPES:
- co_purchase: Bought at the same time (complementary products)
- upgrade: Bought after (premium version of same product)
- accessory: Bought to enhance primary purchase
- replenishment: Bought repeatedly (consumables)
- exploration: Bought in same category (trying alternatives)

ARCHITECTURE:
                    ┌─────────────────────┐
                    │  bought_together    │
                    │  (from metadata)    │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Journey Graph      │
                    │  ASIN → ASIN edges  │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │ Cross-Product   │ │ Journey     │ │ Bundle          │
    │ Recommendations │ │ Stage       │ │ Intelligence    │
    └─────────────────┘ └─────────────┘ └─────────────────┘
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class JourneyEdge:
    """An edge in the purchase journey graph."""
    source_asin: str
    target_asin: str
    source_brand: str = ""
    target_brand: str = ""
    frequency: int = 1
    journey_type: str = "co_purchase"
    category: str = ""
    price_delta: float = 0.0  # Positive = upgrade, negative = downgrade


@dataclass
class ProductNode:
    """A product in the journey graph."""
    asin: str
    brand: str = ""
    title: str = ""
    category: str = ""
    price: float = 0.0
    
    # Journey metrics
    inbound_edges: int = 0  # How many products lead here
    outbound_edges: int = 0  # How many products follow
    journey_centrality: float = 0.0  # How central in journeys


@dataclass
class JourneyCluster:
    """A cluster of products frequently purchased together."""
    cluster_id: str
    products: List[str] = field(default_factory=list)
    primary_product: str = ""
    category: str = ""
    total_frequency: int = 0
    avg_price: float = 0.0


@dataclass
class JourneyIntelligence:
    """Complete journey intelligence for a product."""
    
    asin: str
    brand: str = ""
    
    # Direct relationships
    bought_together: List[Dict[str, Any]] = field(default_factory=list)
    frequently_leads_to: List[Dict[str, Any]] = field(default_factory=list)
    frequently_leads_from: List[Dict[str, Any]] = field(default_factory=list)
    
    # Journey stage analysis
    journey_stage: str = ""  # "entry", "core", "premium", "accessory"
    upgrade_path: List[str] = field(default_factory=list)
    accessory_bundle: List[str] = field(default_factory=list)
    
    # Cross-sell recommendations
    recommended_next: List[Dict[str, Any]] = field(default_factory=list)
    
    # Cluster membership
    cluster_id: Optional[str] = None
    cluster_products: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "asin": self.asin,
            "brand": self.brand,
            "bought_together": self.bought_together,
            "journey_stage": self.journey_stage,
            "upgrade_path": self.upgrade_path,
            "accessory_bundle": self.accessory_bundle,
            "recommended_next": self.recommended_next,
            "cluster_id": self.cluster_id,
        }


# =============================================================================
# JOURNEY INTELLIGENCE SERVICE
# =============================================================================

class JourneyIntelligenceService:
    """
    Builds and queries customer purchase journey intelligence.
    
    Usage:
        service = JourneyIntelligenceService()
        
        # During ingestion
        await service.add_journey_edges(category_metadata)
        
        # During decision-making
        intel = await service.get_journey_intelligence(asin)
    """
    
    def __init__(self):
        """Initialize the service."""
        self._edges: Dict[str, List[JourneyEdge]] = defaultdict(list)  # source_asin → edges
        self._reverse_edges: Dict[str, List[JourneyEdge]] = defaultdict(list)  # target_asin → edges
        self._products: Dict[str, ProductNode] = {}
        self._clusters: Dict[str, JourneyCluster] = {}
        self._user_journeys: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # user_id → journey
    
    # -------------------------------------------------------------------------
    # INGESTION
    # -------------------------------------------------------------------------
    
    def add_journey_edges_from_metadata(
        self,
        metadata_records: List[Dict[str, Any]],
        category: str = "",
    ) -> int:
        """
        Extract journey edges from product metadata.
        
        Args:
            metadata_records: List of product metadata dicts
            category: Product category
            
        Returns:
            Number of edges added
        """
        edges_added = 0
        
        for record in metadata_records:
            source_asin = record.get("parent_asin") or record.get("asin", "")
            if not source_asin:
                continue
            
            # Get product info
            brand = record.get("store") or record.get("details", {}).get("brand", "")
            title = record.get("title", "")
            price = record.get("price", 0.0)
            if isinstance(price, str):
                try:
                    price = float(price.replace("$", "").replace(",", ""))
                except ValueError:
                    price = 0.0
            
            # Store product node
            self._products[source_asin] = ProductNode(
                asin=source_asin,
                brand=brand,
                title=title,
                category=category,
                price=price,
            )
            
            # Extract bought_together
            bought_together = record.get("bought_together", [])
            if bought_together:
                for target_asin in bought_together:
                    if target_asin and target_asin != source_asin:
                        edge = JourneyEdge(
                            source_asin=source_asin,
                            target_asin=target_asin,
                            source_brand=brand,
                            category=category,
                        )
                        self._edges[source_asin].append(edge)
                        self._reverse_edges[target_asin].append(edge)
                        edges_added += 1
        
        return edges_added
    
    def compute_journey_metrics(self) -> None:
        """
        Compute journey metrics for all products.
        
        Call after all edges are loaded.
        """
        # Update edge counts
        for asin, node in self._products.items():
            node.outbound_edges = len(self._edges.get(asin, []))
            node.inbound_edges = len(self._reverse_edges.get(asin, []))
            
            # Simple centrality: product is central if both in and out
            if node.inbound_edges > 0 and node.outbound_edges > 0:
                node.journey_centrality = (
                    node.inbound_edges * node.outbound_edges
                ) / (node.inbound_edges + node.outbound_edges)
    
    def detect_clusters(self, min_size: int = 3) -> int:
        """
        Detect product clusters (frequently purchased together).
        
        Uses simple connected component detection.
        
        Returns:
            Number of clusters found
        """
        visited = set()
        cluster_id = 0
        
        for asin in self._products:
            if asin in visited:
                continue
            
            # BFS to find connected component
            cluster = []
            queue = [asin]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster.append(current)
                
                # Add neighbors
                for edge in self._edges.get(current, []):
                    if edge.target_asin not in visited:
                        queue.append(edge.target_asin)
                
                for edge in self._reverse_edges.get(current, []):
                    if edge.source_asin not in visited:
                        queue.append(edge.source_asin)
            
            # Only save significant clusters
            if len(cluster) >= min_size:
                cid = f"cluster_{cluster_id}"
                
                # Find primary product (most central)
                primary = max(
                    cluster,
                    key=lambda a: self._products.get(a, ProductNode(a)).journey_centrality,
                )
                
                self._clusters[cid] = JourneyCluster(
                    cluster_id=cid,
                    products=cluster,
                    primary_product=primary,
                    total_frequency=len(cluster),
                )
                
                cluster_id += 1
        
        return len(self._clusters)
    
    # -------------------------------------------------------------------------
    # QUERYING
    # -------------------------------------------------------------------------
    
    def get_journey_intelligence(
        self,
        asin: str,
    ) -> JourneyIntelligence:
        """
        Get complete journey intelligence for a product.
        
        Args:
            asin: Product ASIN
            
        Returns:
            JourneyIntelligence with all relationships and recommendations
        """
        intel = JourneyIntelligence(asin=asin)
        
        # Get product info
        product = self._products.get(asin)
        if product:
            intel.brand = product.brand
        
        # Get direct bought_together relationships
        for edge in self._edges.get(asin, []):
            target = self._products.get(edge.target_asin)
            intel.bought_together.append({
                "asin": edge.target_asin,
                "brand": target.brand if target else "",
                "title": target.title if target else "",
                "frequency": edge.frequency,
            })
        
        # Get products that lead TO this one
        for edge in self._reverse_edges.get(asin, []):
            source = self._products.get(edge.source_asin)
            intel.frequently_leads_from.append({
                "asin": edge.source_asin,
                "brand": source.brand if source else "",
                "title": source.title if source else "",
                "frequency": edge.frequency,
            })
        
        # Determine journey stage
        intel.journey_stage = self._determine_journey_stage(asin)
        
        # Build upgrade path
        intel.upgrade_path = self._find_upgrade_path(asin)
        
        # Build accessory bundle
        intel.accessory_bundle = self._find_accessories(asin)
        
        # Get cluster membership
        for cid, cluster in self._clusters.items():
            if asin in cluster.products:
                intel.cluster_id = cid
                intel.cluster_products = [
                    a for a in cluster.products if a != asin
                ][:10]
                break
        
        # Build recommendations
        intel.recommended_next = self._build_recommendations(asin)
        
        return intel
    
    def _determine_journey_stage(self, asin: str) -> str:
        """
        Determine where this product sits in typical journey.
        
        - entry: Many outbound, few inbound (people start here)
        - core: High centrality (people go through here)
        - premium: Many inbound, few outbound (people end here)
        - accessory: Only appears in bought_together, not main journey
        """
        product = self._products.get(asin)
        if not product:
            return "unknown"
        
        inbound = product.inbound_edges
        outbound = product.outbound_edges
        
        if outbound > 5 and inbound <= 2:
            return "entry"
        elif inbound > 5 and outbound <= 2:
            return "premium"
        elif product.journey_centrality > 5:
            return "core"
        elif outbound == 0 and inbound > 0:
            return "accessory"
        else:
            return "standard"
    
    def _find_upgrade_path(self, asin: str, max_steps: int = 3) -> List[str]:
        """Find products that represent upgrades from this one."""
        product = self._products.get(asin)
        if not product or product.price <= 0:
            return []
        
        upgrades = []
        current_price = product.price
        
        for edge in self._edges.get(asin, []):
            target = self._products.get(edge.target_asin)
            if target and target.price > current_price * 1.2:  # 20%+ more expensive
                upgrades.append(edge.target_asin)
        
        # Sort by price
        upgrades.sort(
            key=lambda a: self._products.get(a, ProductNode(a)).price,
        )
        
        return upgrades[:max_steps]
    
    def _find_accessories(self, asin: str, max_count: int = 5) -> List[str]:
        """Find accessory products for this one."""
        accessories = []
        
        for edge in self._edges.get(asin, []):
            target = self._products.get(edge.target_asin)
            if target and target.journey_centrality == 0:  # Low centrality = accessory
                accessories.append(edge.target_asin)
        
        return accessories[:max_count]
    
    def _build_recommendations(
        self,
        asin: str,
        max_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """Build cross-product recommendations."""
        recommendations = []
        
        # Start with bought_together
        for edge in self._edges.get(asin, [])[:max_count]:
            target = self._products.get(edge.target_asin)
            recommendations.append({
                "asin": edge.target_asin,
                "brand": target.brand if target else "",
                "reason": "frequently_bought_together",
                "confidence": min(edge.frequency / 10, 1.0),
            })
        
        return recommendations
    
    # -------------------------------------------------------------------------
    # GRAPH DATABASE INTEGRATION
    # -------------------------------------------------------------------------
    
    async def persist_to_graph(self) -> Dict[str, int]:
        """
        Persist journey intelligence to Neo4j.
        
        Returns counts of persisted items.
        """
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
            JourneyData,
        )
        
        persistence = get_pattern_persistence()
        
        # Convert edges to JourneyData
        journeys = []
        for source_asin, edges in self._edges.items():
            for edge in edges:
                journeys.append(JourneyData(
                    source_asin=source_asin,
                    target_asin=edge.target_asin,
                    bundle_frequency=edge.frequency,
                    category=edge.category,
                    journey_type=edge.journey_type,
                ))
        
        stored = await persistence.store_journey_patterns(journeys)
        
        return {
            "journey_patterns": stored,
            "products": len(self._products),
            "clusters": len(self._clusters),
        }
    
    async def get_journey_from_graph(
        self,
        asin: str,
    ) -> JourneyIntelligence:
        """
        Get journey intelligence from Neo4j (for products not in memory).
        """
        intel = JourneyIntelligence(asin=asin)
        
        try:
            from adam.infrastructure.neo4j.pattern_persistence import (
                get_pattern_persistence,
            )
            
            persistence = get_pattern_persistence()
            products = await persistence.get_journey_products(asin, limit=10)
            
            for product in products:
                intel.bought_together.append({
                    "asin": product["asin"],
                    "brand": product.get("brand", ""),
                    "frequency": product.get("frequency", 1),
                })
            
        except Exception as e:
            logger.debug(f"Failed to get journey from graph: {e}")
        
        return intel
    
    # -------------------------------------------------------------------------
    # REVIEW INGESTION (for full_intelligence_integration compatibility)
    # -------------------------------------------------------------------------
    
    def ingest_review(
        self,
        user_id: str,
        product_id: str,
        brand: str,
        category: str,
        rating: float,
        review_text: str,
    ) -> None:
        """
        Ingest a review to build journey context.
        
        Used by full_intelligence_integration.py to build user journey profiles
        from review data.
        
        Args:
            user_id: User identifier
            product_id: Product ASIN/ID
            brand: Brand name
            category: Product category
            rating: Review rating (1-5)
            review_text: Full review text
        """
        # Track user journey
        if user_id not in self._user_journeys:
            self._user_journeys[user_id] = []
        
        self._user_journeys[user_id].append({
            "product_id": product_id,
            "brand": brand,
            "category": category,
            "rating": rating,
            "sentiment": "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral",
        })
        
        # Ensure product exists
        if product_id not in self._products:
            self._products[product_id] = ProductNode(
                asin=product_id,
                brand=brand,
                title="",
            )
    
    def build_intelligence_profile(
        self,
        product_id: str,
        brand: str,
        user_id: Optional[str] = None,
    ) -> "JourneyIntelligenceProfile":
        """
        Build a comprehensive intelligence profile from ingested reviews.
        
        Used by full_intelligence_integration.py to generate journey-based insights.
        
        Args:
            product_id: Product ASIN/ID
            brand: Brand name
            user_id: Optional user ID to personalize
            
        Returns:
            JourneyIntelligenceProfile with cluster, appeals, and threats
        """
        profile = JourneyIntelligenceProfile()
        
        # Analyze user journey if available
        if user_id and user_id in self._user_journeys:
            journey = self._user_journeys[user_id]
            
            # Determine cluster based on purchase patterns
            categories = [p["category"] for p in journey]
            brands = [p["brand"] for p in journey]
            ratings = [p["rating"] for p in journey]
            
            avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
            
            # Cluster assignment based on behavior
            if avg_rating >= 4.5:
                profile.customer_cluster = "brand_loyalist"
            elif len(set(brands)) > len(brands) * 0.7:
                profile.customer_cluster = "explorer"
            elif len(set(categories)) == 1:
                profile.customer_cluster = "category_focused"
            else:
                profile.customer_cluster = "value_seeker"
            
            # Journey-based appeals
            if profile.customer_cluster == "brand_loyalist":
                profile.journey_based_appeals = ["loyalty_rewards", "exclusive_access", "premium_features"]
            elif profile.customer_cluster == "explorer":
                profile.journey_based_appeals = ["variety", "discovery", "new_experience"]
            elif profile.customer_cluster == "category_focused":
                profile.journey_based_appeals = ["expertise", "specialization", "deep_value"]
            else:
                profile.journey_based_appeals = ["value", "comparison", "reviews"]
            
            # Find competitor brands they've purchased
            profile.competitor_threats = [b for b in set(brands) if b != brand][:5]
        else:
            # Default profile
            profile.customer_cluster = "standard"
            profile.journey_based_appeals = ["quality", "value", "trust"]
            profile.competitor_threats = []
        
        return profile


@dataclass
class JourneyIntelligenceProfile:
    """Profile generated from journey intelligence analysis."""
    
    customer_cluster: str = "standard"
    journey_based_appeals: List[str] = field(default_factory=list)
    competitor_threats: List[str] = field(default_factory=list)
    journey_stage: str = "unknown"
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "customer_cluster": self.customer_cluster,
            "journey_based_appeals": self.journey_based_appeals,
            "competitor_threats": self.competitor_threats,
            "journey_stage": self.journey_stage,
            "confidence": self.confidence,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[JourneyIntelligenceService] = None


def get_journey_intelligence_service() -> JourneyIntelligenceService:
    """Get singleton service."""
    global _service
    if _service is None:
        _service = JourneyIntelligenceService()
    return _service


# Alias for backward compatibility with full_intelligence_integration.py
def get_journey_intelligence_analyzer() -> JourneyIntelligenceService:
    """
    Alias for get_journey_intelligence_service().
    
    Used by full_intelligence_integration.py for journey pattern analysis.
    """
    return get_journey_intelligence_service()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def get_journey_intelligence(asin: str) -> JourneyIntelligence:
    """
    Get journey intelligence for a product.
    
    Tries in-memory first, then falls back to graph.
    """
    service = get_journey_intelligence_service()
    
    # Check in-memory first
    if asin in service._products:
        return service.get_journey_intelligence(asin)
    
    # Fall back to graph
    return await service.get_journey_from_graph(asin)
