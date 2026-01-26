# =============================================================================
# ADAM Nonconscious Analytics - Analysis Pipeline
# =============================================================================

"""
NONCONSCIOUS SIGNAL ANALYSIS

Psychological inference from implicit behavioral signals.

Research-backed analysis methods for:
- Approach-Avoidance motivation detection
- Cognitive load estimation
- Processing fluency measurement
- Implicit preference inference
- Automatic evaluation detection

Key Research References:
- Elliot & Thrash (2002) - Approach-Avoidance Motivation
- Sweller (1988) - Cognitive Load Theory
- Reber et al. (1998) - Processing Fluency
- Greenwald & Banaji (1995) - Implicit Cognition
- Fazio (1990) - Attitude Accessibility
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from adam.signals.nonconscious.models import (
    NonconsciousSignal,
    KinematicSignal,
    ScrollBehaviorSignal,
    KeystrokeSignal,
    TemporalSignal,
    HesitationSignal,
    RhythmicSignal,
    ApproachAvoidanceTendency,
    CognitiveLoadIndicator,
    EmotionalValenceProxy,
    ProcessingFluencyScore,
    EngagementIntensity,
    ImplicitPreference,
    AutomaticEvaluation,
    NonconsciousProfile,
    ProcessingDepth,
    ValenceDirection,
)

logger = logging.getLogger(__name__)


# =============================================================================
# APPROACH-AVOIDANCE ANALYZER
# =============================================================================

class ApproachAvoidanceAnalyzer:
    """
    Analyze approach-avoidance motivation from behavioral signals.
    
    Research basis:
    - Movement toward/away reflects motivation (Elliot & Thrash, 2002)
    - Speed of approach indicates motivation strength (Chen & Bargh, 1999)
    - Hesitation patterns reveal avoidance (Krieglmeyer & Deutsch, 2010)
    """
    
    def analyze(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> ApproachAvoidanceTendency:
        """
        Analyze signals to determine approach-avoidance tendency.
        """
        approach_evidence = []
        avoidance_evidence = []
        
        approach_score = 0.0
        avoidance_score = 0.0
        evidence_count = 0
        
        for signal in signals:
            evidence_count += 1
            
            if isinstance(signal, KinematicSignal):
                # Fast, direct movement = approach
                # Slow, meandering movement = avoidance/conflict
                if signal.directness_ratio > 0.8 and signal.avg_velocity > 500:
                    approach_score += 0.7
                    approach_evidence.append(f"Direct fast movement: {signal.signal_id}")
                elif signal.conflict_indicator > 0.5:
                    avoidance_score += 0.6
                    avoidance_evidence.append(f"Conflict in trajectory: {signal.signal_id}")
                elif signal.directness_ratio < 0.5:
                    avoidance_score += 0.4
                    avoidance_evidence.append(f"Meandering path: {signal.signal_id}")
                else:
                    approach_score += 0.4
            
            elif isinstance(signal, ScrollBehaviorSignal):
                # Deep engagement = approach
                # Quick skim + bounce = avoidance
                if signal.max_depth_percent > 70 and signal.deliberation_score > 0.5:
                    approach_score += 0.6
                    approach_evidence.append(f"Deep engaged scroll: {signal.signal_id}")
                elif signal.max_depth_percent < 20 and signal.avg_scroll_velocity > 2000:
                    avoidance_score += 0.5
                    avoidance_evidence.append(f"Quick skim: {signal.signal_id}")
                else:
                    approach_score += 0.3
            
            elif isinstance(signal, KeystrokeSignal):
                # Confident, fast typing = approach
                # Hesitant, many corrections = avoidance/conflict
                if signal.confidence_score > 0.7 and signal.words_per_minute > 40:
                    approach_score += 0.5
                    approach_evidence.append(f"Confident typing: {signal.signal_id}")
                elif signal.correction_rate > 0.15 or signal.deliberation_score > 0.7:
                    avoidance_score += 0.4
                    avoidance_evidence.append(f"Hesitant typing: {signal.signal_id}")
                else:
                    approach_score += 0.2
            
            elif isinstance(signal, TemporalSignal):
                # Fast response = accessible positive attitude = approach
                # Slow response = inaccessible/negative = avoidance
                if signal.attitude_accessibility > 0.7:
                    approach_score += 0.6
                    approach_evidence.append(f"Fast response: {signal.signal_id}")
                elif signal.deviation_from_baseline > 1.5:
                    avoidance_score += 0.5
                    avoidance_evidence.append(f"Slow response: {signal.signal_id}")
                else:
                    approach_score += 0.3
            
            elif isinstance(signal, HesitationSignal):
                # Hesitation is strong avoidance/conflict signal
                avoidance_score += 0.8 * signal.uncertainty_score
                avoidance_evidence.append(f"Hesitation detected: {signal.signal_id}")
        
        # Normalize scores
        if evidence_count > 0:
            approach_strength = min(1.0, approach_score / evidence_count)
            avoidance_strength = min(1.0, avoidance_score / evidence_count)
        else:
            approach_strength = 0.5
            avoidance_strength = 0.5
        
        # Net tendency
        net = approach_strength - avoidance_strength
        
        # Confidence based on evidence quantity and consistency
        confidence = min(0.9, 0.3 + evidence_count * 0.05)
        
        return ApproachAvoidanceTendency(
            user_id=user_id,
            session_id=session_id,
            approach_strength=approach_strength,
            avoidance_strength=avoidance_strength,
            net_tendency=net,
            approach_signals=approach_evidence,
            avoidance_signals=avoidance_evidence,
            confidence=confidence,
        )


# =============================================================================
# COGNITIVE LOAD ESTIMATOR
# =============================================================================

class CognitiveLoadEstimator:
    """
    Estimate cognitive load from behavioral signals.
    
    Research basis:
    - Cognitive Load Theory (Sweller, 1988)
    - Behavioral signatures of mental effort (Paas et al., 2003)
    - Dual-task performance under load (Kahneman, 1973)
    """
    
    def estimate(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> CognitiveLoadIndicator:
        """
        Estimate cognitive load from behavioral signals.
        """
        # Indicators of high cognitive load:
        # - Slower responses
        # - More corrections
        # - Lower directness in movements
        # - More pauses
        
        load_signals = defaultdict(list)
        
        for signal in signals:
            if isinstance(signal, KeystrokeSignal):
                # Slow typing + corrections = high load
                load_signals["processing_time"].append(
                    1 - min(1.0, signal.words_per_minute / 60)
                )
                load_signals["errors"].append(signal.correction_rate)
                load_signals["pauses"].append(
                    min(1.0, signal.pause_count / 10)
                )
            
            elif isinstance(signal, KinematicSignal):
                # Low directness = effortful navigation
                load_signals["processing_effort"].append(
                    1 - signal.directness_ratio
                )
                load_signals["conflict"].append(signal.conflict_indicator)
            
            elif isinstance(signal, TemporalSignal):
                # Slow responses = high load
                load_signals["processing_time"].append(
                    1 - signal.attitude_accessibility
                )
            
            elif isinstance(signal, ScrollBehaviorSignal):
                # Re-reading = high load
                load_signals["re_processing"].append(
                    min(1.0, signal.reverse_scroll_count / 5)
                )
        
        # Aggregate load components
        def avg_or_default(values: List[float], default: float = 0.5) -> float:
            return sum(values) / len(values) if values else default
        
        # Intrinsic load: from task complexity (inferred from processing patterns)
        intrinsic = avg_or_default(
            load_signals["processing_time"] + load_signals["pauses"]
        )
        
        # Extraneous load: from poor design (inferred from errors/conflict)
        extraneous = avg_or_default(
            load_signals["errors"] + load_signals["conflict"]
        )
        
        # Germane load: productive effort (re-processing indicates learning effort)
        germane = avg_or_default(load_signals["re_processing"])
        
        # Total load
        total = min(1.0, (intrinsic * 0.5 + extraneous * 0.3 + germane * 0.2))
        
        # Capacity remaining
        capacity = 1.0 - total
        
        # Determine processing depth based on load
        if total > 0.7:
            # High load = peripheral/heuristic processing
            depth = ProcessingDepth.PERIPHERAL
        elif total < 0.3:
            # Low load = can engage in central processing
            depth = ProcessingDepth.CENTRAL
        else:
            depth = ProcessingDepth.MIXED
        
        return CognitiveLoadIndicator(
            user_id=user_id,
            session_id=session_id,
            intrinsic_load=intrinsic,
            extraneous_load=extraneous,
            germane_load=germane,
            total_load=total,
            capacity_remaining=capacity,
            is_overloaded=total > 0.8,
            processing_depth=depth,
            confidence=min(0.85, 0.3 + len(signals) * 0.05),
        )


# =============================================================================
# PROCESSING FLUENCY ANALYZER
# =============================================================================

class ProcessingFluencyAnalyzer:
    """
    Analyze processing fluency from behavioral signals.
    
    Research basis:
    - Processing fluency affects preference (Reber et al., 1998)
    - Fluency influences truth judgments (Unkelbach, 2007)
    - Disfluency triggers analytic processing (Alter et al., 2007)
    """
    
    def analyze(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> ProcessingFluencyScore:
        """
        Analyze processing fluency from behavioral patterns.
        """
        # High fluency indicators:
        # - Fast, direct movements
        # - Quick responses
        # - Few corrections
        # - Smooth scrolling
        
        perceptual_scores = []
        conceptual_scores = []
        
        for signal in signals:
            if isinstance(signal, KinematicSignal):
                # Direct movements = high perceptual fluency
                perceptual_scores.append(signal.directness_ratio)
                # Decisive movements = high conceptual fluency
                conceptual_scores.append(signal.decisiveness_score)
            
            elif isinstance(signal, TemporalSignal):
                # Fast responses = high fluency
                perceptual_scores.append(signal.attitude_accessibility)
                conceptual_scores.append(signal.attitude_accessibility)
            
            elif isinstance(signal, ScrollBehaviorSignal):
                # Smooth scrolling = high perceptual fluency
                velocity_smoothness = 1 - min(1.0, signal.velocity_changes / 20)
                perceptual_scores.append(velocity_smoothness)
            
            elif isinstance(signal, KeystrokeSignal):
                # Few corrections = high conceptual fluency
                conceptual_scores.append(1 - signal.correction_rate)
                # Consistent timing = high fluency
                timing_consistency = signal.confidence_score
                perceptual_scores.append(timing_consistency)
        
        # Calculate averages
        perceptual = sum(perceptual_scores) / len(perceptual_scores) if perceptual_scores else 0.5
        conceptual = sum(conceptual_scores) / len(conceptual_scores) if conceptual_scores else 0.5
        
        overall = (perceptual * 0.4 + conceptual * 0.6)
        
        # Estimate preference/trust boosts based on fluency
        # Research shows ~10-20% preference boost for high fluency
        preference_boost = (overall - 0.5) * 0.3  # -0.15 to +0.15
        trust_boost = (overall - 0.5) * 0.2  # -0.1 to +0.1
        
        return ProcessingFluencyScore(
            user_id=user_id,
            session_id=session_id,
            perceptual_fluency=perceptual,
            conceptual_fluency=conceptual,
            overall_fluency=overall,
            likely_preference_boost=preference_boost,
            likely_trust_boost=trust_boost,
            confidence=min(0.85, 0.3 + len(signals) * 0.05),
        )


# =============================================================================
# IMPLICIT PREFERENCE INFERENCE
# =============================================================================

class ImplicitPreferenceInference:
    """
    Infer implicit preferences from behavioral signals.
    
    Research basis:
    - Implicit attitudes predict behavior (Greenwald & Banaji, 1995)
    - Approach behaviors reveal preference (Chen & Bargh, 1999)
    - Response time reflects attitude strength (Fazio, 1990)
    """
    
    def __init__(self):
        # Running statistics for targets
        self._target_stats: Dict[str, Dict[str, float]] = {}
    
    def infer_preference(
        self,
        signals: List[NonconsciousSignal],
        target_id: str,
        target_type: str,
        user_id: str,
    ) -> ImplicitPreference:
        """
        Infer implicit preference for a target from behavioral signals.
        """
        preference_signals = []
        total_score = 0.0
        
        for signal in signals:
            if isinstance(signal, TemporalSignal):
                # Fast responses to target = positive implicit preference
                if signal.attitude_accessibility > 0.7:
                    total_score += 0.6
                    preference_signals.append(signal.signal_id)
                elif signal.attitude_accessibility < 0.3:
                    total_score -= 0.4
                    preference_signals.append(signal.signal_id)
            
            elif isinstance(signal, KinematicSignal):
                # Movement toward = positive preference
                if signal.decisiveness_score > 0.7:
                    total_score += 0.5
                    preference_signals.append(signal.signal_id)
                elif signal.conflict_indicator > 0.5:
                    total_score -= 0.3
                    preference_signals.append(signal.signal_id)
            
            elif isinstance(signal, ScrollBehaviorSignal):
                # Engagement = interest/preference
                if signal.engagement_score > 0.7:
                    total_score += 0.4
                    preference_signals.append(signal.signal_id)
        
        # Normalize to -1 to 1
        evidence_count = len(preference_signals)
        if evidence_count > 0:
            preference_strength = max(-1.0, min(1.0, total_score / evidence_count))
        else:
            preference_strength = 0.0
        
        # Accessibility: faster responses = more accessible
        accessibility_scores = [
            s.attitude_accessibility
            for s in signals
            if isinstance(s, TemporalSignal)
        ]
        accessibility = sum(accessibility_scores) / len(accessibility_scores) if accessibility_scores else 0.5
        
        return ImplicitPreference(
            user_id=user_id,
            target_id=target_id,
            target_type=target_type,
            preference_strength=preference_strength,
            preference_accessibility=accessibility,
            evidence_signals=preference_signals,
            evidence_count=evidence_count,
            confidence=min(0.8, 0.3 + evidence_count * 0.1),
        )
    
    def infer_automatic_evaluation(
        self,
        signal: TemporalSignal,
        stimulus_id: str,
        stimulus_type: str,
    ) -> AutomaticEvaluation:
        """
        Detect automatic (System 1) evaluation from response timing.
        
        Very fast responses (<500ms) are considered automatic.
        """
        # Automatic evaluation threshold (Bargh et al., 1996)
        is_automatic = signal.response_latency_ms < 500
        
        # Valence based on speed deviation
        # Positive stimuli processed faster than negative (Zajonc, 1980)
        if signal.deviation_from_baseline < -1.0:
            # Faster than baseline = likely positive
            valence = 0.3 + signal.attitude_accessibility * 0.5
        elif signal.deviation_from_baseline > 1.0:
            # Slower than baseline = likely negative or conflicted
            valence = -0.3 - (1 - signal.attitude_accessibility) * 0.5
        else:
            valence = 0.0
        
        is_strong = abs(valence) > 0.5
        
        return AutomaticEvaluation(
            user_id=signal.user_id,
            stimulus_id=stimulus_id,
            stimulus_type=stimulus_type,
            valence=max(-1.0, min(1.0, valence)),
            latency_ms=signal.response_latency_ms,
            is_automatic=is_automatic,
            is_strong=is_strong,
            confidence=0.7 if is_automatic else 0.5,
        )


# =============================================================================
# MASTER ANALYZER
# =============================================================================

class NonconsciousAnalyzer:
    """
    Master analyzer combining all nonconscious analysis methods.
    """
    
    def __init__(self):
        self.approach_avoidance = ApproachAvoidanceAnalyzer()
        self.cognitive_load = CognitiveLoadEstimator()
        self.fluency = ProcessingFluencyAnalyzer()
        self.preference = ImplicitPreferenceInference()
    
    async def analyze_session(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> NonconsciousProfile:
        """
        Produce complete nonconscious profile from session signals.
        """
        # Run all analyses
        aa = self.approach_avoidance.analyze(signals, user_id, session_id)
        cl = self.cognitive_load.estimate(signals, user_id, session_id)
        pf = self.fluency.analyze(signals, user_id, session_id)
        
        # Estimate emotional valence from signals
        ev = self._estimate_emotional_valence(signals, user_id, session_id)
        
        # Calculate engagement
        ei = self._calculate_engagement(signals, user_id, session_id)
        
        # Infer automatic evaluations from temporal signals
        auto_evals = [
            self.preference.infer_automatic_evaluation(s, s.stimulus_type, "stimulus")
            for s in signals
            if isinstance(s, TemporalSignal) and s.stimulus_type
        ]
        
        # Determine recommended mechanisms based on profile
        recommended_mechanisms = self._recommend_mechanisms(aa, cl, pf, ev)
        
        # Determine processing route
        if cl.is_overloaded or pf.overall_fluency < 0.4:
            processing_route = ProcessingDepth.PERIPHERAL
        elif pf.overall_fluency > 0.7 and cl.capacity_remaining > 0.5:
            processing_route = ProcessingDepth.CENTRAL
        else:
            processing_route = ProcessingDepth.MIXED
        
        # Calculate overall confidence
        confidences = [aa.confidence, cl.confidence, pf.confidence, ev.confidence, ei.confidence]
        overall_confidence = sum(confidences) / len(confidences)
        
        # Profile completeness based on signal types present
        signal_types = list(set(type(s).__name__ for s in signals))
        completeness = min(1.0, len(signal_types) / 5)
        
        return NonconsciousProfile(
            user_id=user_id,
            session_id=session_id,
            approach_avoidance=aa,
            cognitive_load=cl,
            emotional_valence=ev,
            processing_fluency=pf,
            engagement=ei,
            automatic_evaluations=auto_evals,
            signals_processed=len(signals),
            signal_types=signal_types,
            recommended_processing_route=processing_route,
            recommended_mechanisms=recommended_mechanisms,
            mechanism_confidence={m: 0.6 + 0.1 * i for i, m in enumerate(reversed(recommended_mechanisms))},
            overall_confidence=overall_confidence,
            profile_completeness=completeness,
            valid_until=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
    
    def _estimate_emotional_valence(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> EmotionalValenceProxy:
        """
        Estimate emotional valence from behavioral signals.
        """
        valence_scores = []
        arousal_scores = []
        
        for signal in signals:
            if isinstance(signal, KinematicSignal):
                # Fast smooth movement = positive valence + high arousal
                valence_scores.append(signal.decisiveness_score - 0.5)
                arousal_scores.append(min(1.0, signal.avg_velocity / 1000))
            
            elif isinstance(signal, KeystrokeSignal):
                # Confident typing = positive valence
                valence_scores.append(signal.confidence_score - 0.5)
                arousal_scores.append(signal.emotional_arousal)
            
            elif isinstance(signal, TemporalSignal):
                # Fast accessible responses = positive valence
                valence_scores.append(signal.attitude_accessibility - 0.5)
        
        # Aggregate
        valence = sum(valence_scores) / len(valence_scores) if valence_scores else 0.0
        arousal = sum(arousal_scores) / len(arousal_scores) if arousal_scores else 0.5
        
        # Determine direction
        if valence > 0.2:
            direction = ValenceDirection.POSITIVE
        elif valence < -0.2:
            direction = ValenceDirection.NEGATIVE
        else:
            direction = ValenceDirection.NEUTRAL
        
        return EmotionalValenceProxy(
            user_id=user_id,
            session_id=session_id,
            valence=max(-1.0, min(1.0, valence * 2)),
            valence_direction=direction,
            arousal=arousal,
            dominance=0.5,  # Would need more signals to estimate
            confidence=min(0.75, 0.3 + len(signals) * 0.04),
        )
    
    def _calculate_engagement(
        self,
        signals: List[NonconsciousSignal],
        user_id: str,
        session_id: str,
    ) -> EngagementIntensity:
        """
        Calculate engagement intensity from signals.
        """
        behavioral = []
        cognitive = []
        emotional = []
        
        for signal in signals:
            if isinstance(signal, ScrollBehaviorSignal):
                behavioral.append(signal.engagement_score)
                cognitive.append(signal.deliberation_score)
            
            elif isinstance(signal, KinematicSignal):
                behavioral.append(1 - signal.conflict_indicator)
            
            elif isinstance(signal, KeystrokeSignal):
                cognitive.append(1 - signal.deliberation_score)  # High deliberation = high cognitive engagement
                emotional.append(signal.emotional_arousal)
        
        be = sum(behavioral) / len(behavioral) if behavioral else 0.5
        ce = sum(cognitive) / len(cognitive) if cognitive else 0.5
        ee = sum(emotional) / len(emotional) if emotional else 0.5
        
        overall = (be * 0.3 + ce * 0.4 + ee * 0.3)
        
        return EngagementIntensity(
            user_id=user_id,
            session_id=session_id,
            behavioral_engagement=be,
            cognitive_engagement=ce,
            emotional_engagement=ee,
            overall_engagement=overall,
            engagement_trend="stable",
            confidence=min(0.8, 0.3 + len(signals) * 0.05),
        )
    
    def _recommend_mechanisms(
        self,
        aa: ApproachAvoidanceTendency,
        cl: CognitiveLoadIndicator,
        pf: ProcessingFluencyScore,
        ev: EmotionalValenceProxy,
    ) -> List[str]:
        """
        Recommend persuasion mechanisms based on nonconscious profile.
        """
        mechanisms = []
        
        # Based on approach-avoidance
        if aa.net_tendency > 0.3:
            # High approach = promotion-focused mechanisms
            mechanisms.extend(["social_proof", "gain_framing", "novelty"])
        elif aa.net_tendency < -0.3:
            # High avoidance = prevention-focused mechanisms
            mechanisms.extend(["loss_aversion", "security_appeal", "risk_reduction"])
        
        # Based on cognitive load
        if cl.is_overloaded or cl.processing_depth == ProcessingDepth.PERIPHERAL:
            # High load = heuristic cues
            mechanisms.extend(["authority", "scarcity", "simple_framing"])
        elif cl.capacity_remaining > 0.6:
            # Low load = can handle complex arguments
            mechanisms.extend(["information_appeal", "comparative_reasoning"])
        
        # Based on fluency
        if pf.overall_fluency > 0.7:
            # High fluency = familiar, congruent messages
            mechanisms.extend(["familiarity", "consistency"])
        elif pf.overall_fluency < 0.4:
            # Low fluency = need to reduce friction
            mechanisms.extend(["simplification", "visual_emphasis"])
        
        # Based on emotional valence
        if ev.valence_direction == ValenceDirection.POSITIVE:
            mechanisms.extend(["emotional_appeal_positive", "aspiration"])
        elif ev.valence_direction == ValenceDirection.NEGATIVE:
            mechanisms.extend(["problem_solution", "relief_appeal"])
        
        # Dedupe while preserving order
        seen = set()
        unique = []
        for m in mechanisms:
            if m not in seen:
                seen.add(m)
                unique.append(m)
        
        return unique[:5]  # Top 5 mechanisms
