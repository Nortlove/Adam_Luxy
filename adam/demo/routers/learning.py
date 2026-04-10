# =============================================================================
# ADAM Demo - Learning Router
# Learning system endpoints
# =============================================================================

"""
Learning system API endpoints for the ADAM demo platform.

Includes:
- Learning cycle simulation
- Learning progression demonstration
- Learning statistics
- Graph insights for mechanisms
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Learning"])


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================

@router.post("/learning/simulate-cycle")
async def simulate_learning_cycle(
    archetype: str = Query(..., description="Customer archetype (e.g., achievement_driven)"),
    mechanism: str = Query(..., description="Mechanism to test (e.g., regulatory_focus)"),
) -> Dict[str, Any]:
    """
    Simulate a single learning cycle to demonstrate Thompson Sampling.
    
    This shows:
    1. Current posterior belief about mechanism effectiveness
    2. Simulated campaign outcome (based on psychological research)
    3. Updated posterior after learning
    4. Plain English explanation of what the system learned
    
    Perfect for demonstrating ADAM's learning capabilities in sales presentations.
    """
    try:
        from adam.demo.demo_learning import get_demo_learner
        
        learner = get_demo_learner()
        result = await learner.learn_from_simulated_campaign(
            archetype=archetype,
            mechanism=mechanism,
        )
        
        return {
            "archetype": result.archetype,
            "mechanism": result.mechanism,
            "before": {
                "effectiveness": result.before_posterior_mean,
                "confidence": 1 - result.before_uncertainty,
                "alpha": result.before_posterior_alpha,
                "beta": result.before_posterior_beta,
            },
            "simulation": {
                "outcome": "SUCCESS" if result.simulated_outcome else "FAILED",
                "probability": result.outcome_probability,
                "reasoning": result.simulation_reasoning,
            },
            "after": {
                "effectiveness": result.after_posterior_mean,
                "confidence": 1 - result.after_uncertainty,
                "alpha": result.after_posterior_alpha,
                "beta": result.after_posterior_beta,
            },
            "learning": {
                "effectiveness_change": result.mean_change,
                "direction": "improved" if result.mean_change > 0 else "decreased" if result.mean_change < 0 else "unchanged",
                "explanation": result.explanation,
            },
        }
    except ImportError as e:
        logger.warning(f"Demo learning module not available: {e}")
        raise HTTPException(status_code=503, detail="Learning system not available")
    except Exception as e:
        logger.error(f"Error in learning simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/demo-progression")
async def run_learning_demo(
    archetype: str = Query(..., description="Customer archetype to learn about"),
    cycles: int = Query(default=10, ge=1, le=50, description="Number of learning cycles"),
) -> Dict[str, Any]:
    """
    Run multiple learning cycles to demonstrate learning progression.
    
    This shows the system improving its mechanism selection over time,
    learning which mechanisms work best for each archetype.
    
    Great for demonstrating continuous improvement in demo presentations.
    """
    try:
        from adam.demo.demo_learning import get_demo_learner
        
        learner = get_demo_learner()
        summary = await learner.run_learning_demo(
            archetype=archetype,
            n_cycles=cycles,
        )
        
        return {
            "archetype": summary["archetype"],
            "cycles_completed": summary["cycles_run"],
            "success_rate": summary["success_rate"],
            "mechanism_ranking": summary["final_mechanism_ranking"],
            "progression": summary["learning_progression"],
            "total_system_updates": summary["total_updates"],
            "interpretation": (
                f"After {summary['cycles_run']} simulated campaigns, ADAM learned which "
                f"psychological mechanisms work best for {archetype.replace('_', ' ')} customers. "
                f"The top mechanism is now {summary['final_mechanism_ranking'][0]['mechanism']} "
                f"with {summary['final_mechanism_ranking'][0]['expected_effectiveness']:.0%} expected effectiveness."
            ),
        }
    except ImportError as e:
        logger.warning(f"Demo learning module not available: {e}")
        raise HTTPException(status_code=503, detail="Learning system not available")
    except Exception as e:
        logger.error(f"Error in learning demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/stats")
async def get_learning_stats() -> Dict[str, Any]:
    """
    Get current learning system statistics.
    
    Shows the accumulated knowledge from all learning cycles.
    """
    try:
        from adam.demo.demo_learning import get_demo_learner
        
        learner = get_demo_learner()
        return learner.get_learning_stats()
    except ImportError as e:
        logger.warning(f"Demo learning module not available: {e}")
        raise HTTPException(status_code=503, detail="Learning system not available")
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GRAPH INSIGHTS ENDPOINTS
# =============================================================================

@router.get("/graph/insights/{mechanism}")
async def get_mechanism_insights(mechanism: str) -> Dict[str, Any]:
    """
    Get comprehensive graph-based insights for a mechanism.
    
    Shows:
    - Synergies with other mechanisms
    - Antagonisms to avoid
    - Research domain backing
    - Effective sequences
    """
    try:
        from adam.intelligence.graph_edge_service import get_graph_edge_service
        
        service = get_graph_edge_service()
        
        # Get synergies
        synergies = await service.get_mechanism_synergies(mechanism)
        
        # Get research backing
        research = await service.get_research_backing(mechanism)
        
        # Get causal paths involving this mechanism
        causal = await service.find_causal_paths("conversion")
        relevant_paths = [
            p for p in causal
            if mechanism in p.path_nodes
        ]
        
        # Get temporal sequences
        sequences = await service.find_effective_sequences("conversion")
        relevant_sequences = [
            s for s in sequences
            if mechanism in s.get("sequence", [])
        ]
        
        return {
            "mechanism": mechanism,
            "synergies": [
                {
                    "target": s.target_mechanism,
                    "type": s.relationship_type,
                    "multiplier": s.synergy_multiplier,
                    "context": s.context,
                }
                for s in synergies
            ],
            "research_backing": [
                {
                    "domain": r.research_domain,
                    "citations": r.citation_count,
                    "key_findings": r.key_findings,
                }
                for r in research
            ],
            "causal_paths": [
                {
                    "path": p.path_nodes,
                    "strength": p.path_strength,
                }
                for p in relevant_paths[:5]
            ],
            "effective_sequences": relevant_sequences[:3],
        }
    except ImportError:
        # Return mock data for demo
        return {
            "mechanism": mechanism,
            "synergies": [
                {"target": "commitment", "type": "enhances", "multiplier": 1.3, "context": "product consideration"},
                {"target": "social_proof", "type": "complements", "multiplier": 1.2, "context": "trust building"},
            ],
            "research_backing": [
                {"domain": "cognitive_psychology", "citations": 342, "key_findings": ["Effective for analytical archetypes"]},
            ],
            "causal_paths": [],
            "effective_sequences": [],
            "note": "Using demo data - graph service not connected",
        }
    except Exception as e:
        logger.error(f"Error getting mechanism insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-status")
async def get_learning_status() -> Dict[str, Any]:
    """
    Get the status of learned intelligence from re-ingestion.
    
    Shows what the system has learned from review analysis.
    """
    try:
        from adam.demo.review_intelligence import get_review_intelligence
        
        intel = get_review_intelligence()
        status = intel.get_status()
        
        return {
            "status": "active" if status.get("categories_loaded", 0) > 0 else "inactive",
            "categories_loaded": status.get("categories_loaded", 0),
            "total_templates": status.get("total_templates", 0),
            "mechanisms_tracked": status.get("mechanisms_tracked", 0),
            "archetypes_tracked": status.get("archetypes_tracked", 0),
            "last_updated": status.get("last_updated"),
        }
    except ImportError:
        return {
            "status": "not_available",
            "message": "Review intelligence module not installed",
        }
    except Exception as e:
        logger.error(f"Error getting learning status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
