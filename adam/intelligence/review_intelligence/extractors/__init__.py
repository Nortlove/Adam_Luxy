"""
Review Intelligence Extractors
==============================

Each extractor is specialized for a specific data source and extracts
the unique psychological intelligence that source provides.

THE COOKIE-LESS TARGETING PUZZLE:
- Each extractor contributes a unique piece
- Combined, they enable precision targeting without tracking
- Serves DSP (demand), SSP (supply), and Agency layers

DATASET COVERAGE:
1. Google Local - Hyperlocal persuasion (666M reviews, 5M businesses)
2. Twitter Mental Health - Emotional state intelligence (11.8M tweets)
3. Yelp - Social influence layer (7M reviews, 2M users with social graph)
4. Amazon - Product/brand intelligence (1B reviews) [In amazon_ingestion]
5. Steam - Engagement depth psychology (48M reviews)
6. Sephora - Physical identity intelligence (1.1M reviews)
7. MovieLens - Content psychology (25M ratings, 1128 psychological tags)
8. Podcast - Audio content layer (5.6M reviews)
9. Airline - Service experience intelligence (140K reviews)
10. Automotive - Brand personality layer (227K reviews, 50 brands)
"""

from .. import DataSource

# Import extractors as they're built
try:
    from .google_local_extractor import GoogleLocalExtractor
except ImportError:
    GoogleLocalExtractor = None

try:
    from .twitter_mental_health_extractor import TwitterMentalHealthExtractor
except ImportError:
    TwitterMentalHealthExtractor = None

try:
    from .yelp_extractor import YelpExtractor
except ImportError:
    YelpExtractor = None


# Register all available extractors
EXTRACTORS = {}

if GoogleLocalExtractor:
    EXTRACTORS[DataSource.GOOGLE_LOCAL] = GoogleLocalExtractor

if TwitterMentalHealthExtractor:
    EXTRACTORS[DataSource.TWITTER_MENTAL_HEALTH] = TwitterMentalHealthExtractor

if YelpExtractor:
    EXTRACTORS[DataSource.YELP] = YelpExtractor


__all__ = [
    "GoogleLocalExtractor",
    "TwitterMentalHealthExtractor", 
    "YelpExtractor",
    "EXTRACTORS",
]
