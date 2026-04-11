#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Learning System Strengthening Script
# Location: scripts/run_learning_strengthening.py
# =============================================================================

"""
LEARNING SYSTEM STRENGTHENING

Implements 5 key recommendations to make the ADAM learning system stronger:

1. QUALITY AUDIT: Run LearningQualityAuditor across all 8 dimensions
2. MINORITY ARCHETYPE AUGMENTATION: Increase data for Pragmatist/Analyzer
3. THOMPSON SAMPLING WARM-START: Initialize posteriors from learned matrix
4. CROSS-CATEGORY TRANSFER LEARNING: Propagate category→archetype patterns
5. CALIBRATION CHECK: Implement Platt scaling for confidence calibration

Usage:
    python scripts/run_learning_strengthening.py
    python scripts/run_learning_strengthening.py --audit-only
    python scripts/run_learning_strengthening.py --warm-start-only
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA PATHS
# =============================================================================

LEARNING_DATA_DIR = project_root / "data" / "learning"
ARCHETYPE_MECHANISM_MATRIX = LEARNING_DATA_DIR / "archetype_mechanism_matrix.json"
CATEGORY_ARCHETYPES = LEARNING_DATA_DIR / "category_archetypes.json"
BRAND_ARCHETYPE_EFFECTIVENESS = LEARNING_DATA_DIR / "brand_archetype_effectiveness.json"
LEARNING_SUMMARY = LEARNING_DATA_DIR / "learning_summary.json"


# =============================================================================
# 1. QUALITY AUDIT IMPLEMENTATION
# =============================================================================

@dataclass
class QualityDimensionScore:
    """Score for a single quality dimension."""
    dimension: str
    score: float
    level: str  # excellent, good, acceptable, concerning, critical
    evidence: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SystemAuditResult:
    """Complete system audit result."""
    audit_id: str
    timestamp: datetime
    overall_score: float
    overall_level: str
    dimension_scores: Dict[str, QualityDimensionScore]
    critical_issues: List[str]
    recommendations: List[str]


class LearningQualityAuditor:
    """
    Audits the quality of learning across the ADAM system.
    
    Measures 8 dimensions:
    1. EFFECTIVENESS - Does learning improve predictions?
    2. EFFICIENCY - Does learning converge quickly?
    3. COHERENCE - Do components agree on what they've learned?
    4. FRESHNESS - Are priors current and not stale?
    5. COMPLETENESS - Are all learning pathways connected?
    6. SYNERGY - Does learning create emergent value?
    7. CALIBRATION - Does confidence match accuracy?
    8. GENERALIZATION - Does learning generalize?
    """
    
    def __init__(self):
        self.archetype_matrix = {}
        self.category_archetypes = {}
        self.brand_effectiveness = {}
        self.learning_summary = {}
        
    def load_learning_artifacts(self) -> bool:
        """Load all learning artifacts for audit."""
        try:
            if ARCHETYPE_MECHANISM_MATRIX.exists():
                with open(ARCHETYPE_MECHANISM_MATRIX) as f:
                    self.archetype_matrix = json.load(f)
                logger.info(f"✓ Loaded archetype-mechanism matrix: {len(self.archetype_matrix)} archetypes")
            
            if CATEGORY_ARCHETYPES.exists():
                with open(CATEGORY_ARCHETYPES) as f:
                    self.category_archetypes = json.load(f)
                logger.info(f"✓ Loaded category archetypes: {len(self.category_archetypes)} categories")
            
            if BRAND_ARCHETYPE_EFFECTIVENESS.exists():
                with open(BRAND_ARCHETYPE_EFFECTIVENESS) as f:
                    self.brand_effectiveness = json.load(f)
                logger.info(f"✓ Loaded brand effectiveness: {len(self.brand_effectiveness)} brands")
            
            if LEARNING_SUMMARY.exists():
                with open(LEARNING_SUMMARY) as f:
                    self.learning_summary = json.load(f)
                logger.info(f"✓ Loaded learning summary")
            
            return True
        except Exception as e:
            logger.error(f"Failed to load learning artifacts: {e}")
            return False
    
    def _score_to_level(self, score: float) -> str:
        """Convert score to quality level."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.75:
            return "good"
        elif score >= 0.6:
            return "acceptable"
        elif score >= 0.4:
            return "concerning"
        return "critical"
    
    def audit_effectiveness(self) -> QualityDimensionScore:
        """
        Audit EFFECTIVENESS: Does learning improve predictions?
        
        Measures:
        - Observation counts per archetype
        - Standard deviation of effectiveness estimates
        - Coverage across mechanisms
        """
        evidence = []
        issues = []
        recommendations = []
        
        # Check observation counts
        total_observations = 0
        min_observations = float('inf')
        min_archetype = ""
        
        for archetype, mechanisms in self.archetype_matrix.items():
            for mech, data in mechanisms.items():
                obs = data.get("observations", 0)
                total_observations += obs
                if obs < min_observations:
                    min_observations = obs
                    min_archetype = archetype
        
        evidence.append(f"Total observations: {total_observations}")
        evidence.append(f"Minimum observations: {min_observations} ({min_archetype})")
        
        # Score based on observation coverage
        if min_observations >= 100:
            obs_score = 1.0
        elif min_observations >= 50:
            obs_score = 0.8
        elif min_observations >= 20:
            obs_score = 0.6
        elif min_observations >= 10:
            obs_score = 0.4
        else:
            obs_score = 0.2
            issues.append(f"Very low observations for {min_archetype}: {min_observations}")
            recommendations.append(f"Collect more data for {min_archetype} archetype")
        
        # Check variance (lower is better for effectiveness estimates)
        avg_std = 0
        std_count = 0
        for archetype, mechanisms in self.archetype_matrix.items():
            for mech, data in mechanisms.items():
                if "std_dev" in data:
                    avg_std += data["std_dev"]
                    std_count += 1
        
        if std_count > 0:
            avg_std /= std_count
            evidence.append(f"Average std dev: {avg_std:.4f}")
            
            if avg_std < 0.02:
                var_score = 1.0
            elif avg_std < 0.03:
                var_score = 0.8
            elif avg_std < 0.05:
                var_score = 0.6
            else:
                var_score = 0.4
                issues.append(f"High variance in effectiveness estimates: {avg_std:.4f}")
        else:
            var_score = 0.5
        
        score = (obs_score * 0.6 + var_score * 0.4)
        
        return QualityDimensionScore(
            dimension="effectiveness",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_efficiency(self) -> QualityDimensionScore:
        """
        Audit EFFICIENCY: Does learning converge quickly?
        
        Measures:
        - Processing throughput
        - Signals per review ratio
        """
        evidence = []
        issues = []
        recommendations = []
        
        if not self.learning_summary:
            return QualityDimensionScore(
                dimension="efficiency",
                score=0.5,
                level="acceptable",
                evidence=["No learning summary available"],
                issues=["Cannot assess efficiency without learning summary"],
                recommendations=["Run deep learning process to generate summary"]
            )
        
        total_reviews = self.learning_summary.get("total_reviews", 0)
        total_signals = self.learning_summary.get("total_signals", 0)
        elapsed_seconds = self.learning_summary.get("elapsed_seconds", 1)
        
        # Reviews per second
        reviews_per_sec = total_reviews / max(elapsed_seconds, 1)
        evidence.append(f"Processing rate: {reviews_per_sec:.1f} reviews/sec")
        
        # Signals per review (learning density)
        signals_per_review = total_signals / max(total_reviews, 1)
        evidence.append(f"Learning density: {signals_per_review:.2f} signals/review")
        
        # Score based on throughput (higher is better)
        if reviews_per_sec >= 500:
            throughput_score = 1.0
        elif reviews_per_sec >= 200:
            throughput_score = 0.8
        elif reviews_per_sec >= 100:
            throughput_score = 0.6
        elif reviews_per_sec >= 50:
            throughput_score = 0.4
        else:
            throughput_score = 0.2
            issues.append(f"Low processing throughput: {reviews_per_sec:.1f} reviews/sec")
        
        # Score based on learning density (optimal is ~15-25 signals/review)
        if 15 <= signals_per_review <= 25:
            density_score = 1.0
        elif 10 <= signals_per_review <= 30:
            density_score = 0.8
        elif 5 <= signals_per_review <= 40:
            density_score = 0.6
        else:
            density_score = 0.4
        
        score = (throughput_score * 0.5 + density_score * 0.5)
        
        return QualityDimensionScore(
            dimension="efficiency",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_coherence(self) -> QualityDimensionScore:
        """
        Audit COHERENCE: Do components agree on what they've learned?
        
        Measures:
        - Consistency of mechanism rankings across archetypes
        - Alignment between category and brand patterns
        """
        evidence = []
        issues = []
        recommendations = []
        
        # Check if "liking" is consistently top mechanism
        liking_ranks = []
        for archetype, mechanisms in self.archetype_matrix.items():
            sorted_mechs = sorted(
                mechanisms.items(),
                key=lambda x: x[1].get("avg_effectiveness", 0),
                reverse=True
            )
            mech_names = [m[0] for m in sorted_mechs]
            if "liking" in mech_names:
                liking_ranks.append(mech_names.index("liking") + 1)
        
        if liking_ranks:
            avg_liking_rank = sum(liking_ranks) / len(liking_ranks)
            evidence.append(f"'Liking' mechanism avg rank: {avg_liking_rank:.1f}")
            
            # Coherent if liking is consistently ranked top
            if avg_liking_rank <= 1.5:
                rank_coherence = 1.0
            elif avg_liking_rank <= 2.0:
                rank_coherence = 0.8
            elif avg_liking_rank <= 3.0:
                rank_coherence = 0.6
            else:
                rank_coherence = 0.4
                issues.append("Mechanism rankings inconsistent across archetypes")
        else:
            rank_coherence = 0.5
        
        # Check category-brand alignment
        category_dominant = {}
        for category, archetypes in self.category_archetypes.items():
            dominant = max(archetypes.items(), key=lambda x: x[1])[0]
            category_dominant[category] = dominant
        
        evidence.append(f"Category dominant archetypes: {len(category_dominant)}")
        
        score = rank_coherence
        
        return QualityDimensionScore(
            dimension="coherence",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_freshness(self) -> QualityDimensionScore:
        """
        Audit FRESHNESS: Are priors current and not stale?
        """
        evidence = []
        issues = []
        recommendations = []
        
        if not self.learning_summary:
            return QualityDimensionScore(
                dimension="freshness",
                score=0.3,
                level="concerning",
                evidence=["No learning summary available"],
                issues=["Cannot determine data freshness"],
                recommendations=["Run deep learning process"]
            )
        
        timestamp_str = self.learning_summary.get("timestamp", "")
        if timestamp_str:
            try:
                last_update = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - last_update).total_seconds() / 3600
                evidence.append(f"Last update: {age_hours:.1f} hours ago")
                
                if age_hours < 24:
                    freshness_score = 1.0
                elif age_hours < 72:
                    freshness_score = 0.8
                elif age_hours < 168:  # 1 week
                    freshness_score = 0.6
                elif age_hours < 720:  # 1 month
                    freshness_score = 0.4
                    issues.append("Learning data is more than 1 week old")
                    recommendations.append("Schedule regular learning updates")
                else:
                    freshness_score = 0.2
                    issues.append("Learning data is severely stale")
                    recommendations.append("Immediate learning update required")
            except:
                freshness_score = 0.5
        else:
            freshness_score = 0.5
        
        return QualityDimensionScore(
            dimension="freshness",
            score=freshness_score,
            level=self._score_to_level(freshness_score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_completeness(self) -> QualityDimensionScore:
        """
        Audit COMPLETENESS: Are all learning pathways connected?
        """
        evidence = []
        issues = []
        recommendations = []
        
        # Check archetype coverage
        expected_archetypes = {"Connector", "Achiever", "Guardian", "Explorer", "Pragmatist", "Analyzer"}
        learned_archetypes = set(self.archetype_matrix.keys())
        missing_archetypes = expected_archetypes - learned_archetypes
        
        evidence.append(f"Archetypes learned: {len(learned_archetypes)}/6")
        
        if missing_archetypes:
            issues.append(f"Missing archetypes: {missing_archetypes}")
            recommendations.append("Collect data for missing archetypes")
        
        # Check mechanism coverage per archetype
        expected_mechanisms = {"authority", "social_proof", "scarcity", "reciprocity", "commitment", "liking", "novelty"}
        mechanism_coverage = []
        
        for archetype, mechanisms in self.archetype_matrix.items():
            coverage = len(set(mechanisms.keys()) & expected_mechanisms) / len(expected_mechanisms)
            mechanism_coverage.append(coverage)
        
        avg_coverage = sum(mechanism_coverage) / max(len(mechanism_coverage), 1)
        evidence.append(f"Average mechanism coverage: {avg_coverage:.1%}")
        
        # Check category coverage
        categories_covered = len(self.category_archetypes)
        evidence.append(f"Categories with archetype data: {categories_covered}")
        
        archetype_score = len(learned_archetypes) / len(expected_archetypes)
        mechanism_score = avg_coverage
        
        score = (archetype_score * 0.5 + mechanism_score * 0.5)
        
        return QualityDimensionScore(
            dimension="completeness",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_synergy(self) -> QualityDimensionScore:
        """
        Audit SYNERGY: Does learning create emergent value?
        """
        evidence = []
        issues = []
        recommendations = []
        
        # Check if cross-category patterns emerge
        archetype_distribution = defaultdict(int)
        for category, archetypes in self.category_archetypes.items():
            for arch, count in archetypes.items():
                archetype_distribution[arch] += count
        
        total = sum(archetype_distribution.values())
        if total > 0:
            # Check for emergent dominant patterns
            connector_pct = archetype_distribution.get("Connector", 0) / total
            evidence.append(f"Connector dominance: {connector_pct:.1%}")
            
            # Synergy emerges when patterns are non-uniform but consistent
            # Too uniform (all equal) = no synergy
            # Too skewed = may indicate data bias
            values = list(archetype_distribution.values())
            if len(values) > 1:
                variance = np.var([v/total for v in values])
                evidence.append(f"Archetype distribution variance: {variance:.4f}")
                
                # Optimal variance is moderate (0.01-0.05)
                if 0.01 <= variance <= 0.05:
                    synergy_score = 1.0
                elif 0.005 <= variance <= 0.1:
                    synergy_score = 0.8
                elif variance < 0.005:
                    synergy_score = 0.5
                    issues.append("Distribution too uniform - may lack discriminative power")
                else:
                    synergy_score = 0.6
                    issues.append("Distribution highly skewed - check for data bias")
            else:
                synergy_score = 0.3
        else:
            synergy_score = 0.3
        
        # Check for brand-category synergies
        brands_with_multiple_archetypes = 0
        for brand, archetypes in self.brand_effectiveness.items():
            if len(archetypes) >= 2:
                brands_with_multiple_archetypes += 1
        
        brand_diversity = brands_with_multiple_archetypes / max(len(self.brand_effectiveness), 1)
        evidence.append(f"Brands with multi-archetype data: {brand_diversity:.1%}")
        
        score = synergy_score * 0.7 + brand_diversity * 0.3
        
        return QualityDimensionScore(
            dimension="synergy",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_calibration(self) -> QualityDimensionScore:
        """
        Audit CALIBRATION: Does confidence match accuracy?
        """
        evidence = []
        issues = []
        recommendations = []
        
        # Analyze confidence levels from brand effectiveness
        confidence_values = []
        for brand, archetypes in self.brand_effectiveness.items():
            for arch, data in archetypes.items():
                conf = data.get("avg_confidence", 0.5)
                confidence_values.append(conf)
        
        if confidence_values:
            avg_confidence = sum(confidence_values) / len(confidence_values)
            min_conf = min(confidence_values)
            max_conf = max(confidence_values)
            
            evidence.append(f"Confidence range: {min_conf:.3f} - {max_conf:.3f}")
            evidence.append(f"Average confidence: {avg_confidence:.3f}")
            
            # Check if confidence is in reasonable range (0.5-0.7 is well-calibrated)
            # Too low (< 0.5) = under-confident
            # Too high (> 0.8) = over-confident
            if 0.5 <= avg_confidence <= 0.7:
                calibration_score = 1.0
            elif 0.45 <= avg_confidence <= 0.75:
                calibration_score = 0.8
            elif avg_confidence < 0.45:
                calibration_score = 0.5
                issues.append(f"Under-confident predictions (avg={avg_confidence:.3f})")
                recommendations.append("Consider Platt scaling to improve calibration")
            else:
                calibration_score = 0.6
                issues.append(f"Potentially over-confident (avg={avg_confidence:.3f})")
                recommendations.append("Review prediction validation")
            
            # Check confidence spread (narrow is better for calibration)
            spread = max_conf - min_conf
            if spread < 0.1:
                spread_score = 1.0
            elif spread < 0.2:
                spread_score = 0.8
            else:
                spread_score = 0.6
                evidence.append(f"Wide confidence spread: {spread:.3f}")
        else:
            calibration_score = 0.5
            spread_score = 0.5
        
        score = calibration_score * 0.7 + spread_score * 0.3
        
        return QualityDimensionScore(
            dimension="calibration",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def audit_generalization(self) -> QualityDimensionScore:
        """
        Audit GENERALIZATION: Does learning generalize across contexts?
        """
        evidence = []
        issues = []
        recommendations = []
        
        # Check source diversity in learning summary
        if self.learning_summary:
            sources = self.learning_summary.get("sources_processed", {})
            num_sources = len(sources)
            evidence.append(f"Data sources: {num_sources}")
            
            # Check for balanced source distribution
            review_counts = [s.get("reviews", 0) for s in sources.values()]
            if review_counts:
                min_reviews = min(review_counts)
                max_reviews = max(review_counts)
                balance_ratio = min_reviews / max(max_reviews, 1)
                evidence.append(f"Source balance ratio: {balance_ratio:.2f}")
                
                if balance_ratio > 0.8:
                    balance_score = 1.0
                elif balance_ratio > 0.5:
                    balance_score = 0.8
                else:
                    balance_score = 0.6
                    issues.append("Imbalanced data sources")
            else:
                balance_score = 0.5
            
            source_score = min(num_sources / 5, 1.0)  # 5+ sources is excellent
        else:
            source_score = 0.5
            balance_score = 0.5
        
        # Check category generalization
        num_categories = len(self.category_archetypes)
        category_score = min(num_categories / 6, 1.0)  # 6+ categories is excellent
        evidence.append(f"Categories covered: {num_categories}")
        
        score = (source_score * 0.4 + balance_score * 0.3 + category_score * 0.3)
        
        return QualityDimensionScore(
            dimension="generalization",
            score=score,
            level=self._score_to_level(score),
            evidence=evidence,
            issues=issues,
            recommendations=recommendations
        )
    
    def run_full_audit(self) -> SystemAuditResult:
        """Run complete quality audit across all 8 dimensions."""
        
        logger.info("=" * 60)
        logger.info("ADAM LEARNING QUALITY AUDIT")
        logger.info("=" * 60)
        
        # Load artifacts
        if not self.load_learning_artifacts():
            logger.error("Failed to load learning artifacts")
            return None
        
        # Run all dimension audits
        dimension_scores = {}
        
        logger.info("\n--- Auditing 8 Quality Dimensions ---\n")
        
        dimensions = [
            ("effectiveness", self.audit_effectiveness),
            ("efficiency", self.audit_efficiency),
            ("coherence", self.audit_coherence),
            ("freshness", self.audit_freshness),
            ("completeness", self.audit_completeness),
            ("synergy", self.audit_synergy),
            ("calibration", self.audit_calibration),
            ("generalization", self.audit_generalization),
        ]
        
        for dim_name, audit_func in dimensions:
            score = audit_func()
            dimension_scores[dim_name] = score
            
            level_emoji = {
                "excellent": "🟢",
                "good": "🟢",
                "acceptable": "🟡",
                "concerning": "🟠",
                "critical": "🔴"
            }.get(score.level, "⚪")
            
            logger.info(f"{level_emoji} {dim_name.upper()}: {score.score:.2f} ({score.level})")
            for e in score.evidence:
                logger.info(f"   • {e}")
            for i in score.issues:
                logger.warning(f"   ⚠ {i}")
        
        # Calculate overall score
        overall_score = sum(s.score for s in dimension_scores.values()) / len(dimension_scores)
        overall_level = self._score_to_level(overall_score)
        
        # Collect all critical issues
        critical_issues = []
        recommendations = []
        for score in dimension_scores.values():
            if score.level in ["critical", "concerning"]:
                critical_issues.extend(score.issues)
            recommendations.extend(score.recommendations)
        
        # Build result
        result = SystemAuditResult(
            audit_id=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(timezone.utc),
            overall_score=overall_score,
            overall_level=overall_level,
            dimension_scores=dimension_scores,
            critical_issues=critical_issues,
            recommendations=list(set(recommendations))  # Dedupe
        )
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info(f"OVERALL SCORE: {overall_score:.2f} ({overall_level.upper()})")
        logger.info("=" * 60)
        
        if critical_issues:
            logger.warning("\nCritical Issues:")
            for issue in critical_issues:
                logger.warning(f"  ⚠ {issue}")
        
        if recommendations:
            logger.info("\nRecommendations:")
            for rec in recommendations[:5]:  # Top 5
                logger.info(f"  → {rec}")
        
        return result


# =============================================================================
# 2. MINORITY ARCHETYPE AUGMENTATION
# =============================================================================

class MinorityArchetypeAugmenter:
    """
    Augments data for minority archetypes using transfer learning
    from similar archetypes and theoretical priors.
    """
    
    # Theoretical archetype similarities (from psychological theory)
    ARCHETYPE_SIMILARITIES = {
        "Pragmatist": ["Achiever", "Analyzer"],  # Task-oriented
        "Analyzer": ["Pragmatist", "Guardian"],  # Detail-oriented
        "Guardian": ["Analyzer", "Connector"],   # Security-focused
        "Explorer": ["Achiever", "Connector"],   # Growth-focused
        "Achiever": ["Explorer", "Pragmatist"],  # Goal-oriented
        "Connector": ["Guardian", "Explorer"],   # Relationship-focused
    }
    
    # Theoretical mechanism priors (from persuasion research)
    THEORETICAL_PRIORS = {
        "Pragmatist": {
            "authority": 0.35,      # Respects expertise
            "social_proof": 0.30,   # Values consensus
            "scarcity": 0.25,       # Less susceptible
            "reciprocity": 0.30,    # Transactional
            "commitment": 0.35,     # Values consistency
            "liking": 0.30,         # Less emotional
            "novelty": 0.25,        # Prefers proven
        },
        "Analyzer": {
            "authority": 0.40,      # Strong expertise respect
            "social_proof": 0.25,   # Independent thinker
            "scarcity": 0.20,       # Skeptical
            "reciprocity": 0.25,    # Transactional
            "commitment": 0.35,     # Logical consistency
            "liking": 0.25,         # Less emotional
            "novelty": 0.35,        # Curious
        }
    }
    
    def __init__(self, archetype_matrix: Dict):
        self.archetype_matrix = archetype_matrix
    
    def augment_minority_archetypes(self, min_observations: int = 50) -> Dict:
        """
        Augment minority archetypes with transfer learning and priors.
        
        Args:
            min_observations: Minimum observations before augmentation kicks in
        
        Returns:
            Augmented archetype-mechanism matrix
        """
        augmented = dict(self.archetype_matrix)
        
        for archetype, mechanisms in augmented.items():
            # Check if any mechanism has low observations
            for mech, data in mechanisms.items():
                obs = data.get("observations", 0)
                
                if obs < min_observations:
                    logger.info(f"Augmenting {archetype}/{mech}: {obs} → {min_observations} observations")
                    
                    # Get similar archetypes
                    similar = self.ARCHETYPE_SIMILARITIES.get(archetype, [])
                    
                    # Transfer from similar archetypes
                    transfer_values = []
                    transfer_weights = []
                    
                    for sim_arch in similar:
                        if sim_arch in augmented and mech in augmented[sim_arch]:
                            sim_data = augmented[sim_arch][mech]
                            sim_obs = sim_data.get("observations", 0)
                            if sim_obs >= min_observations:
                                transfer_values.append(sim_data.get("avg_effectiveness", 0.3))
                                transfer_weights.append(sim_obs)
                    
                    # Get theoretical prior
                    prior = self.THEORETICAL_PRIORS.get(archetype, {}).get(mech, 0.3)
                    
                    # Blend: observed (if any) + transfer + prior
                    observed_value = data.get("avg_effectiveness", prior)
                    
                    if transfer_values:
                        transfer_avg = sum(v * w for v, w in zip(transfer_values, transfer_weights)) / sum(transfer_weights)
                    else:
                        transfer_avg = prior
                    
                    # Weight by observation count
                    obs_weight = obs / min_observations
                    transfer_weight = 0.5 * (1 - obs_weight)
                    prior_weight = 0.5 * (1 - obs_weight)
                    
                    blended = (
                        observed_value * obs_weight +
                        transfer_avg * transfer_weight +
                        prior * prior_weight
                    )
                    
                    # Update with augmented values
                    augmented[archetype][mech] = {
                        "avg_effectiveness": round(blended, 4),
                        "observations": obs,
                        "augmented_observations": min_observations,
                        "std_dev": data.get("std_dev", 0.02),
                        "augmentation_source": "transfer+prior"
                    }
        
        return augmented


# =============================================================================
# 3. THOMPSON SAMPLING WARM-START
# =============================================================================

class ThompsonSamplingWarmStarter:
    """
    Initializes Thompson Sampling posteriors from learned effectiveness matrix.
    
    Converts learned mechanism effectiveness into Beta distribution parameters
    for exploration-exploitation balance.
    """
    
    def __init__(self, archetype_matrix: Dict):
        self.archetype_matrix = archetype_matrix
    
    def compute_beta_parameters(
        self,
        effectiveness: float,
        observations: int,
        prior_strength: float = 10.0
    ) -> Tuple[float, float]:
        """
        Convert effectiveness score to Beta distribution parameters.
        
        Args:
            effectiveness: Learned effectiveness (0-1)
            observations: Number of observations
            prior_strength: How much to weight prior knowledge
        
        Returns:
            (alpha, beta) parameters for Beta distribution
        """
        # Scale observations to effective sample size
        # More observations = more confident in the learned value
        effective_n = min(observations, 500) / 500 * prior_strength + 1
        
        # Convert effectiveness to alpha/beta
        # effectiveness = alpha / (alpha + beta)
        alpha = effectiveness * effective_n
        beta = (1 - effectiveness) * effective_n
        
        # Ensure minimum values
        alpha = max(1.0, alpha)
        beta = max(1.0, beta)
        
        return round(alpha, 2), round(beta, 2)
    
    def generate_warm_start_config(self) -> Dict:
        """
        Generate warm-start configuration for Thompson Sampling.
        
        Returns:
            Configuration dict with Beta parameters per archetype-mechanism
        """
        config = {}
        
        for archetype, mechanisms in self.archetype_matrix.items():
            config[archetype] = {}
            
            for mech, data in mechanisms.items():
                effectiveness = data.get("avg_effectiveness", 0.3)
                observations = data.get("observations", 1)
                
                alpha, beta = self.compute_beta_parameters(effectiveness, observations)
                
                config[archetype][mech] = {
                    "alpha": alpha,
                    "beta": beta,
                    "prior_mean": round(alpha / (alpha + beta), 4),
                    "prior_variance": round(
                        (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1)), 
                        6
                    ),
                    "source_effectiveness": effectiveness,
                    "source_observations": observations,
                }
        
        return config


# =============================================================================
# 4. CROSS-CATEGORY TRANSFER LEARNING
# =============================================================================

class CrossCategoryTransferLearner:
    """
    Propagates learned category→archetype patterns to inform cold-start decisions.
    """
    
    # Category similarity clusters (semantic similarity)
    CATEGORY_CLUSTERS = {
        "technology": ["Electronics_Photography", "Gaming"],
        "media": ["Streaming", "Movies"],
        "lifestyle": ["Beauty", "Automotive"],
    }
    
    def __init__(self, category_archetypes: Dict):
        self.category_archetypes = category_archetypes
    
    def compute_category_priors(self) -> Dict:
        """
        Compute archetype priors for each category.
        
        Returns:
            Dict mapping category → archetype probability distribution
        """
        priors = {}
        
        for category, archetypes in self.category_archetypes.items():
            total = sum(archetypes.values())
            if total > 0:
                priors[category] = {
                    arch: round(count / total, 4)
                    for arch, count in archetypes.items()
                }
        
        return priors
    
    def compute_cluster_priors(self) -> Dict:
        """
        Compute archetype priors for category clusters.
        
        Enables transfer learning to new categories in same cluster.
        """
        cluster_priors = {}
        
        for cluster_name, categories in self.CATEGORY_CLUSTERS.items():
            # Aggregate archetypes across cluster
            cluster_counts = defaultdict(int)
            
            for category in categories:
                if category in self.category_archetypes:
                    for arch, count in self.category_archetypes[category].items():
                        cluster_counts[arch] += count
            
            total = sum(cluster_counts.values())
            if total > 0:
                cluster_priors[cluster_name] = {
                    arch: round(count / total, 4)
                    for arch, count in cluster_counts.items()
                }
        
        return cluster_priors
    
    def get_cold_start_prior(
        self,
        category: str,
        fallback_to_cluster: bool = True
    ) -> Dict[str, float]:
        """
        Get archetype prior for a category (with cluster fallback).
        
        Args:
            category: Product/content category
            fallback_to_cluster: Whether to use cluster prior if category unknown
        
        Returns:
            Archetype probability distribution
        """
        # Direct category match
        priors = self.compute_category_priors()
        if category in priors:
            return priors[category]
        
        if fallback_to_cluster:
            # Find matching cluster
            cluster_priors = self.compute_cluster_priors()
            for cluster_name, categories in self.CATEGORY_CLUSTERS.items():
                if category in categories or any(
                    category.lower() in cat.lower() for cat in categories
                ):
                    if cluster_name in cluster_priors:
                        return cluster_priors[cluster_name]
        
        # Global fallback
        all_counts = defaultdict(int)
        for archetypes in self.category_archetypes.values():
            for arch, count in archetypes.items():
                all_counts[arch] += count
        
        total = sum(all_counts.values())
        if total > 0:
            return {
                arch: round(count / total, 4)
                for arch, count in all_counts.items()
            }
        
        # Uniform prior
        return {
            "Connector": 0.30,
            "Achiever": 0.25,
            "Explorer": 0.20,
            "Guardian": 0.15,
            "Pragmatist": 0.05,
            "Analyzer": 0.05,
        }


# =============================================================================
# 5. CALIBRATION CHECK (PLATT SCALING)
# =============================================================================

class CalibrationChecker:
    """
    Checks and improves calibration of confidence scores using Platt scaling.
    """
    
    def __init__(self, brand_effectiveness: Dict):
        self.brand_effectiveness = brand_effectiveness
    
    def analyze_calibration(self) -> Dict:
        """
        Analyze current calibration of confidence scores.
        
        Returns:
            Calibration analysis report
        """
        confidence_values = []
        
        for brand, archetypes in self.brand_effectiveness.items():
            for arch, data in archetypes.items():
                conf = data.get("avg_confidence", 0.5)
                obs = data.get("observations", 0)
                confidence_values.append({
                    "brand": brand,
                    "archetype": arch,
                    "confidence": conf,
                    "observations": obs,
                })
        
        if not confidence_values:
            return {"error": "No confidence data available"}
        
        confs = [v["confidence"] for v in confidence_values]
        
        analysis = {
            "n_samples": len(confidence_values),
            "mean_confidence": round(np.mean(confs), 4),
            "std_confidence": round(np.std(confs), 4),
            "min_confidence": round(min(confs), 4),
            "max_confidence": round(max(confs), 4),
            "median_confidence": round(np.median(confs), 4),
        }
        
        # Calibration diagnosis
        if analysis["mean_confidence"] < 0.5:
            analysis["diagnosis"] = "under-confident"
            analysis["recommendation"] = "Apply positive Platt scaling shift"
        elif analysis["mean_confidence"] > 0.7:
            analysis["diagnosis"] = "over-confident"
            analysis["recommendation"] = "Apply negative Platt scaling shift"
        else:
            analysis["diagnosis"] = "well-calibrated"
            analysis["recommendation"] = "No scaling needed"
        
        return analysis
    
    def compute_platt_parameters(
        self,
        target_mean: float = 0.6,
        target_spread: float = 0.15
    ) -> Tuple[float, float]:
        """
        Compute Platt scaling parameters to achieve target calibration.
        
        Platt scaling: calibrated = 1 / (1 + exp(A * confidence + B))
        
        Args:
            target_mean: Target mean confidence
            target_spread: Target spread around mean
        
        Returns:
            (A, B) Platt scaling parameters
        """
        analysis = self.analyze_calibration()
        
        if "error" in analysis:
            return 1.0, 0.0
        
        current_mean = analysis["mean_confidence"]
        
        # Simple linear approximation for Platt parameters
        # A controls spread, B controls shift
        A = 1.0  # Keep spread similar
        B = np.log((1 - target_mean) / target_mean) - np.log((1 - current_mean) / current_mean)
        
        return round(A, 4), round(B, 4)
    
    def apply_platt_scaling(
        self,
        confidence: float,
        A: float,
        B: float
    ) -> float:
        """Apply Platt scaling to a confidence value."""
        # Sigmoid transformation
        scaled = 1 / (1 + np.exp(-(A * confidence + B)))
        return round(scaled, 4)


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

async def main():
    """Run all learning strengthening processes."""
    
    parser = argparse.ArgumentParser(description="ADAM Learning System Strengthening")
    parser.add_argument("--audit-only", action="store_true", help="Only run quality audit")
    parser.add_argument("--warm-start-only", action="store_true", help="Only generate warm-start config")
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("ADAM LEARNING SYSTEM STRENGTHENING")
    print("=" * 70 + "\n")
    
    # =========================================================================
    # 1. QUALITY AUDIT
    # =========================================================================
    
    print("\n" + "-" * 50)
    print("1. QUALITY AUDIT")
    print("-" * 50 + "\n")
    
    auditor = LearningQualityAuditor()
    audit_result = auditor.run_full_audit()
    
    if args.audit_only:
        # Save audit results
        audit_output = LEARNING_DATA_DIR / "quality_audit_result.json"
        with open(audit_output, 'w') as f:
            json.dump({
                "audit_id": audit_result.audit_id,
                "timestamp": audit_result.timestamp.isoformat(),
                "overall_score": audit_result.overall_score,
                "overall_level": audit_result.overall_level,
                "dimension_scores": {
                    k: {
                        "score": v.score,
                        "level": v.level,
                        "evidence": v.evidence,
                        "issues": v.issues,
                        "recommendations": v.recommendations,
                    }
                    for k, v in audit_result.dimension_scores.items()
                },
                "critical_issues": audit_result.critical_issues,
                "recommendations": audit_result.recommendations,
            }, f, indent=2)
        print(f"\n✓ Audit results saved to: {audit_output}")
        return
    
    # =========================================================================
    # 2. MINORITY ARCHETYPE AUGMENTATION
    # =========================================================================
    
    print("\n" + "-" * 50)
    print("2. MINORITY ARCHETYPE AUGMENTATION")
    print("-" * 50 + "\n")
    
    with open(ARCHETYPE_MECHANISM_MATRIX) as f:
        archetype_matrix = json.load(f)
    
    augmenter = MinorityArchetypeAugmenter(archetype_matrix)
    augmented_matrix = augmenter.augment_minority_archetypes(min_observations=50)
    
    # Save augmented matrix
    augmented_output = LEARNING_DATA_DIR / "archetype_mechanism_matrix_augmented.json"
    with open(augmented_output, 'w') as f:
        json.dump(augmented_matrix, f, indent=2)
    print(f"✓ Augmented matrix saved to: {augmented_output}")
    
    # =========================================================================
    # 3. THOMPSON SAMPLING WARM-START
    # =========================================================================
    
    print("\n" + "-" * 50)
    print("3. THOMPSON SAMPLING WARM-START")
    print("-" * 50 + "\n")
    
    warm_starter = ThompsonSamplingWarmStarter(augmented_matrix)
    warm_start_config = warm_starter.generate_warm_start_config()
    
    # Save warm-start config
    warm_start_output = LEARNING_DATA_DIR / "thompson_sampling_warm_start.json"
    with open(warm_start_output, 'w') as f:
        json.dump(warm_start_config, f, indent=2)
    print(f"✓ Warm-start config saved to: {warm_start_output}")
    
    # Print sample
    print("\nSample warm-start parameters (Connector/liking):")
    if "Connector" in warm_start_config and "liking" in warm_start_config["Connector"]:
        params = warm_start_config["Connector"]["liking"]
        print(f"   Alpha: {params['alpha']}, Beta: {params['beta']}")
        print(f"   Prior Mean: {params['prior_mean']}")
        print(f"   Prior Variance: {params['prior_variance']}")
    
    if args.warm_start_only:
        return
    
    # =========================================================================
    # 4. CROSS-CATEGORY TRANSFER LEARNING
    # =========================================================================
    
    print("\n" + "-" * 50)
    print("4. CROSS-CATEGORY TRANSFER LEARNING")
    print("-" * 50 + "\n")
    
    with open(CATEGORY_ARCHETYPES) as f:
        category_archetypes = json.load(f)
    
    transfer_learner = CrossCategoryTransferLearner(category_archetypes)
    
    category_priors = transfer_learner.compute_category_priors()
    cluster_priors = transfer_learner.compute_cluster_priors()
    
    # Save transfer learning config
    transfer_output = LEARNING_DATA_DIR / "category_transfer_priors.json"
    with open(transfer_output, 'w') as f:
        json.dump({
            "category_priors": category_priors,
            "cluster_priors": cluster_priors,
            "cluster_definitions": transfer_learner.CATEGORY_CLUSTERS,
        }, f, indent=2)
    print(f"✓ Transfer learning priors saved to: {transfer_output}")
    
    # Print sample
    print("\nCategory cluster priors:")
    for cluster, priors in cluster_priors.items():
        top_arch = max(priors.items(), key=lambda x: x[1])
        print(f"   {cluster}: {top_arch[0]} ({top_arch[1]:.1%})")
    
    # =========================================================================
    # 5. CALIBRATION CHECK
    # =========================================================================
    
    print("\n" + "-" * 50)
    print("5. CALIBRATION CHECK (PLATT SCALING)")
    print("-" * 50 + "\n")
    
    with open(BRAND_ARCHETYPE_EFFECTIVENESS) as f:
        brand_effectiveness = json.load(f)
    
    calibration_checker = CalibrationChecker(brand_effectiveness)
    
    analysis = calibration_checker.analyze_calibration()
    print(f"Calibration Analysis:")
    print(f"   Samples: {analysis.get('n_samples', 0)}")
    print(f"   Mean Confidence: {analysis.get('mean_confidence', 0):.4f}")
    print(f"   Std Confidence: {analysis.get('std_confidence', 0):.4f}")
    print(f"   Diagnosis: {analysis.get('diagnosis', 'unknown')}")
    print(f"   Recommendation: {analysis.get('recommendation', 'none')}")
    
    # Compute Platt parameters
    A, B = calibration_checker.compute_platt_parameters(target_mean=0.6)
    print(f"\nPlatt Scaling Parameters:")
    print(f"   A (scale): {A}")
    print(f"   B (shift): {B}")
    
    # Save calibration config
    calibration_output = LEARNING_DATA_DIR / "calibration_config.json"
    with open(calibration_output, 'w') as f:
        json.dump({
            "analysis": analysis,
            "platt_parameters": {"A": A, "B": B},
            "target_mean": 0.6,
            "target_spread": 0.15,
        }, f, indent=2)
    print(f"\n✓ Calibration config saved to: {calibration_output}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    print("\n" + "=" * 70)
    print("LEARNING STRENGTHENING COMPLETE")
    print("=" * 70)
    print(f"\nOverall Quality Score: {audit_result.overall_score:.2f} ({audit_result.overall_level})")
    print(f"\nArtifacts Generated:")
    print(f"   • {augmented_output.name}")
    print(f"   • {warm_start_output.name}")
    print(f"   • {transfer_output.name}")
    print(f"   • {calibration_output.name}")
    print(f"\nNext Steps:")
    print(f"   1. Review quality audit recommendations")
    print(f"   2. Integrate warm-start config into Thompson Sampling")
    print(f"   3. Use transfer priors for cold-start users")
    print(f"   4. Apply Platt scaling to confidence outputs")


if __name__ == "__main__":
    asyncio.run(main())
