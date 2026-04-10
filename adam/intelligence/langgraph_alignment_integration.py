#!/usr/bin/env python3
"""
LANGGRAPH ALIGNMENT INTEGRATION
===============================

Integrates the Customer-Advertisement Alignment System into the LangGraph
workflow as a first-class citizen. This creates a closed-loop learning
system that:

1. Profiles customers and advertisements in real-time
2. Calculates alignment scores for routing decisions
3. Captures outcomes for learning feedback
4. Updates alignment matrices based on empirical evidence
5. Stores learned patterns in Neo4j

Architecture:
┌──────────────────────────────────────────────────────────────────────┐
│                        ADAM ALIGNMENT GRAPH                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [START] ─▶ [Profile Customer] ─▶ [Profile Ad/Product]              │
│                                            │                         │
│                                            ▼                         │
│                               [Calculate Alignment]                  │
│                                            │                         │
│              ┌─────────────────────────────┼─────────────────┐       │
│              ▼                             ▼                 ▼       │
│      [High Alignment]           [Medium Alignment]    [Low Alignment]│
│      (Proceed with ad)          (Optimize first)      (Find better)  │
│              │                             │                 │       │
│              └─────────────────────────────┴─────────────────┘       │
│                                            │                         │
│                                            ▼                         │
│                               [Execute & Track]                      │
│                                            │                         │
│                                            ▼                         │
│                               [Outcome Capture]                      │
│                                            │                         │
│                                            ▼                         │
│                               [Learning Update]                      │
│                                            │                         │
│                                            ▼                         │
│                                        [END]                         │
└──────────────────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Annotated
from enum import Enum
import json
import time
from datetime import datetime
from pathlib import Path

# LangGraph imports (conditional for when not installed)
try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"

from .customer_ad_alignment import (
    CustomerAdAlignmentService,
    AlignmentScore,
    export_alignment_priors,
)
from .advertisement_psychology_framework import (
    AdvertisementProfile,
    create_advertisement_profile,
    export_advertisement_framework_priors,
)
from .expanded_type_integration import (
    ExpandedTypeIntegrationService,
    UnifiedGranularType,
    export_expanded_priors,
)


# =============================================================================
# STATE DEFINITIONS
# =============================================================================

class AlignmentDecision(Enum):
    """Routing decisions based on alignment score."""
    PROCEED = "proceed"  # High alignment - use ad as-is
    OPTIMIZE = "optimize"  # Medium alignment - adjust ad
    FIND_BETTER = "find_better"  # Low alignment - find different ad
    ABORT = "abort"  # Very low alignment - don't show ad


@dataclass
class AlignmentState:
    """
    State object for the alignment workflow.
    """
    
    # Input
    customer_text: Optional[str] = None
    customer_motivation: Optional[str] = None
    customer_decision_style: Optional[str] = None
    customer_archetype: str = "pragmatist"
    
    ad_text: Optional[str] = None
    product_id: Optional[str] = None
    
    context_domain: Optional[str] = None
    context_time_slot: Optional[str] = None
    
    # Computed profiles
    customer_profile: Optional[Dict[str, Any]] = None
    ad_profile: Optional[Dict[str, Any]] = None
    
    # Alignment results
    alignment_score: Optional[Dict[str, Any]] = None
    alignment_decision: Optional[str] = None
    
    # Optimization (if needed)
    optimized_ad: Optional[str] = None
    alternative_ads: Optional[List[Dict[str, Any]]] = None
    
    # Execution tracking
    execution_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    # Outcome (for learning)
    outcome_captured: bool = False
    outcome_conversion: Optional[bool] = None
    outcome_engagement: Optional[float] = None
    outcome_sentiment: Optional[float] = None
    
    # Learning updates
    learning_applied: bool = False
    matrix_updates: Optional[Dict[str, Any]] = None


# =============================================================================
# ALIGNMENT GRAPH NODES
# =============================================================================

class AlignmentGraphNodes:
    """
    Node implementations for the alignment workflow.
    """
    
    def __init__(self):
        self.alignment_service = CustomerAdAlignmentService()
        self.type_service = ExpandedTypeIntegrationService()
        
        # Thresholds for routing decisions
        self.HIGH_ALIGNMENT_THRESHOLD = 0.65
        self.MEDIUM_ALIGNMENT_THRESHOLD = 0.45
        self.ABORT_THRESHOLD = 0.25
    
    def profile_customer_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Profile the customer from text or explicit parameters.
        """
        
        if state.get("customer_text"):
            # Infer from text
            customer = self.type_service.infer_type_from_text(
                state["customer_text"],
                state.get("customer_archetype", "pragmatist")
            )
        else:
            # Use explicit parameters
            customer = self.type_service.get_unified_type(
                motivation=state.get("customer_motivation", "functional_need"),
                decision_style=state.get("customer_decision_style", "moderate"),
                archetype=state.get("customer_archetype", "pragmatist"),
            )
        
        # Store profile as dict for state serialization
        state["customer_profile"] = {
            "type_code": customer.original_type_code,
            "expanded_type_code": customer.expanded_type_code,
            "motivation": customer.motivation,
            "expanded_motivation": customer.expanded_motivation,
            "decision_style": customer.decision_style,
            "expanded_decision_style": customer.expanded_decision_style,
            "archetype": customer.archetype,
            "persuadability_score": customer.persuadability_score,
            "cognitive_load_tolerance": customer.cognitive_load_tolerance,
            "social_influence_type": customer.social_influence_type,
        }
        
        state["timestamp"] = datetime.now().isoformat()
        state["execution_id"] = f"align_{int(time.time() * 1000)}"
        
        return state
    
    def profile_ad_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Profile the advertisement or product description.
        """
        
        if not state.get("ad_text"):
            raise ValueError("ad_text is required")
        
        ad_profile = create_advertisement_profile(
            state["ad_text"],
            state.get("product_id", "ad_001")
        )
        
        # Store profile as dict
        state["ad_profile"] = ad_profile.to_dict()
        
        return state
    
    def calculate_alignment_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate alignment between customer and ad profiles.
        """
        
        # Reconstruct customer type from profile dict
        customer_profile = state["customer_profile"]
        customer = self.type_service.get_unified_type(
            motivation=customer_profile["motivation"],
            decision_style=customer_profile["decision_style"],
            archetype=customer_profile["archetype"],
            expanded_motivation=customer_profile.get("expanded_motivation"),
            expanded_decision_style=customer_profile.get("expanded_decision_style"),
        )
        
        # Reconstruct ad profile
        ad_profile = create_advertisement_profile(
            state["ad_text"],
            state.get("product_id", "ad_001")
        )
        
        # Calculate alignment
        alignment = self.alignment_service.calculate_alignment(customer, ad_profile)
        
        # Store alignment as dict
        state["alignment_score"] = alignment.to_dict()
        
        # Determine routing decision
        overall = alignment.overall_alignment
        
        if overall >= self.HIGH_ALIGNMENT_THRESHOLD:
            state["alignment_decision"] = AlignmentDecision.PROCEED.value
        elif overall >= self.MEDIUM_ALIGNMENT_THRESHOLD:
            state["alignment_decision"] = AlignmentDecision.OPTIMIZE.value
        elif overall >= self.ABORT_THRESHOLD:
            state["alignment_decision"] = AlignmentDecision.FIND_BETTER.value
        else:
            state["alignment_decision"] = AlignmentDecision.ABORT.value
        
        return state
    
    def optimize_ad_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate optimized ad suggestions based on customer profile.
        """
        
        alignment = state["alignment_score"]
        customer = state["customer_profile"]
        
        suggestions = alignment["recommendations"]["suggestions"]
        
        # Generate optimization recommendations
        state["optimized_ad"] = {
            "original": state["ad_text"],
            "suggestions": suggestions,
            "recommended_mechanisms": self._get_recommended_mechanisms(customer),
            "recommended_emotions": self._get_recommended_emotions(customer),
            "recommended_style": self._get_recommended_style(customer),
        }
        
        return state
    
    def find_alternatives_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find alternative ads/products with better alignment.
        """
        
        customer = state["customer_profile"]
        
        # This would typically query a database of pre-profiled ads
        # For now, generate recommendations based on customer profile
        state["alternative_ads"] = [
            {
                "recommendation": f"Find ads emphasizing {customer['expanded_motivation']} motivation",
                "optimal_mechanisms": self._get_recommended_mechanisms(customer),
                "avoid_mechanisms": self._get_avoid_mechanisms(customer),
            }
        ]
        
        return state
    
    def capture_outcome_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture actual outcome for learning.
        
        This would typically be called asynchronously after ad exposure.
        """
        
        # In practice, this receives outcome data from tracking systems
        state["outcome_captured"] = True
        
        return state
    
    def learning_update_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update alignment matrices based on outcome.
        
        This is where the system learns from experience.
        """
        
        if not state.get("outcome_captured"):
            return state
        
        alignment = state["alignment_score"]
        outcome = {
            "conversion": state.get("outcome_conversion"),
            "engagement": state.get("outcome_engagement"),
            "sentiment": state.get("outcome_sentiment"),
        }
        
        # Calculate prediction error
        predicted_effectiveness = alignment["scores"]["predicted_effectiveness"]
        actual_effectiveness = self._calculate_actual_effectiveness(outcome)
        
        if actual_effectiveness is not None:
            prediction_error = actual_effectiveness - predicted_effectiveness
            
            # Generate matrix updates
            state["matrix_updates"] = {
                "prediction_error": prediction_error,
                "customer_profile": state["customer_profile"],
                "ad_profile": state["ad_profile"],
                "alignment_components": alignment["components"],
                "outcome": outcome,
                "timestamp": datetime.now().isoformat(),
            }
            
            state["learning_applied"] = True
        
        return state
    
    def _get_recommended_mechanisms(self, customer: Dict[str, Any]) -> List[str]:
        """Get recommended persuasion mechanisms for customer."""
        
        decision_style = customer.get("expanded_decision_style", "satisficing")
        
        mechanism_recommendations = {
            "gut_instinct": ["scarcity", "liking", "social_proof"],
            "analytical_systematic": ["authority", "commitment"],
            "affect_driven": ["liking", "reciprocity"],
            "social_referencing": ["social_proof", "unity"],
            "authority_deferring": ["authority", "commitment"],
        }
        
        return mechanism_recommendations.get(decision_style, ["social_proof", "authority"])
    
    def _get_recommended_emotions(self, customer: Dict[str, Any]) -> List[str]:
        """Get recommended emotional appeals for customer."""
        
        motivation = customer.get("expanded_motivation", "functional_need")
        
        emotion_recommendations = {
            "immediate_gratification": ["excitement", "joy"],
            "mastery_seeking": ["pride", "empowerment"],
            "anxiety_reduction": ["trust", "contentment"],
            "status_signaling": ["pride", "envy"],
            "social_approval": ["belonging_connection", "joy"],
        }
        
        return emotion_recommendations.get(motivation, ["trust", "contentment"])
    
    def _get_recommended_style(self, customer: Dict[str, Any]) -> str:
        """Get recommended linguistic style for customer."""
        
        cognitive_load = customer.get("cognitive_load_tolerance", "moderate_cognitive")
        
        style_recommendations = {
            "minimal_cognitive": "minimalist",
            "moderate_cognitive": "conversational",
            "high_cognitive": "technical",
        }
        
        return style_recommendations.get(cognitive_load, "conversational")
    
    def _get_avoid_mechanisms(self, customer: Dict[str, Any]) -> List[str]:
        """Get mechanisms to avoid for customer."""
        
        social_influence = customer.get("social_influence_type", "socially_aware")
        
        avoid_recommendations = {
            "highly_independent": ["bandwagon", "social_proof_numbers"],
            "informational_seeker": ["scarcity_limited_time", "fear_appeal"],
        }
        
        return avoid_recommendations.get(social_influence, [])
    
    def _calculate_actual_effectiveness(self, outcome: Dict[str, Any]) -> Optional[float]:
        """Calculate actual effectiveness from outcome data."""
        
        if outcome.get("conversion") is not None:
            conversion_score = 1.0 if outcome["conversion"] else 0.0
        else:
            conversion_score = None
        
        engagement = outcome.get("engagement")
        sentiment = outcome.get("sentiment")
        
        scores = [s for s in [conversion_score, engagement, sentiment] if s is not None]
        
        if scores:
            return sum(scores) / len(scores)
        return None


# =============================================================================
# LANGGRAPH WORKFLOW BUILDER
# =============================================================================

def build_alignment_graph():
    """
    Build the LangGraph workflow for customer-ad alignment.
    """
    
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("LangGraph is not installed. Install with: pip install langgraph")
    
    nodes = AlignmentGraphNodes()
    
    # Create the graph
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("profile_customer", nodes.profile_customer_node)
    workflow.add_node("profile_ad", nodes.profile_ad_node)
    workflow.add_node("calculate_alignment", nodes.calculate_alignment_node)
    workflow.add_node("optimize_ad", nodes.optimize_ad_node)
    workflow.add_node("find_alternatives", nodes.find_alternatives_node)
    workflow.add_node("capture_outcome", nodes.capture_outcome_node)
    workflow.add_node("learning_update", nodes.learning_update_node)
    
    # Define edges
    workflow.set_entry_point("profile_customer")
    workflow.add_edge("profile_customer", "profile_ad")
    workflow.add_edge("profile_ad", "calculate_alignment")
    
    # Conditional routing based on alignment
    def route_by_alignment(state: Dict[str, Any]) -> str:
        decision = state.get("alignment_decision", AlignmentDecision.PROCEED.value)
        
        if decision == AlignmentDecision.PROCEED.value:
            return "capture_outcome"
        elif decision == AlignmentDecision.OPTIMIZE.value:
            return "optimize_ad"
        elif decision == AlignmentDecision.FIND_BETTER.value:
            return "find_alternatives"
        else:  # ABORT
            return "capture_outcome"  # Still capture for learning
    
    workflow.add_conditional_edges(
        "calculate_alignment",
        route_by_alignment,
        {
            "capture_outcome": "capture_outcome",
            "optimize_ad": "optimize_ad",
            "find_alternatives": "find_alternatives",
        }
    )
    
    workflow.add_edge("optimize_ad", "capture_outcome")
    workflow.add_edge("find_alternatives", "capture_outcome")
    workflow.add_edge("capture_outcome", "learning_update")
    workflow.add_edge("learning_update", END)
    
    return workflow.compile()


# =============================================================================
# STANDALONE ALIGNMENT PIPELINE
# =============================================================================

class AlignmentPipeline:
    """
    Standalone alignment pipeline for use without LangGraph.
    Provides the same functionality with explicit step execution.
    """
    
    def __init__(self):
        self.nodes = AlignmentGraphNodes()
    
    def run(
        self,
        customer_text: Optional[str] = None,
        customer_motivation: Optional[str] = None,
        customer_decision_style: Optional[str] = None,
        customer_archetype: str = "pragmatist",
        ad_text: str = "",
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the alignment pipeline.
        """
        
        # Initialize state
        state = {
            "customer_text": customer_text,
            "customer_motivation": customer_motivation,
            "customer_decision_style": customer_decision_style,
            "customer_archetype": customer_archetype,
            "ad_text": ad_text,
            "product_id": product_id,
        }
        
        # Execute nodes in sequence
        state = self.nodes.profile_customer_node(state)
        state = self.nodes.profile_ad_node(state)
        state = self.nodes.calculate_alignment_node(state)
        
        # Route based on alignment
        decision = state.get("alignment_decision")
        
        if decision == AlignmentDecision.OPTIMIZE.value:
            state = self.nodes.optimize_ad_node(state)
        elif decision == AlignmentDecision.FIND_BETTER.value:
            state = self.nodes.find_alternatives_node(state)
        
        return state
    
    def capture_outcome(
        self,
        state: Dict[str, Any],
        conversion: Optional[bool] = None,
        engagement: Optional[float] = None,
        sentiment: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Capture outcome and trigger learning.
        """
        
        state["outcome_conversion"] = conversion
        state["outcome_engagement"] = engagement
        state["outcome_sentiment"] = sentiment
        
        state = self.nodes.capture_outcome_node(state)
        state = self.nodes.learning_update_node(state)
        
        return state


# =============================================================================
# BATCH PROCESSING FOR HISTORICAL DATA
# =============================================================================

class HistoricalDataProcessor:
    """
    Processor for analyzing historical reviews and product descriptions.
    Designed for batch processing at scale.
    """
    
    def __init__(self, batch_size: int = 1000):
        self.alignment_service = CustomerAdAlignmentService()
        self.batch_size = batch_size
        self.processed_count = 0
        self.alignment_stats = {
            "total": 0,
            "high_alignment": 0,
            "medium_alignment": 0,
            "low_alignment": 0,
            "average_alignment": 0.0,
        }
    
    def process_review_product_pair(
        self,
        review_text: str,
        product_description: str,
        review_rating: Optional[float] = None,
        archetype: str = "pragmatist",
    ) -> Dict[str, Any]:
        """
        Process a single review-product pair.
        """
        
        alignment = self.alignment_service.analyze_ad_for_customer_text(
            customer_text=review_text,
            ad_text=product_description,
            archetype=archetype,
        )
        
        result = {
            "alignment": alignment.to_dict(),
            "review_sentiment_inferred": self._infer_sentiment_from_rating(review_rating),
            "prediction_vs_reality": None,
        }
        
        # If we have rating, calculate prediction accuracy
        if review_rating is not None:
            actual_satisfaction = review_rating / 5.0  # Normalize to 0-1
            predicted_effectiveness = alignment.predicted_effectiveness
            result["prediction_vs_reality"] = {
                "predicted": predicted_effectiveness,
                "actual": actual_satisfaction,
                "error": actual_satisfaction - predicted_effectiveness,
            }
        
        # Update stats
        self.processed_count += 1
        self._update_stats(alignment.overall_alignment)
        
        return result
    
    def process_batch(
        self,
        batch: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of review-product pairs.
        
        Each item in batch should have:
        - review_text: str
        - product_description: str
        - review_rating: Optional[float]
        """
        
        results = []
        
        for item in batch:
            result = self.process_review_product_pair(
                review_text=item["review_text"],
                product_description=item["product_description"],
                review_rating=item.get("review_rating"),
            )
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        
        return {
            **self.alignment_stats,
            "processed_count": self.processed_count,
        }
    
    def _update_stats(self, alignment_score: float) -> None:
        """Update running statistics."""
        
        self.alignment_stats["total"] += 1
        
        if alignment_score >= 0.65:
            self.alignment_stats["high_alignment"] += 1
        elif alignment_score >= 0.45:
            self.alignment_stats["medium_alignment"] += 1
        else:
            self.alignment_stats["low_alignment"] += 1
        
        # Running average
        n = self.alignment_stats["total"]
        old_avg = self.alignment_stats["average_alignment"]
        self.alignment_stats["average_alignment"] = (old_avg * (n - 1) + alignment_score) / n
    
    def _infer_sentiment_from_rating(self, rating: Optional[float]) -> Optional[str]:
        """Infer sentiment category from rating."""
        
        if rating is None:
            return None
        
        if rating >= 4.5:
            return "very_positive"
        elif rating >= 3.5:
            return "positive"
        elif rating >= 2.5:
            return "neutral"
        elif rating >= 1.5:
            return "negative"
        else:
            return "very_negative"


# =============================================================================
# NEO4J LEARNING STORE
# =============================================================================

class Neo4jLearningStore:
    """
    Store and retrieve learned alignment patterns from Neo4j.
    """
    
    STORE_PATTERN_QUERY = """
    MERGE (c:CustomerType {motivation: $motivation, decision_style: $decision_style})
    MERGE (a:AdType {persuasion: $persuasion, emotion: $emotion, value: $value})
    MERGE (c)-[r:ALIGNED_WITH]->(a)
    SET r.alignment_score = $alignment_score,
        r.prediction_error = $prediction_error,
        r.sample_count = COALESCE(r.sample_count, 0) + 1,
        r.last_updated = datetime()
    RETURN r
    """
    
    GET_LEARNED_ALIGNMENT_QUERY = """
    MATCH (c:CustomerType {motivation: $motivation, decision_style: $decision_style})
    MATCH (a:AdType {persuasion: $persuasion})
    MATCH (c)-[r:ALIGNED_WITH]->(a)
    WHERE r.sample_count >= 10
    RETURN r.alignment_score as learned_alignment,
           r.prediction_error as avg_error,
           r.sample_count as samples
    """
    
    def __init__(self, driver=None):
        self.driver = driver
    
    def store_alignment_pattern(
        self,
        customer_profile: Dict[str, Any],
        ad_profile: Dict[str, Any],
        alignment_score: float,
        prediction_error: float,
    ) -> None:
        """Store a learned alignment pattern."""
        
        if not self.driver:
            return
        
        with self.driver.session() as session:
            session.run(
                self.STORE_PATTERN_QUERY,
                motivation=customer_profile.get("expanded_motivation"),
                decision_style=customer_profile.get("expanded_decision_style"),
                persuasion=ad_profile.get("persuasion", {}).get("primary"),
                emotion=ad_profile.get("emotion", {}).get("primary"),
                value=ad_profile.get("value", {}).get("primary"),
                alignment_score=alignment_score,
                prediction_error=prediction_error,
            )
    
    def get_learned_alignment(
        self,
        customer_motivation: str,
        customer_decision_style: str,
        ad_persuasion: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve learned alignment from historical data."""
        
        if not self.driver:
            return None
        
        with self.driver.session() as session:
            result = session.run(
                self.GET_LEARNED_ALIGNMENT_QUERY,
                motivation=customer_motivation,
                decision_style=customer_decision_style,
                persuasion=ad_persuasion,
            )
            
            record = result.single()
            if record:
                return {
                    "learned_alignment": record["learned_alignment"],
                    "avg_error": record["avg_error"],
                    "samples": record["samples"],
                }
        
        return None


# =============================================================================
# EXPORTS
# =============================================================================

def export_integration_priors() -> Dict[str, Any]:
    """Export all integration data for cold-start priors."""
    
    return {
        "customer_priors": export_expanded_priors(),
        "ad_priors": export_advertisement_framework_priors(),
        "alignment_priors": export_alignment_priors(),
        "integration_config": {
            "high_alignment_threshold": 0.65,
            "medium_alignment_threshold": 0.45,
            "abort_threshold": 0.25,
            "learning_min_samples": 10,
        },
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("LANGGRAPH ALIGNMENT INTEGRATION TEST")
    print("="*70)
    
    # Test standalone pipeline
    pipeline = AlignmentPipeline()
    
    print("\n=== Alignment Pipeline Test ===")
    
    result = pipeline.run(
        customer_text="I need this NOW! So excited about this deal!",
        ad_text="LIMITED TIME OFFER! Only 3 left. Join millions of happy customers!",
    )
    
    print(f"\nCustomer Profile:")
    print(f"  Motivation: {result['customer_profile']['expanded_motivation']}")
    print(f"  Decision Style: {result['customer_profile']['expanded_decision_style']}")
    print(f"  Persuadability: {result['customer_profile']['persuadability_score']:.0%}")
    
    print(f"\nAd Profile:")
    print(f"  Persuasion: {result['ad_profile']['persuasion']['primary']}")
    print(f"  Emotion: {result['ad_profile']['emotion']['primary']}")
    
    print(f"\nAlignment Results:")
    print(f"  Overall: {result['alignment_score']['scores']['overall_alignment']:.0%}")
    print(f"  Predicted Effectiveness: {result['alignment_score']['scores']['predicted_effectiveness']:.0%}")
    print(f"  Decision: {result['alignment_decision'].upper()}")
    
    # Test historical data processor
    print("\n\n=== Historical Data Processor Test ===")
    
    processor = HistoricalDataProcessor()
    
    # Simulate processing reviews
    test_reviews = [
        {
            "review_text": "Amazing product! Exactly what I needed!",
            "product_description": "Premium quality, trusted by experts. Satisfaction guaranteed.",
            "review_rating": 5.0,
        },
        {
            "review_text": "It's okay, nothing special.",
            "product_description": "LIMITED OFFER! ACT NOW! DON'T MISS OUT!",
            "review_rating": 3.0,
        },
        {
            "review_text": "Waste of money. Doesn't work as advertised.",
            "product_description": "Revolutionary breakthrough! Proven results!",
            "review_rating": 1.0,
        },
    ]
    
    for review in test_reviews:
        result = processor.process_review_product_pair(
            review_text=review["review_text"],
            product_description=review["product_description"],
            review_rating=review["review_rating"],
        )
        
        pred_vs_real = result.get("prediction_vs_reality", {})
        print(f"\nReview: \"{review['review_text'][:40]}...\"")
        print(f"  Rating: {review['review_rating']}/5")
        print(f"  Alignment: {result['alignment']['scores']['overall_alignment']:.0%}")
        if pred_vs_real:
            print(f"  Predicted: {pred_vs_real['predicted']:.0%}, Actual: {pred_vs_real['actual']:.0%}")
            print(f"  Error: {pred_vs_real['error']:+.0%}")
    
    print(f"\n\nProcessing Stats:")
    stats = processor.get_stats()
    print(f"  Total Processed: {stats['processed_count']}")
    print(f"  Average Alignment: {stats['average_alignment']:.0%}")
    print(f"  High/Medium/Low: {stats['high_alignment']}/{stats['medium_alignment']}/{stats['low_alignment']}")
