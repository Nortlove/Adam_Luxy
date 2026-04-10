#!/usr/bin/env python3
"""
CUSTOMER INFLUENCE GRAPH
========================

Phase 6+ Enhancement: Track Customer-to-Customer Influence

This module models how customers influence each other through reviews.
When Customer A's review gets helpful votes, it means other customers
found it influential in their purchase decision.

Key Insight (from ADAM_CORE_PHILOSOPHY.md):
"Something we failed to take out of the Amazon review was the information
on 'up votes' - where one customer gives a thumbs up to another customer
review and acknowledges that the review was helpful in helping them
decide to buy or not to buy."

This creates an implicit INFLUENCE GRAPH:
- Nodes: Reviews (representing customer voices)
- Edges: Helpful votes (representing influence)
- Edge Weight: The review influenced a purchase decision

We can use this to:
1. Identify "super-influencer" reviews
2. Learn what language patterns spread influence
3. Build customer archetypes from influential reviewers
4. Weight learning by influence power
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime
import math

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class InfluenceNode:
    """A node in the influence graph (a review/customer)."""
    
    node_id: str                          # Unique ID (usually review ID)
    review_text: str = ""
    helpful_votes: int = 0
    rating: float = 0.0
    verified_purchase: bool = False
    
    # Influence metrics
    influence_score: float = 0.0          # Computed influence
    influence_tier: str = "standard"      # super, high, medium, standard
    
    # Psychological profile (if analyzed)
    construct_profile: Dict[str, float] = field(default_factory=dict)
    persuasion_profile: Dict[str, float] = field(default_factory=dict)
    
    # Temporal
    review_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "helpful_votes": self.helpful_votes,
            "rating": self.rating,
            "influence_score": self.influence_score,
            "influence_tier": self.influence_tier,
            "verified_purchase": self.verified_purchase,
        }


@dataclass
class InfluenceEdge:
    """An edge in the influence graph (helpful vote relationship)."""
    
    source_id: str          # Review that was helpful
    target_id: str          # Customer who found it helpful (implicit)
    weight: float = 1.0     # Influence strength
    edge_type: str = "helpful_vote"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "weight": self.weight,
            "type": self.edge_type,
        }


@dataclass
class InfluenceCluster:
    """A cluster of similarly influential reviewers."""
    
    cluster_id: str
    cluster_name: str
    
    # Cluster members
    member_ids: List[str] = field(default_factory=list)
    
    # Aggregate profile
    avg_influence_score: float = 0.0
    total_helpful_votes: int = 0
    
    # Dominant characteristics
    dominant_constructs: Dict[str, float] = field(default_factory=dict)
    dominant_persuasion: Dict[str, float] = field(default_factory=dict)
    common_language_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "member_count": len(self.member_ids),
            "avg_influence_score": self.avg_influence_score,
            "total_helpful_votes": self.total_helpful_votes,
            "dominant_constructs": self.dominant_constructs,
            "dominant_persuasion": self.dominant_persuasion,
        }


# =============================================================================
# INFLUENCE GRAPH
# =============================================================================

class CustomerInfluenceGraph:
    """
    Models customer-to-customer influence through reviews.
    
    This is an implicit graph where helpful votes create edges
    between the review author and the voters.
    """
    
    def __init__(self):
        # Graph structure
        self._nodes: Dict[str, InfluenceNode] = {}
        self._edges: List[InfluenceEdge] = []
        
        # Indexes
        self._by_product: Dict[str, List[str]] = defaultdict(list)  # asin -> node_ids
        self._by_brand: Dict[str, List[str]] = defaultdict(list)    # brand -> node_ids
        self._by_influence_tier: Dict[str, List[str]] = defaultdict(list)
        
        # Clusters
        self._clusters: Dict[str, InfluenceCluster] = {}
        
        # Statistics
        self._total_influence = 0.0
    
    def add_review(
        self,
        review_id: str,
        review_text: str,
        helpful_votes: int,
        rating: float = 0.0,
        verified_purchase: bool = False,
        product_asin: Optional[str] = None,
        brand: Optional[str] = None,
        construct_profile: Optional[Dict[str, float]] = None,
        persuasion_profile: Optional[Dict[str, float]] = None,
        review_date: Optional[datetime] = None,
    ) -> InfluenceNode:
        """
        Add a review to the influence graph.
        
        Args:
            review_id: Unique review identifier
            review_text: Review text
            helpful_votes: Number of helpful votes
            rating: Star rating
            verified_purchase: Whether purchase was verified
            product_asin: Product ASIN
            brand: Brand name
            construct_profile: Psychological construct scores
            persuasion_profile: Persuasion technique scores
            review_date: Date of review
            
        Returns:
            InfluenceNode for the review
        """
        # Calculate influence score
        influence_score = self._calculate_influence_score(helpful_votes, verified_purchase)
        influence_tier = self._get_influence_tier(influence_score)
        
        node = InfluenceNode(
            node_id=review_id,
            review_text=review_text,
            helpful_votes=helpful_votes,
            rating=rating,
            verified_purchase=verified_purchase,
            influence_score=influence_score,
            influence_tier=influence_tier,
            construct_profile=construct_profile or {},
            persuasion_profile=persuasion_profile or {},
            review_date=review_date,
        )
        
        # Add to graph
        self._nodes[review_id] = node
        
        # Add implicit edges (each helpful vote = one influence edge)
        for i in range(helpful_votes):
            edge = InfluenceEdge(
                source_id=review_id,
                target_id=f"implicit_voter_{review_id}_{i}",
                weight=1.0,
            )
            self._edges.append(edge)
        
        # Update indexes
        if product_asin:
            self._by_product[product_asin].append(review_id)
        if brand:
            self._by_brand[brand.lower()].append(review_id)
        self._by_influence_tier[influence_tier].append(review_id)
        
        # Update total
        self._total_influence += influence_score
        
        return node
    
    def _calculate_influence_score(
        self,
        helpful_votes: int,
        verified_purchase: bool,
    ) -> float:
        """
        Calculate influence score for a review.
        
        Uses logarithmic scaling to handle viral reviews while
        still differentiating moderate-vote reviews.
        """
        if helpful_votes <= 0:
            base_score = 0.1
        else:
            # Log scaling: 10 votes -> 2.3, 100 votes -> 4.6, 1000 votes -> 6.9
            base_score = math.log(1 + helpful_votes)
        
        # Verified purchase bonus (more credible influence)
        if verified_purchase:
            base_score *= 1.2
        
        return base_score
    
    def _get_influence_tier(self, score: float) -> str:
        """Get influence tier from score."""
        if score >= 6.0:    # ~400+ votes
            return "super"
        elif score >= 4.0:  # ~50+ votes
            return "high"
        elif score >= 2.0:  # ~6+ votes
            return "medium"
        else:
            return "standard"
    
    def get_super_influencers(
        self,
        limit: int = 10,
        brand: Optional[str] = None,
        product_asin: Optional[str] = None,
    ) -> List[InfluenceNode]:
        """
        Get the most influential reviews.
        
        These are the reviews that have proven their persuasive power
        through high helpful vote counts.
        
        Args:
            limit: Maximum number to return
            brand: Filter by brand
            product_asin: Filter by product
            
        Returns:
            List of top InfluenceNodes
        """
        # Get candidate node IDs
        if product_asin:
            candidates = self._by_product.get(product_asin, [])
        elif brand:
            candidates = self._by_brand.get(brand.lower(), [])
        else:
            candidates = list(self._nodes.keys())
        
        # Get nodes and sort by influence
        nodes = [self._nodes[nid] for nid in candidates if nid in self._nodes]
        nodes.sort(key=lambda n: n.influence_score, reverse=True)
        
        return nodes[:limit]
    
    def get_influence_distribution(self) -> Dict[str, Any]:
        """
        Get the distribution of influence across the graph.
        
        Returns statistics about how influence is distributed.
        """
        if not self._nodes:
            return {"total_nodes": 0}
        
        scores = [n.influence_score for n in self._nodes.values()]
        votes = [n.helpful_votes for n in self._nodes.values()]
        
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "total_influence": self._total_influence,
            "tier_distribution": {
                tier: len(nodes) for tier, nodes in self._by_influence_tier.items()
            },
            "influence_stats": {
                "mean": sum(scores) / len(scores),
                "max": max(scores),
                "min": min(scores),
            },
            "vote_stats": {
                "total": sum(votes),
                "mean": sum(votes) / len(votes),
                "max": max(votes),
                "reviews_with_votes": sum(1 for v in votes if v > 0),
            },
        }
    
    def extract_influencer_archetypes(
        self,
        min_influence_score: float = 4.0,
    ) -> List[InfluenceCluster]:
        """
        Extract archetypes from high-influence reviewers.
        
        Groups influential reviewers by their psychological and
        persuasion profiles to identify "types" of effective communicators.
        
        Args:
            min_influence_score: Minimum score to include
            
        Returns:
            List of InfluenceClusters
        """
        # Get high-influence nodes
        high_influence = [
            n for n in self._nodes.values()
            if n.influence_score >= min_influence_score
        ]
        
        if not high_influence:
            return []
        
        # Simple clustering by dominant construct
        clusters_by_construct: Dict[str, List[InfluenceNode]] = defaultdict(list)
        
        for node in high_influence:
            if node.construct_profile:
                # Get dominant construct
                dominant = max(
                    node.construct_profile.items(),
                    key=lambda x: x[1],
                    default=(None, 0)
                )
                if dominant[0]:
                    clusters_by_construct[dominant[0]].append(node)
            else:
                clusters_by_construct["unclassified"].append(node)
        
        # Build cluster objects
        clusters = []
        for construct, nodes in clusters_by_construct.items():
            if len(nodes) >= 2:  # Minimum cluster size
                cluster = InfluenceCluster(
                    cluster_id=f"cluster_{construct}",
                    cluster_name=f"{construct.title()} Influencers",
                    member_ids=[n.node_id for n in nodes],
                    avg_influence_score=sum(n.influence_score for n in nodes) / len(nodes),
                    total_helpful_votes=sum(n.helpful_votes for n in nodes),
                    dominant_constructs=self._aggregate_profiles(
                        [n.construct_profile for n in nodes]
                    ),
                    dominant_persuasion=self._aggregate_profiles(
                        [n.persuasion_profile for n in nodes]
                    ),
                )
                clusters.append(cluster)
        
        # Store clusters
        for cluster in clusters:
            self._clusters[cluster.cluster_id] = cluster
        
        return clusters
    
    def _aggregate_profiles(
        self,
        profiles: List[Dict[str, float]],
    ) -> Dict[str, float]:
        """Aggregate multiple profiles into dominant traits."""
        if not profiles:
            return {}
        
        aggregated: Dict[str, List[float]] = defaultdict(list)
        for profile in profiles:
            for key, value in profile.items():
                aggregated[key].append(value)
        
        return {
            key: sum(values) / len(values)
            for key, values in aggregated.items()
            if values
        }
    
    def get_influence_weighted_profile(
        self,
        brand: Optional[str] = None,
        product_asin: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get psychological profile weighted by influence.
        
        More influential reviews get more weight in the aggregate profile.
        This gives us the "voice" of effective communicators for a brand.
        
        Args:
            brand: Filter by brand
            product_asin: Filter by product
            
        Returns:
            Influence-weighted aggregate profile
        """
        # Get relevant nodes
        if product_asin:
            node_ids = self._by_product.get(product_asin, [])
        elif brand:
            node_ids = self._by_brand.get(brand.lower(), [])
        else:
            node_ids = list(self._nodes.keys())
        
        nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]
        
        if not nodes:
            return {}
        
        # Weighted aggregation
        total_weight = sum(n.influence_score for n in nodes)
        if total_weight == 0:
            return {}
        
        weighted_constructs: Dict[str, float] = defaultdict(float)
        weighted_persuasion: Dict[str, float] = defaultdict(float)
        
        for node in nodes:
            weight = node.influence_score / total_weight
            
            for key, value in node.construct_profile.items():
                weighted_constructs[key] += value * weight
            
            for key, value in node.persuasion_profile.items():
                weighted_persuasion[key] += value * weight
        
        return {
            "weighted_constructs": dict(weighted_constructs),
            "weighted_persuasion": dict(weighted_persuasion),
            "total_influence": total_weight,
            "node_count": len(nodes),
            "super_influencer_count": sum(1 for n in nodes if n.influence_tier == "super"),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "brands": len(self._by_brand),
            "products": len(self._by_product),
            "clusters": len(self._clusters),
            "total_influence": self._total_influence,
            "distribution": self.get_influence_distribution(),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_graph: Optional[CustomerInfluenceGraph] = None


def get_customer_influence_graph() -> CustomerInfluenceGraph:
    """Get singleton customer influence graph."""
    global _graph
    if _graph is None:
        _graph = CustomerInfluenceGraph()
    return _graph


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def add_review_to_influence_graph(
    review_id: str,
    review_text: str,
    helpful_votes: int,
    **kwargs,
) -> Dict[str, Any]:
    """
    Add a review to the influence graph.
    
    Returns the created node as a dict.
    """
    graph = get_customer_influence_graph()
    node = graph.add_review(review_id, review_text, helpful_votes, **kwargs)
    return node.to_dict()


def get_top_influencers(
    limit: int = 10,
    brand: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get top influencer reviews for a brand."""
    graph = get_customer_influence_graph()
    nodes = graph.get_super_influencers(limit=limit, brand=brand)
    return [n.to_dict() for n in nodes]


def get_brand_influence_profile(brand: str) -> Dict[str, Any]:
    """Get influence-weighted profile for a brand."""
    graph = get_customer_influence_graph()
    return graph.get_influence_weighted_profile(brand=brand)
