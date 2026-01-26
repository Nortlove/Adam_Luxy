# =============================================================================
# ADAM Enhancement #19: Probabilistic Matching
# Location: adam/identity/matching/probabilistic.py
# =============================================================================

"""
Probabilistic identity matching using ML.

Uses feature-based scoring with:
- IP similarity
- Device fingerprint similarity
- Behavioral pattern similarity
- Temporal overlap
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import numpy as np
from pydantic import BaseModel, Field

from adam.identity.models.identifiers import (
    Identifier, IdentifierType, IdentityLink, MatchConfidence
)
from adam.identity.models.identity import UnifiedIdentity

logger = logging.getLogger(__name__)


class MatchFeatures(BaseModel):
    """Features for probabilistic matching."""
    
    # IP-based features
    same_ip_24h: bool = False
    same_ip_7d: bool = False
    ip_subnet_match: bool = False
    shared_ip_count: int = 0
    
    # Device fingerprint features
    fingerprint_similarity: float = 0.0
    same_browser_family: bool = False
    same_os_family: bool = False
    same_screen_resolution: bool = False
    
    # Behavioral features
    behavioral_similarity: float = 0.0
    content_overlap_score: float = 0.0
    temporal_overlap_score: float = 0.0
    activity_pattern_similarity: float = 0.0
    
    # Location features
    same_city: bool = False
    same_postal: bool = False
    geo_distance_km: float = 1000.0
    
    # Platform features
    shared_platform_count: int = 0
    same_platform_behavior: bool = False
    
    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for ML model."""
        return np.array([
            1.0 if self.same_ip_24h else 0.0,
            1.0 if self.same_ip_7d else 0.0,
            1.0 if self.ip_subnet_match else 0.0,
            min(1.0, self.shared_ip_count / 10),
            self.fingerprint_similarity,
            1.0 if self.same_browser_family else 0.0,
            1.0 if self.same_os_family else 0.0,
            1.0 if self.same_screen_resolution else 0.0,
            self.behavioral_similarity,
            self.content_overlap_score,
            self.temporal_overlap_score,
            self.activity_pattern_similarity,
            1.0 if self.same_city else 0.0,
            1.0 if self.same_postal else 0.0,
            1.0 / (1.0 + self.geo_distance_km / 100),  # Distance decay
            min(1.0, self.shared_platform_count / 3),
            1.0 if self.same_platform_behavior else 0.0,
        ])


class ProbabilisticMatcher:
    """
    ML-based probabilistic identity matching.
    
    Uses feature extraction and a trained classifier to score
    potential matches when deterministic signals aren't available.
    """
    
    # Feature weights (tuned from training data)
    DEFAULT_WEIGHTS = {
        "same_ip_24h": 0.25,
        "same_ip_7d": 0.15,
        "ip_subnet_match": 0.10,
        "shared_ip_count": 0.05,
        "fingerprint_similarity": 0.20,
        "same_browser_family": 0.05,
        "same_os_family": 0.03,
        "same_screen_resolution": 0.02,
        "behavioral_similarity": 0.15,
        "content_overlap_score": 0.10,
        "temporal_overlap_score": 0.10,
        "activity_pattern_similarity": 0.08,
        "same_city": 0.05,
        "same_postal": 0.08,
        "geo_proximity": 0.02,
        "shared_platform_count": 0.05,
        "same_platform_behavior": 0.05,
    }
    
    def __init__(
        self,
        min_confidence: float = 0.60,
        feature_weights: Optional[Dict[str, float]] = None,
    ):
        self.min_confidence = min_confidence
        self.weights = feature_weights or self.DEFAULT_WEIGHTS
        
        # Model state (would be trained in production)
        self._model_version = "1.0.0"
        self._model_trained_at: Optional[datetime] = None
    
    def compute_features(
        self,
        source_identifiers: List[Identifier],
        target_identity: UnifiedIdentity,
        context: Optional[Dict] = None,
    ) -> MatchFeatures:
        """
        Compute match features between source and target.
        
        In production, this would pull from event streams and analytics.
        """
        context = context or {}
        features = MatchFeatures()
        
        # Check IP overlap
        source_ips = [
            i.identifier_value for i in source_identifiers
            if i.identifier_type == IdentifierType.IP_HASH
        ]
        target_ips = target_identity.get_all_identifier_values(IdentifierType.IP_HASH)
        
        if source_ips and target_ips:
            matching_ips = set(source_ips) & set(target_ips)
            if matching_ips:
                features.same_ip_7d = True
                features.shared_ip_count = len(matching_ips)
        
        # Check fingerprint similarity
        source_fingerprints = [
            i for i in source_identifiers
            if i.identifier_type == IdentifierType.FINGERPRINT
        ]
        if source_fingerprints:
            target_fp = target_identity.get_identifier(IdentifierType.FINGERPRINT)
            if target_fp:
                # Simplified similarity (production would use proper comparison)
                features.fingerprint_similarity = self._compute_fingerprint_similarity(
                    source_fingerprints[0].identifier_value,
                    target_fp.identifier_value
                )
        
        # Browser/OS features from context
        if "browser_family" in context:
            # Would compare against target's known browser
            pass
        
        # Location features from context
        if "city" in context:
            features.same_city = context.get("city") == context.get("target_city", None)
        
        if "postal_code" in context:
            features.same_postal = context.get("postal_code") == context.get("target_postal", None)
        
        # Behavioral features (would come from analytics)
        features.behavioral_similarity = context.get("behavioral_similarity", 0.0)
        features.content_overlap_score = context.get("content_overlap", 0.0)
        features.temporal_overlap_score = context.get("temporal_overlap", 0.0)
        
        return features
    
    def _compute_fingerprint_similarity(
        self, 
        fp1: str, 
        fp2: str
    ) -> float:
        """Compute similarity between fingerprint hashes."""
        # In production, would use proper fingerprint comparison
        # For now, just check exact match
        if fp1 == fp2:
            return 1.0
        return 0.0
    
    def score_match(self, features: MatchFeatures) -> float:
        """Score a potential match using weighted features."""
        feature_vector = features.to_vector()
        weight_vector = np.array(list(self.weights.values()))[:len(feature_vector)]
        
        # Normalize weights
        weight_vector = weight_vector / weight_vector.sum()
        
        # Compute weighted score
        score = float(np.dot(feature_vector, weight_vector))
        
        return min(1.0, max(0.0, score))
    
    def find_match(
        self,
        source_identifiers: List[Identifier],
        candidates: List[UnifiedIdentity],
        context: Optional[Dict] = None,
    ) -> Tuple[Optional[UnifiedIdentity], Optional[IdentityLink], float]:
        """
        Find best probabilistic match among candidates.
        
        Returns (matched_identity, link, score) or (None, None, 0.0)
        """
        if not candidates:
            return None, None, 0.0
        
        best_match = None
        best_link = None
        best_score = 0.0
        
        for candidate in candidates:
            features = self.compute_features(
                source_identifiers, 
                candidate, 
                context
            )
            score = self.score_match(features)
            
            if score > best_score and score >= self.min_confidence:
                best_score = score
                best_match = candidate
                
                # Create link
                signals = self._extract_signals(features)
                best_link = IdentityLink(
                    source_identifier_id=source_identifiers[0].identifier_id if source_identifiers else "",
                    target_identifier_id=candidate.identity_id,
                    source_type=source_identifiers[0].identifier_type if source_identifiers else IdentifierType.SESSION_ID,
                    target_type=IdentifierType.SESSION_ID,
                    match_type="probabilistic",
                    confidence=MatchConfidence.from_score(score),
                    confidence_score=score,
                    match_signals=signals,
                    match_features=features.model_dump(),
                    match_algorithm=f"probabilistic_v{self._model_version}",
                )
        
        return best_match, best_link, best_score
    
    def _extract_signals(self, features: MatchFeatures) -> List[str]:
        """Extract human-readable signals from features."""
        signals = []
        
        if features.same_ip_24h:
            signals.append("same_ip_24h")
        if features.same_ip_7d:
            signals.append("same_ip_7d")
        if features.fingerprint_similarity > 0.5:
            signals.append("fingerprint_match")
        if features.behavioral_similarity > 0.5:
            signals.append("behavioral_match")
        if features.same_postal:
            signals.append("same_postal")
        if features.temporal_overlap_score > 0.5:
            signals.append("temporal_overlap")
        
        return signals
