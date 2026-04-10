# =============================================================================
# ADAM Hybrid Extractor — Rule-Based + ML Ensemble
# Location: adam/ml/hybrid_extractor.py
# =============================================================================

"""
HYBRID EXTRACTION ENGINE

Combines rule-based and ML extraction in a confidence-weighted ensemble
that captures the best of both approaches:

Rule-based strengths:
  - Deterministic, interpretable, fast (10K+ reviews/sec)
  - No training data needed
  - Consistent across runs
  - Captures exact patterns (word lists, regex)

ML strengths:
  - Context-aware (negation, sarcasm, irony)
  - Captures implicit signals (writing style, sentence structure)
  - Non-linear dimension interactions
  - Transfer across domains

Ensemble strategy:
  - When rule + ML agree → HIGH confidence
  - When rule + ML disagree → weight by domain-specific accuracy
  - When only rule fires → use rule with moderate confidence
  - When only ML fires → use ML with lower confidence (less interpretable)

The ensemble combiner is itself learnable — its weights are updated
based on downstream outcomes (Thompson Sampling feedback).
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION RESULT
# =============================================================================

@dataclass
class ExtractionResult:
    """Result from a single extraction method (rule or ML)."""
    method: str  # "rule" or "ml"
    
    # NDF dimensions (0-1)
    ndf_profile: Dict[str, float] = field(default_factory=dict)
    ndf_confidence: float = 0.0
    
    # 430+ dimensions
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    dimension_confidence: float = 0.0
    
    # Archetype
    archetype: Optional[str] = None
    archetype_confidence: float = 0.0
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    
    # Mechanism susceptibility
    mechanism_scores: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    latency_ms: float = 0.0
    tokens_processed: int = 0


@dataclass
class HybridExtractionResult:
    """Fused result from rule + ML ensemble."""
    
    # Fused NDF profile
    ndf_profile: Dict[str, float] = field(default_factory=dict)
    ndf_confidence: float = 0.0
    ndf_agreement: float = 0.0  # How much rule and ML agreed
    
    # Fused dimensions
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    dimension_confidence: float = 0.0
    
    # Fused archetype
    archetype: Optional[str] = None
    archetype_confidence: float = 0.0
    
    # Fused mechanism susceptibility
    mechanism_scores: Dict[str, float] = field(default_factory=dict)
    
    # Disagreement detection
    disagreements: List[Dict[str, Any]] = field(default_factory=list)
    
    # Method contributions
    rule_weight: float = 0.6   # How much rule-based contributed
    ml_weight: float = 0.4     # How much ML contributed
    
    # Performance
    total_latency_ms: float = 0.0


# =============================================================================
# HYBRID EXTRACTOR
# =============================================================================

class HybridExtractor:
    """
    Combines rule-based and ML extraction in a confidence-weighted ensemble.
    
    The ensemble weights start with a prior (rule=0.6, ML=0.4) and are
    updated based on downstream outcomes via the learning loop.
    """
    
    # Default ensemble weights (updated by learning)
    DEFAULT_RULE_WEIGHT = 0.6
    DEFAULT_ML_WEIGHT = 0.4
    
    # Agreement bonus: when both methods agree, boost confidence
    AGREEMENT_BONUS = 0.15
    
    # Disagreement threshold: beyond this, flag for review
    DISAGREEMENT_THRESHOLD = 0.3
    
    def __init__(
        self,
        rule_weight: float = DEFAULT_RULE_WEIGHT,
        ml_weight: float = DEFAULT_ML_WEIGHT,
        ml_model_path: Optional[str] = None,
    ):
        self.rule_weight = rule_weight
        self.ml_weight = ml_weight
        self._ml_model = None
        self._ml_available = False
        
        if ml_model_path:
            self._load_ml_model(ml_model_path)
    
    def _load_ml_model(self, model_path: str) -> None:
        """Load the ML extraction model."""
        try:
            from adam.ml.ndf_predictor import NDFPredictor
            self._ml_model = NDFPredictor.load(model_path)
            self._ml_available = True
            logger.info(f"Loaded ML extraction model from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load ML model: {e}. Using rule-only extraction.")
            self._ml_available = False
    
    def extract_rule_based(self, text: str, category: str = "") -> ExtractionResult:
        """Run rule-based extraction pipeline."""
        import time
        start = time.time()
        
        result = ExtractionResult(method="rule")
        
        try:
            # NDF extraction
            from adam.intelligence.ndf_extractor import extract_ndf
            ndf = extract_ndf(text)
            if ndf:
                result.ndf_profile = ndf
                non_default = sum(1 for v in ndf.values() if abs(v - 0.5) > 0.05)
                result.ndf_confidence = min(0.9, 0.3 + non_default * 0.1)
        except ImportError:
            logger.debug("NDF extractor not available")
        
        try:
            # 430+ dimension extraction
            from adam.intelligence.complete_psychological_analyzer import extract_comprehensive_profile
            profile = extract_comprehensive_profile(text)
            if profile:
                result.dimension_scores = profile
                result.dimension_confidence = min(0.85, 0.2 + len(profile) * 0.005)
        except ImportError:
            logger.debug("Comprehensive profiler not available")
        
        try:
            # Archetype detection
            from adam.intelligence.deep_archetype_detection import detect_deep_archetype
            arch_result = detect_deep_archetype(text)
            if arch_result:
                result.archetype = arch_result.get("primary_archetype")
                result.archetype_confidence = arch_result.get("confidence", 0.0)
                result.archetype_scores = arch_result.get("archetype_scores", {})
        except ImportError:
            logger.debug("Archetype detector not available")
        
        try:
            # Mechanism susceptibility
            from adam.intelligence.ndf_extractor import compute_mechanism_susceptibility
            if result.ndf_profile:
                mechs = compute_mechanism_susceptibility(result.ndf_profile)
                result.mechanism_scores = mechs
        except ImportError:
            pass
        
        result.latency_ms = (time.time() - start) * 1000
        result.tokens_processed = len(text.split())
        
        return result
    
    def extract_ml(self, text: str, category: str = "") -> ExtractionResult:
        """Run ML extraction pipeline."""
        import time
        start = time.time()
        
        result = ExtractionResult(method="ml")
        
        if not self._ml_available or not self._ml_model:
            result.latency_ms = (time.time() - start) * 1000
            return result
        
        try:
            ml_output = self._ml_model.predict(text, category=category)
            
            if ml_output.get("ndf_profile"):
                result.ndf_profile = ml_output["ndf_profile"]
                result.ndf_confidence = ml_output.get("ndf_confidence", 0.5)
            
            if ml_output.get("archetype"):
                result.archetype = ml_output["archetype"]
                result.archetype_confidence = ml_output.get("archetype_confidence", 0.5)
            
            if ml_output.get("mechanism_scores"):
                result.mechanism_scores = ml_output["mechanism_scores"]
                
        except Exception as e:
            logger.warning(f"ML extraction failed: {e}")
        
        result.latency_ms = (time.time() - start) * 1000
        result.tokens_processed = len(text.split())
        
        return result
    
    def _fuse_profiles(
        self,
        rule_profile: Dict[str, float],
        ml_profile: Dict[str, float],
        rule_conf: float,
        ml_conf: float,
    ) -> Tuple[Dict[str, float], float, float]:
        """
        Fuse two profiles using confidence-weighted combination.
        
        Returns: (fused_profile, fused_confidence, agreement_score)
        """
        if not rule_profile and not ml_profile:
            return {}, 0.0, 0.0
        
        if not ml_profile:
            return rule_profile, rule_conf, 0.0
        
        if not rule_profile:
            return ml_profile, ml_conf * 0.8, 0.0  # Penalize ML-only
        
        # Compute agreement
        common_dims = set(rule_profile.keys()) & set(ml_profile.keys())
        if common_dims:
            disagreements = [
                abs(rule_profile[d] - ml_profile[d])
                for d in common_dims
            ]
            agreement = 1.0 - (sum(disagreements) / len(disagreements))
        else:
            agreement = 0.0
        
        # Confidence-weighted fusion
        rule_w = self.rule_weight * rule_conf
        ml_w = self.ml_weight * ml_conf
        total_w = rule_w + ml_w
        
        if total_w == 0:
            return rule_profile, 0.3, agreement
        
        fused = {}
        all_dims = set(rule_profile.keys()) | set(ml_profile.keys())
        
        for dim in all_dims:
            rule_val = rule_profile.get(dim, 0.5)
            ml_val = ml_profile.get(dim, 0.5)
            
            fused[dim] = (rule_w * rule_val + ml_w * ml_val) / total_w
        
        # Fused confidence: base + agreement bonus
        fused_conf = min(0.95, (rule_w + ml_w) / 2 + agreement * self.AGREEMENT_BONUS)
        
        return fused, fused_conf, agreement
    
    def extract(
        self,
        text: str,
        category: str = "",
        run_ml: bool = True,
    ) -> HybridExtractionResult:
        """
        Run the full hybrid extraction pipeline.
        
        This is the main entry point. Runs rule-based extraction,
        optionally runs ML extraction, and fuses the results.
        """
        import time
        start = time.time()
        
        # Step 1: Rule-based extraction (always runs)
        rule_result = self.extract_rule_based(text, category)
        
        # Step 2: ML extraction (if available and requested)
        ml_result = None
        if run_ml and self._ml_available:
            ml_result = self.extract_ml(text, category)
        
        # Step 3: Fuse results
        result = HybridExtractionResult()
        
        if ml_result and ml_result.ndf_profile:
            # Full hybrid fusion
            ndf_fused, ndf_conf, ndf_agreement = self._fuse_profiles(
                rule_result.ndf_profile,
                ml_result.ndf_profile,
                rule_result.ndf_confidence,
                ml_result.ndf_confidence,
            )
            result.ndf_profile = ndf_fused
            result.ndf_confidence = ndf_conf
            result.ndf_agreement = ndf_agreement
            
            # Archetype fusion (take higher confidence)
            if rule_result.archetype_confidence >= ml_result.archetype_confidence:
                result.archetype = rule_result.archetype
                result.archetype_confidence = rule_result.archetype_confidence
            else:
                result.archetype = ml_result.archetype
                result.archetype_confidence = ml_result.archetype_confidence
            
            # Mechanism fusion
            mech_fused, _, _ = self._fuse_profiles(
                rule_result.mechanism_scores,
                ml_result.mechanism_scores,
                rule_result.ndf_confidence,
                ml_result.ndf_confidence,
            )
            result.mechanism_scores = mech_fused
            
            # Detect disagreements
            if ndf_agreement < (1.0 - self.DISAGREEMENT_THRESHOLD):
                for dim in set(rule_result.ndf_profile.keys()) & set(ml_result.ndf_profile.keys()):
                    diff = abs(rule_result.ndf_profile[dim] - ml_result.ndf_profile[dim])
                    if diff > self.DISAGREEMENT_THRESHOLD:
                        result.disagreements.append({
                            "dimension": dim,
                            "rule_value": rule_result.ndf_profile[dim],
                            "ml_value": ml_result.ndf_profile[dim],
                            "difference": diff,
                        })
            
            result.rule_weight = self.rule_weight
            result.ml_weight = self.ml_weight
            
        else:
            # Rule-only (no ML available)
            result.ndf_profile = rule_result.ndf_profile
            result.ndf_confidence = rule_result.ndf_confidence
            result.archetype = rule_result.archetype
            result.archetype_confidence = rule_result.archetype_confidence
            result.mechanism_scores = rule_result.mechanism_scores
            result.rule_weight = 1.0
            result.ml_weight = 0.0
        
        # Always use rule-based dimensions (ML doesn't predict all 430+)
        result.dimension_scores = rule_result.dimension_scores
        result.dimension_confidence = rule_result.dimension_confidence
        
        result.total_latency_ms = (time.time() - start) * 1000
        
        return result
    
    def update_weights(
        self,
        outcome_success: bool,
        rule_prediction: float,
        ml_prediction: float,
        learning_rate: float = 0.01,
    ) -> None:
        """
        Update ensemble weights based on outcome feedback.
        
        Called by the learning loop when we get outcome data.
        Adjusts rule_weight and ml_weight based on which method
        was more accurate.
        """
        # Compute prediction errors
        target = 1.0 if outcome_success else 0.0
        rule_error = abs(rule_prediction - target)
        ml_error = abs(ml_prediction - target)
        
        # Update weights: reduce weight of less accurate method
        if rule_error < ml_error:
            self.rule_weight = min(0.8, self.rule_weight + learning_rate)
            self.ml_weight = max(0.2, self.ml_weight - learning_rate)
        else:
            self.ml_weight = min(0.6, self.ml_weight + learning_rate)
            self.rule_weight = max(0.4, self.rule_weight - learning_rate)
        
        logger.debug(
            f"Updated ensemble weights: rule={self.rule_weight:.3f}, ml={self.ml_weight:.3f}"
        )


# =============================================================================
# SINGLETON
# =============================================================================

_hybrid_extractor: Optional[HybridExtractor] = None


def get_hybrid_extractor(
    ml_model_path: Optional[str] = None,
) -> HybridExtractor:
    """Get or create the singleton hybrid extractor."""
    global _hybrid_extractor
    if _hybrid_extractor is None:
        _hybrid_extractor = HybridExtractor(ml_model_path=ml_model_path)
    return _hybrid_extractor
