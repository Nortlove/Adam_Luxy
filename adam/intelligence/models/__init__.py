# =============================================================================
# ADAM Intelligence Models
# Location: adam/intelligence/models/__init__.py
# =============================================================================

"""
Intelligence data models for the ADAM platform.

These models support:
- Customer Intelligence from review analysis
- Review psychological profiling
- Purchase motivation extraction
- Language pattern analysis
"""

from adam.intelligence.models.customer_intelligence import (
    CustomerIntelligenceProfile,
    ReviewAnalysis,
    ReviewerProfile,
    LanguagePatterns,
    PurchaseMotivation,
    IdealCustomerProfile,
)

__all__ = [
    "CustomerIntelligenceProfile",
    "ReviewAnalysis",
    "ReviewerProfile",
    "LanguagePatterns",
    "PurchaseMotivation",
    "IdealCustomerProfile",
]
