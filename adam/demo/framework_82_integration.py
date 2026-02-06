#!/usr/bin/env python3
"""
82-FRAMEWORK PSYCHOLOGICAL INTELLIGENCE INTEGRATION
====================================================

Integrates the complete 82-framework psychological analysis system
with the ADAM demo platform.

This service:
1. Loads learned priors from the 82-framework learning pipeline
2. Provides real-time psychological analysis of product descriptions
3. Generates comprehensive persuasion strategies based on 82 frameworks
4. Matches products to optimal customer segments using deep psychology

FRAMEWORK COVERAGE:
- 20 Categories, 82 Frameworks, ~3,600+ patterns
- Personality, Motivation, Cognition, Neuroscience, Social, Decision,
  Linguistic, Temporal, Behavioral, Brand, Moral, Memory, Narrative,
  Trust, Price, Mechanism Interaction, Context, Cultural, Ethics, Advanced
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
LEARNING_DATA_DIR = PROJECT_ROOT / "data" / "learning"


@dataclass
class PersuasionStrategy:
    """Complete persuasion strategy for a target segment."""
    archetype: str
    archetype_confidence: float
    
    # Regulatory approach
    regulatory_focus: str  # "promotion" or "prevention"
    framing: str  # "gain" or "loss"
    message_focus: str
    
    # Processing approach
    construal_level: str  # "abstract" or "concrete"
    processing_route: str  # "central" or "peripheral"
    message_complexity: str  # "high" or "low"
    
    # Mechanisms
    primary_mechanisms: List[str] = field(default_factory=list)
    secondary_mechanisms: List[str] = field(default_factory=list)
    avoid_mechanisms: List[str] = field(default_factory=list)
    
    # Synergies
    mechanism_synergies: List[Dict[str, Any]] = field(default_factory=list)
    
    # Narrative
    narrative_style: str = ""
    
    # Emotional approach
    emotional_intensity: str = ""
    
    # Ethical considerations
    ethical_notes: List[str] = field(default_factory=list)


@dataclass
class PsychologicalIntelligence:
    """Complete psychological intelligence for a product/brand."""
    
    # Archetype analysis
    primary_archetype: str = ""
    archetype_scores: Dict[str, float] = field(default_factory=dict)
    
    # Framework scores
    personality_profile: Dict[str, float] = field(default_factory=dict)
    motivation_profile: Dict[str, float] = field(default_factory=dict)
    cognitive_mechanisms: Dict[str, float] = field(default_factory=dict)
    neuroscience_profile: Dict[str, float] = field(default_factory=dict)
    social_profile: Dict[str, float] = field(default_factory=dict)
    decision_profile: Dict[str, float] = field(default_factory=dict)
    linguistic_profile: Dict[str, float] = field(default_factory=dict)
    narrative_profile: Dict[str, float] = field(default_factory=dict)
    
    # Persuasion strategy
    strategy: Optional[PersuasionStrategy] = None
    
    # Segment recommendations
    target_segments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Matched brand psychology (if brand found in priors)
    brand_match: Optional[Dict[str, Any]] = None
    
    # Category insights
    category_insights: Optional[Dict[str, Any]] = None


class Framework82Intelligence:
    """
    82-Framework Psychological Intelligence Engine.
    
    Provides comprehensive psychological analysis and persuasion strategy
    generation using learnings from millions of customer reviews.
    """
    
    def __init__(self):
        self.priors_loaded = False
        self.complete_priors: Dict[str, Any] = {}
        self.framework_priors: Dict[str, Any] = {}
        self.archetype_priors: Dict[str, Any] = {}
        self.mechanism_effectiveness: Dict[str, Any] = {}
        self.brand_profiles: Dict[str, Any] = {}
        self.category_profiles: Dict[str, Any] = {}
        
        # Try to load priors
        self._load_priors()
        
        # Initialize the real-time analyzer
        try:
            from adam.intelligence.complete_psychological_analyzer import (
                CompletePsychologicalAnalyzer
            )
            self.analyzer = CompletePsychologicalAnalyzer()
            self.analyzer_available = True
            logger.info("82-framework real-time analyzer initialized")
        except Exception as e:
            logger.warning(f"Could not initialize real-time analyzer: {e}")
            self.analyzer = None
            self.analyzer_available = False
    
    def _load_priors(self):
        """Load all learned priors from the learning pipeline.
        
        CORRECTED FILENAMES (Feb 2026):
        - complete_coldstart_priors.json (941M reviews integrated)
        - 82_framework_priors.json (545M Amazon reviews with 82 frameworks)
        - archetype_mechanism_matrix_augmented.json (mechanism effectiveness)
        - category_transfer_priors.json (category-level priors)
        """
        try:
            # Load complete unified priors (941M reviews from all sources)
            priors_path = LEARNING_DATA_DIR / "complete_coldstart_priors.json"
            if priors_path.exists():
                logger.info("Loading complete_coldstart_priors.json (941M+ reviews)...")
                with open(priors_path, 'r') as f:
                    self.complete_priors = json.load(f)
                # Extract source statistics to report total
                source_stats = self.complete_priors.get('source_statistics', {})
                total_reviews = sum(s.get('reviews', 0) for s in source_stats.values())
                logger.info(f"Loaded complete priors: {total_reviews:,} reviews from {len(source_stats)} sources")
            else:
                logger.warning(f"complete_coldstart_priors.json not found at {priors_path}")
            
            # Load 82-framework priors (Amazon 545M reviews)
            # NOTE: File is 20GB+ - this may take time on first load
            framework_path = LEARNING_DATA_DIR / "82_framework_priors.json"
            if framework_path.exists():
                logger.info("Loading 82_framework_priors.json (545M Amazon reviews, 20GB file)...")
                # Use streaming load for large file if needed
                try:
                    with open(framework_path, 'r') as f:
                        self.framework_priors = json.load(f)
                    total_reviews = self.framework_priors.get('metadata', {}).get('total_reviews', 0)
                    logger.info(f"Loaded 82-framework priors: {total_reviews:,} reviews")
                except MemoryError:
                    logger.warning("82_framework_priors.json too large for memory - using category-level summary")
                    self.framework_priors = {}
            else:
                logger.info(f"82_framework_priors.json not found at {framework_path} - using coldstart priors")
            
            # Load archetype → mechanism effectiveness matrix
            archetype_path = LEARNING_DATA_DIR / "archetype_mechanism_matrix_augmented.json"
            if archetype_path.exists():
                with open(archetype_path, 'r') as f:
                    self.archetype_priors = json.load(f)
                logger.info(f"Loaded archetype-mechanism matrix")
            
            # Load mechanism effectiveness from coldstart priors
            if self.complete_priors:
                self.mechanism_effectiveness = self.complete_priors.get('archetype_persuasion_sensitivity', {})
                if self.mechanism_effectiveness:
                    logger.info(f"Loaded mechanism effectiveness for {len(self.mechanism_effectiveness)} archetypes")
            
            # Load brand profiles from coldstart priors
            if self.complete_priors:
                self.brand_profiles = {'brands': self.complete_priors.get('brand_archetype_priors', {})}
                brand_count = len(self.brand_profiles.get('brands', {}))
                if brand_count:
                    logger.info(f"Loaded {brand_count:,} brand profiles")
            
            # Load category profiles from transfer priors
            category_path = LEARNING_DATA_DIR / "category_transfer_priors.json"
            if category_path.exists():
                with open(category_path, 'r') as f:
                    self.category_profiles = json.load(f)
                logger.info(f"Loaded category transfer priors")
            elif self.complete_priors:
                # Fallback to coldstart category priors
                self.category_profiles = {
                    'categories': self.complete_priors.get('category_archetype_priors', {})
                }
            
            self.priors_loaded = bool(self.complete_priors)
            
            if self.priors_loaded:
                logger.info("✅ Framework82Intelligence successfully loaded all priors")
            else:
                logger.warning("⚠️ Framework82Intelligence priors not fully loaded")
            
        except Exception as e:
            logger.error(f"Error loading priors: {e}")
            import traceback
            traceback.print_exc()
            self.priors_loaded = False
    
    def analyze_product(
        self,
        product_description: str,
        brand_name: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[float] = None,
    ) -> PsychologicalIntelligence:
        """
        Analyze a product using the 82-framework system.
        
        Args:
            product_description: Product description text
            brand_name: Optional brand name for brand-specific priors
            category: Optional category for category-specific priors
            price: Optional price point
            
        Returns:
            PsychologicalIntelligence with complete analysis
        """
        intel = PsychologicalIntelligence()
        
        # 1. Real-time analysis if analyzer available
        if self.analyzer_available and self.analyzer and product_description:
            try:
                profile = self.analyzer.analyze(product_description)
                
                # Map profile to intelligence
                intel.primary_archetype = profile.primary_archetype
                intel.archetype_scores = profile.archetype_scores
                
                # Core framework scores
                intel.personality_profile = profile.core_profile.personality_scores
                intel.motivation_profile = profile.core_profile.motivation_scores
                intel.cognitive_mechanisms = profile.core_profile.cognitive_mechanism_scores
                intel.neuroscience_profile = profile.core_profile.neuroscience_scores
                intel.social_profile = profile.core_profile.social_scores
                intel.decision_profile = profile.core_profile.decision_scores
                intel.linguistic_profile = profile.core_profile.linguistic_scores
                intel.narrative_profile = profile.narrative
                
                # Generate strategy from profile
                strategy_dict = profile.get_persuasion_strategy()
                intel.strategy = PersuasionStrategy(
                    archetype=intel.primary_archetype,
                    archetype_confidence=intel.archetype_scores.get(intel.primary_archetype, 0),
                    regulatory_focus=strategy_dict.get("regulatory_focus", "promotion"),
                    framing=strategy_dict.get("framing", "gain"),
                    message_focus=strategy_dict.get("message_focus", ""),
                    construal_level=strategy_dict.get("construal_level", "concrete"),
                    processing_route=strategy_dict.get("processing_route", "peripheral"),
                    message_complexity=strategy_dict.get("message_complexity", "low"),
                    primary_mechanisms=strategy_dict.get("primary_mechanisms", []),
                    mechanism_synergies=[
                        {"mechanism_1": m1, "mechanism_2": m2, "multiplier": mult}
                        for m1, m2, mult in profile.mechanism_synergies
                    ],
                )
                
                # Add vulnerability check
                if profile.vulnerability_detected:
                    intel.strategy.ethical_notes.append(
                        "VULNERABILITY DETECTED: Use supportive, non-pressure messaging"
                    )
                
            except Exception as e:
                logger.warning(f"Real-time analysis error: {e}")
        
        # 2. Enhance with brand-specific priors
        if brand_name and self.brand_profiles:
            brand_key = brand_name.lower().strip()
            for stored_brand, profile in self.brand_profiles.get("brands", {}).items():
                if stored_brand.lower() == brand_key:
                    intel.brand_match = {
                        "brand": stored_brand,
                        "review_count": profile.get("review_count", 0),
                        "primary_archetype": profile.get("primary_archetype"),
                        "archetype_distribution": profile.get("archetype_distribution", {}),
                        "mechanism_effectiveness": profile.get("mechanism_effectiveness", {}),
                    }
                    
                    # Use brand archetype if no real-time analysis
                    if not intel.primary_archetype and profile.get("primary_archetype"):
                        intel.primary_archetype = profile["primary_archetype"]
                        intel.archetype_scores = profile.get("archetype_distribution", {})
                    
                    break
        
        # 3. Enhance with category-specific insights
        if category and self.category_profiles:
            cat_key = category.replace(" ", "_")
            cat_profile = self.category_profiles.get("categories", {}).get(cat_key)
            if cat_profile:
                intel.category_insights = {
                    "category": category,
                    "review_count": cat_profile.get("review_count", 0),
                    "dominant_archetype": cat_profile.get("primary_archetype"),
                    "archetype_distribution": cat_profile.get("archetype_distribution", {}),
                    "narrative_patterns": cat_profile.get("narrative_patterns", {}),
                    "price_psychology": cat_profile.get("price_psychology", {}),
                }
        
        # 4. Generate target segments
        intel.target_segments = self._generate_target_segments(intel)
        
        # 5. Enhance strategy with learned mechanism effectiveness
        if intel.strategy and intel.primary_archetype:
            self._enhance_strategy_with_priors(intel)
        
        return intel
    
    def _generate_target_segments(self, intel: PsychologicalIntelligence) -> List[Dict[str, Any]]:
        """Generate target customer segments from analysis."""
        segments = []
        
        # Get archetype scores
        archetype_scores = intel.archetype_scores or {}
        if not archetype_scores and self.complete_priors:
            archetype_scores = self.complete_priors.get("archetype_distribution", {})
        
        # Archetype descriptions
        archetype_info = {
            "achiever": {
                "name": "Achievement-Driven Performers",
                "description": "Success-focused individuals who value quality and status",
                "icon": "🏆",
                "regulatory_focus": "promotion",
                "key_values": ["success", "excellence", "status", "quality"],
            },
            "explorer": {
                "name": "Curious Experience Seekers",
                "description": "Novelty-seeking individuals driven by discovery and adventure",
                "icon": "🧭",
                "regulatory_focus": "promotion",
                "key_values": ["novelty", "adventure", "discovery", "experience"],
            },
            "guardian": {
                "name": "Security-Focused Protectors",
                "description": "Safety-conscious individuals who prioritize reliability",
                "icon": "🛡️",
                "regulatory_focus": "prevention",
                "key_values": ["safety", "reliability", "trust", "protection"],
            },
            "connector": {
                "name": "Relationship-Centered Sharers",
                "description": "Community-oriented individuals who value relationships",
                "icon": "🤝",
                "regulatory_focus": "mixed",
                "key_values": ["connection", "sharing", "community", "relationships"],
            },
            "analyst": {
                "name": "Detail-Oriented Researchers",
                "description": "Knowledge-driven individuals who value thorough analysis",
                "icon": "🔬",
                "regulatory_focus": "prevention",
                "key_values": ["knowledge", "accuracy", "research", "evidence"],
            },
            "pragmatist": {
                "name": "Value-Conscious Optimizers",
                "description": "Practical individuals focused on efficiency and value",
                "icon": "⚖️",
                "regulatory_focus": "prevention",
                "key_values": ["value", "efficiency", "practicality", "function"],
            },
        }
        
        # Generate segments for top archetypes
        sorted_archetypes = sorted(archetype_scores.items(), key=lambda x: -x[1])
        
        for archetype, score in sorted_archetypes[:4]:
            if score < 0.05:
                continue
            
            info = archetype_info.get(archetype, {})
            
            # Get mechanism effectiveness for this archetype
            mechanisms = self._get_mechanism_effectiveness(archetype)
            
            segment = {
                "archetype": archetype,
                "name": info.get("name", f"{archetype.title()} Segment"),
                "description": info.get("description", ""),
                "icon": info.get("icon", "👤"),
                "match_score": score,
                "regulatory_focus": info.get("regulatory_focus", "promotion"),
                "key_values": info.get("key_values", []),
                "primary_mechanisms": mechanisms[:3] if mechanisms else [],
                "persuasion_approach": self._get_persuasion_approach(archetype),
            }
            
            segments.append(segment)
        
        return segments
    
    def _get_mechanism_effectiveness(self, archetype: str) -> List[str]:
        """Get effective mechanisms for an archetype from learned priors."""
        if not self.mechanism_effectiveness:
            return []
        
        global_effectiveness = self.mechanism_effectiveness.get("global", {})
        archetype_mechanisms = global_effectiveness.get(archetype, {})
        
        if not archetype_mechanisms:
            return []
        
        # Sort by effectiveness
        sorted_mechs = sorted(archetype_mechanisms.items(), key=lambda x: -x[1])
        return [m[0] for m in sorted_mechs if m[1] > 0]
    
    def _get_persuasion_approach(self, archetype: str) -> Dict[str, Any]:
        """Get persuasion approach from learned priors."""
        if not self.complete_priors:
            return {}
        
        strategies = self.complete_priors.get("persuasion_strategies", {})
        return strategies.get(archetype, {})
    
    def _enhance_strategy_with_priors(self, intel: PsychologicalIntelligence):
        """Enhance persuasion strategy with learned priors."""
        archetype = intel.primary_archetype
        
        # Get learned mechanism effectiveness
        if self.mechanism_effectiveness:
            global_eff = self.mechanism_effectiveness.get("global", {})
            arch_mechs = global_eff.get(archetype, {})
            
            if arch_mechs:
                # Sort by effectiveness
                sorted_mechs = sorted(arch_mechs.items(), key=lambda x: -x[1])
                intel.strategy.primary_mechanisms = [m[0] for m in sorted_mechs[:3] if m[1] > 0]
                intel.strategy.secondary_mechanisms = [m[0] for m in sorted_mechs[3:6] if m[1] > 0]
                intel.strategy.avoid_mechanisms = [m[0] for m in sorted_mechs if m[1] < 0][:2]
        
        # Add synergies from priors
        if self.complete_priors:
            synergies = self.complete_priors.get("mechanism_synergies", {})
            for combo, multiplier in synergies.items():
                parts = combo.split("+")
                if len(parts) == 2:
                    intel.strategy.mechanism_synergies.append({
                        "mechanism_1": parts[0],
                        "mechanism_2": parts[1],
                        "multiplier": multiplier,
                    })
    
    def get_archetype_distribution(self, category: Optional[str] = None) -> Dict[str, float]:
        """Get archetype distribution (global or by category)."""
        if category and self.archetype_priors:
            cat_key = category.replace(" ", "_")
            cat_dist = self.archetype_priors.get("by_category", {}).get(cat_key)
            if cat_dist:
                return cat_dist
        
        return self.complete_priors.get("archetype_distribution", {})
    
    def get_brand_psychology(self, brand_name: str) -> Optional[Dict[str, Any]]:
        """Get psychological profile for a brand."""
        if not self.brand_profiles:
            return None
        
        brand_key = brand_name.lower().strip()
        for stored_brand, profile in self.brand_profiles.get("brands", {}).items():
            if stored_brand.lower() == brand_key:
                return {
                    "brand": stored_brand,
                    "review_count": profile.get("review_count", 0),
                    "primary_archetype": profile.get("primary_archetype"),
                    "archetype_distribution": profile.get("archetype_distribution", {}),
                    "personality": profile.get("personality", {}),
                    "motivation": profile.get("motivation", {}),
                    "mechanism_effectiveness": profile.get("mechanism_effectiveness", {}),
                }
        
        return None
    
    def get_mechanism_synergies(self) -> List[Dict[str, Any]]:
        """Get known mechanism synergies with multipliers."""
        synergies = []
        
        if self.complete_priors:
            for combo, multiplier in self.complete_priors.get("mechanism_synergies", {}).items():
                parts = combo.split("+")
                if len(parts) == 2:
                    synergies.append({
                        "mechanism_1": parts[0],
                        "mechanism_2": parts[1],
                        "multiplier": multiplier,
                        "description": f"{parts[0].title()} + {parts[1].title()} produces {multiplier}x combined effect"
                    })
        
        return synergies
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            "priors_loaded": self.priors_loaded,
            "analyzer_available": self.analyzer_available,
            "total_reviews_learned": self.complete_priors.get("total_reviews_analyzed", 0),
            "total_brands": self.complete_priors.get("total_brands", 0),
            "total_categories": self.complete_priors.get("total_categories", 0),
            "frameworks_count": 82,
            "categories_count": 20,
            "pattern_count": "~3,600+",
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_framework_intelligence: Optional[Framework82Intelligence] = None


def get_framework_intelligence() -> Framework82Intelligence:
    """Get or create the singleton Framework82Intelligence instance."""
    global _framework_intelligence
    if _framework_intelligence is None:
        _framework_intelligence = Framework82Intelligence()
    return _framework_intelligence


# =============================================================================
# API ENDPOINTS INTEGRATION
# =============================================================================

def analyze_product_psychology(
    product_description: str,
    brand_name: Optional[str] = None,
    category: Optional[str] = None,
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    High-level function for API integration.
    
    Returns a dictionary suitable for JSON serialization.
    """
    intel_service = get_framework_intelligence()
    intel = intel_service.analyze_product(
        product_description=product_description,
        brand_name=brand_name,
        category=category,
        price=price,
    )
    
    return {
        "primary_archetype": intel.primary_archetype,
        "archetype_scores": intel.archetype_scores,
        "personality": intel.personality_profile,
        "motivation": intel.motivation_profile,
        "cognitive_mechanisms": intel.cognitive_mechanisms,
        "strategy": {
            "archetype": intel.strategy.archetype if intel.strategy else None,
            "regulatory_focus": intel.strategy.regulatory_focus if intel.strategy else None,
            "framing": intel.strategy.framing if intel.strategy else None,
            "message_focus": intel.strategy.message_focus if intel.strategy else None,
            "construal_level": intel.strategy.construal_level if intel.strategy else None,
            "processing_route": intel.strategy.processing_route if intel.strategy else None,
            "primary_mechanisms": intel.strategy.primary_mechanisms if intel.strategy else [],
            "secondary_mechanisms": intel.strategy.secondary_mechanisms if intel.strategy else [],
            "avoid_mechanisms": intel.strategy.avoid_mechanisms if intel.strategy else [],
            "mechanism_synergies": intel.strategy.mechanism_synergies if intel.strategy else [],
            "ethical_notes": intel.strategy.ethical_notes if intel.strategy else [],
        } if intel.strategy else None,
        "target_segments": intel.target_segments,
        "brand_match": intel.brand_match,
        "category_insights": intel.category_insights,
        "service_status": intel_service.get_status(),
    }
