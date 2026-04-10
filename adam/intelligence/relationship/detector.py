"""
Relationship Detector Service
=============================

Core service for detecting consumer-brand relationships from text across
multiple observation channels.

This service:
1. Analyzes text using validated language patterns
2. Aggregates signals across channels
3. Determines primary and secondary relationship types
4. Calculates relationship strength and characteristics
5. Generates actionable recommendations for ad targeting

The detection follows the 5-Channel Observation Framework:
- Channels 1-4 (Customer Reviews, Social Signals, Self-Expression, Brand Positioning) 
  are INPUT channels for detection
- Channel 5 (Advertising) is the OUTPUT channel for recommendations
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import uuid
from collections import defaultdict

from .models import (
    ObservationChannel,
    RelationshipTypeId,
    RelationshipStrength,
    RelationshipSignal,
    ConsumerBrandRelationship,
    RELATIONSHIP_MECHANISM_MAP,
)
from .patterns import (
    ALL_PATTERNS,
    PATTERN_BY_ID,
    PATTERNS_BY_RELATIONSHIP,
    LanguagePattern,
)


logger = logging.getLogger(__name__)


class RelationshipDetector:
    """
    Detects consumer-brand relationship types from text signals.
    
    The detector processes text from multiple channels, matches validated
    language patterns, and aggregates results into a comprehensive
    relationship profile.
    """
    
    def __init__(self):
        """Initialize the relationship detector with pattern registry."""
        self.patterns = ALL_PATTERNS
        self.patterns_by_relationship = PATTERNS_BY_RELATIONSHIP
        
        # Thresholds for relationship detection
        self.min_confidence_threshold = 0.3
        self.min_pattern_matches = 1
        self.multi_channel_boost = 0.15
        self.self_expression_premium = 1.5  # Weight boost for identity relationships
        
    def detect_signals(
        self,
        text: str,
        channel: ObservationChannel,
        brand_id: Optional[str] = None,
        consumer_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> List[RelationshipSignal]:
        """
        Detect relationship signals from a single text input.
        
        Args:
            text: The text to analyze (review, social post, etc.)
            channel: The observation channel this text comes from
            brand_id: Optional brand identifier
            consumer_id: Optional consumer identifier
            source_id: Optional source document ID
            
        Returns:
            List of detected RelationshipSignal objects
        """
        signals = []
        text_lower = text.lower()
        
        # Track which relationship types we've detected in this text
        detected_types: Dict[RelationshipTypeId, Tuple[float, List[str]]] = {}
        
        for pattern in self.patterns:
            if pattern.matches(text_lower):
                confidence = pattern.get_weight_for_channel(channel)
                rel_type = pattern.relationship_type
                
                if rel_type not in detected_types:
                    detected_types[rel_type] = (confidence, [pattern.pattern_id])
                else:
                    # Multiple patterns for same relationship - boost confidence
                    existing_conf, existing_patterns = detected_types[rel_type]
                    # Use max confidence + small boost for additional patterns
                    new_conf = max(existing_conf, confidence) + (0.05 * len(existing_patterns))
                    new_conf = min(new_conf, 1.0)  # Cap at 1.0
                    detected_types[rel_type] = (new_conf, existing_patterns + [pattern.pattern_id])
        
        # Create signals for each detected relationship type
        for rel_type, (confidence, pattern_ids) in detected_types.items():
            if confidence >= self.min_confidence_threshold:
                signal = RelationshipSignal(
                    signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                    channel=channel,
                    source_text=text[:500],  # Truncate for storage
                    source_id=source_id,
                    matched_patterns=pattern_ids,
                    relationship_type=rel_type,
                    confidence=confidence,
                    brand_id=brand_id,
                    consumer_id=consumer_id,
                    detected_at=datetime.utcnow().isoformat(),
                    emotional_intensity=self._calculate_emotional_intensity(text_lower),
                    identity_integration=self._calculate_identity_integration(text_lower, rel_type),
                    social_display=self._calculate_social_display(text_lower, rel_type),
                )
                signals.append(signal)
        
        return signals
    
    def analyze_texts(
        self,
        texts: List[Dict[str, Any]],
        brand_id: str,
        consumer_id: Optional[str] = None,
    ) -> ConsumerBrandRelationship:
        """
        Analyze multiple texts to build a complete relationship profile.
        
        Args:
            texts: List of dicts with 'text', 'channel', and optional 'source_id'
            brand_id: The brand being analyzed
            consumer_id: Optional consumer identifier
            
        Returns:
            ConsumerBrandRelationship with aggregated analysis
        """
        all_signals: List[RelationshipSignal] = []
        channel_evidence: Dict[ObservationChannel, float] = defaultdict(float)
        relationship_scores: Dict[RelationshipTypeId, float] = defaultdict(float)
        
        # Process each text
        for text_entry in texts:
            text = text_entry.get('text', '')
            channel = text_entry.get('channel', ObservationChannel.CUSTOMER_REVIEWS)
            source_id = text_entry.get('source_id')
            
            signals = self.detect_signals(
                text=text,
                channel=channel,
                brand_id=brand_id,
                consumer_id=consumer_id,
                source_id=source_id,
            )
            all_signals.extend(signals)
            
            # Track channel evidence
            if signals:
                channel_evidence[channel] += sum(s.confidence for s in signals) / len(signals)
        
        # Aggregate relationship scores across all signals
        channels_per_relationship: Dict[RelationshipTypeId, set] = defaultdict(set)
        
        for signal in all_signals:
            rel_type = signal.relationship_type
            
            # Apply self-expression premium for identity relationships
            weight = signal.confidence
            if signal.channel == ObservationChannel.SELF_EXPRESSION and rel_type in [
                RelationshipTypeId.SELF_IDENTITY_CORE,
                RelationshipTypeId.SELF_EXPRESSION_VEHICLE,
            ]:
                weight *= self.self_expression_premium
            
            relationship_scores[rel_type] += weight
            channels_per_relationship[rel_type].add(signal.channel)
        
        # Apply multi-channel boost
        for rel_type, channels in channels_per_relationship.items():
            if len(channels) >= 2:
                relationship_scores[rel_type] += self.multi_channel_boost * (len(channels) - 1)
        
        # Determine primary and secondary relationships
        if not relationship_scores:
            # No relationship detected - default to reliable tool (functional)
            primary_type = RelationshipTypeId.RELIABLE_TOOL
            primary_confidence = 0.3
            secondary_relationships = {}
        else:
            sorted_relationships = sorted(
                relationship_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            primary_type = sorted_relationships[0][0]
            primary_confidence = min(sorted_relationships[0][1], 1.0)
            
            # Secondary relationships (top 3 after primary)
            secondary_relationships = {
                rel_type: min(score, 1.0)
                for rel_type, score in sorted_relationships[1:4]
                if score >= self.min_confidence_threshold
            }
        
        # Calculate aggregated characteristics
        avg_emotional = sum(s.emotional_intensity for s in all_signals) / max(len(all_signals), 1)
        avg_identity = sum(s.identity_integration for s in all_signals) / max(len(all_signals), 1)
        avg_social = sum(s.social_display for s in all_signals) / max(len(all_signals), 1)
        
        # Determine strength
        strength, strength_score = self._calculate_strength(primary_confidence, len(all_signals))
        
        # Get recommended mechanisms and strategies
        recommended_mechanisms = RELATIONSHIP_MECHANISM_MAP.get(primary_type, [])
        
        # Build the relationship profile
        relationship = ConsumerBrandRelationship(
            relationship_id=f"rel_{uuid.uuid4().hex[:12]}",
            brand_id=brand_id,
            consumer_id=consumer_id,
            primary_relationship_type=primary_type,
            primary_confidence=primary_confidence,
            secondary_relationships=secondary_relationships,
            strength=strength,
            strength_score=strength_score,
            channel_evidence=dict(channel_evidence),
            signals=[s.signal_id for s in all_signals],
            signal_count=len(all_signals),
            emotional_intensity=avg_emotional,
            identity_integration=avg_identity,
            social_function=avg_social,
            functional_orientation=1.0 - avg_emotional if primary_type == RelationshipTypeId.RELIABLE_TOOL else 0.3,
            vulnerability_to_dissolution=self._get_vulnerability(primary_type),
            predicted_loyalty=self._calculate_loyalty(primary_type, strength_score),
            advocacy_likelihood=self._calculate_advocacy(primary_type, avg_social, avg_emotional),
            recommended_engagement_strategy=self._get_engagement_strategy(primary_type),
            recommended_ad_templates=self._get_ad_templates(primary_type),
            recommended_mechanisms=recommended_mechanisms[:4],
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        
        return relationship
    
    def analyze_review(
        self,
        review_text: str,
        brand_id: str,
        source_id: Optional[str] = None,
    ) -> ConsumerBrandRelationship:
        """
        Convenience method to analyze a single customer review.
        """
        return self.analyze_texts(
            texts=[{
                'text': review_text,
                'channel': ObservationChannel.CUSTOMER_REVIEWS,
                'source_id': source_id,
            }],
            brand_id=brand_id,
        )
    
    def analyze_social_post(
        self,
        post_text: str,
        brand_id: str,
        source_id: Optional[str] = None,
    ) -> ConsumerBrandRelationship:
        """
        Convenience method to analyze a single social media post.
        """
        return self.analyze_texts(
            texts=[{
                'text': post_text,
                'channel': ObservationChannel.SOCIAL_SIGNALS,
                'source_id': source_id,
            }],
            brand_id=brand_id,
        )
    
    def _calculate_emotional_intensity(self, text: str) -> float:
        """Calculate emotional intensity from text features."""
        intensity = 0.5  # Base
        
        # Exclamation marks indicate intensity
        exclamation_count = text.count('!')
        intensity += min(exclamation_count * 0.1, 0.3)
        
        # Superlatives and intensifiers
        intensifiers = [
            'absolutely', 'completely', 'totally', 'extremely', 'incredibly',
            'amazing', 'wonderful', 'terrible', 'horrible', 'best', 'worst',
            'love', 'hate', 'obsessed', 'addicted', 'passionate'
        ]
        for intensifier in intensifiers:
            if intensifier in text:
                intensity += 0.05
        
        # Caps indicate intensity
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:
            intensity += 0.15
        
        return min(intensity, 1.0)
    
    def _calculate_identity_integration(
        self,
        text: str,
        rel_type: RelationshipTypeId
    ) -> float:
        """Calculate how integrated the brand is with self-identity."""
        if rel_type not in [
            RelationshipTypeId.SELF_IDENTITY_CORE,
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE,
            RelationshipTypeId.TRIBAL_BADGE,
        ]:
            return 0.2  # Low baseline for non-identity relationships
        
        integration = 0.5  # Base for identity relationships
        
        identity_words = [
            'i am', 'part of me', 'who i am', 'defines me', 'reflects me',
            'my identity', 'blood', 'dna', 'born', 'always been', 'forever'
        ]
        for word in identity_words:
            if word in text:
                integration += 0.1
        
        return min(integration, 1.0)
    
    def _calculate_social_display(
        self,
        text: str,
        rel_type: RelationshipTypeId
    ) -> float:
        """Calculate social display/signaling function."""
        if rel_type not in [
            RelationshipTypeId.STATUS_MARKER,
            RelationshipTypeId.TRIBAL_BADGE,
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE,
        ]:
            return 0.2  # Low baseline for non-social relationships
        
        display = 0.5  # Base for social relationships
        
        social_words = [
            'people notice', 'compliments', 'turns heads', 'exclusive',
            'prestigious', 'my tribe', 'my people', 'community', 'status',
            'flexing', 'showing off', 'everyone asks'
        ]
        for word in social_words:
            if word in text:
                display += 0.1
        
        return min(display, 1.0)
    
    def _calculate_strength(
        self,
        primary_confidence: float,
        signal_count: int
    ) -> Tuple[RelationshipStrength, float]:
        """Calculate overall relationship strength."""
        # Combine confidence with signal volume
        base_score = primary_confidence
        
        # More signals = stronger evidence
        volume_bonus = min(signal_count * 0.05, 0.3)
        strength_score = min(base_score + volume_bonus, 1.0)
        
        if strength_score >= 0.8:
            return RelationshipStrength.VERY_STRONG, strength_score
        elif strength_score >= 0.6:
            return RelationshipStrength.STRONG, strength_score
        elif strength_score >= 0.4:
            return RelationshipStrength.MODERATE, strength_score
        else:
            return RelationshipStrength.WEAK, strength_score
    
    def _get_vulnerability(self, rel_type: RelationshipTypeId) -> str:
        """Get vulnerability to dissolution for a relationship type."""
        vulnerability_map = {
            RelationshipTypeId.SELF_IDENTITY_CORE: "very_low",
            RelationshipTypeId.TRIBAL_BADGE: "low",
            RelationshipTypeId.COMMITTED_PARTNERSHIP: "low",
            RelationshipTypeId.DEPENDENCY: "very_low",
            RelationshipTypeId.CHILDHOOD_FRIEND: "low",
            RelationshipTypeId.ENEMY: "low",  # Hard to convert back
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: "moderate",
            RelationshipTypeId.MENTOR: "moderate",
            RelationshipTypeId.COMFORT_COMPANION: "moderate",
            RelationshipTypeId.ASPIRATIONAL_ICON: "moderate",
            RelationshipTypeId.STATUS_MARKER: "high",
            RelationshipTypeId.RELIABLE_TOOL: "high",
        }
        return vulnerability_map.get(rel_type, "moderate")
    
    def _calculate_loyalty(
        self,
        rel_type: RelationshipTypeId,
        strength_score: float
    ) -> float:
        """Calculate predicted loyalty based on relationship type and strength."""
        # Base loyalty by relationship type
        type_loyalty = {
            RelationshipTypeId.SELF_IDENTITY_CORE: 0.95,
            RelationshipTypeId.DEPENDENCY: 0.90,
            RelationshipTypeId.TRIBAL_BADGE: 0.85,
            RelationshipTypeId.COMMITTED_PARTNERSHIP: 0.85,
            RelationshipTypeId.CHILDHOOD_FRIEND: 0.80,
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: 0.75,
            RelationshipTypeId.MENTOR: 0.70,
            RelationshipTypeId.COMFORT_COMPANION: 0.65,
            RelationshipTypeId.ASPIRATIONAL_ICON: 0.60,
            RelationshipTypeId.STATUS_MARKER: 0.50,
            RelationshipTypeId.RELIABLE_TOOL: 0.45,
            RelationshipTypeId.ENEMY: 0.0,
        }
        base = type_loyalty.get(rel_type, 0.5)
        
        # Adjust by strength
        return base * strength_score
    
    def _calculate_advocacy(
        self,
        rel_type: RelationshipTypeId,
        social_display: float,
        emotional_intensity: float
    ) -> float:
        """Calculate likelihood of brand advocacy (word-of-mouth)."""
        # Types that drive advocacy
        advocacy_types = {
            RelationshipTypeId.SELF_IDENTITY_CORE: 0.9,
            RelationshipTypeId.TRIBAL_BADGE: 0.95,  # Tribal = high advocacy
            RelationshipTypeId.COMMITTED_PARTNERSHIP: 0.8,
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: 0.75,
            RelationshipTypeId.STATUS_MARKER: 0.7,  # Social display drives sharing
            RelationshipTypeId.MENTOR: 0.65,
            RelationshipTypeId.ENEMY: 0.85,  # Negative advocacy
            RelationshipTypeId.CHILDHOOD_FRIEND: 0.6,
            RelationshipTypeId.RELIABLE_TOOL: 0.4,  # Low emotional = low sharing
        }
        base = advocacy_types.get(rel_type, 0.5)
        
        # Social display and emotion boost advocacy
        boost = (social_display * 0.15) + (emotional_intensity * 0.1)
        
        return min(base + boost, 1.0)
    
    def _get_engagement_strategy(self, rel_type: RelationshipTypeId) -> str:
        """Get recommended engagement strategy name."""
        strategy_map = {
            RelationshipTypeId.SELF_IDENTITY_CORE: "identity_affirmation",
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: "value_expression",
            RelationshipTypeId.STATUS_MARKER: "status_recognition",
            RelationshipTypeId.TRIBAL_BADGE: "tribal_belonging",
            RelationshipTypeId.COMMITTED_PARTNERSHIP: "relationship_deepening",
            RelationshipTypeId.DEPENDENCY: "reassurance_reliability",
            RelationshipTypeId.RELIABLE_TOOL: "functional_value",
            RelationshipTypeId.MENTOR: "expertise_guidance",
            RelationshipTypeId.COMFORT_COMPANION: "comfort_provision",
            RelationshipTypeId.CHILDHOOD_FRIEND: "nostalgia_connection",
            RelationshipTypeId.ASPIRATIONAL_ICON: "aspiration_bridge",
            RelationshipTypeId.ENEMY: "trust_rebuilding",
        }
        return strategy_map.get(rel_type, "general_engagement")
    
    def _get_ad_templates(self, rel_type: RelationshipTypeId) -> List[str]:
        """Get recommended ad creative templates."""
        template_map = {
            RelationshipTypeId.SELF_IDENTITY_CORE: [
                "heritage_authenticity",
                "community_celebration",
            ],
            RelationshipTypeId.SELF_EXPRESSION_VEHICLE: [
                "value_expression",
                "authentic_self",
            ],
            RelationshipTypeId.STATUS_MARKER: [
                "luxury_aspiration",
                "exclusive_access",
            ],
            RelationshipTypeId.TRIBAL_BADGE: [
                "community_gathering",
                "insider_access",
            ],
            RelationshipTypeId.COMMITTED_PARTNERSHIP: [
                "partnership_journey",
                "appreciation_loyalty",
            ],
            RelationshipTypeId.RELIABLE_TOOL: [
                "performance_proof",
                "comparison_value",
            ],
            RelationshipTypeId.MENTOR: [
                "expert_masterclass",
                "educational_series",
            ],
            RelationshipTypeId.COMFORT_COMPANION: [
                "comfort_sanctuary",
                "self_care_moment",
            ],
            RelationshipTypeId.CHILDHOOD_FRIEND: [
                "heritage_nostalgia",
                "tradition_continuation",
            ],
            RelationshipTypeId.ASPIRATIONAL_ICON: [
                "achievement_milestone",
                "transformation_journey",
            ],
        }
        return template_map.get(rel_type, ["general_brand"])


# Singleton instance for service use
_detector_instance: Optional[RelationshipDetector] = None


def get_relationship_detector() -> RelationshipDetector:
    """Get or create the singleton RelationshipDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = RelationshipDetector()
    return _detector_instance
