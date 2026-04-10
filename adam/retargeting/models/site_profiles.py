# =============================================================================
# Therapeutic Retargeting Engine — Site Psychological Profile Models
# Location: adam/retargeting/models/site_profiles.py
# Spec: Enhancement #33, Section C.4
# =============================================================================

"""
Site psychological profile models.

Used to match placement environments to buyer archetype psychology.
A Status Seeker should see ads on sites with high aspirational_level
and low urgency_pressure. A Careful Truster should see ads on sites
with high rational_density and high trust_signaling.
"""

from datetime import datetime, timezone
from typing import Dict

from pydantic import BaseModel, Field


class SitePsychologicalProfile(BaseModel):
    """Psychological profile of a website/domain.

    12 psychological dimensions (0.0 to 1.0) extracted via Claude analysis
    of page content + visual signals. Stored as SitePsychProfile nodes
    in Neo4j, used for domain whitelist generation per archetype.
    """

    domain: str = Field(description="e.g., 'businesstraveller.com'")
    url_analyzed: str = Field(description="Specific page URL that was crawled")
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # 12 psychological dimensions (0.0 to 1.0)
    trust_signaling: float = Field(ge=0.0, le=1.0)
    emotional_warmth: float = Field(ge=0.0, le=1.0)
    rational_density: float = Field(ge=0.0, le=1.0)
    aspirational_level: float = Field(ge=0.0, le=1.0)
    simplicity: float = Field(ge=0.0, le=1.0)
    urgency_pressure: float = Field(ge=0.0, le=1.0)
    social_proof_density: float = Field(ge=0.0, le=1.0)
    narrative_richness: float = Field(ge=0.0, le=1.0)
    autonomy_respect: float = Field(ge=0.0, le=1.0)
    processing_route: float = Field(
        ge=0.0,
        le=1.0,
        description="0=peripheral (image/emotion), 1=central (data/argument)",
    )
    regulatory_framing: float = Field(
        ge=0.0, le=1.0, description="0=prevention/loss, 1=promotion/gain"
    )
    construal_level: float = Field(
        ge=0.0, le=1.0, description="0=concrete (specs), 1=abstract (values)"
    )

    # Metadata
    page_category: str = Field(
        description="'editorial', 'review', 'ecommerce', 'social', 'news'"
    )
    content_quality_score: float = Field(ge=0.0, le=1.0)
    estimated_audience_affluence: float = Field(ge=0.0, le=1.0, default=0.5)

    # Archetype alignment scores (computed from dimension x archetype weight matrix)
    archetype_alignments: Dict[str, float] = Field(
        default_factory=dict,
        description="archetype_id -> alignment_score",
    )


class SiteArchetypeAlignment(BaseModel):
    """Pre-computed alignment between a site profile and a buyer archetype."""

    domain: str
    archetype_id: str
    alignment_score: float = Field(ge=0.0, le=1.0)

    # Which dimensions drove the alignment
    dimension_contributions: Dict[str, float] = Field(
        description="dimension_name -> contribution to alignment score"
    )

    # Recommendation
    include_in_whitelist: bool = True
    whitelist_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
