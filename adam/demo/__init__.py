# =============================================================================
# ADAM Demo Application
# =============================================================================

"""
ADAM DEMONSTRATION PLATFORM

Interactive showcase for ADAM's AI-Driven Asset & Decision Manager capabilities.

This demo is designed for sales presentations and stakeholder demonstrations,
providing visual proof of ADAM's psychological intelligence infrastructure.

Key Features:
1. User Psychological Profiling - Live visualization of user state
2. Ad Decision Engine - Real-time ad personalization demonstration
3. Mechanism Reasoning - Explainable AI traces
4. A/B Testing Dashboard - Experiment effectiveness visualization
5. Learning Intelligence - Gradient Bridge feedback loops

Target Audiences:
- iHeart Media executives
- WPP Ad Desk stakeholders
- Potential platform integrators
"""

from adam.demo.app import create_demo_app
from adam.demo.api import demo_router

__all__ = [
    "create_demo_app",
    "demo_router",
]
