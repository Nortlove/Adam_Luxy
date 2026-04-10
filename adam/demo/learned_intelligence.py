# =============================================================================
# ADAM Demo - Learned Intelligence Integration
# Location: adam/demo/learned_intelligence.py
# =============================================================================

"""
LEARNED INTELLIGENCE INTEGRATION FOR DEMO

This module loads and provides access to all the pre-learned psychological
intelligence from the full Amazon review corpus processing:

- 608 psychological profiles
- 2.4M+ reviews analyzed
- Mechanism effectiveness matrix
- Archetype-specific insights
- Category-specific constructs

The demo uses this learned data to:
1. Provide more accurate mechanism recommendations
2. Better archetype detection
3. Category-specific psychological priors
4. Segment-specific targeting guidance
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# DATA PATHS
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "data"
LEARNING_DIR = DATA_DIR / "learning"
INSIGHTS_DIR = DATA_DIR / "insights"

MECHANISM_MATRIX_PATH = LEARNING_DIR / "full_mechanism_matrix.json"
CHECKPOINT_PATH = LEARNING_DIR / "checkpoint.json"
COPY_PATTERNS_PATH = LEARNING_DIR / "copy_patterns.json"
INSIGHTS_DB_PATH = INSIGHTS_DIR / "psychological_insights.db"


# =============================================================================
# LEARNED DATA MODELS
# =============================================================================

@dataclass
class LearnedMechanismEffectiveness:
    """Learned mechanism effectiveness for an archetype."""
    mechanism: str
    avg_effectiveness: float
    observation_count: int
    min_score: float
    max_score: float


@dataclass
class LearnedArchetypeProfile:
    """Learned archetype profile from corpus analysis."""
    archetype: str
    count: int
    percentage: float
    top_mechanisms: List[LearnedMechanismEffectiveness]
    top_constructs: List[Tuple[str, float]]
    preferred_tone: str


@dataclass
class LearnedCategoryProfile:
    """Learned category-specific psychological profile."""
    category: str
    primary_archetype: str
    archetype_confidence: float
    mechanism_predictions: Dict[str, float]
    regulatory_focus: Dict[str, float]
    top_constructs: List[Tuple[str, float]]
    segment_insights: Dict[str, Any]


# =============================================================================
# LEARNED INTELLIGENCE LOADER
# =============================================================================

class LearnedIntelligenceLoader:
    """
    Loads and caches learned intelligence from full corpus processing.
    
    This is the central access point for all pre-learned data.
    """
    
    def __init__(self):
        self._mechanism_matrix: Optional[Dict] = None
        self._checkpoint: Optional[Dict] = None
        self._copy_patterns: Optional[Dict] = None
        self._category_profiles: Dict[str, LearnedCategoryProfile] = {}
        self._archetype_profiles: Dict[str, LearnedArchetypeProfile] = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """Load all learned data."""
        if self._initialized:
            return True
        
        try:
            # 1. Load mechanism matrix
            if MECHANISM_MATRIX_PATH.exists():
                with open(MECHANISM_MATRIX_PATH) as f:
                    self._mechanism_matrix = json.load(f)
                logger.info(f"Loaded mechanism matrix: {len(self._mechanism_matrix)} archetypes")
            
            # 2. Load checkpoint (archetype counts)
            if CHECKPOINT_PATH.exists():
                with open(CHECKPOINT_PATH) as f:
                    self._checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint: {self._checkpoint.get('total_profiles_created', 0)} profiles")
            
            # 3. Load copy patterns
            if COPY_PATTERNS_PATH.exists():
                with open(COPY_PATTERNS_PATH) as f:
                    self._copy_patterns = json.load(f)
                logger.info(f"Loaded copy patterns")
            
            # 4. Build archetype profiles
            self._build_archetype_profiles()
            
            # 5. Load category profiles from database
            self._load_category_profiles()
            
            self._initialized = True
            logger.info("Learned intelligence initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize learned intelligence: {e}")
            return False
    
    def _build_archetype_profiles(self) -> None:
        """Build archetype profiles from loaded data."""
        if not self._checkpoint or not self._mechanism_matrix:
            return
        
        archetype_counts = self._checkpoint.get("archetype_counts", {})
        total = sum(archetype_counts.values())
        
        for archetype, count in archetype_counts.items():
            # Get mechanism effectiveness
            mech_data = self._mechanism_matrix.get(archetype, {})
            top_mechanisms = []
            
            for mech, data in sorted(
                mech_data.items(),
                key=lambda x: x[1].get("avg", 0),
                reverse=True
            )[:5]:
                top_mechanisms.append(LearnedMechanismEffectiveness(
                    mechanism=mech,
                    avg_effectiveness=data.get("avg", 0.5),
                    observation_count=data.get("count", 0),
                    min_score=data.get("min", 0),
                    max_score=data.get("max", 1),
                ))
            
            # Get copy patterns
            top_constructs = []
            preferred_tone = "balanced_neutral"
            
            if self._copy_patterns:
                constructs = self._copy_patterns.get("top_constructs", {}).get(archetype, [])
                top_constructs = [(c[0], c[1]) for c in constructs]
                
                tones = self._copy_patterns.get("language_patterns", {}).get(archetype, {})
                if tones:
                    preferred_tone = max(tones.items(), key=lambda x: x[1])[0]
            
            self._archetype_profiles[archetype] = LearnedArchetypeProfile(
                archetype=archetype,
                count=count,
                percentage=(count / total * 100) if total > 0 else 0,
                top_mechanisms=top_mechanisms,
                top_constructs=top_constructs,
                preferred_tone=preferred_tone,
            )
    
    def _load_category_profiles(self) -> None:
        """Load category profiles from SQLite database."""
        if not INSIGHTS_DB_PATH.exists():
            return
        
        try:
            conn = sqlite3.connect(str(INSIGHTS_DB_PATH))
            
            # Get category profiles using the full_profile_json column
            cursor = conn.execute("""
                SELECT 
                    brand_name,
                    primary_archetype,
                    archetype_confidence,
                    promotion_focus,
                    prevention_focus,
                    reviews_analyzed,
                    full_profile_json
                FROM psychological_profiles
                WHERE product_name LIKE '%Full Category%'
                ORDER BY reviews_analyzed DESC
            """)
            
            for row in cursor.fetchall():
                category = row[0].replace(" ", "_")
                
                # Parse full profile JSON for mechanism predictions and constructs
                mechanisms = {}
                constructs = {}
                
                if row[6]:  # full_profile_json
                    try:
                        full_profile = json.loads(row[6])
                        mechanisms = full_profile.get("mechanism_predictions", {})
                        constructs = full_profile.get("unified_constructs", {})
                    except json.JSONDecodeError:
                        pass
                
                # Get top constructs
                top_constructs = sorted(
                    constructs.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                self._category_profiles[category] = LearnedCategoryProfile(
                    category=category,
                    primary_archetype=row[1] or "Unknown",
                    archetype_confidence=row[2] or 0.5,
                    mechanism_predictions=mechanisms,
                    regulatory_focus={
                        "promotion": row[3] or 0.5,
                        "prevention": row[4] or 0.5,
                    },
                    top_constructs=top_constructs,
                    segment_insights={},
                )
            
            # Load segment insights for each category
            cursor = conn.execute("""
                SELECT 
                    brand_name,
                    product_name,
                    primary_archetype,
                    archetype_confidence
                FROM psychological_profiles
                WHERE product_name LIKE '%Segment%'
            """)
            
            for row in cursor.fetchall():
                category = row[0].replace(" ", "_").split("_Satisfied")[0].split("_Critical")[0].split("_Detailed")[0].split("_Verified")[0]
                segment_type = row[1]
                
                if category in self._category_profiles:
                    self._category_profiles[category].segment_insights[segment_type] = {
                        "archetype": row[2],
                        "confidence": row[3],
                    }
            
            conn.close()
            logger.info(f"Loaded {len(self._category_profiles)} category profiles")
        
        except Exception as e:
            logger.warning(f"Failed to load category profiles: {e}")
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def get_mechanism_effectiveness(
        self,
        archetype: str,
        mechanism: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get learned mechanism effectiveness for an archetype.
        
        Args:
            archetype: Target archetype
            mechanism: Specific mechanism (optional)
            
        Returns:
            Mechanism effectiveness data
        """
        self.initialize()
        
        if archetype not in self._archetype_profiles:
            # Try case-insensitive match
            for key in self._archetype_profiles:
                if key.lower() == archetype.lower():
                    archetype = key
                    break
        
        profile = self._archetype_profiles.get(archetype)
        if not profile:
            return {"mechanisms": [], "archetype": archetype, "found": False}
        
        if mechanism:
            for m in profile.top_mechanisms:
                if m.mechanism.lower() == mechanism.lower():
                    return {
                        "mechanism": m.mechanism,
                        "effectiveness": m.avg_effectiveness,
                        "observations": m.observation_count,
                        "archetype": archetype,
                        "found": True,
                    }
            return {"mechanism": mechanism, "effectiveness": 0.5, "archetype": archetype, "found": False}
        
        return {
            "archetype": archetype,
            "mechanisms": [
                {
                    "mechanism": m.mechanism,
                    "effectiveness": m.avg_effectiveness,
                    "observations": m.observation_count,
                }
                for m in profile.top_mechanisms
            ],
            "found": True,
        }
    
    def get_archetype_profile(self, archetype: str) -> Optional[LearnedArchetypeProfile]:
        """Get learned profile for an archetype."""
        self.initialize()
        
        # Try case-insensitive match
        for key, profile in self._archetype_profiles.items():
            if key.lower() == archetype.lower():
                return profile
        return None
    
    def get_category_profile(self, category: str) -> Optional[LearnedCategoryProfile]:
        """Get learned profile for a category."""
        self.initialize()
        
        # Normalize category name
        category = category.replace(" ", "_")
        
        # Try direct match
        if category in self._category_profiles:
            return self._category_profiles[category]
        
        # Try case-insensitive match
        for key, profile in self._category_profiles.items():
            if key.lower() == category.lower():
                return profile
        
        return None
    
    def get_all_archetypes(self) -> List[LearnedArchetypeProfile]:
        """Get all learned archetype profiles."""
        self.initialize()
        return list(self._archetype_profiles.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall learning statistics."""
        self.initialize()
        
        if not self._checkpoint:
            return {"initialized": False}
        
        return {
            "initialized": True,
            "total_profiles": self._checkpoint.get("total_profiles_created", 0),
            "total_signals": self._checkpoint.get("total_signals_emitted", 0),
            "total_reviews": self._checkpoint.get("total_reviews_processed", 0),
            "categories_learned": len(self._category_profiles),
            "archetypes_learned": len(self._archetype_profiles),
            "archetype_distribution": self._checkpoint.get("archetype_counts", {}),
        }
    
    def enhance_recommendation(
        self,
        base_recommendation: Dict[str, Any],
        archetype: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enhance a recommendation with learned intelligence.
        
        Args:
            base_recommendation: Base recommendation to enhance
            archetype: Detected archetype
            category: Product category (optional)
            
        Returns:
            Enhanced recommendation with learned insights
        """
        self.initialize()
        
        enhanced = base_recommendation.copy()
        
        # Add archetype-specific mechanism adjustments
        archetype_profile = self.get_archetype_profile(archetype)
        if archetype_profile:
            enhanced["learned_insights"] = {
                "archetype_observations": archetype_profile.count,
                "archetype_prevalence": f"{archetype_profile.percentage:.1f}%",
                "preferred_tone": archetype_profile.preferred_tone,
            }
            
            # Adjust mechanism scores based on learned effectiveness
            if "mechanisms" in enhanced:
                for mech in enhanced["mechanisms"]:
                    for learned_mech in archetype_profile.top_mechanisms:
                        if learned_mech.mechanism.lower() == mech.get("mechanism", "").lower():
                            mech["learned_effectiveness"] = learned_mech.avg_effectiveness
                            mech["learned_observations"] = learned_mech.observation_count
                            # Boost score based on learned data
                            original_score = mech.get("score", 0.5)
                            learned_score = learned_mech.avg_effectiveness
                            # Weighted average: 60% learned, 40% original
                            mech["score"] = 0.6 * learned_score + 0.4 * original_score
                            break
            
            # Add top constructs
            if archetype_profile.top_constructs:
                enhanced["learned_insights"]["top_constructs"] = [
                    {"construct": c[0], "score": c[1]}
                    for c in archetype_profile.top_constructs
                ]
        
        # Add category-specific insights
        if category:
            category_profile = self.get_category_profile(category)
            if category_profile:
                enhanced["category_insights"] = {
                    "category_archetype": category_profile.primary_archetype,
                    "category_confidence": category_profile.archetype_confidence,
                    "category_mechanisms": category_profile.mechanism_predictions,
                    "regulatory_focus": category_profile.regulatory_focus,
                    "segment_data": category_profile.segment_insights,
                }
        
        return enhanced


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_learned_intelligence: Optional[LearnedIntelligenceLoader] = None


def get_learned_intelligence() -> LearnedIntelligenceLoader:
    """Get the singleton learned intelligence loader."""
    global _learned_intelligence
    if _learned_intelligence is None:
        _learned_intelligence = LearnedIntelligenceLoader()
        _learned_intelligence.initialize()
    return _learned_intelligence


# =============================================================================
# ENHANCED MECHANISM RECOMMENDATIONS
# =============================================================================

def get_learned_mechanism_recommendations(
    archetype: str,
    category: Optional[str] = None,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Get mechanism recommendations enhanced by learned data.
    
    This is the main entry point for demo recommendations.
    """
    loader = get_learned_intelligence()
    
    recommendations = []
    
    # Get archetype-specific mechanisms
    archetype_profile = loader.get_archetype_profile(archetype)
    if archetype_profile:
        for mech in archetype_profile.top_mechanisms[:top_n]:
            recommendations.append({
                "mechanism": mech.mechanism,
                "score": mech.avg_effectiveness,
                "observations": mech.observation_count,
                "source": "learned_archetype",
                "confidence": min(0.95, 0.5 + (mech.observation_count / 500)),
            })
    
    # Enhance with category data
    if category:
        category_profile = loader.get_category_profile(category)
        if category_profile:
            for mech, score in category_profile.mechanism_predictions.items():
                # Check if mechanism already in list
                existing = next(
                    (r for r in recommendations if r["mechanism"].lower() == mech.lower()),
                    None
                )
                if existing:
                    # Combine scores
                    existing["category_score"] = score
                    existing["score"] = (existing["score"] + score) / 2
                else:
                    recommendations.append({
                        "mechanism": mech,
                        "score": score,
                        "observations": 0,
                        "source": "learned_category",
                        "confidence": category_profile.archetype_confidence,
                    })
    
    # Sort by score
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return recommendations[:top_n]


# =============================================================================
# LEARNED DATA SUMMARY FOR DEMO
# =============================================================================

def get_demo_learning_summary() -> Dict[str, Any]:
    """Get a summary of learned data for demo display."""
    loader = get_learned_intelligence()
    stats = loader.get_statistics()
    
    return {
        "learning_status": "complete" if stats.get("initialized") else "pending",
        "reviews_analyzed": f"{stats.get('total_reviews', 0):,}",
        "profiles_learned": stats.get("total_profiles", 0),
        "categories_learned": stats.get("categories_learned", 0),
        "archetypes_learned": stats.get("archetypes_learned", 0),
        "archetype_distribution": stats.get("archetype_distribution", {}),
        "learning_signals": stats.get("total_signals", 0),
    }
