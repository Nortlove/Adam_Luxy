# =============================================================================
# ADAM Amazon Pre-Learning Orchestrator
# Location: adam/data/amazon/prelearning.py
# =============================================================================

"""
PRE-LEARNING ORCHESTRATOR

Coordinates batch processing of Amazon reviews for system training.

This module handles:
1. Processing reviews in batches for psychological profiling
2. Computing category-level psychological priors
3. Building brand-archetype effectiveness data
4. Extracting helpful-vote weighted patterns

Pre-learning runs offline to build the foundational intelligence that
informs real-time decisions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class PreLearningStage(str, Enum):
    """Stages of pre-learning."""
    NOT_STARTED = "not_started"
    LOADING_DATA = "loading_data"
    EXTRACTING_PSYCHOLOGY = "extracting_psychology"
    BUILDING_PRIORS = "building_priors"
    COMPUTING_ARCHETYPES = "computing_archetypes"
    ANALYZING_HELPFUL_PATTERNS = "analyzing_helpful_patterns"
    SAVING_CHECKPOINTS = "saving_checkpoints"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PreLearningConfig:
    """Configuration for pre-learning."""
    
    # Data sources
    reviews_dir: Path = field(default_factory=lambda: Path("/Users/chrisnocera/Sites/adam-platform/amazon"))
    output_dir: Path = field(default_factory=lambda: Path("/Users/chrisnocera/Sites/adam-platform/learned_priors"))
    
    # Processing
    batch_size: int = 1000
    max_reviews_per_category: int = 100000
    min_reviews_for_prior: int = 50
    
    # Helpful vote analysis
    min_helpful_for_pattern: int = 5
    extract_persuasive_patterns: bool = True
    
    # Checkpointing
    checkpoint_frequency: int = 10000
    resume_from_checkpoint: bool = True


@dataclass
class PreLearningProgress:
    """Progress tracking for pre-learning."""
    
    stage: PreLearningStage = PreLearningStage.NOT_STARTED
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Counts
    categories_processed: int = 0
    total_categories: int = 0
    reviews_processed: int = 0
    brands_processed: int = 0
    
    # Results
    priors_computed: int = 0
    archetypes_identified: int = 0
    persuasive_patterns_extracted: int = 0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        return self.stage == PreLearningStage.COMPLETE
    
    @property
    def progress_pct(self) -> float:
        if self.total_categories == 0:
            return 0.0
        return min(100.0, (self.categories_processed / self.total_categories) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "progress_pct": round(self.progress_pct, 1),
            "categories": f"{self.categories_processed}/{self.total_categories}",
            "reviews_processed": self.reviews_processed,
            "brands_processed": self.brands_processed,
            "priors_computed": self.priors_computed,
            "archetypes_identified": self.archetypes_identified,
            "persuasive_patterns": self.persuasive_patterns_extracted,
            "errors": len(self.errors),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# PRE-LEARNING ORCHESTRATOR
# =============================================================================

class PreLearningOrchestrator:
    """
    Orchestrates batch pre-learning from Amazon reviews.
    
    Pre-learning builds:
    1. Category-level psychological priors
    2. Brand-archetype effectiveness scores
    3. Persuasive language patterns (from high-helpful reviews)
    
    Usage:
        orchestrator = PreLearningOrchestrator(config)
        await orchestrator.run_full_prelearning()
        progress = orchestrator.get_progress()
    """
    
    def __init__(self, config: Optional[PreLearningConfig] = None):
        self.config = config or PreLearningConfig()
        self.progress = PreLearningProgress()
        
        self._running = False
        self._cancel_requested = False
        
        logger.info("PreLearningOrchestrator initialized")
    
    async def run_full_prelearning(self) -> PreLearningProgress:
        """
        Run the full pre-learning pipeline.
        
        Stages:
        1. Load and index review data
        2. Extract psychological profiles
        3. Build category priors
        4. Compute brand-archetype scores
        5. Analyze helpful-vote patterns
        6. Save checkpoints
        
        Returns:
            Final progress state
        """
        if self._running:
            logger.warning("Pre-learning already running")
            return self.progress
        
        self._running = True
        self.progress = PreLearningProgress(
            stage=PreLearningStage.LOADING_DATA,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        try:
            # Stage 1: Load data
            await self._load_data()
            
            # Stage 2: Extract psychology
            self.progress.stage = PreLearningStage.EXTRACTING_PSYCHOLOGY
            await self._extract_psychology()
            
            # Stage 3: Build priors
            self.progress.stage = PreLearningStage.BUILDING_PRIORS
            await self._build_priors()
            
            # Stage 4: Compute archetypes
            self.progress.stage = PreLearningStage.COMPUTING_ARCHETYPES
            await self._compute_archetypes()
            
            # Stage 5: Analyze helpful patterns
            if self.config.extract_persuasive_patterns:
                self.progress.stage = PreLearningStage.ANALYZING_HELPFUL_PATTERNS
                await self._analyze_helpful_patterns()
            
            # Stage 6: Save
            self.progress.stage = PreLearningStage.SAVING_CHECKPOINTS
            await self._save_checkpoints()
            
            # Complete
            self.progress.stage = PreLearningStage.COMPLETE
            self.progress.completed_at = datetime.now(timezone.utc)
            
            logger.info(f"Pre-learning complete: {self.progress.reviews_processed} reviews processed")
            
        except Exception as e:
            self.progress.stage = PreLearningStage.FAILED
            self.progress.errors.append(str(e))
            logger.error(f"Pre-learning failed: {e}")
            
        finally:
            self._running = False
        
        return self.progress
    
    async def _load_data(self) -> None:
        """Load and index review data."""
        from adam.data.amazon import get_amazon_client
        
        client = get_amazon_client()
        await client.initialize()
        
        stats = client.get_stats()
        self.progress.total_categories = stats.get("category_files", 0)
        self.progress.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Found {self.progress.total_categories} category files")
    
    async def _extract_psychology(self) -> None:
        """Extract psychological profiles from reviews."""
        # This would use the review analyzer to extract psychological dimensions
        # For now, this is a placeholder for the full implementation
        
        logger.info("Extracting psychological profiles...")
        await asyncio.sleep(0.1)  # Placeholder
        self.progress.updated_at = datetime.now(timezone.utc)
    
    async def _build_priors(self) -> None:
        """Build category-level psychological priors."""
        logger.info("Building category priors...")
        await asyncio.sleep(0.1)  # Placeholder
        self.progress.updated_at = datetime.now(timezone.utc)
    
    async def _compute_archetypes(self) -> None:
        """Compute brand-archetype effectiveness scores."""
        logger.info("Computing archetypes...")
        await asyncio.sleep(0.1)  # Placeholder
        self.progress.updated_at = datetime.now(timezone.utc)
    
    async def _analyze_helpful_patterns(self) -> None:
        """
        Analyze high-helpful-vote reviews for persuasive patterns.
        
        Reviews with high helpful votes contain language that influenced
        other customers' decisions. Extracting these patterns provides
        insight into what makes review content persuasive.
        """
        logger.info("Analyzing persuasive patterns from high-helpful reviews...")
        await asyncio.sleep(0.1)  # Placeholder
        self.progress.updated_at = datetime.now(timezone.utc)
    
    async def _save_checkpoints(self) -> None:
        """Save learned data to checkpoint files."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving checkpoints to {self.config.output_dir}")
        await asyncio.sleep(0.1)  # Placeholder
        self.progress.updated_at = datetime.now(timezone.utc)
    
    def get_progress(self) -> PreLearningProgress:
        """Get current progress."""
        return self.progress
    
    def cancel(self) -> None:
        """Request cancellation of the current run."""
        self._cancel_requested = True


# =============================================================================
# SINGLETON FACTORY
# =============================================================================

_orchestrator: Optional[PreLearningOrchestrator] = None


def get_prelearning_orchestrator(
    config: Optional[PreLearningConfig] = None,
) -> PreLearningOrchestrator:
    """
    Get or create the pre-learning orchestrator singleton.
    
    Args:
        config: Optional configuration (uses default if None)
        
    Returns:
        PreLearningOrchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = PreLearningOrchestrator(config)
    
    return _orchestrator
