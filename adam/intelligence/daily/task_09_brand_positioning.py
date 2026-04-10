"""
Task 9: Brand Psychological Positioning Tracker
================================================

Crawls product pages and brand pages for top brands to understand
their psychological self-presentation and mechanism deployment.

Key insight: brands that deploy authority on their own pages respond
best to ad creatives that COMPLEMENT rather than REPEAT that mechanism.

Produces:
- BrandPsychologicalProfile: NDF vector, deployed mechanisms, voice
- BrandMechanismComplementMap: which ad mechanism complements the brand

Consumed at bid time:
- When generating creative for a brand, the complement map tells the
  system to use a DIFFERENT mechanism than the landing page.

Redis keys:
- informativ:brand:{brand_id}:profile — brand profile (7-day TTL)
- informativ:brand:{brand_id}:complement — complement map
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Top brands to track (expandable via inventory)
_TRACKED_BRANDS = {
    "nike": "https://www.nike.com",
    "apple": "https://www.apple.com",
    "amazon": "https://www.amazon.com",
    "samsung": "https://www.samsung.com",
    "target": "https://www.target.com",
    "walmart": "https://www.walmart.com",
    "sephora": "https://www.sephora.com",
    "bestbuy": "https://www.bestbuy.com",
    "homedepot": "https://www.homedepot.com",
    "nordstrom": "https://www.nordstrom.com",
    "ulta": "https://www.ulta.com",
    "costco": "https://www.costco.com",
    "macys": "https://www.macys.com",
    "kohls": "https://www.kohls.com",
    "wayfair": "https://www.wayfair.com",
    "chewy": "https://www.chewy.com",
    "rei": "https://www.rei.com",
    "lowes": "https://www.lowes.com",
    "gap": "https://www.gap.com",
    "adidas": "https://www.adidas.com",
}

# Mechanism complement pairs: which mechanisms enhance vs saturate each other
_COMPLEMENT_GRAPH = {
    "authority": ["social_proof", "reciprocity", "curiosity"],
    "social_proof": ["authority", "scarcity", "commitment"],
    "scarcity": ["social_proof", "loss_aversion", "curiosity"],
    "reciprocity": ["commitment", "liking", "authority"],
    "commitment": ["reciprocity", "authority", "social_proof"],
    "liking": ["social_proof", "reciprocity", "curiosity"],
    "loss_aversion": ["authority", "commitment", "scarcity"],
    "curiosity": ["authority", "social_proof", "scarcity"],
    "unity": ["social_proof", "liking", "commitment"],
    "cognitive_ease": ["liking", "social_proof", "reciprocity"],
}


class BrandPositioningTask(DailyStrengtheningTask):
    """Track brand psychological positioning for complement optimization."""

    @property
    def name(self) -> str:
        return "brand_positioning"

    @property
    def schedule_hours(self) -> List[int]:
        return [3]  # Weekly task runs at 3 AM

    @property
    def frequency_hours(self) -> int:
        return 168  # Weekly

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        for brand_id, brand_url in _TRACKED_BRANDS.items():
            try:
                profile = await self._profile_brand(brand_id, brand_url)
                if profile:
                    # Store brand profile
                    profile_key = f"informativ:brand:{brand_id}:profile"
                    if self._store_redis_hash(profile_key, profile, ttl=86400 * 7):
                        result.items_stored += 1

                    # Compute and store complement map
                    complement = self._compute_complement(profile)
                    comp_key = f"informativ:brand:{brand_id}:complement"
                    if self._store_redis_hash(comp_key, complement, ttl=86400 * 7):
                        result.items_stored += 1

                    result.items_processed += 1
            except Exception as e:
                result.errors += 1
                logger.debug("Brand profiling failed for %s: %s", brand_id, e)

        return result

    async def _profile_brand(self, brand_id: str, url: str) -> Dict[str, Any]:
        """Fetch and profile a brand's psychological positioning."""
        try:
            import httpx
        except ImportError:
            return {}

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                })
                if resp.status_code != 200:
                    return {}

                # Extract text content
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text = soup.get_text(separator=" ", strip=True)
                    text = " ".join(text.split())[:8000]
                except ImportError:
                    return {}

                if len(text.split()) < 30:
                    return {}

                # NDF profile
                ndf = self._ndf_from_text(text)

                # Detect mechanisms in brand copy
                from adam.intelligence.daily.task_01_competitive_intel import _detect_mechanisms
                mechanisms = _detect_mechanisms(text)

                # Determine dominant mechanism
                dominant_mech = max(mechanisms.items(), key=lambda x: x[1])[0] if mechanisms else "social_proof"

                # Voice analysis
                text_lower = text.lower()
                formality = 0.5
                if any(w in text_lower for w in ["we believe", "our mission", "our commitment"]):
                    formality = 0.7
                if any(w in text_lower for w in ["hey", "check out", "you'll love"]):
                    formality = 0.3

                return {
                    "brand_id": brand_id,
                    "ndf_vector": ndf,
                    "mechanism_deployment": mechanisms,
                    "dominant_mechanism": dominant_mech,
                    "voice_formality": round(formality, 2),
                    "voice_energy": round(ndf.get("arousal_seeking", 0.5), 2),
                    "voice_warmth": round(ndf.get("social_calibration", 0.5), 2),
                    "computed_at": time.time(),
                }
        except Exception as e:
            logger.debug("Brand fetch failed for %s: %s", brand_id, e)
            return {}

    def _compute_complement(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Compute the optimal ad mechanism complement for a brand.

        If the brand's page already hammers authority, the ad should use
        social_proof or reciprocity to complement rather than saturate.
        """
        mechanisms = profile.get("mechanism_deployment", {})
        dominant = profile.get("dominant_mechanism", "")

        # Find mechanisms NOT heavily used by the brand
        complement_candidates = _COMPLEMENT_GRAPH.get(dominant, [])

        # Rank by: high complement value × low brand usage
        ranked = []
        for candidate in complement_candidates:
            brand_usage = mechanisms.get(candidate, 0.0)
            complement_score = round(1.0 - brand_usage, 3)
            ranked.append((candidate, complement_score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        recommended = ranked[0][0] if ranked else "social_proof"

        return {
            "brand_id": profile.get("brand_id", ""),
            "brand_dominant_mechanism": dominant,
            "recommended_complement": recommended,
            "complement_ranking": {m: s for m, s in ranked[:5]},
            "avoid_mechanism": dominant,  # Don't repeat what brand page does
            "computed_at": time.time(),
        }
