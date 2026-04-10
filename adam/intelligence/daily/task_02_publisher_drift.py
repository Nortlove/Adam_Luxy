"""
Task 2: Publisher Psychological Drift Monitor
=============================================

Monitors how publisher domains' psychological profiles shift over time.
News sites drift fast (daily); review sites drift slowly (weekly).

Produces:
- DomainPsychologicalDrift: NDF delta + drift velocity per domain
- DomainMindsetDistribution: mindset probability shifts

Consumed at bid time:
- When NYTimes drifts toward higher uncertainty_tolerance this week,
  mechanism adjustments for that domain shift: authority boosted,
  scarcity penalized. Flows into mechanism_adjustments on the profile.

Redis keys:
- informativ:page:drift:{domain} -- drift vector (24h TTL)
- informativ:page:centroid:{domain} -- current NDF centroid
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Top publisher domains to monitor (seed list; inventory tracker supplements)
_SEED_PUBLISHERS = [
    "cnn.com", "nytimes.com", "washingtonpost.com", "bbc.com", "foxnews.com",
    "nbcnews.com", "reuters.com", "apnews.com", "espn.com", "forbes.com",
    "techcrunch.com", "theverge.com", "wired.com", "webmd.com", "healthline.com",
    "allrecipes.com", "buzzfeed.com", "huffpost.com", "businessinsider.com",
    "cnbc.com", "wsj.com", "bloomberg.com", "people.com", "variety.com",
]

# 20 edge dimensions — same space as bilateral edges
EDGE_DIMENSIONS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire", "interoceptive_awareness",
    "cooperative_framing_fit", "decision_entropy",
]


class PublisherDriftTask(DailyStrengtheningTask):
    """Monitor publisher psychological profile drift."""

    @property
    def name(self) -> str:
        return "publisher_drift"

    @property
    def schedule_hours(self) -> List[int]:
        return [2]  # 2 AM UTC

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Get domains from inventory tracker + seed list
        domains = list(_SEED_PUBLISHERS)
        try:
            from adam.intelligence.page_intelligence import get_inventory_tracker
            tracker = get_inventory_tracker()
            top_domains = tracker.get_top_domains(n=200)
            for domain, _ in top_domains:
                if domain not in domains:
                    domains.append(domain)
        except Exception:
            pass

        domains = domains[:500]  # Cap at 500

        for domain in domains:
            try:
                await self._process_domain(domain, result)
            except Exception as e:
                result.errors += 1
                logger.debug("Drift check failed for %s: %s", domain, e)

        result.details["domains_checked"] = len(domains)
        return result

    async def _process_domain(self, domain: str, result: TaskResult) -> None:
        """Fetch domain content, compute NDF centroid, detect drift."""
        result.items_processed += 1

        # Fetch homepage + RSS/section pages
        texts = await self._fetch_domain_content(domain)
        if not texts:
            return

        # Compute current NDF centroid from all fetched pages
        edge_vectors = []
        mindsets = []
        for text in texts:
            ndf = self._extract_edge_dims(text["content"])
            if ndf:
                edge_vectors.append(ndf)
            from adam.intelligence.page_intelligence import profile_page_content
            profile = profile_page_content(url=f"https://{domain}/", text_content=text["content"])
            mindsets.append(profile.mindset)

        if not edge_vectors:
            return

        # Compute centroid
        current_centroid = {}
        for dim in EDGE_DIMENSIONS:
            values = [v.get(dim, 0.5) for v in edge_vectors]
            current_centroid[dim] = round(sum(values) / len(values), 4)

        # Load previous centroid
        prev_key = f"informativ:page:centroid:{domain}"
        prev_data = self._read_redis_hash(prev_key)

        drift_vector = {}
        drift_magnitude = 0.0
        flagged_dimensions = []

        if prev_data:
            for dim in EDGE_DIMENSIONS:
                prev_val = float(prev_data.get(dim, 0.5))
                curr_val = current_centroid.get(dim, 0.5)
                delta = curr_val - prev_val
                drift_vector[dim] = round(delta, 4)
                drift_magnitude += delta ** 2
                if abs(delta) > 0.3:
                    flagged_dimensions.append(dim)
            drift_magnitude = round(math.sqrt(drift_magnitude), 4)

        # Compute mindset distribution
        mindset_dist = {}
        for m in mindsets:
            mindset_dist[m] = mindset_dist.get(m, 0) + 1
        total_m = len(mindsets)
        mindset_dist = {k: round(v / total_m, 3) for k, v in mindset_dist.items()}

        # Store current centroid
        centroid_data = dict(current_centroid)
        centroid_data["computed_at"] = str(time.time())
        centroid_data["sample_size"] = str(len(edge_vectors))
        self._store_redis_hash(prev_key, centroid_data, ttl=86400 * 7)

        # Store drift data
        drift_data = {
            "domain": domain,
            "drift_vector": drift_vector,
            "drift_magnitude": drift_magnitude,
            "flagged_dimensions": flagged_dimensions,
            "mindset_distribution": mindset_dist,
            "sample_size": len(edge_vectors),
            "needs_deep_rescore": len(flagged_dimensions) > 0,
            "computed_at": time.time(),
        }
        drift_key = f"informativ:page:drift:{domain}"
        if self._store_redis_hash(drift_key, drift_data, ttl=86400):
            result.items_stored += 1

        if flagged_dimensions:
            logger.info(
                "DRIFT ALERT: %s shifted >0.3 in %s (magnitude=%.3f)",
                domain, flagged_dimensions, drift_magnitude,
            )

    async def _fetch_domain_content(self, domain: str) -> List[Dict[str, str]]:
        """Fetch homepage + section pages for a domain."""
        texts = []
        try:
            import httpx
        except ImportError:
            return texts

        sections = ["", "business", "technology", "sports", "entertainment", "health"]

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for section in sections[:4]:  # Limit to save time
                url = f"https://{domain}/{section}" if section else f"https://{domain}/"
                try:
                    resp = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    })
                    if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                        # Extract text content
                        from adam.intelligence.page_intelligence import _extract_domain
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(resp.text, "html.parser")
                            for tag in soup(["script", "style", "nav", "footer", "header"]):
                                tag.decompose()
                            main = soup.find("article") or soup.find("main") or soup.find("body")
                            text = main.get_text(separator=" ", strip=True) if main else ""
                            text = " ".join(text.split())[:8000]
                            if len(text.split()) > 30:
                                texts.append({"url": url, "content": text})
                        except ImportError:
                            pass
                except Exception:
                    pass

                # Rate limit between requests
                import asyncio
                await asyncio.sleep(1.0)

        return texts
