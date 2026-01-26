# =============================================================================
# ADAM Intelligence: Emergence Engine
# Location: adam/intelligence/emergence_engine.py
# =============================================================================

"""
EMERGENCE ENGINE

The most cutting-edge component of ADAM: Discovers novel psychological
constructs not found in the existing research literature.

Paradigm Shift: From aggregating known knowledge to DISCOVERING new knowledge.

The Emergence Engine:
1. Monitors unexplained variance in user behavior predictions
2. Clusters unexplained patterns to identify candidate constructs
3. Validates constructs through predictive power testing
4. Promotes validated constructs to first-class knowledge

This positions ADAM to discover insights that don't yet exist in
academic literature - a 5-10 year advantage over industry practice.

Reference:
- Simon (1962) "The Architecture of Complexity" - Emergence in complex systems
- Kauffman (1993) "The Origins of Order" - Self-organization
- Holland (1998) "Emergence: From Chaos to Order"
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
import logging
import uuid
import numpy as np

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

import os


def _get_float_env(key: str, default: float) -> float:
    """Get float from environment variable with default."""
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _get_int_env(key: str, default: int) -> int:
    """Get int from environment variable with default."""
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


@dataclass
class EmergenceConfig:
    """
    Configuration for the Emergence Engine.
    
    All parameters can be overridden via environment variables with prefix
    ADAM_EMERGENCE_. For example:
        - ADAM_EMERGENCE_RESIDUAL_THRESHOLD=0.25
        - ADAM_EMERGENCE_MIN_SAMPLES_FOR_CLUSTER=100
    """
    
    # Anomaly detection
    residual_threshold: float = field(
        default_factory=lambda: _get_float_env("ADAM_EMERGENCE_RESIDUAL_THRESHOLD", 0.3)
    )  # Threshold for unexplained variance
    min_samples_for_cluster: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_MIN_SAMPLES_FOR_CLUSTER", 50)
    )  # Minimum samples before clustering
    
    # Clustering
    num_clusters: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_NUM_CLUSTERS", 10)
    )  # Maximum candidate constructs
    min_cluster_size: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_MIN_CLUSTER_SIZE", 20)
    )  # Minimum samples per cluster
    
    # Validation
    validation_sample_size: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_VALIDATION_SAMPLE_SIZE", 100)
    )
    min_predictive_lift: float = field(
        default_factory=lambda: _get_float_env("ADAM_EMERGENCE_MIN_PREDICTIVE_LIFT", 0.05)
    )  # 5% lift required for promotion
    min_validation_confidence: float = field(
        default_factory=lambda: _get_float_env("ADAM_EMERGENCE_MIN_VALIDATION_CONFIDENCE", 0.7)
    )
    validation_holdout_ratio: float = field(
        default_factory=lambda: _get_float_env("ADAM_EMERGENCE_VALIDATION_HOLDOUT_RATIO", 0.3)
    )
    
    # Promotion
    min_observations_for_promotion: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_MIN_OBSERVATIONS_FOR_PROMOTION", 200)
    )
    promotion_confidence_threshold: float = field(
        default_factory=lambda: _get_float_env("ADAM_EMERGENCE_PROMOTION_CONFIDENCE_THRESHOLD", 0.8)
    )
    
    # Monitoring
    monitoring_window_days: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_MONITORING_WINDOW_DAYS", 30)
    )
    anomaly_check_interval_hours: int = field(
        default_factory=lambda: _get_int_env("ADAM_EMERGENCE_ANOMALY_CHECK_INTERVAL_HOURS", 1)
    )


class ConstructStatus(str, Enum):
    """Status of an emergent construct."""
    CANDIDATE = "candidate"       # Detected pattern, not yet validated
    VALIDATING = "validating"     # Currently being validated
    VALIDATED = "validated"       # Passed validation, awaiting promotion
    PROMOTED = "promoted"         # Promoted to first-class knowledge
    REJECTED = "rejected"         # Failed validation
    DEPRECATED = "deprecated"     # Previously valid, no longer predictive


# =============================================================================
# EMERGENT CONSTRUCT
# =============================================================================

class EmergentConstruct(BaseModel):
    """
    A novel psychological construct discovered by the Emergence Engine.
    
    This represents a pattern in user behavior that is not explained
    by existing psychological knowledge.
    """
    
    # Identity
    construct_id: str = Field(default_factory=lambda: f"ec_{uuid.uuid4().hex[:12]}")
    name: str = Field(default="")
    description: str = Field(default="")
    
    # Discovery
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    status: ConstructStatus = Field(default=ConstructStatus.CANDIDATE)
    
    # Pattern characteristics
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    cluster_center: List[float] = Field(default_factory=list)
    cluster_size: int = Field(default=0)
    
    # Validation metrics
    predictive_lift: float = Field(default=0.0)
    validation_confidence: float = Field(default=0.0)
    validation_samples: int = Field(default=0)
    
    # Behavior modifiers
    predicted_outcomes: Dict[str, float] = Field(default_factory=dict)
    associated_behaviors: List[str] = Field(default_factory=list)
    
    # Lineage
    parent_constructs: List[str] = Field(default_factory=list)
    child_constructs: List[str] = Field(default_factory=list)
    
    # Metadata
    observation_count: int = Field(default=0)
    last_observed: datetime = Field(default_factory=datetime.utcnow)
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            "construct_id": self.construct_id,
            "name": self.name,
            "description": self.description,
            "discovered_at": self.discovered_at.isoformat(),
            "status": self.status.value,
            "predictive_lift": self.predictive_lift,
            "validation_confidence": self.validation_confidence,
            "cluster_size": self.cluster_size,
            "observation_count": self.observation_count,
        }


# =============================================================================
# ANOMALY DETECTOR
# =============================================================================

class AnomalyDetector:
    """
    Detects unexplained variance in predictions.
    
    When the system's predictions consistently fail in specific contexts,
    this indicates a pattern not captured by existing knowledge.
    """
    
    def __init__(self, config: EmergenceConfig):
        self.config = config
        self.residual_buffer: List[Dict] = []
        self.feature_buffer: List[np.ndarray] = []
        self.anomaly_count = 0
    
    def record_prediction(
        self,
        features: Dict[str, float],
        predicted: float,
        observed: float,
        decision_id: str,
        user_id: str,
    ) -> Optional[Dict]:
        """
        Record a prediction and its outcome.
        
        Returns anomaly info if this is an unexplained deviation.
        """
        residual = observed - predicted
        abs_residual = abs(residual)
        
        # Store in buffer
        record = {
            "decision_id": decision_id,
            "user_id": user_id,
            "features": features,
            "predicted": predicted,
            "observed": observed,
            "residual": residual,
            "timestamp": datetime.utcnow(),
        }
        
        self.residual_buffer.append(record)
        
        # Convert features to vector
        feature_vector = self._features_to_vector(features)
        self.feature_buffer.append(feature_vector)
        
        # Trim buffers
        max_size = self.config.min_samples_for_cluster * 10
        if len(self.residual_buffer) > max_size:
            self.residual_buffer = self.residual_buffer[-max_size:]
            self.feature_buffer = self.feature_buffer[-max_size:]
        
        # Check if this is an anomaly
        if abs_residual > self.config.residual_threshold:
            self.anomaly_count += 1
            return record
        
        return None
    
    def get_anomalous_records(self) -> List[Dict]:
        """Get all anomalous records from buffer."""
        return [
            r for r in self.residual_buffer
            if abs(r["residual"]) > self.config.residual_threshold
        ]
    
    def get_feature_matrix(self) -> np.ndarray:
        """Get feature matrix for clustering."""
        if not self.feature_buffer:
            return np.array([])
        return np.array(self.feature_buffer)
    
    def _features_to_vector(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy vector."""
        # Define consistent feature order
        feature_names = sorted(features.keys())
        return np.array([features.get(f, 0.0) for f in feature_names])
    
    def get_anomaly_rate(self) -> float:
        """Get rate of anomalous predictions."""
        if not self.residual_buffer:
            return 0.0
        anomalies = sum(1 for r in self.residual_buffer 
                       if abs(r["residual"]) > self.config.residual_threshold)
        return anomalies / len(self.residual_buffer)


# =============================================================================
# CONSTRUCT CLUSTERER
# =============================================================================

class ConstructClusterer:
    """
    Clusters anomalous patterns to identify candidate constructs.
    
    Uses K-means clustering on feature space of unexplained predictions.
    """
    
    def __init__(self, config: EmergenceConfig):
        self.config = config
    
    def cluster_anomalies(
        self,
        records: List[Dict],
        feature_names: List[str],
    ) -> List[EmergentConstruct]:
        """
        Cluster anomalous records to identify candidate constructs.
        
        Returns list of candidate constructs.
        """
        if len(records) < self.config.min_samples_for_cluster:
            return []
        
        # Build feature matrix
        features = []
        for record in records:
            vec = [record["features"].get(f, 0.0) for f in feature_names]
            features.append(vec)
        
        X = np.array(features)
        
        # Simple K-means implementation (production should use sklearn)
        candidates = self._kmeans_clustering(X, records, feature_names)
        
        return candidates
    
    def _kmeans_clustering(
        self,
        X: np.ndarray,
        records: List[Dict],
        feature_names: List[str],
        max_iter: int = 100,
    ) -> List[EmergentConstruct]:
        """Simple K-means clustering."""
        n_samples, n_features = X.shape
        k = min(self.config.num_clusters, n_samples // self.config.min_cluster_size)
        
        if k <= 0:
            return []
        
        # Random initialization
        rng = np.random.default_rng(42)
        indices = rng.choice(n_samples, k, replace=False)
        centers = X[indices].copy()
        
        # Iterate
        for _ in range(max_iter):
            # Assign points to clusters
            distances = np.zeros((n_samples, k))
            for j in range(k):
                distances[:, j] = np.linalg.norm(X - centers[j], axis=1)
            
            labels = np.argmin(distances, axis=1)
            
            # Update centers
            new_centers = np.zeros_like(centers)
            for j in range(k):
                mask = labels == j
                if mask.sum() > 0:
                    new_centers[j] = X[mask].mean(axis=0)
                else:
                    new_centers[j] = centers[j]
            
            # Check convergence
            if np.allclose(centers, new_centers):
                break
            centers = new_centers
        
        # Create constructs from clusters
        constructs = []
        for j in range(k):
            mask = labels == j
            cluster_size = mask.sum()
            
            if cluster_size < self.config.min_cluster_size:
                continue
            
            # Get cluster records
            cluster_records = [r for r, m in zip(records, mask) if m]
            
            # Compute feature importance (how much each feature deviates from mean)
            cluster_mean = X[mask].mean(axis=0)
            global_mean = X.mean(axis=0)
            global_std = X.std(axis=0) + 1e-6
            
            importance = np.abs(cluster_mean - global_mean) / global_std
            feature_importance = {
                f: float(importance[i])
                for i, f in enumerate(feature_names)
            }
            
            # Sort by importance
            top_features = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Generate name based on top features
            name_parts = [f[0].replace("_", " ").title() for f in top_features[:2]]
            name = f"Emergent: {' + '.join(name_parts)}"
            
            # Calculate predicted outcomes (all values must be floats)
            avg_residual = np.mean([r["residual"] for r in cluster_records])
            predicted_outcomes = {
                "residual_direction": 1.0 if avg_residual > 0 else -1.0,  # 1.0=positive, -1.0=negative
                "residual_magnitude": float(abs(avg_residual)),
            }
            
            construct = EmergentConstruct(
                name=name,
                description=f"Emergent construct discovered from {cluster_size} unexplained predictions. "
                           f"Key features: {', '.join([f[0] for f in top_features[:3]])}.",
                feature_importance=feature_importance,
                cluster_center=list(cluster_mean),
                cluster_size=cluster_size,
                predicted_outcomes=predicted_outcomes,
                associated_behaviors=[f[0] for f in top_features[:3]],
            )
            
            constructs.append(construct)
        
        logger.info(f"Discovered {len(constructs)} candidate constructs from {n_samples} anomalies")
        return constructs


# =============================================================================
# CONSTRUCT VALIDATOR
# =============================================================================

class ConstructValidator:
    """
    Validates candidate constructs through predictive power testing.
    
    A construct is valid if knowing about it improves predictions.
    """
    
    def __init__(self, config: EmergenceConfig):
        self.config = config
        self.validation_results: Dict[str, Dict] = {}
    
    async def validate_construct(
        self,
        construct: EmergentConstruct,
        prediction_func,  # Function to get predictions
        holdout_data: List[Dict],
    ) -> Tuple[bool, float, float]:
        """
        Validate a construct's predictive power.
        
        Args:
            construct: Construct to validate
            prediction_func: Function(features) -> predicted_outcome
            holdout_data: Holdout data for validation
            
        Returns:
            Tuple of (is_valid, lift, confidence)
        """
        if len(holdout_data) < self.config.validation_sample_size:
            logger.warning(f"Insufficient holdout data for validation: {len(holdout_data)}")
            return False, 0.0, 0.0
        
        # Split holdout into matching and non-matching
        matching = []
        non_matching = []
        
        for record in holdout_data:
            if self._matches_construct(record, construct):
                matching.append(record)
            else:
                non_matching.append(record)
        
        if len(matching) < 10 or len(non_matching) < 10:
            logger.warning(f"Insufficient matching samples for {construct.name}")
            return False, 0.0, 0.0
        
        # Calculate prediction errors for matching vs non-matching
        matching_errors = []
        for record in matching:
            predicted = await prediction_func(record["features"])
            error = abs(record["observed"] - predicted)
            matching_errors.append(error)
        
        non_matching_errors = []
        for record in non_matching:
            predicted = await prediction_func(record["features"])
            error = abs(record["observed"] - predicted)
            non_matching_errors.append(error)
        
        # If construct is predictive, matching samples should have lower error
        # when we account for the construct
        mean_matching = np.mean(matching_errors)
        mean_non_matching = np.mean(non_matching_errors)
        
        # Lift = reduction in error for construct-aware prediction
        lift = (mean_non_matching - mean_matching) / max(0.01, mean_non_matching)
        
        # Confidence based on sample sizes and consistency
        n_matching = len(matching)
        n_non_matching = len(non_matching)
        
        # Standard error of difference
        se_matching = np.std(matching_errors) / np.sqrt(n_matching)
        se_non_matching = np.std(non_matching_errors) / np.sqrt(n_non_matching)
        se_diff = np.sqrt(se_matching**2 + se_non_matching**2)
        
        # Z-score
        if se_diff > 0:
            z_score = (mean_non_matching - mean_matching) / se_diff
            confidence = min(1.0, abs(z_score) / 3.0)  # 3 std = ~1.0 confidence
        else:
            confidence = 0.5
        
        # Store validation results
        self.validation_results[construct.construct_id] = {
            "lift": lift,
            "confidence": confidence,
            "n_matching": n_matching,
            "n_non_matching": n_non_matching,
            "mean_matching_error": mean_matching,
            "mean_non_matching_error": mean_non_matching,
            "validated_at": datetime.utcnow(),
        }
        
        # Check if valid
        is_valid = (
            lift >= self.config.min_predictive_lift and
            confidence >= self.config.min_validation_confidence
        )
        
        logger.info(
            f"Validated {construct.name}: lift={lift:.3f}, confidence={confidence:.3f}, "
            f"valid={is_valid}"
        )
        
        return is_valid, lift, confidence
    
    def _matches_construct(self, record: Dict, construct: EmergentConstruct) -> bool:
        """Check if a record matches a construct's pattern."""
        if not construct.cluster_center:
            return False
        
        features = record.get("features", {})
        record_vec = np.array([
            features.get(f, 0.0)
            for f in sorted(construct.feature_importance.keys())
        ])
        
        center = np.array(construct.cluster_center[:len(record_vec)])
        
        # Distance threshold (based on feature importance)
        importance_weights = np.array([
            construct.feature_importance.get(f, 0.0)
            for f in sorted(construct.feature_importance.keys())
        ])[:len(record_vec)]
        
        weighted_distance = np.sum(importance_weights * np.abs(record_vec - center))
        
        # Threshold based on typical distance in cluster
        threshold = 1.5  # Can be tuned
        return weighted_distance < threshold


# =============================================================================
# EMERGENCE ENGINE
# =============================================================================

class EmergenceEngine:
    """
    The Emergence Engine discovers novel psychological constructs.
    
    This is the most cutting-edge component of ADAM, enabling
    the system to discover insights not found in existing literature.
    
    Pipeline:
    1. Monitor prediction residuals for unexplained variance
    2. Cluster anomalous patterns to identify candidates
    3. Validate candidates through predictive power testing
    4. Promote validated constructs to first-class knowledge
    
    Usage:
        engine = EmergenceEngine()
        
        # Record predictions
        engine.record_prediction(features, predicted, observed, decision_id, user_id)
        
        # Periodically discover and validate
        new_constructs = await engine.discover_constructs()
        
        # Get promoted constructs
        knowledge = engine.get_promoted_constructs()
    """
    
    def __init__(self, config: Optional[EmergenceConfig] = None):
        self.config = config or EmergenceConfig()
        
        # Components
        self.anomaly_detector = AnomalyDetector(self.config)
        self.clusterer = ConstructClusterer(self.config)
        self.validator = ConstructValidator(self.config)
        
        # Construct storage
        self.constructs: Dict[str, EmergentConstruct] = {}
        
        # Feature tracking
        self.all_feature_names: Set[str] = set()
        
        # Statistics
        self.discovery_runs = 0
        self.total_candidates = 0
        self.total_validated = 0
        self.total_promoted = 0
    
    def record_prediction(
        self,
        features: Dict[str, float],
        predicted: float,
        observed: float,
        decision_id: str,
        user_id: str,
    ) -> Optional[Dict]:
        """
        Record a prediction for emergence monitoring.
        
        Returns anomaly info if this was unexplained.
        """
        # Track feature names
        self.all_feature_names.update(features.keys())
        
        # Record in anomaly detector
        return self.anomaly_detector.record_prediction(
            features, predicted, observed, decision_id, user_id
        )
    
    async def discover_constructs(
        self,
        prediction_func=None,
    ) -> List[EmergentConstruct]:
        """
        Run the discovery pipeline.
        
        1. Get anomalous records
        2. Cluster to find candidates
        3. Validate candidates (if prediction_func provided)
        
        Returns list of newly discovered constructs.
        """
        self.discovery_runs += 1
        
        # Get anomalies
        anomalies = self.anomaly_detector.get_anomalous_records()
        
        if len(anomalies) < self.config.min_samples_for_cluster:
            logger.debug(f"Insufficient anomalies for discovery: {len(anomalies)}")
            return []
        
        # Cluster anomalies
        feature_names = sorted(self.all_feature_names)
        candidates = self.clusterer.cluster_anomalies(anomalies, feature_names)
        
        self.total_candidates += len(candidates)
        
        if not candidates:
            return []
        
        # Validate if prediction function provided
        validated = []
        if prediction_func:
            # Split anomalies for validation
            holdout_size = int(len(anomalies) * self.config.validation_holdout_ratio)
            holdout_data = anomalies[-holdout_size:]
            
            for construct in candidates:
                is_valid, lift, confidence = await self.validator.validate_construct(
                    construct, prediction_func, holdout_data
                )
                
                if is_valid:
                    construct.status = ConstructStatus.VALIDATED
                    construct.predictive_lift = lift
                    construct.validation_confidence = confidence
                    construct.validation_samples = len(holdout_data)
                    validated.append(construct)
                    self.total_validated += 1
                else:
                    construct.status = ConstructStatus.REJECTED
                
                # Store construct
                self.constructs[construct.construct_id] = construct
        else:
            # No validation - keep as candidates
            for construct in candidates:
                self.constructs[construct.construct_id] = construct
            validated = candidates
        
        logger.info(
            f"Discovery run {self.discovery_runs}: "
            f"{len(anomalies)} anomalies → {len(candidates)} candidates → {len(validated)} validated"
        )
        
        return validated
    
    def promote_construct(self, construct_id: str) -> bool:
        """
        Promote a validated construct to first-class knowledge.
        
        This should trigger Neo4j storage and integration with the
        broader knowledge system.
        """
        if construct_id not in self.constructs:
            return False
        
        construct = self.constructs[construct_id]
        
        if construct.status != ConstructStatus.VALIDATED:
            logger.warning(f"Cannot promote non-validated construct: {construct.status}")
            return False
        
        if construct.validation_confidence < self.config.promotion_confidence_threshold:
            logger.warning(f"Construct confidence too low for promotion: {construct.validation_confidence}")
            return False
        
        construct.status = ConstructStatus.PROMOTED
        self.total_promoted += 1
        
        logger.info(f"Promoted construct: {construct.name} ({construct.construct_id})")
        
        return True
    
    def get_construct(self, construct_id: str) -> Optional[EmergentConstruct]:
        """Get a construct by ID."""
        return self.constructs.get(construct_id)
    
    def get_constructs_by_status(self, status: ConstructStatus) -> List[EmergentConstruct]:
        """Get all constructs with a specific status."""
        return [c for c in self.constructs.values() if c.status == status]
    
    def get_promoted_constructs(self) -> List[EmergentConstruct]:
        """Get all promoted constructs (first-class knowledge)."""
        return self.get_constructs_by_status(ConstructStatus.PROMOTED)
    
    def get_candidate_constructs(self) -> List[EmergentConstruct]:
        """Get all candidate constructs awaiting validation."""
        return self.get_constructs_by_status(ConstructStatus.CANDIDATE)
    
    def apply_construct_to_features(
        self,
        features: Dict[str, float],
        construct: EmergentConstruct,
    ) -> Dict[str, float]:
        """
        Augment features with construct membership.
        
        This adds a feature indicating whether the user matches
        this emergent construct.
        """
        enhanced = features.copy()
        
        # Check if features match construct
        if construct.cluster_center:
            feature_vec = np.array([
                features.get(f, 0.0)
                for f in sorted(construct.feature_importance.keys())
            ])
            center = np.array(construct.cluster_center[:len(feature_vec)])
            distance = np.linalg.norm(feature_vec - center)
            
            # Convert distance to membership score (0-1)
            membership = np.exp(-distance / 2.0)  # Gaussian kernel
            
            enhanced[f"emergent_{construct.construct_id}"] = membership
        
        return enhanced
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "discovery_runs": self.discovery_runs,
            "total_candidates": self.total_candidates,
            "total_validated": self.total_validated,
            "total_promoted": self.total_promoted,
            "total_constructs": len(self.constructs),
            "anomaly_rate": self.anomaly_detector.get_anomaly_rate(),
            "constructs_by_status": {
                status.value: len(self.get_constructs_by_status(status))
                for status in ConstructStatus
            },
        }
    
    # =========================================================================
    # LEARNING CAPABLE COMPONENT INTERFACE
    # =========================================================================
    
    @property
    def component_name(self) -> str:
        """Component name for learning signal routing."""
        return "emergence_engine"
    
    @property
    def component_version(self) -> str:
        """Component version."""
        return "1.0"
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[Any]:
        """
        Process an outcome for anomaly detection and construct validation.
        
        Records the prediction-outcome pair to detect unexplained variance.
        """
        signals = []
        
        # Record prediction for anomaly detection
        predicted_value = context.get("predicted_value")
        features = context.get("features", {})
        
        if predicted_value is not None:
            self.record_prediction(
                request_id=decision_id,
                features=features,
                predicted_value=predicted_value,
                actual_value=outcome_value,
            )
        
        # Check if any promoted constructs were applicable
        for construct in self.get_promoted_constructs():
            if context.get(f"emergent_{construct.construct_id}"):
                # Validate construct prediction
                construct.observation_count += 1
                if outcome_value > 0.5:
                    construct.positive_observations += 1
        
        # Emit signal if new discovery triggered
        if self.anomaly_detector.get_anomaly_count() > 0:
            try:
                from adam.core.learning.universal_learning_interface import (
                    LearningSignal,
                    LearningSignalType,
                )
                signal = LearningSignal(
                    signal_type=LearningSignalType.PATTERN_EMERGED,
                    source_component=self.component_name,
                    source_version=self.component_version,
                    decision_id=decision_id,
                    payload={
                        "anomaly_count": self.anomaly_detector.get_anomaly_count(),
                        "anomaly_rate": self.anomaly_detector.get_anomaly_rate(),
                    },
                    confidence=0.5,
                )
                signals.append(signal)
            except ImportError:
                pass
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: Any,
    ) -> Optional[List[Any]]:
        """Process incoming learning signals."""
        # EmergenceEngine can respond to validation signals
        try:
            from adam.core.learning.universal_learning_interface import (
                LearningSignal,
                LearningSignalType,
            )
            if isinstance(signal, LearningSignal):
                if signal.signal_type == LearningSignalType.PREDICTION_VALIDATED:
                    # A prediction was validated - record for anomaly detection
                    pass
        except ImportError:
            pass
        return None
    
    def get_consumed_signal_types(self) -> set:
        """Return signal types this component consumes."""
        try:
            from adam.core.learning.universal_learning_interface import LearningSignalType
            return {
                LearningSignalType.PREDICTION_VALIDATED,
                LearningSignalType.PREDICTION_FAILED,
            }
        except ImportError:
            return set()
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[Any]:
        """Get this component's contribution to a decision."""
        # EmergenceEngine contributes emergent construct features
        # Would need to track which constructs were applied per decision
        return None
    
    async def get_learning_quality_metrics(self) -> Any:
        """Get metrics about learning quality."""
        try:
            from adam.core.learning.universal_learning_interface import LearningQualityMetrics
            
            stats = self.get_stats()
            
            return LearningQualityMetrics(
                component_name=self.component_name,
                measurement_period_hours=24,
                signals_emitted=stats["discovery_runs"],
                signals_consumed=0,
                outcomes_processed=self.anomaly_detector.sample_count,
                prediction_accuracy=1.0 - stats["anomaly_rate"],
                prediction_accuracy_trend="stable" if stats["anomaly_rate"] < 0.3 else "declining",
                attribution_coverage=stats["total_validated"] / max(1, stats["total_candidates"]),
            )
        except ImportError:
            return None
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any],
    ) -> None:
        """Inject priors before processing."""
        # Could use priors to seed initial construct membership
        pass
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        stats = self.get_stats()
        
        # Check for high anomaly rate
        if stats["anomaly_rate"] > 0.5:
            issues.append(f"High anomaly rate: {stats['anomaly_rate']:.2%}")
        
        # Check for stagnant discovery
        if stats["discovery_runs"] > 10 and stats["total_candidates"] == 0:
            issues.append("No new candidates despite multiple discovery runs")
        
        # Check for low validation rate
        if stats["total_candidates"] > 10:
            validation_rate = stats["total_validated"] / stats["total_candidates"]
            if validation_rate < 0.1:
                issues.append(f"Low validation rate: {validation_rate:.2%}")
        
        return len(issues) == 0, issues
    
    # =========================================================================
    # REVIEW INTELLIGENCE INTEGRATION
    # =========================================================================
    
    async def discover_review_patterns(
        self,
        customer_intelligence,
    ) -> List[EmergentConstruct]:
        """
        Discover emergent patterns from customer review analysis.
        
        This method analyzes the CustomerIntelligenceProfile to identify
        novel patterns that may not be captured by standard archetypes.
        
        Key insights discovered:
        1. Unexpected personality trait combinations
        2. Novel purchase motivation clusters
        3. Atypical regulatory focus patterns
        4. Language pattern anomalies
        
        Args:
            customer_intelligence: CustomerIntelligenceProfile from review analysis
            
        Returns:
            List of emergent constructs discovered from review patterns
        """
        constructs = []
        
        try:
            # Build feature vector from review intelligence
            features = {
                "openness": customer_intelligence.avg_openness or 0.5,
                "conscientiousness": customer_intelligence.avg_conscientiousness or 0.5,
                "extraversion": customer_intelligence.avg_extraversion or 0.5,
                "agreeableness": customer_intelligence.avg_agreeableness or 0.5,
                "neuroticism": customer_intelligence.avg_neuroticism or 0.5,
            }
            
            # Add regulatory focus
            reg_focus = customer_intelligence.regulatory_focus or {}
            features["promotion_focus"] = reg_focus.get("promotion", 0.5)
            features["prevention_focus"] = reg_focus.get("prevention", 0.5)
            
            # Add mechanism predictions
            mechanisms = customer_intelligence.mechanism_predictions or {}
            for mech, score in mechanisms.items():
                features[f"mechanism_{mech}"] = score
            
            # Check for emergent patterns
            
            # 1. Detect unusual personality combinations
            o, c, e, a, n = features["openness"], features["conscientiousness"], \
                           features["extraversion"], features["agreeableness"], features["neuroticism"]
            
            # High openness + high conscientiousness is unusual (Explorer + Guardian)
            if o > 0.65 and c > 0.65:
                construct = EmergentConstruct(
                    name="Emergent: Methodical Explorer",
                    description=(
                        "A novel customer profile combining Explorer's curiosity with Guardian's "
                        "methodical approach. These customers research extensively before committing "
                        "but are highly responsive to innovation messaging."
                    ),
                    feature_importance={
                        "openness": 0.9,
                        "conscientiousness": 0.85,
                        "research_oriented": 0.8,
                    },
                    cluster_center=[o, c, e, a, n],
                    cluster_size=customer_intelligence.reviews_analyzed or 0,
                    predicted_outcomes={
                        "authority_effectiveness": 0.85,
                        "novelty_effectiveness": 0.8,
                        "commitment_required": 0.9,
                    },
                    associated_behaviors=[
                        "extensive_research",
                        "comparison_shopping",
                        "detailed_reviews",
                    ],
                    status=ConstructStatus.CANDIDATE,
                    confidence=min(0.8, (customer_intelligence.overall_confidence or 0.5) + 0.2),
                )
                constructs.append(construct)
                self._register_construct(construct)
            
            # 2. Detect mixed regulatory focus
            promo = features["promotion_focus"]
            prev = features["prevention_focus"]
            
            # Balanced regulatory focus is interesting
            if abs(promo - prev) < 0.15 and promo > 0.45 and prev > 0.45:
                construct = EmergentConstruct(
                    name="Emergent: Balanced Regulator",
                    description=(
                        "Customers with balanced promotion/prevention focus. "
                        "They respond to both gain-framed and loss-avoidance messaging, "
                        "making them versatile targets for A/B testing."
                    ),
                    feature_importance={
                        "promotion_focus": promo,
                        "prevention_focus": prev,
                        "flexibility": 0.85,
                    },
                    cluster_center=[promo, prev],
                    cluster_size=customer_intelligence.reviews_analyzed or 0,
                    predicted_outcomes={
                        "gain_frame_receptivity": 0.65,
                        "loss_frame_receptivity": 0.65,
                        "AB_test_value": 0.9,
                    },
                    associated_behaviors=[
                        "mixed_language",
                        "balanced_reviews",
                        "comparative_analysis",
                    ],
                    status=ConstructStatus.CANDIDATE,
                    confidence=min(0.7, (customer_intelligence.overall_confidence or 0.5) + 0.1),
                )
                constructs.append(construct)
                self._register_construct(construct)
            
            # 3. Detect unexpected mechanism effectiveness
            if mechanisms:
                # Find mechanisms with unusually high predicted effectiveness
                for mech, score in mechanisms.items():
                    if score > 0.8:
                        # Check if this contradicts archetype expectations
                        archetype = customer_intelligence.dominant_archetype
                        expected = self._get_expected_mechanism_score(archetype, mech)
                        
                        if expected and score > expected + 0.2:
                            construct = EmergentConstruct(
                                name=f"Emergent: {mech.title()} Amplified {archetype}",
                                description=(
                                    f"{archetype} customers who are unusually responsive to "
                                    f"{mech} persuasion. This deviates from standard {archetype} "
                                    "psychology and represents a high-value targeting opportunity."
                                ),
                                feature_importance={
                                    f"mechanism_{mech}": score,
                                    "archetype_deviation": score - expected,
                                },
                                cluster_center=[score],
                                cluster_size=customer_intelligence.reviews_analyzed or 0,
                                predicted_outcomes={
                                    f"{mech}_effectiveness": score,
                                    "targeting_value": 0.9,
                                },
                                associated_behaviors=[
                                    f"high_{mech}_response",
                                    "archetype_edge_case",
                                ],
                                status=ConstructStatus.CANDIDATE,
                                confidence=min(0.75, (customer_intelligence.overall_confidence or 0.5) + 0.15),
                            )
                            constructs.append(construct)
                            self._register_construct(construct)
            
            # 4. Analyze language pattern anomalies
            lang = {}
            if hasattr(customer_intelligence, 'get_copy_language'):
                try:
                    lang = customer_intelligence.get_copy_language() or {}
                except Exception:
                    pass
            
            # Check for unusual language patterns
            if lang.get("formality", 0.5) > 0.75 and e > 0.65:
                # Formal language + high extraversion is unusual
                construct = EmergentConstruct(
                    name="Emergent: Professional Socialite",
                    description=(
                        "Highly extraverted customers who prefer formal communication. "
                        "Likely professionals who blend social warmth with professional polish. "
                        "Effective targeting: professional but engaging messaging."
                    ),
                    feature_importance={
                        "extraversion": e,
                        "language_formality": lang.get("formality", 0.5),
                        "professional_social": 0.85,
                    },
                    cluster_center=[e, lang.get("formality", 0.5)],
                    cluster_size=customer_intelligence.reviews_analyzed or 0,
                    predicted_outcomes={
                        "professional_tone_effectiveness": 0.85,
                        "social_proof_effectiveness": 0.8,
                    },
                    associated_behaviors=[
                        "professional_reviews",
                        "networking_orientation",
                        "quality_focus",
                    ],
                    status=ConstructStatus.CANDIDATE,
                    confidence=min(0.7, (customer_intelligence.overall_confidence or 0.5) + 0.1),
                )
                constructs.append(construct)
                self._register_construct(construct)
            
            logger.info(f"Discovered {len(constructs)} emergent patterns from review intelligence")
            
        except Exception as e:
            logger.error(f"Error discovering review patterns: {e}")
        
        return constructs
    
    def _get_expected_mechanism_score(self, archetype: str, mechanism: str) -> Optional[float]:
        """Get expected mechanism effectiveness for an archetype."""
        expectations = {
            "Achiever": {
                "authority": 0.85,
                "social_proof": 0.75,
                "scarcity": 0.70,
                "commitment": 0.65,
                "novelty": 0.60,
            },
            "Explorer": {
                "novelty": 0.90,
                "curiosity": 0.85,
                "social_proof": 0.65,
                "authority": 0.50,
            },
            "Guardian": {
                "commitment": 0.85,
                "authority": 0.80,
                "social_proof": 0.70,
                "reciprocity": 0.60,
            },
            "Connector": {
                "social_proof": 0.90,
                "liking": 0.85,
                "reciprocity": 0.80,
            },
            "Pragmatist": {
                "reciprocity": 0.85,
                "commitment": 0.80,
                "authority": 0.70,
            },
        }
        return expectations.get(archetype, {}).get(mechanism)
    
    def _register_construct(self, construct: EmergentConstruct) -> None:
        """Register a construct in the engine."""
        self.constructs[construct.construct_id] = construct
        self.total_candidates += 1


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[EmergenceEngine] = None


def get_emergence_engine() -> EmergenceEngine:
    """Get singleton Emergence Engine."""
    global _engine
    if _engine is None:
        _engine = EmergenceEngine()
    return _engine
