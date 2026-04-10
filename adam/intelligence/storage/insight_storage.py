# =============================================================================
# Insight Storage Service
# Location: adam/intelligence/storage/insight_storage.py
# =============================================================================

"""
Insight Storage Service - Persistent Storage for Psychological Intelligence

This service persists all psychological intelligence insights to a local SQLite
database for:
1. Future queries of brand/product intelligence
2. Continuous learning from accumulated insights
3. Testing advertising message effectiveness
4. Cross-brand psychological pattern discovery

Storage Schema:
- psychological_profiles: Unified profiles with all module outputs
- flow_state_profiles: Flow state analysis results
- psychological_needs: Individual need detections
- psycholinguistic_constructs: Individual construct measurements
- ad_recommendations: Generated recommendations and their outcomes
- learning_signals: Signals emitted for learning system

Usage:
    from adam.intelligence.storage.insight_storage import (
        InsightStorageService,
        get_insight_storage
    )
    
    storage = get_insight_storage()
    
    # Store a profile
    await storage.store_profile(unified_profile)
    
    # Query by brand/product
    profiles = await storage.get_profiles_for_brand("DeWalt")
    
    # Get similar profiles
    similar = await storage.find_similar_profiles(profile)
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

INSIGHT_SCHEMA = """
-- Psychological Profiles (unified from all 3 modules)
CREATE TABLE IF NOT EXISTS psychological_profiles (
    profile_id TEXT PRIMARY KEY,
    brand_name TEXT NOT NULL,
    product_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Archetype determination
    primary_archetype TEXT,
    archetype_confidence REAL DEFAULT 0.0,
    unified_archetype TEXT,
    unified_archetype_confidence REAL DEFAULT 0.0,
    
    -- Flow state summary
    flow_arousal REAL DEFAULT 0.5,
    flow_valence REAL DEFAULT 0.5,
    flow_energy REAL DEFAULT 0.5,
    flow_cognitive_load REAL DEFAULT 0.5,
    flow_ad_receptivity REAL DEFAULT 0.5,
    flow_optimal_formats TEXT,
    flow_recommended_tone TEXT,
    
    -- Psychological needs summary
    promotion_focus REAL DEFAULT 0.5,
    prevention_focus REAL DEFAULT 0.5,
    alignment_score REAL DEFAULT 0.5,
    unmet_needs TEXT,
    
    -- Processing metadata
    reviews_analyzed INTEGER DEFAULT 0,
    analysis_time_ms REAL DEFAULT 0.0,
    modules_used TEXT,
    
    -- Full profile (JSON blob for complete data)
    full_profile_json TEXT
);

-- Flow State Profiles
CREATE TABLE IF NOT EXISTS flow_state_profiles (
    flow_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Core dimensions
    arousal REAL DEFAULT 0.5,
    valence REAL DEFAULT 0.5,
    energy REAL DEFAULT 0.5,
    cognitive_load REAL DEFAULT 0.5,
    nostalgia REAL DEFAULT 0.5,
    social_energy REAL DEFAULT 0.5,
    flow_stability REAL DEFAULT 0.5,
    ad_receptivity REAL DEFAULT 0.5,
    
    -- Recommendations
    optimal_formats TEXT,  -- JSON array
    recommended_tone TEXT,
    
    FOREIGN KEY (profile_id) REFERENCES psychological_profiles(profile_id)
);

-- Psychological Needs
CREATE TABLE IF NOT EXISTS psychological_needs (
    need_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Need identification
    need_type TEXT NOT NULL,
    need_name TEXT NOT NULL,
    category TEXT,
    
    -- Activation
    activation_strength REAL DEFAULT 0.0,
    alignment_status TEXT,
    unmet BOOLEAN DEFAULT FALSE,
    
    -- Recommendations
    recommended_actions TEXT,  -- JSON array
    
    FOREIGN KEY (profile_id) REFERENCES psychological_profiles(profile_id)
);

-- Psycholinguistic Constructs
CREATE TABLE IF NOT EXISTS psycholinguistic_constructs (
    construct_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Construct identification
    construct_type TEXT NOT NULL,
    construct_name TEXT NOT NULL,
    
    -- Scoring
    score REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    effect_size REAL,
    
    -- Recommendations
    ad_recommendation TEXT,
    supporting_evidence TEXT,  -- JSON array
    
    FOREIGN KEY (profile_id) REFERENCES psychological_profiles(profile_id)
);

-- Ad Recommendations
CREATE TABLE IF NOT EXISTS ad_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Recommendation
    priority_score REAL DEFAULT 0.0,
    construct_name TEXT,
    recommendation TEXT,
    confidence REAL DEFAULT 0.5,
    
    -- Source tracking
    source_modules TEXT,  -- JSON array
    effect_size REAL,
    supporting_evidence TEXT,  -- JSON array
    
    -- Outcome tracking (for learning)
    outcome_measured BOOLEAN DEFAULT FALSE,
    outcome_engagement_rate REAL,
    outcome_conversion_rate REAL,
    outcome_measured_at TIMESTAMP,
    
    FOREIGN KEY (profile_id) REFERENCES psychological_profiles(profile_id)
);

-- Learning Signals
CREATE TABLE IF NOT EXISTS learning_signals (
    signal_id TEXT PRIMARY KEY,
    profile_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Signal type
    signal_type TEXT NOT NULL,
    source_module TEXT,
    
    -- Signal payload
    payload_json TEXT,
    confidence REAL DEFAULT 0.5,
    
    -- Processing status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    
    FOREIGN KEY (profile_id) REFERENCES psychological_profiles(profile_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_profiles_brand ON psychological_profiles(brand_name);
CREATE INDEX IF NOT EXISTS idx_profiles_product ON psychological_profiles(product_name);
CREATE INDEX IF NOT EXISTS idx_profiles_archetype ON psychological_profiles(primary_archetype);
CREATE INDEX IF NOT EXISTS idx_needs_profile ON psychological_needs(profile_id);
CREATE INDEX IF NOT EXISTS idx_constructs_profile ON psycholinguistic_constructs(profile_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_profile ON ad_recommendations(profile_id);
CREATE INDEX IF NOT EXISTS idx_signals_profile ON learning_signals(profile_id);
CREATE INDEX IF NOT EXISTS idx_signals_unprocessed ON learning_signals(processed) WHERE processed = FALSE;
"""


# =============================================================================
# STORAGE SERVICE
# =============================================================================

class InsightStorageService:
    """
    Service for storing and retrieving psychological intelligence insights.
    
    Uses SQLite for persistent local storage with efficient querying.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the storage service.
        
        Args:
            db_path: Path to SQLite database file (default: in adam data directory)
        """
        if db_path is None:
            # Default to adam data directory
            adam_platform = Path("/Users/chrisnocera/Sites/adam-platform")
            data_dir = adam_platform / "data" / "insights"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "psychological_insights.db")
        
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._initialized = False
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        
        return self._conn
    
    async def initialize(self) -> bool:
        """Initialize the database schema."""
        if self._initialized:
            return True
        
        try:
            conn = self._get_connection()
            
            # Create tables
            conn.executescript(INSIGHT_SCHEMA)
            conn.commit()
            
            self._initialized = True
            logger.info(f"Insight storage initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize insight storage: {e}")
            return False
    
    async def store_profile(
        self,
        profile: "UnifiedPsychologicalProfile",
    ) -> bool:
        """
        Store a unified psychological profile.
        
        Args:
            profile: UnifiedPsychologicalProfile to store
            
        Returns:
            True if successful
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            
            # Store main profile
            conn.execute("""
                INSERT OR REPLACE INTO psychological_profiles (
                    profile_id, brand_name, product_name, created_at,
                    primary_archetype, archetype_confidence,
                    unified_archetype, unified_archetype_confidence,
                    flow_arousal, flow_valence, flow_energy,
                    flow_cognitive_load, flow_ad_receptivity,
                    flow_optimal_formats, flow_recommended_tone,
                    promotion_focus, prevention_focus, alignment_score,
                    unmet_needs, reviews_analyzed, analysis_time_ms,
                    modules_used, full_profile_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.profile_id,
                profile.brand_name,
                profile.product_name,
                profile.created_at.isoformat(),
                profile.primary_archetype,
                profile.archetype_confidence,
                profile.primary_archetype,  # unified_archetype same as primary
                profile.archetype_confidence,
                profile.flow_state.arousal,
                profile.flow_state.valence,
                profile.flow_state.energy,
                profile.flow_state.cognitive_load,
                profile.flow_state.ad_receptivity_score,
                json.dumps(profile.flow_state.optimal_formats),
                profile.flow_state.recommended_tone,
                profile.psychological_needs.promotion_focus,
                profile.psychological_needs.prevention_focus,
                profile.psychological_needs.overall_alignment_score,
                json.dumps(profile.psychological_needs.unmet_needs),
                profile.reviews_analyzed,
                profile.analysis_time_ms,
                json.dumps(profile.modules_used),
                json.dumps(profile.to_dict()),
            ))
            
            # Store flow state
            flow_id = f"{profile.profile_id}_flow"
            conn.execute("""
                INSERT OR REPLACE INTO flow_state_profiles (
                    flow_id, profile_id, created_at,
                    arousal, valence, energy, cognitive_load,
                    nostalgia, social_energy, flow_stability,
                    ad_receptivity, optimal_formats, recommended_tone
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flow_id,
                profile.profile_id,
                profile.created_at.isoformat(),
                profile.flow_state.arousal,
                profile.flow_state.valence,
                profile.flow_state.energy,
                profile.flow_state.cognitive_load,
                profile.flow_state.nostalgia,
                profile.flow_state.social_energy,
                profile.flow_state.flow_stability,
                profile.flow_state.ad_receptivity_score,
                json.dumps(profile.flow_state.optimal_formats),
                profile.flow_state.recommended_tone,
            ))
            
            # Store psychological needs
            for i, (need_id, activation) in enumerate(profile.psychological_needs.primary_needs[:20]):
                need_db_id = f"{profile.profile_id}_need_{i}"
                category = need_id.split("_")[0] if "_" in need_id else "general"
                unmet = need_id in profile.psychological_needs.unmet_needs
                
                conn.execute("""
                    INSERT OR REPLACE INTO psychological_needs (
                        need_id, profile_id, created_at,
                        need_type, need_name, category,
                        activation_strength, alignment_status, unmet
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    need_db_id,
                    profile.profile_id,
                    profile.created_at.isoformat(),
                    need_id,
                    need_id.replace("_", " ").title(),
                    category,
                    activation,
                    "unmet" if unmet else "met",
                    unmet,
                ))
            
            # Store constructs
            for construct_id, score in profile.unified_constructs.items():
                construct_db_id = f"{profile.profile_id}_construct_{construct_id}"
                confidence = profile.psycholinguistic.confidence_scores.get(construct_id, 0.5)
                
                conn.execute("""
                    INSERT OR REPLACE INTO psycholinguistic_constructs (
                        construct_id, profile_id, created_at,
                        construct_type, construct_name, score, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    construct_db_id,
                    profile.profile_id,
                    profile.created_at.isoformat(),
                    construct_id,
                    construct_id.replace("_", " ").title(),
                    score,
                    confidence,
                ))
            
            # Store ad recommendations
            for i, rec in enumerate(profile.unified_ad_recommendations[:20]):
                rec_id = f"{profile.profile_id}_rec_{i}"
                
                conn.execute("""
                    INSERT OR REPLACE INTO ad_recommendations (
                        recommendation_id, profile_id, created_at,
                        priority_score, construct_name, recommendation,
                        confidence, source_modules, effect_size
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec_id,
                    profile.profile_id,
                    profile.created_at.isoformat(),
                    rec.priority_score,
                    rec.construct_name,
                    rec.recommendation,
                    rec.confidence,
                    json.dumps([s.value for s in rec.source_modules]),
                    rec.effect_size,
                ))
            
            conn.commit()
            logger.info(f"Stored profile {profile.profile_id} for {profile.brand_name} {profile.product_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store profile: {e}")
            return False
    
    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a profile by ID."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM psychological_profiles WHERE profile_id = ?",
                (profile_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return None
    
    async def get_profiles_for_brand(
        self,
        brand_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get all profiles for a brand."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT * FROM psychological_profiles 
                WHERE brand_name = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (brand_name, limit)
            )
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get profiles for brand: {e}")
            return []
    
    # Alias for compatibility
    async def find_profiles_by_brand(
        self,
        brand_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Alias for get_profiles_for_brand."""
        return await self.get_profiles_for_brand(brand_name, limit)
    
    async def get_profiles_for_product(
        self,
        brand_name: str,
        product_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get profiles for a specific brand/product combination."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT * FROM psychological_profiles 
                WHERE brand_name = ? AND product_name LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (brand_name, f"%{product_name}%", limit)
            )
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get profiles for product: {e}")
            return []
    
    async def find_similar_profiles(
        self,
        profile_id: str,
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find profiles similar to the given profile.
        
        Similarity is based on flow state and regulatory focus dimensions.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get the source profile
            source = await self.get_profile(profile_id)
            if not source:
                return []
            
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT *,
                    1.0 - (
                        ABS(flow_arousal - ?) +
                        ABS(flow_valence - ?) +
                        ABS(promotion_focus - ?) +
                        ABS(prevention_focus - ?)
                    ) / 4.0 AS similarity
                FROM psychological_profiles
                WHERE profile_id != ?
                HAVING similarity >= ?
                ORDER BY similarity DESC
                LIMIT ?
                """,
                (
                    source["flow_arousal"],
                    source["flow_valence"],
                    source["promotion_focus"],
                    source["prevention_focus"],
                    profile_id,
                    min_similarity,
                    limit,
                )
            )
            
            results = []
            for row in cursor.fetchall():
                profile_dict = dict(row)
                similarity = profile_dict.pop("similarity", 0.0)
                results.append((profile_dict, similarity))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar profiles: {e}")
            return []
    
    async def store_learning_signal(
        self,
        profile_id: Optional[str],
        signal_type: str,
        source_module: str,
        payload: Dict[str, Any],
        confidence: float = 0.5,
    ) -> bool:
        """Store a learning signal for later processing."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            signal_id = str(uuid.uuid4())[:8]
            
            conn.execute("""
                INSERT INTO learning_signals (
                    signal_id, profile_id, signal_type,
                    source_module, payload_json, confidence
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                profile_id,
                signal_type,
                source_module,
                json.dumps(payload),
                confidence,
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store learning signal: {e}")
            return False
    
    async def get_unprocessed_signals(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get unprocessed learning signals for the learning system."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT * FROM learning_signals
                WHERE processed = FALSE
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get unprocessed signals: {e}")
            return []
    
    async def mark_signal_processed(self, signal_id: str) -> bool:
        """Mark a learning signal as processed."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            conn.execute(
                """
                UPDATE learning_signals
                SET processed = TRUE, processed_at = ?
                WHERE signal_id = ?
                """,
                (datetime.utcnow().isoformat(), signal_id)
            )
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark signal processed: {e}")
            return False
    
    async def record_recommendation_outcome(
        self,
        recommendation_id: str,
        engagement_rate: Optional[float] = None,
        conversion_rate: Optional[float] = None,
    ) -> bool:
        """
        Record the outcome of an ad recommendation for learning.
        
        This enables the system to learn which recommendations work best.
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            conn.execute(
                """
                UPDATE ad_recommendations
                SET outcome_measured = TRUE,
                    outcome_engagement_rate = ?,
                    outcome_conversion_rate = ?,
                    outcome_measured_at = ?
                WHERE recommendation_id = ?
                """,
                (
                    engagement_rate,
                    conversion_rate,
                    datetime.utcnow().isoformat(),
                    recommendation_id,
                )
            )
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to record recommendation outcome: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored insights."""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = self._get_connection()
            
            # Count various entities
            profiles_count = conn.execute(
                "SELECT COUNT(*) FROM psychological_profiles"
            ).fetchone()[0]
            
            brands_count = conn.execute(
                "SELECT COUNT(DISTINCT brand_name) FROM psychological_profiles"
            ).fetchone()[0]
            
            needs_count = conn.execute(
                "SELECT COUNT(*) FROM psychological_needs"
            ).fetchone()[0]
            
            constructs_count = conn.execute(
                "SELECT COUNT(*) FROM psycholinguistic_constructs"
            ).fetchone()[0]
            
            recommendations_count = conn.execute(
                "SELECT COUNT(*) FROM ad_recommendations"
            ).fetchone()[0]
            
            signals_count = conn.execute(
                "SELECT COUNT(*) FROM learning_signals"
            ).fetchone()[0]
            
            unprocessed_signals = conn.execute(
                "SELECT COUNT(*) FROM learning_signals WHERE processed = FALSE"
            ).fetchone()[0]
            
            return {
                "profiles": profiles_count,
                "brands": brands_count,
                "needs": needs_count,
                "constructs": constructs_count,
                "recommendations": recommendations_count,
                "learning_signals": signals_count,
                "unprocessed_signals": unprocessed_signals,
                "db_path": self.db_path,
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_insight_storage: Optional[InsightStorageService] = None


def get_insight_storage(db_path: Optional[str] = None) -> InsightStorageService:
    """Get the singleton InsightStorageService instance."""
    global _insight_storage
    if _insight_storage is None:
        _insight_storage = InsightStorageService(db_path)
    return _insight_storage


def reset_insight_storage() -> None:
    """Reset the singleton (for testing)."""
    global _insight_storage
    if _insight_storage:
        _insight_storage.close()
    _insight_storage = None
