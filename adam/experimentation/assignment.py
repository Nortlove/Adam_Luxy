# =============================================================================
# ADAM Experiment Assignment Engine
# Location: adam/experimentation/assignment.py
# =============================================================================

"""
ASSIGNMENT ENGINE

Consistent assignment of users to experiment variants.

Features:
- Consistent hashing for sticky assignments
- Traffic splitting
- Targeting filters
- Mutual exclusion groups
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.experimentation.models import (
    Experiment,
    ExperimentVariant,
    ExperimentAssignment,
    ExperimentStatus,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class AssignmentEngine:
    """
    Engine for assigning users to experiment variants.
    
    Uses consistent hashing to ensure users get the same
    variant across sessions.
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
        salt: str = "adam_experiment_salt_v1",
    ):
        self.cache = cache
        self.salt = salt
        
        # Track assignments
        self._assignments: Dict[str, ExperimentAssignment] = {}
    
    async def get_assignment(
        self,
        experiment: Experiment,
        user_id: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExperimentAssignment]:
        """
        Get or create assignment for a user.
        
        Returns None if user is not eligible for experiment.
        """
        
        # Check experiment status
        if experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check for existing assignment
        assignment_key = f"{experiment.experiment_id}:{user_id}"
        
        existing = await self._get_cached_assignment(assignment_key)
        if existing:
            return existing
        
        # Check targeting
        if not self._check_targeting(experiment, user_id, user_context or {}):
            return None
        
        # Assign to variant
        variant = self._select_variant(experiment, user_id)
        if not variant:
            return None
        
        # Create assignment
        assignment = ExperimentAssignment(
            assignment_id=f"assign_{uuid4().hex[:12]}",
            experiment_id=experiment.experiment_id,
            variant_id=variant.variant_id,
            user_id=user_id,
            user_context=user_context or {},
        )
        
        # Cache assignment
        await self._cache_assignment(assignment_key, assignment)
        
        logger.info(
            f"Assigned user {user_id} to variant {variant.variant_id} "
            f"in experiment {experiment.experiment_id}"
        )
        
        return assignment
    
    def _select_variant(
        self,
        experiment: Experiment,
        user_id: str,
    ) -> Optional[ExperimentVariant]:
        """
        Select variant using consistent hashing.
        """
        
        # Hash user + experiment for consistent bucket
        hash_input = f"{self.salt}:{experiment.experiment_id}:{user_id}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Convert to bucket (0-10000 for 0.01% precision)
        bucket = int(hash_value[:8], 16) % 10000
        bucket_percentage = bucket / 100  # 0-100
        
        # Walk through variants
        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if bucket_percentage < cumulative:
                return variant
        
        # Fallback to control
        return experiment.get_control()
    
    def _check_targeting(
        self,
        experiment: Experiment,
        user_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """Check if user matches targeting criteria."""
        
        targeting = experiment.target_audience
        if not targeting:
            return True
        
        # Check platform
        if "platforms" in targeting:
            user_platform = context.get("platform")
            if user_platform and user_platform not in targeting["platforms"]:
                return False
        
        # Check categories
        if "categories" in targeting:
            user_category = context.get("category")
            if user_category and user_category not in targeting["categories"]:
                return False
        
        # Check user segment
        if "segments" in targeting:
            user_segments = context.get("segments", [])
            if not any(s in targeting["segments"] for s in user_segments):
                return False
        
        # Check percentage sampling
        if "sample_percentage" in targeting:
            sample_pct = targeting["sample_percentage"]
            hash_input = f"{self.salt}:sample:{experiment.experiment_id}:{user_id}"
            hash_value = hashlib.sha256(hash_input.encode()).hexdigest()
            bucket = int(hash_value[:8], 16) % 100
            if bucket >= sample_pct:
                return False
        
        return True
    
    async def _get_cached_assignment(
        self,
        key: str,
    ) -> Optional[ExperimentAssignment]:
        """Get cached assignment."""
        
        if key in self._assignments:
            return self._assignments[key]
        
        if self.cache:
            cached = await self.cache.get(f"exp_assign:{key}")
            if cached:
                assignment = ExperimentAssignment(**cached)
                self._assignments[key] = assignment
                return assignment
        
        return None
    
    async def _cache_assignment(
        self,
        key: str,
        assignment: ExperimentAssignment,
    ) -> None:
        """Cache assignment."""
        
        self._assignments[key] = assignment
        
        if self.cache:
            await self.cache.set(
                f"exp_assign:{key}",
                assignment.model_dump(),
                ttl=86400 * 30,  # 30 days
            )
    
    async def record_exposure(
        self,
        assignment: ExperimentAssignment,
    ) -> ExperimentAssignment:
        """Record that user was exposed to variant."""
        
        if assignment.first_exposure_at is None:
            assignment.first_exposure_at = datetime.now(timezone.utc)
        
        assignment.exposure_count += 1
        
        # Update cache
        key = f"{assignment.experiment_id}:{assignment.user_id}"
        await self._cache_assignment(key, assignment)
        
        return assignment
    
    async def deactivate_assignment(
        self,
        assignment: ExperimentAssignment,
    ) -> ExperimentAssignment:
        """Deactivate a user's assignment."""
        
        assignment.is_active = False
        
        key = f"{assignment.experiment_id}:{assignment.user_id}"
        await self._cache_assignment(key, assignment)
        
        return assignment
