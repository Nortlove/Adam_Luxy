"""
Task 1: Ad Creative Competitive Intelligence
=============================================

Crawls Meta Ad Library and Google Ads Transparency Center to understand
what psychological mechanisms competitors are deploying.

Produces:
- CategoryMechanismSaturation: fraction of ads using each mechanism per category
- CompetitorPsychologicalStrategy: per-advertiser NDF + mechanism portfolio

Consumed at bid time:
- Mechanism saturation creates a counter-cyclical advantage: if 80% of
  Beauty ads use social_proof, ADAM's marginal social_proof effectiveness
  drops -> system automatically diversifies to fresher mechanisms.

Redis keys:
- informativ:competitive:{category}:{mechanism} -- saturation scores (24h TTL)
- informativ:competitive:advertiser:{advertiser_id} -- strategy profiles
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Mechanism detection patterns in ad copy
_MECHANISM_PATTERNS = {
    "social_proof": [
        r"\b\d+[,.]?\d*\s*(million|thousand|customers|users|people|reviews|ratings)\b",
        r"\bbest\s*sell", r"\bmost\s*popular\b", r"\beveryone\b", r"\btrending\b",
        r"\b#1\b", r"\btop\s*rated\b", r"\btrusted\s*by\b",
    ],
    "scarcity": [
        r"\blimited\b", r"\bonly\s*\d+\s*left\b", r"\bexpires?\b", r"\bending\s*soon\b",
        r"\bwhile\s*supplies\b", r"\bexclusive\b", r"\bdon'?t\s*miss\b",
        r"\blast\s*chance\b", r"\bhurry\b",
    ],
    "authority": [
        r"\bexpert\b", r"\bclinically?\b", r"\bscientifically\b", r"\bproven\b",
        r"\bcertified\b", r"\brecommended\s*by\b", r"\bdoctor\b", r"\bstud(y|ies)\b",
        r"\bpatented\b", r"\baward\b",
    ],
    "reciprocity": [
        r"\bfree\b", r"\bbonus\b", r"\bgift\b", r"\bcomplimentary\b",
        r"\bno\s*cost\b", r"\btrial\b", r"\bsample\b",
    ],
    "commitment": [
        r"\bguarantee\b", r"\bmoney\s*back\b", r"\brisk\s*free\b",
        r"\bcancel\s*any\s*time\b", r"\bno\s*commitment\b",
    ],
    "liking": [
        r"\byou\b", r"\byour\b", r"\bpersonaliz", r"\bcustom\b",
        r"\bmade\s*for\s*you\b", r"\btailored\b",
    ],
    "loss_aversion": [
        r"\bdon'?t\s*lose\b", r"\bmissing\s*out\b", r"\bprotect\b",
        r"\bavoid\b", r"\brisk\b", r"\bbefore\s*it'?s\s*too\s*late\b",
    ],
    "curiosity": [
        r"\bdiscover\b", r"\bsecret\b", r"\breveal\b", r"\bfind\s*out\b",
        r"\bsurpris", r"\bunlock\b", r"\bhidden\b",
    ],
}

# IAB categories to product category mapping
_IAB_TO_CATEGORY = {
    "IAB1": "arts_entertainment", "IAB2": "automotive", "IAB3": "business",
    "IAB4": "careers", "IAB5": "education", "IAB6": "family_parenting",
    "IAB7": "health_fitness", "IAB8": "food_drink", "IAB9": "hobbies",
    "IAB10": "home_garden", "IAB13": "personal_finance", "IAB14": "society",
    "IAB15": "science", "IAB17": "sports", "IAB18": "style_fashion",
    "IAB19": "technology", "IAB22": "shopping",
}


def _detect_mechanisms(text: str) -> Dict[str, float]:
    """Detect persuasion mechanisms in ad copy. Returns mechanism -> confidence."""
    text_lower = text.lower()
    results = {}
    for mechanism, patterns in _MECHANISM_PATTERNS.items():
        hits = sum(1 for p in patterns if re.search(p, text_lower))
        if hits > 0:
            results[mechanism] = min(1.0, hits / len(patterns) * 2.0)
    return results


class CompetitiveIntelligenceTask(DailyStrengtheningTask):
    """Crawl ad libraries for competitive mechanism intelligence."""

    @property
    def name(self) -> str:
        return "competitive_intelligence"

    @property
    def schedule_hours(self) -> List[int]:
        return [2, 8, 14, 20]  # Every 6 hours

    @property
    def frequency_hours(self) -> int:
        return 6

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Fetch ad creatives from Meta Ad Library
        creatives = await self._fetch_meta_ad_library()
        # Fetch from Google Ads Transparency
        creatives.extend(await self._fetch_google_transparency())

        if not creatives:
            result.details["note"] = "No creatives fetched (API unavailable or rate limited)"
            return result

        # Process: extract mechanism deployment per creative
        category_mechanism_counts: Dict[str, Dict[str, int]] = {}
        category_totals: Dict[str, int] = {}
        advertiser_profiles: Dict[str, Dict[str, Any]] = {}

        for creative in creatives:
            result.items_processed += 1
            text = creative.get("text", "")
            category = creative.get("category", "general")
            advertiser = creative.get("advertiser_id", "")

            if not text:
                continue

            # NDF-profile the ad copy
            ndf = self._ndf_from_text(text)

            # Detect mechanisms deployed
            mechanisms = _detect_mechanisms(text)

            # Aggregate by category
            if category not in category_mechanism_counts:
                category_mechanism_counts[category] = {}
                category_totals[category] = 0
            category_totals[category] += 1
            for mech, score in mechanisms.items():
                if score > 0.3:  # Confident detection
                    category_mechanism_counts[category][mech] = (
                        category_mechanism_counts[category].get(mech, 0) + 1
                    )

            # Track per-advertiser strategy
            if advertiser:
                if advertiser not in advertiser_profiles:
                    advertiser_profiles[advertiser] = {
                        "ndf_sum": {k: 0.0 for k in ndf},
                        "mechanism_counts": {},
                        "creative_count": 0,
                    }
                ap = advertiser_profiles[advertiser]
                ap["creative_count"] += 1
                for k, v in ndf.items():
                    ap["ndf_sum"][k] += v
                for mech, score in mechanisms.items():
                    ap["mechanism_counts"][mech] = ap["mechanism_counts"].get(mech, 0) + 1

        # Store category-level mechanism saturation
        for category, mech_counts in category_mechanism_counts.items():
            total = max(1, category_totals.get(category, 1))
            for mechanism, count in mech_counts.items():
                saturation = count / total
                key = f"informativ:competitive:{category}:{mechanism}"
                stored = self._store_redis_hash(key, {
                    "saturation": round(saturation, 3),
                    "sample_size": total,
                    "mechanism": mechanism,
                    "category": category,
                    "computed_at": __import__("time").time(),
                }, ttl=86400)
                if stored:
                    result.items_stored += 1

        # Store advertiser profiles
        for adv_id, profile in advertiser_profiles.items():
            n = max(1, profile["creative_count"])
            avg_ndf = {k: round(v / n, 3) for k, v in profile["ndf_sum"].items()}
            key = f"informativ:competitive:advertiser:{adv_id}"
            stored = self._store_redis_hash(key, {
                "ndf_vector": avg_ndf,
                "mechanism_portfolio": profile["mechanism_counts"],
                "creative_count": n,
                "computed_at": __import__("time").time(),
            }, ttl=86400 * 3)
            if stored:
                result.items_stored += 1

        result.details["categories_analyzed"] = len(category_mechanism_counts)
        result.details["advertisers_profiled"] = len(advertiser_profiles)
        return result

    async def _fetch_meta_ad_library(self) -> List[Dict[str, Any]]:
        """Fetch active ads from Meta Ad Library API.

        Uses the Meta Ad Library API (requires access token).
        Falls back to HTML scraping if API unavailable.
        """
        creatives = []
        try:
            import httpx
        except ImportError:
            return creatives

        # Categories to monitor
        search_terms = [
            "skincare", "insurance", "credit card", "mattress", "meal kit",
            "fitness", "investing", "fashion", "supplements", "software",
        ]

        for term in search_terms[:5]:  # Rate limit awareness
            try:
                # Meta Ad Library search page (public, no API key needed)
                url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q={term}&media_type=all"
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    })
                    if resp.status_code == 200:
                        # Extract ad text from HTML (basic extraction)
                        text = resp.text
                        # Find ad copy blocks -- Meta renders these in specific div patterns
                        import re
                        ad_texts = re.findall(
                            r'"(?:ad_creative_body|message)"\s*:\s*"([^"]{20,500})"',
                            text,
                        )
                        for ad_text in ad_texts[:20]:  # Cap per term
                            creatives.append({
                                "text": ad_text.replace("\\n", " ").replace('\\"', '"'),
                                "category": term,
                                "advertiser_id": f"meta_{term}",
                                "source": "meta_ad_library",
                            })
            except Exception as e:
                logger.debug("Meta Ad Library fetch failed for '%s': %s", term, e)

        return creatives

    async def _fetch_google_transparency(self) -> List[Dict[str, Any]]:
        """Fetch ads from Google Ads Transparency Center.

        The Transparency Center is public and requires no API key.
        """
        creatives = []
        try:
            import httpx
        except ImportError:
            return creatives

        # Known major advertisers to track
        advertisers = [
            "Amazon", "Apple", "Nike", "Geico", "Progressive",
            "Samsung", "Target", "Walmart", "Google", "Microsoft",
        ]

        for advertiser in advertisers[:5]:  # Rate limit
            try:
                url = f"https://adstransparency.google.com/advertiser/{advertiser}"
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    })
                    if resp.status_code == 200:
                        # Extract ad text patterns from response
                        import re
                        ad_texts = re.findall(
                            r'(?:"text"|"headline"|"description")\s*:\s*"([^"]{15,300})"',
                            resp.text,
                        )
                        for ad_text in ad_texts[:10]:
                            creatives.append({
                                "text": ad_text,
                                "category": "general",
                                "advertiser_id": f"google_{advertiser.lower()}",
                                "source": "google_transparency",
                            })
            except Exception as e:
                logger.debug("Google Transparency fetch failed for '%s': %s", advertiser, e)

        return creatives
