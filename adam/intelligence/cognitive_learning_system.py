#!/usr/bin/env python3
"""
ADAM COGNITIVE LEARNING SYSTEM
==============================

This module implements the closed-loop learning system that integrates:
1. LangGraph Alignment Pipeline (real-time predictions)
2. Atom-of-Thought (AoT) Reasoning (pattern analysis)
3. Neo4j Graph Database (pattern storage)

The system learns from every interaction:
- Predictions become falsifiable hypotheses
- Outcomes provide ground truth
- AoT reasons about discrepancies
- Neo4j stores learned patterns
- Alignment matrices self-improve

Architecture:
┌────────────────────────────────────────────────────────────────────────────┐
│                     COGNITIVE LEARNING LOOP                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    PREDICTION PHASE                                  │  │
│  │                                                                      │  │
│  │  [Customer Profile] + [Ad Profile] → [Alignment Matrices]           │  │
│  │                                        ↓                             │  │
│  │                              [Predicted Effectiveness]               │  │
│  │                              [Predicted Backfire Risk]               │  │
│  └──────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                      │
│                                     ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    OBSERVATION PHASE                                 │  │
│  │                                                                      │  │
│  │  [Show Ad] → [Track Engagement] → [Track Conversion] → [Sentiment]  │  │
│  │                                        ↓                             │  │
│  │                              [Actual Effectiveness]                  │  │
│  └──────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                      │
│                                     ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    REASONING PHASE (AoT)                             │  │
│  │                                                                      │  │
│  │  [Predicted] vs [Actual] → [Why discrepancy?]                       │  │
│  │                                        ↓                             │  │
│  │  Atom-of-Thought Reasoning:                                         │  │
│  │    - Was motivation inference wrong?                                │  │
│  │    - Was alignment matrix outdated?                                 │  │
│  │    - Was context factor missed?                                     │  │
│  │    - Was persuasion technique mismatched?                           │  │
│  │                                        ↓                             │  │
│  │                              [Pattern Hypothesis]                    │  │
│  └──────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                      │
│                                     ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    UPDATE PHASE                                      │  │
│  │                                                                      │  │
│  │  [Pattern Hypothesis] → [Validate with similar cases]               │  │
│  │                                        ↓                             │  │
│  │  If validated (n >= threshold):                                     │  │
│  │    - Update alignment matrices                                      │  │
│  │    - Store pattern in Neo4j                                         │  │
│  │    - Adjust confidence weights                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import math


# =============================================================================
# REASONING PATTERNS (Atom-of-Thought Structure)
# =============================================================================

class ReasoningAtomType(Enum):
    """Types of atomic reasoning units."""
    
    OBSERVATION = "observation"  # What happened
    PREDICTION = "prediction"  # What was expected
    DISCREPANCY = "discrepancy"  # Gap between expected and actual
    HYPOTHESIS = "hypothesis"  # Why the gap exists
    EVIDENCE = "evidence"  # Supporting or refuting data
    CONCLUSION = "conclusion"  # Final determination
    ACTION = "action"  # What to do about it


@dataclass
class ReasoningAtom:
    """
    Single atomic unit of reasoning.
    Represents one "thought" in the Atom-of-Thought framework.
    """
    
    atom_type: ReasoningAtomType
    content: str
    confidence: float  # 0-1
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    derived_from: List[str] = field(default_factory=list)  # IDs of parent atoms
    atom_id: str = ""
    
    def __post_init__(self):
        if not self.atom_id:
            self.atom_id = f"{self.atom_type.value}_{hash(self.content) % 10000:04d}"


@dataclass
class ReasoningChain:
    """
    Chain of reasoning atoms forming a complete analysis.
    """
    
    chain_id: str
    atoms: List[ReasoningAtom] = field(default_factory=list)
    final_conclusion: Optional[ReasoningAtom] = None
    confidence_score: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def add_atom(self, atom: ReasoningAtom) -> None:
        self.atoms.append(atom)
        self._recalculate_confidence()
    
    def _recalculate_confidence(self) -> None:
        if not self.atoms:
            self.confidence_score = 0.0
            return
        
        # Chain confidence is product of individual confidences (Bayesian-like)
        confidence_product = 1.0
        for atom in self.atoms:
            confidence_product *= atom.confidence
        
        # But we don't want it to collapse too quickly, so use geometric mean
        self.confidence_score = math.pow(confidence_product, 1 / len(self.atoms))


# =============================================================================
# PATTERN LEARNER
# =============================================================================

@dataclass
class LearnedPattern:
    """
    A pattern discovered through learning.
    """
    
    pattern_id: str
    pattern_type: str
    description: str
    
    # The pattern itself
    customer_dimension: str  # e.g., "motivation"
    customer_value: str  # e.g., "immediate_gratification"
    ad_dimension: str  # e.g., "persuasion"
    ad_value: str  # e.g., "scarcity"
    
    # Learned statistics
    original_alignment: float  # What matrix said
    actual_effectiveness: float  # What really happened
    correction_factor: float  # How much to adjust
    
    # Evidence
    sample_count: int
    positive_outcomes: int
    negative_outcomes: int
    confidence: float
    
    # Metadata
    first_observed: str
    last_updated: str
    reasoning_chain_id: Optional[str] = None


class PatternLearner:
    """
    Learns patterns from alignment predictions vs actual outcomes.
    Implements the AoT reasoning to discover why predictions fail.
    """
    
    def __init__(self, min_samples_for_pattern: int = 10):
        self.min_samples = min_samples_for_pattern
        self.pending_observations: List[Dict[str, Any]] = []
        self.learned_patterns: Dict[str, LearnedPattern] = {}
        self.correction_factors: Dict[str, float] = {}
    
    def observe_outcome(
        self,
        customer_profile: Dict[str, Any],
        ad_profile: Dict[str, Any],
        alignment_prediction: Dict[str, Any],
        actual_outcome: Dict[str, Any],
    ) -> Optional[ReasoningChain]:
        """
        Observe an outcome and potentially learn from it.
        """
        
        # Calculate discrepancy
        predicted = alignment_prediction.get("predicted_effectiveness", 0.5)
        actual = self._calculate_actual_effectiveness(actual_outcome)
        
        discrepancy = actual - predicted
        
        # Store observation
        observation = {
            "customer": customer_profile,
            "ad": ad_profile,
            "predicted": predicted,
            "actual": actual,
            "discrepancy": discrepancy,
            "timestamp": datetime.now().isoformat(),
        }
        self.pending_observations.append(observation)
        
        # If significant discrepancy, trigger reasoning
        if abs(discrepancy) > 0.15:  # 15% threshold
            return self._reason_about_discrepancy(observation, alignment_prediction)
        
        return None
    
    def _reason_about_discrepancy(
        self,
        observation: Dict[str, Any],
        alignment_prediction: Dict[str, Any],
    ) -> ReasoningChain:
        """
        Use AoT reasoning to understand why prediction failed.
        """
        
        chain = ReasoningChain(
            chain_id=f"reason_{int(datetime.now().timestamp())}"
        )
        
        # Atom 1: Observation
        obs_atom = ReasoningAtom(
            atom_type=ReasoningAtomType.OBSERVATION,
            content=f"Observed {observation['actual']:.0%} effectiveness vs predicted {observation['predicted']:.0%}",
            confidence=1.0,  # Observations are facts
            supporting_data={"outcome": observation}
        )
        chain.add_atom(obs_atom)
        
        # Atom 2: Discrepancy identification
        discrepancy = observation["discrepancy"]
        direction = "under-predicted" if discrepancy > 0 else "over-predicted"
        
        disc_atom = ReasoningAtom(
            atom_type=ReasoningAtomType.DISCREPANCY,
            content=f"System {direction} effectiveness by {abs(discrepancy):.0%}",
            confidence=1.0,
            supporting_data={"discrepancy": discrepancy, "direction": direction},
            derived_from=[obs_atom.atom_id]
        )
        chain.add_atom(disc_atom)
        
        # Atom 3-N: Hypothesis generation
        hypotheses = self._generate_hypotheses(
            observation, alignment_prediction, discrepancy
        )
        
        best_hypothesis = None
        best_confidence = 0.0
        
        for hyp_content, hyp_confidence, hyp_data in hypotheses:
            hyp_atom = ReasoningAtom(
                atom_type=ReasoningAtomType.HYPOTHESIS,
                content=hyp_content,
                confidence=hyp_confidence,
                supporting_data=hyp_data,
                derived_from=[disc_atom.atom_id]
            )
            chain.add_atom(hyp_atom)
            
            if hyp_confidence > best_confidence:
                best_hypothesis = hyp_atom
                best_confidence = hyp_confidence
        
        # Atom: Conclusion
        if best_hypothesis:
            conclusion = ReasoningAtom(
                atom_type=ReasoningAtomType.CONCLUSION,
                content=f"Most likely cause: {best_hypothesis.content}",
                confidence=best_confidence,
                supporting_data={
                    "best_hypothesis": best_hypothesis.content,
                    "correction_suggested": self._suggest_correction(
                        observation, best_hypothesis
                    )
                },
                derived_from=[best_hypothesis.atom_id]
            )
            chain.add_atom(conclusion)
            chain.final_conclusion = conclusion
            
            # Atom: Action
            action = self._determine_action(observation, conclusion)
            chain.add_atom(action)
        
        return chain
    
    def _generate_hypotheses(
        self,
        observation: Dict[str, Any],
        alignment_prediction: Dict[str, Any],
        discrepancy: float,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Generate hypotheses for why the prediction was wrong.
        Returns list of (hypothesis_text, confidence, supporting_data)
        """
        
        hypotheses = []
        customer = observation["customer"]
        ad = observation["ad"]
        components = alignment_prediction.get("component_scores", {})
        
        # Hypothesis 1: Motivation mismatch
        if components.get("motivation_alignment", 0.5) < 0.5:
            conf = 0.7 if discrepancy < 0 else 0.3
            hypotheses.append((
                f"Motivation alignment matrix underestimates "
                f"{customer.get('expanded_motivation')} ↔ {ad.get('value', {}).get('primary')}",
                conf,
                {"dimension": "motivation", "current_score": components.get("motivation_alignment")}
            ))
        
        # Hypothesis 2: Decision style mismatch
        if components.get("decision_style_alignment", 0.5) < 0.5:
            conf = 0.65 if discrepancy < 0 else 0.35
            hypotheses.append((
                f"Decision style ↔ linguistic style matrix needs adjustment for "
                f"{customer.get('expanded_decision_style')}",
                conf,
                {"dimension": "decision_style", "current_score": components.get("decision_style_alignment")}
            ))
        
        # Hypothesis 3: Persuasion technique effectiveness
        persuasion = ad.get("persuasion", {}).get("primary", "unknown")
        if discrepancy > 0.1:  # Under-predicted
            hypotheses.append((
                f"Persuasion technique '{persuasion}' more effective than modeled "
                f"for this customer segment",
                0.6,
                {"dimension": "persuasion", "technique": persuasion}
            ))
        elif discrepancy < -0.1:  # Over-predicted
            hypotheses.append((
                f"Persuasion technique '{persuasion}' backfired or was ineffective "
                f"for this customer segment",
                0.6,
                {"dimension": "persuasion", "technique": persuasion, "potential_backfire": True}
            ))
        
        # Hypothesis 4: Context factor missed
        hypotheses.append((
            "Unknown contextual factor may have influenced outcome",
            0.3,  # Lower confidence - catch-all
            {"dimension": "context", "unobserved_factor": True}
        ))
        
        # Hypothesis 5: Cognitive load mismatch
        cognitive_load = customer.get("cognitive_load_tolerance", "moderate_cognitive")
        linguistic_style = ad.get("linguistic_style", {}).get("primary", "unknown")
        
        if cognitive_load == "minimal_cognitive" and linguistic_style == "technical":
            hypotheses.append((
                f"Cognitive load tolerance ({cognitive_load}) exceeded by ad complexity ({linguistic_style})",
                0.75,
                {"dimension": "cognitive_load", "customer_tolerance": cognitive_load, "ad_style": linguistic_style}
            ))
        
        return hypotheses
    
    def _suggest_correction(
        self,
        observation: Dict[str, Any],
        hypothesis: ReasoningAtom,
    ) -> Dict[str, Any]:
        """
        Suggest how to correct the alignment matrix based on hypothesis.
        """
        
        hyp_data = hypothesis.supporting_data
        dimension = hyp_data.get("dimension", "unknown")
        discrepancy = observation["discrepancy"]
        
        # Calculate correction factor (Bayesian update style)
        # Start conservative, increase with more evidence
        base_correction = discrepancy * 0.1  # 10% of discrepancy
        confidence_weighted = base_correction * hypothesis.confidence
        
        return {
            "dimension": dimension,
            "correction_amount": confidence_weighted,
            "direction": "increase" if discrepancy > 0 else "decrease",
            "confidence": hypothesis.confidence,
            "requires_validation": True,
        }
    
    def _determine_action(
        self,
        observation: Dict[str, Any],
        conclusion: ReasoningAtom,
    ) -> ReasoningAtom:
        """
        Determine what action to take based on conclusion.
        """
        
        correction = conclusion.supporting_data.get("correction_suggested", {})
        dimension = correction.get("dimension", "unknown")
        
        # Check if we have enough samples to act
        pattern_key = self._make_pattern_key(observation, dimension)
        similar_observations = self._count_similar_observations(pattern_key)
        
        if similar_observations >= self.min_samples:
            action_content = (
                f"Update {dimension} alignment matrix: "
                f"{correction.get('direction')} by {abs(correction.get('correction_amount', 0)):.1%}"
            )
            action_confidence = min(conclusion.confidence, similar_observations / (self.min_samples * 2))
        else:
            action_content = (
                f"Collect more data ({similar_observations}/{self.min_samples} samples) "
                f"before updating {dimension} matrix"
            )
            action_confidence = 0.3
        
        return ReasoningAtom(
            atom_type=ReasoningAtomType.ACTION,
            content=action_content,
            confidence=action_confidence,
            supporting_data={
                "pattern_key": pattern_key,
                "samples_collected": similar_observations,
                "samples_needed": self.min_samples,
            },
            derived_from=[conclusion.atom_id]
        )
    
    def _calculate_actual_effectiveness(self, outcome: Dict[str, Any]) -> float:
        """Calculate actual effectiveness from outcome metrics."""
        
        scores = []
        
        if outcome.get("conversion") is not None:
            scores.append(1.0 if outcome["conversion"] else 0.0)
        
        if outcome.get("engagement") is not None:
            scores.append(outcome["engagement"])
        
        if outcome.get("sentiment") is not None:
            scores.append(outcome["sentiment"])
        
        if scores:
            return sum(scores) / len(scores)
        return 0.5  # Neutral if no data
    
    def _make_pattern_key(
        self,
        observation: Dict[str, Any],
        dimension: str,
    ) -> str:
        """Create a unique key for pattern matching."""
        
        customer = observation["customer"]
        ad = observation["ad"]
        
        if dimension == "motivation":
            return f"mot:{customer.get('expanded_motivation')}→val:{ad.get('value', {}).get('primary')}"
        elif dimension == "decision_style":
            return f"dec:{customer.get('expanded_decision_style')}→ling:{ad.get('linguistic_style', {}).get('primary')}"
        elif dimension == "persuasion":
            return f"per:{ad.get('persuasion', {}).get('primary')}→cust:{customer.get('expanded_motivation')}"
        else:
            return f"{dimension}:general"
    
    def _count_similar_observations(self, pattern_key: str) -> int:
        """Count observations matching the pattern key."""
        
        count = 0
        for obs in self.pending_observations:
            # Simplified matching - in production would be more sophisticated
            if pattern_key.split(":")[0] in str(obs):
                count += 1
        return count
    
    def consolidate_learning(self) -> List[LearnedPattern]:
        """
        Consolidate pending observations into learned patterns.
        Called periodically to crystallize learning.
        """
        
        new_patterns = []
        
        # Group observations by pattern
        pattern_groups: Dict[str, List[Dict[str, Any]]] = {}
        
        for obs in self.pending_observations:
            for dimension in ["motivation", "decision_style", "persuasion"]:
                key = self._make_pattern_key(obs, dimension)
                if key not in pattern_groups:
                    pattern_groups[key] = []
                pattern_groups[key].append(obs)
        
        # Create patterns from groups with enough samples
        for pattern_key, observations in pattern_groups.items():
            if len(observations) >= self.min_samples:
                pattern = self._create_pattern(pattern_key, observations)
                if pattern:
                    new_patterns.append(pattern)
                    self.learned_patterns[pattern.pattern_id] = pattern
        
        return new_patterns
    
    def _create_pattern(
        self,
        pattern_key: str,
        observations: List[Dict[str, Any]],
    ) -> Optional[LearnedPattern]:
        """Create a learned pattern from observations."""
        
        if not observations:
            return None
        
        # Parse pattern key
        parts = pattern_key.split("→")
        if len(parts) != 2:
            return None
        
        customer_part = parts[0].split(":")
        ad_part = parts[1].split(":")
        
        # Calculate statistics
        discrepancies = [obs["discrepancy"] for obs in observations]
        avg_discrepancy = sum(discrepancies) / len(discrepancies)
        
        predicted_avg = sum(obs["predicted"] for obs in observations) / len(observations)
        actual_avg = sum(obs["actual"] for obs in observations) / len(observations)
        
        positive = sum(1 for obs in observations if obs["discrepancy"] > 0)
        negative = sum(1 for obs in observations if obs["discrepancy"] <= 0)
        
        # Calculate confidence based on consistency
        variance = sum((d - avg_discrepancy) ** 2 for d in discrepancies) / len(discrepancies)
        consistency = 1 / (1 + math.sqrt(variance))  # Lower variance = higher confidence
        
        return LearnedPattern(
            pattern_id=f"pat_{hash(pattern_key) % 100000:05d}",
            pattern_type=customer_part[0],
            description=f"Learned alignment correction for {pattern_key}",
            customer_dimension=customer_part[0],
            customer_value=customer_part[1] if len(customer_part) > 1 else "unknown",
            ad_dimension=ad_part[0],
            ad_value=ad_part[1] if len(ad_part) > 1 else "unknown",
            original_alignment=predicted_avg,
            actual_effectiveness=actual_avg,
            correction_factor=avg_discrepancy,
            sample_count=len(observations),
            positive_outcomes=positive,
            negative_outcomes=negative,
            confidence=consistency,
            first_observed=min(obs["timestamp"] for obs in observations),
            last_updated=datetime.now().isoformat(),
        )
    
    def get_correction_factor(
        self,
        customer_dimension: str,
        customer_value: str,
        ad_dimension: str,
        ad_value: str,
    ) -> Optional[float]:
        """
        Get learned correction factor for alignment calculation.
        """
        
        pattern_key = f"{customer_dimension}:{customer_value}→{ad_dimension}:{ad_value}"
        
        if pattern_key in self.correction_factors:
            return self.correction_factors[pattern_key]
        
        # Look for matching pattern
        for pattern in self.learned_patterns.values():
            if (pattern.customer_dimension == customer_dimension and
                pattern.customer_value == customer_value and
                pattern.ad_dimension == ad_dimension and
                pattern.ad_value == ad_value):
                
                return pattern.correction_factor
        
        return None


# =============================================================================
# COGNITIVE LEARNING SYSTEM (MAIN ORCHESTRATOR)
# =============================================================================

class CognitiveLearningSystem:
    """
    Main orchestrator for the cognitive learning loop.
    Integrates alignment predictions, outcome tracking, and pattern learning.
    """
    
    def __init__(self, neo4j_driver=None):
        from .langgraph_alignment_integration import AlignmentPipeline
        
        self.alignment_pipeline = AlignmentPipeline()
        self.pattern_learner = PatternLearner()
        self.neo4j_driver = neo4j_driver
        
        # Statistics
        self.predictions_made = 0
        self.outcomes_observed = 0
        self.patterns_learned = 0
        self.corrections_applied = 0
    
    def predict_alignment(
        self,
        customer_text: Optional[str] = None,
        customer_motivation: Optional[str] = None,
        customer_decision_style: Optional[str] = None,
        customer_archetype: str = "pragmatist",
        ad_text: str = "",
    ) -> Dict[str, Any]:
        """
        Make alignment prediction (Phase 1 of learning loop).
        """
        
        result = self.alignment_pipeline.run(
            customer_text=customer_text,
            customer_motivation=customer_motivation,
            customer_decision_style=customer_decision_style,
            customer_archetype=customer_archetype,
            ad_text=ad_text,
        )
        
        self.predictions_made += 1
        
        # Apply learned corrections if available
        corrected_score = self._apply_learned_corrections(
            result["customer_profile"],
            result["ad_profile"],
            result["alignment_score"],
        )
        
        result["alignment_score"]["corrected_effectiveness"] = corrected_score
        
        return result
    
    def observe_outcome(
        self,
        prediction_state: Dict[str, Any],
        conversion: Optional[bool] = None,
        engagement: Optional[float] = None,
        sentiment: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Observe outcome and trigger learning (Phase 2-3 of learning loop).
        """
        
        outcome = {
            "conversion": conversion,
            "engagement": engagement,
            "sentiment": sentiment,
        }
        
        # Observe and potentially reason
        reasoning_chain = self.pattern_learner.observe_outcome(
            customer_profile=prediction_state["customer_profile"],
            ad_profile=prediction_state["ad_profile"],
            alignment_prediction=prediction_state["alignment_score"],
            actual_outcome=outcome,
        )
        
        self.outcomes_observed += 1
        
        # Store outcome in state for tracking
        result = self.alignment_pipeline.capture_outcome(
            prediction_state,
            conversion=conversion,
            engagement=engagement,
            sentiment=sentiment,
        )
        
        result["reasoning_chain"] = None
        if reasoning_chain:
            result["reasoning_chain"] = {
                "chain_id": reasoning_chain.chain_id,
                "atoms": [
                    {
                        "type": a.atom_type.value,
                        "content": a.content,
                        "confidence": a.confidence,
                    }
                    for a in reasoning_chain.atoms
                ],
                "conclusion": reasoning_chain.final_conclusion.content if reasoning_chain.final_conclusion else None,
                "confidence": reasoning_chain.confidence_score,
            }
        
        return result
    
    def consolidate_learning(self) -> Dict[str, Any]:
        """
        Consolidate learned patterns (Phase 4 of learning loop).
        Call periodically to crystallize learning.
        """
        
        new_patterns = self.pattern_learner.consolidate_learning()
        self.patterns_learned += len(new_patterns)
        
        # Store patterns in Neo4j if available
        if self.neo4j_driver and new_patterns:
            self._store_patterns_in_neo4j(new_patterns)
        
        return {
            "new_patterns": len(new_patterns),
            "total_patterns": len(self.pattern_learner.learned_patterns),
            "patterns": [
                {
                    "id": p.pattern_id,
                    "description": p.description,
                    "correction_factor": p.correction_factor,
                    "confidence": p.confidence,
                    "sample_count": p.sample_count,
                }
                for p in new_patterns
            ],
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        
        return {
            "predictions_made": self.predictions_made,
            "outcomes_observed": self.outcomes_observed,
            "patterns_learned": self.patterns_learned,
            "corrections_applied": self.corrections_applied,
            "pending_observations": len(self.pattern_learner.pending_observations),
            "learned_patterns": len(self.pattern_learner.learned_patterns),
        }
    
    def _apply_learned_corrections(
        self,
        customer_profile: Dict[str, Any],
        ad_profile: Dict[str, Any],
        alignment_score: Dict[str, Any],
    ) -> float:
        """
        Apply learned correction factors to predicted effectiveness.
        
        Integrates corpus priors as Bayesian base rates — the corpus provides
        the empirical anchor (what typically works), and learned corrections
        adjust from there based on observed outcomes.
        """
        
        base_effectiveness = alignment_score["scores"]["predicted_effectiveness"]
        
        # Apply corpus prior as base rate anchor (Bayesian: start from empirical data)
        corpus_base = self._get_corpus_base_rate(customer_profile, ad_profile)
        if corpus_base is not None:
            # Blend: 70% model prediction, 30% corpus empirical base rate
            base_effectiveness = 0.70 * base_effectiveness + 0.30 * corpus_base
        
        # Look for relevant corrections
        motivation_correction = self.pattern_learner.get_correction_factor(
            "motivation",
            customer_profile.get("expanded_motivation", "functional_need"),
            "value",
            ad_profile.get("value", {}).get("primary", "unknown"),
        )
        
        decision_correction = self.pattern_learner.get_correction_factor(
            "decision_style",
            customer_profile.get("expanded_decision_style", "satisficing"),
            "linguistic_style",
            ad_profile.get("linguistic_style", {}).get("primary", "unknown"),
        )
        
        # Apply corrections
        total_correction = 0.0
        
        if motivation_correction:
            total_correction += motivation_correction * 0.5
            self.corrections_applied += 1
        
        if decision_correction:
            total_correction += decision_correction * 0.5
            self.corrections_applied += 1
        
        # Bound the result
        corrected = max(0.0, min(1.0, base_effectiveness + total_correction))
        
        return corrected
    
    def _get_corpus_base_rate(
        self,
        customer_profile: Dict[str, Any],
        ad_profile: Dict[str, Any],
    ) -> Optional[float]:
        """
        Get corpus-derived base rate for this customer-ad alignment.
        
        Uses PriorExtractionService to get empirical mechanism effectiveness
        for the customer's archetype and the ad's primary persuasion mechanism.
        """
        try:
            from adam.fusion.prior_extraction import get_prior_extraction_service
            prior_service = get_prior_extraction_service()
            
            archetype = customer_profile.get("archetype", "")
            mechanism = ad_profile.get("persuasion", {}).get("primary", "")
            
            if not mechanism:
                return None
            
            corpus_prior = prior_service.extract_prior(
                category="",  # Cross-category
                archetype=archetype or None,
                target_mechanism=mechanism,
            )
            
            if corpus_prior and corpus_prior.mechanism_priors:
                # Get the score for the specific mechanism
                normalized = mechanism.lower().replace(" ", "_")
                mech_dict = corpus_prior.get_mechanism_dict()
                for mech_name, score in mech_dict.items():
                    if mech_name.lower().replace(" ", "_") == normalized:
                        return score
                
                # If specific mechanism not found, use average as base
                if mech_dict:
                    return sum(mech_dict.values()) / len(mech_dict)
        except ImportError:
            pass
        except Exception:
            pass
        
        return None
    
    def _store_patterns_in_neo4j(self, patterns: List[LearnedPattern]) -> None:
        """Store learned patterns in Neo4j."""
        
        if not self.neo4j_driver:
            return
        
        query = """
        MERGE (p:LearnedPattern {pattern_id: $pattern_id})
        SET p.description = $description,
            p.customer_dimension = $customer_dimension,
            p.customer_value = $customer_value,
            p.ad_dimension = $ad_dimension,
            p.ad_value = $ad_value,
            p.correction_factor = $correction_factor,
            p.sample_count = $sample_count,
            p.confidence = $confidence,
            p.last_updated = datetime()
        RETURN p
        """
        
        with self.neo4j_driver.session() as session:
            for pattern in patterns:
                session.run(
                    query,
                    pattern_id=pattern.pattern_id,
                    description=pattern.description,
                    customer_dimension=pattern.customer_dimension,
                    customer_value=pattern.customer_value,
                    ad_dimension=pattern.ad_dimension,
                    ad_value=pattern.ad_value,
                    correction_factor=pattern.correction_factor,
                    sample_count=pattern.sample_count,
                    confidence=pattern.confidence,
                )


# =============================================================================
# EXPORTS
# =============================================================================

def export_learning_system_priors() -> Dict[str, Any]:
    """Export learning system configuration for cold-start priors."""
    
    return {
        "reasoning_config": {
            "atom_types": [t.value for t in ReasoningAtomType],
            "discrepancy_threshold": 0.15,
            "min_samples_for_pattern": 10,
        },
        "learning_config": {
            "correction_factor_weight": 0.1,
            "confidence_decay": 0.95,
            "consolidation_interval_observations": 100,
        },
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("COGNITIVE LEARNING SYSTEM TEST")
    print("="*70)
    
    system = CognitiveLearningSystem()
    
    # Simulate a learning loop
    print("\n=== Simulating Learning Loop ===")
    
    # Prediction 1
    print("\n--- Prediction 1: High alignment expected ---")
    pred1 = system.predict_alignment(
        customer_text="I need to buy this right now! So excited!",
        ad_text="LIMITED TIME OFFER! Only 3 left! Don't miss out!",
    )
    print(f"Predicted effectiveness: {pred1['alignment_score']['scores']['predicted_effectiveness']:.0%}")
    
    # Observe outcome (positive - validates prediction)
    outcome1 = system.observe_outcome(pred1, conversion=True, engagement=0.9, sentiment=0.85)
    if outcome1.get("reasoning_chain"):
        print(f"Reasoning triggered: {outcome1['reasoning_chain']['conclusion']}")
    else:
        print("No significant discrepancy - prediction accurate")
    
    # Prediction 2
    print("\n--- Prediction 2: Medium alignment expected ---")
    pred2 = system.predict_alignment(
        customer_text="I need to research this carefully before deciding.",
        ad_text="ACT NOW! This deal won't last! Limited time only!",
    )
    print(f"Predicted effectiveness: {pred2['alignment_score']['scores']['predicted_effectiveness']:.0%}")
    
    # Observe outcome (negative - contradicts prediction)
    outcome2 = system.observe_outcome(pred2, conversion=False, engagement=0.2, sentiment=0.3)
    if outcome2.get("reasoning_chain"):
        print(f"Reasoning chain:")
        for atom in outcome2["reasoning_chain"]["atoms"]:
            print(f"  [{atom['type']}] {atom['content'][:60]}...")
    
    # Prediction 3
    print("\n--- Prediction 3: Low alignment expected ---")
    pred3 = system.predict_alignment(
        customer_text="I want expert recommendations and detailed specifications.",
        ad_text="Everyone's buying this! Be like them! Join the crowd!",
    )
    print(f"Predicted effectiveness: {pred3['alignment_score']['scores']['predicted_effectiveness']:.0%}")
    
    # Observe outcome (surprisingly positive - contradicts prediction)
    outcome3 = system.observe_outcome(pred3, conversion=True, engagement=0.7, sentiment=0.6)
    if outcome3.get("reasoning_chain"):
        print(f"Reasoning triggered: {outcome3['reasoning_chain']['conclusion']}")
    
    # Show stats
    print("\n=== Learning System Stats ===")
    stats = system.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n=== Testing Complete ===")


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_cognitive_learning_system_instance: Optional[CognitiveLearningSystem] = None


def get_cognitive_learning_system() -> CognitiveLearningSystem:
    """
    Return the module-level singleton CognitiveLearningSystem.

    This ensures accumulated learning (pattern observations, alignment
    matrices, correction factors) persists across calls rather than being
    discarded with a fresh instance on every invocation.
    """
    global _cognitive_learning_system_instance
    if _cognitive_learning_system_instance is None:
        _cognitive_learning_system_instance = CognitiveLearningSystem()
    return _cognitive_learning_system_instance
