# =============================================================================
# ADAM Multimodal Service
# Location: adam/multimodal/service.py
# =============================================================================

"""
MULTIMODAL SERVICE

Cross-modal fusion for holistic user understanding.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.multimodal.models import (
    Modality,
    SignalSource,
    ModalitySignal,
    ModalityWeight,
    FusedProfile,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class CrossModalFusion:
    """
    Fuse signals across modalities.
    
    Uses weighted combination with conflict detection.
    """
    
    # Default modality weights
    DEFAULT_WEIGHTS = {
        Modality.AUDIO: ModalityWeight(
            modality=Modality.AUDIO,
            weight=0.25,
            reliability=0.85,
        ),
        Modality.VISUAL: ModalityWeight(
            modality=Modality.VISUAL,
            weight=0.20,
            reliability=0.75,
        ),
        Modality.TEXT: ModalityWeight(
            modality=Modality.TEXT,
            weight=0.25,
            reliability=0.90,
        ),
        Modality.BEHAVIORAL: ModalityWeight(
            modality=Modality.BEHAVIORAL,
            weight=0.25,
            reliability=0.95,
        ),
        Modality.CONTEXTUAL: ModalityWeight(
            modality=Modality.CONTEXTUAL,
            weight=0.05,
            reliability=0.70,
        ),
    }
    
    def __init__(
        self,
        weights: Optional[Dict[Modality, ModalityWeight]] = None,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS
    
    def fuse(
        self,
        signals: List[ModalitySignal],
    ) -> Dict[str, Any]:
        """
        Fuse signals from multiple modalities.
        
        Returns fused features with confidence.
        """
        
        if not signals:
            return {"features": {}, "confidence": 0.0}
        
        # Group by modality
        by_modality: Dict[Modality, List[ModalitySignal]] = {}
        for signal in signals:
            if signal.modality not in by_modality:
                by_modality[signal.modality] = []
            by_modality[signal.modality].append(signal)
        
        # Fuse each feature across modalities
        all_features = set()
        for signals in by_modality.values():
            for s in signals:
                all_features.update(s.features.keys())
        
        fused_features = {}
        conflicts = []
        
        for feature in all_features:
            values = []
            
            for modality, mod_signals in by_modality.items():
                mod_weight = self.weights.get(modality)
                if not mod_weight:
                    continue
                
                for signal in mod_signals:
                    if feature in signal.features:
                        weight = (
                            mod_weight.weight *
                            mod_weight.reliability *
                            signal.confidence
                        )
                        values.append({
                            "value": signal.features[feature],
                            "weight": weight,
                            "modality": modality.value,
                        })
            
            if not values:
                continue
            
            # Detect conflicts
            if len(values) > 1:
                vals = [v["value"] for v in values]
                if max(vals) - min(vals) > 0.3:
                    conflicts.append({
                        "feature": feature,
                        "values": values,
                        "spread": max(vals) - min(vals),
                    })
            
            # Weighted average
            total_weight = sum(v["weight"] for v in values)
            if total_weight > 0:
                fused_features[feature] = (
                    sum(v["value"] * v["weight"] for v in values) / total_weight
                )
            else:
                fused_features[feature] = values[0]["value"]
        
        # Calculate overall confidence
        modality_coverage = len(by_modality) / len(Modality)
        signal_confidence = sum(s.confidence for s in signals) / len(signals)
        conflict_penalty = max(0, 1 - len(conflicts) * 0.1)
        
        overall_confidence = (
            modality_coverage * 0.3 +
            signal_confidence * 0.5 +
            conflict_penalty * 0.2
        )
        
        return {
            "features": fused_features,
            "confidence": overall_confidence,
            "conflicts": conflicts,
            "modality_coverage": list(by_modality.keys()),
        }


class MultimodalService:
    """
    Unified multimodal processing service.
    """
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        self.fusion = CrossModalFusion()
        
        # Signal buffer
        self._signals: Dict[str, List[ModalitySignal]] = {}
    
    async def ingest_signal(
        self,
        user_id: str,
        modality: Modality,
        source: SignalSource,
        raw_data: Dict[str, Any],
        features: Dict[str, float],
        confidence: float = 0.5,
    ) -> ModalitySignal:
        """Ingest a signal from any modality."""
        
        signal = ModalitySignal(
            signal_id=f"sig_{uuid4().hex[:12]}",
            modality=modality,
            source=source,
            user_id=user_id,
            raw_data=raw_data,
            features=features,
            confidence=confidence,
        )
        
        if user_id not in self._signals:
            self._signals[user_id] = []
        self._signals[user_id].append(signal)
        
        # Keep recent signals only (last 24h, max 100)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self._signals[user_id] = [
            s for s in self._signals[user_id]
            if s.observed_at > cutoff
        ][-100:]
        
        return signal
    
    async def get_fused_profile(
        self,
        user_id: str,
    ) -> FusedProfile:
        """Get multimodal fused profile for user."""
        
        signals = self._signals.get(user_id, [])
        
        # Fuse signals
        fused = self.fusion.fuse(signals)
        
        # Extract Big Five if present
        big_five = {}
        for trait in ["openness", "conscientiousness", "extraversion",
                      "agreeableness", "neuroticism"]:
            if trait in fused["features"]:
                big_five[trait] = fused["features"][trait]
        
        # Extract regulatory focus
        reg_focus = {
            "promotion": fused["features"].get("promotion_focus", 0.5),
            "prevention": fused["features"].get("prevention_focus", 0.5),
        }
        
        # Modality contributions
        contributions = {}
        for modality in fused.get("modality_coverage", []):
            contributions[modality.value] = {}
            for s in signals:
                if s.modality == modality:
                    for k, v in s.features.items():
                        contributions[modality.value][k] = v
        
        return FusedProfile(
            user_id=user_id,
            big_five=big_five,
            regulatory_focus=reg_focus,
            construal_level=fused["features"].get("construal_level", 0.5),
            modality_contributions=contributions,
            conflicts=fused.get("conflicts", []),
            overall_confidence=fused["confidence"],
            modality_coverage={
                m.value: m in fused.get("modality_coverage", [])
                for m in Modality
            },
        )
    
    async def get_signals(
        self,
        user_id: str,
        modality: Optional[Modality] = None,
        limit: int = 50,
    ) -> List[ModalitySignal]:
        """Get signals for a user."""
        
        signals = self._signals.get(user_id, [])
        
        if modality:
            signals = [s for s in signals if s.modality == modality]
        
        return signals[-limit:]
