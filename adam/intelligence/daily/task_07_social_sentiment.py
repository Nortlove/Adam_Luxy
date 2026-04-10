"""
Task 7: Social Sentiment Mechanism Signal Extraction
====================================================

Monitors Reddit and social platforms for category-relevant discussions
that reveal current mechanism receptivity.

A thread asking "what's everyone's holy grail moisturizer?" signals
high social_calibration and social_proof as the dominant mechanism.

Produces:
- CategorySocialPulse: dominant needs + mechanism preferences per category
- EmergingNeedSignal: newly elevated psychological needs

Consumed at bid time:
- Feeds Level 2 (Category Posterior) of the cascade. Social pulse
  blends with graph-derived priors to reflect what population is
  currently receptive to.

Redis keys:
- informativ:social:{category}:pulse — social pulse (24h TTL)
- informativ:social:{category}:mechanisms — peer mechanism effectiveness
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Category-to-subreddit mapping
_CATEGORY_SUBREDDITS = {
    "beauty": ["SkincareAddiction", "MakeupAddiction", "beauty", "AsianBeauty"],
    "electronics": ["gadgets", "technology", "buildapc", "hometheater"],
    "health": ["fitness", "nutrition", "loseit", "running", "yoga"],
    "fashion": ["femalefashionadvice", "malefashionadvice", "streetwear"],
    "finance": ["personalfinance", "investing", "financialindependence"],
    "home": ["HomeImprovement", "InteriorDesign", "DIY", "homeowners"],
    "automotive": ["cars", "whatcarshouldIbuy", "electricvehicles"],
    "food": ["cooking", "MealPrepSunday", "recipes", "food"],
    "travel": ["travel", "solotravel", "TravelHacks"],
    "gaming": ["gaming", "pcgaming", "PS5", "NintendoSwitch"],
}

# Need detection patterns in social discussion
_SOCIAL_NEED_PATTERNS = {
    "recommendation_seeking": ["recommend", "suggestion", "what should I", "best",
                                "holy grail", "favorite", "go-to", "worth it"],
    "problem_solving": ["help", "issue", "problem", "fix", "alternative",
                        "stopped working", "doesn't work", "disappointed"],
    "social_validation": ["anyone else", "is it just me", "thoughts on",
                          "what do you think", "should I", "opinions"],
    "deal_seeking": ["deal", "sale", "discount", "cheap", "budget",
                     "affordable", "coupon", "worth the price"],
    "expertise_seeking": ["expert", "professional", "experience with",
                          "how long", "which is better", "comparison"],
    "identity_expression": ["I love", "changed my life", "obsessed with",
                            "can't live without", "my routine", "my setup"],
}


class SocialSentimentTask(DailyStrengtheningTask):
    """Extract mechanism signals from social discussions."""

    @property
    def name(self) -> str:
        return "social_sentiment"

    @property
    def schedule_hours(self) -> List[int]:
        return [3]  # 3 AM UTC

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        for category, subreddits in _CATEGORY_SUBREDDITS.items():
            try:
                pulse = await self._analyze_category(category, subreddits)
                if pulse:
                    result.items_processed += pulse.get("posts_analyzed", 0)

                    # Store category pulse
                    pulse_key = f"informativ:social:{category}:pulse"
                    if self._store_redis_hash(pulse_key, pulse, ttl=86400):
                        result.items_stored += 1

                    # Store mechanism signals
                    if pulse.get("mechanism_preferences"):
                        mech_key = f"informativ:social:{category}:mechanisms"
                        if self._store_redis_hash(mech_key, {
                            "preferences": pulse["mechanism_preferences"],
                            "category": category,
                            "computed_at": time.time(),
                        }, ttl=86400):
                            result.items_stored += 1
            except Exception as e:
                result.errors += 1
                logger.debug("Social analysis failed for %s: %s", category, e)

        return result

    async def _analyze_category(
        self, category: str, subreddits: List[str],
    ) -> Dict[str, Any]:
        """Analyze social posts for a category."""
        posts = await self._fetch_reddit_posts(subreddits)
        if not posts:
            return {}

        # Aggregate NDF across all posts
        all_ndf_vectors = []
        need_counts: Dict[str, int] = {}
        mechanism_signals: Dict[str, List[float]] = {}

        for post in posts:
            text = post.get("text", "")
            if len(text) < 20:
                continue

            # NDF profile
            ndf = self._ndf_from_text(text)
            all_ndf_vectors.append(ndf)

            # Detect needs
            text_lower = text.lower()
            for need, patterns in _SOCIAL_NEED_PATTERNS.items():
                hits = sum(1 for p in patterns if p in text_lower)
                if hits >= 1:
                    need_counts[need] = need_counts.get(need, 0) + 1

            # Infer mechanism preferences from how people persuade each other
            mech = self._infer_peer_mechanisms(text_lower)
            for m, score in mech.items():
                if m not in mechanism_signals:
                    mechanism_signals[m] = []
                mechanism_signals[m].append(score)

        if not all_ndf_vectors:
            return {}

        # Compute centroid
        centroid = {}
        for dim in all_ndf_vectors[0].keys():
            values = [v.get(dim, 0.5) for v in all_ndf_vectors]
            centroid[dim] = round(sum(values) / len(values), 4)

        # Normalize need counts
        total_posts = len(posts)
        dominant_needs = {
            need: round(count / total_posts, 3)
            for need, count in sorted(need_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }

        # Average mechanism preferences
        mechanism_preferences = {
            mech: round(sum(scores) / len(scores), 3)
            for mech, scores in mechanism_signals.items()
        }

        return {
            "category": category,
            "ndf_centroid": centroid,
            "dominant_needs": dominant_needs,
            "mechanism_preferences": mechanism_preferences,
            "posts_analyzed": len(posts),
            "dominant_valence": "positive" if centroid.get("approach_avoidance", 0) > 0.1 else (
                "negative" if centroid.get("approach_avoidance", 0) < -0.1 else "neutral"
            ),
            "computed_at": time.time(),
        }

    def _infer_peer_mechanisms(self, text_lower: str) -> Dict[str, float]:
        """Infer which persuasion mechanisms peers use on each other."""
        mechanisms = {}

        # Social proof: "everyone uses", "popular", "recommended"
        sp_hits = sum(1 for w in ["everyone", "popular", "most people", "recommended",
                                    "reviews say", "rated", "best seller"] if w in text_lower)
        if sp_hits:
            mechanisms["social_proof"] = min(1.0, sp_hits * 0.3)

        # Authority: "expert says", "research shows", "dermatologist"
        auth_hits = sum(1 for w in ["expert", "research", "doctor", "professional",
                                     "study shows", "scientifically"] if w in text_lower)
        if auth_hits:
            mechanisms["authority"] = min(1.0, auth_hits * 0.3)

        # Scarcity: "sold out", "limited", "hard to find"
        sc_hits = sum(1 for w in ["sold out", "limited", "hard to find", "rare",
                                    "exclusive", "back in stock"] if w in text_lower)
        if sc_hits:
            mechanisms["scarcity"] = min(1.0, sc_hits * 0.3)

        # Liking: "love", "obsessed", "changed my life"
        like_hits = sum(1 for w in ["love", "obsessed", "amazing", "changed my life",
                                     "can't live without", "favorite"] if w in text_lower)
        if like_hits:
            mechanisms["liking"] = min(1.0, like_hits * 0.25)

        # Commitment: "been using for years", "loyal", "committed"
        commit_hits = sum(1 for w in ["been using", "years", "loyal", "committed",
                                       "long term", "stick with"] if w in text_lower)
        if commit_hits:
            mechanisms["commitment"] = min(1.0, commit_hits * 0.3)

        return mechanisms

    async def _fetch_reddit_posts(self, subreddits: List[str]) -> List[Dict[str, str]]:
        """Fetch top posts from subreddits using Reddit JSON API."""
        posts = []
        try:
            import httpx
        except ImportError:
            return posts

        async with httpx.AsyncClient(timeout=10) as client:
            for sub in subreddits[:3]:  # Rate limit
                try:
                    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
                    resp = await client.get(url, headers={
                        "User-Agent": "ADAM-Intelligence/1.0 (research)"
                    })
                    if resp.status_code == 200:
                        data = resp.json()
                        children = data.get("data", {}).get("children", [])
                        for child in children:
                            post_data = child.get("data", {})
                            title = post_data.get("title", "")
                            selftext = post_data.get("selftext", "")
                            text = f"{title} {selftext}".strip()
                            if len(text) > 20:
                                posts.append({
                                    "text": text[:2000],
                                    "subreddit": sub,
                                    "score": post_data.get("score", 0),
                                })
                except Exception as e:
                    logger.debug("Reddit fetch failed for r/%s: %s", sub, e)

                import asyncio
                await asyncio.sleep(2.0)  # Reddit rate limit

        return posts
