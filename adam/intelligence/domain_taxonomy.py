"""
Domain Taxonomy & Hierarchical Psychological Intelligence
==========================================================

Instead of scoring every page individually (impossible at scale), this
module builds a hierarchical taxonomy per publisher domain and learns
edge-dimension patterns at each level (20-dim, same space as bilateral edges):

    Domain → Category → Subcategory → Author → Article

When an unscored article arrives, the system rolls up to the nearest
level with sufficient data:

    1. Check exact URL → profile exists? Use it. (conf 0.8+)
    2. Check author × category → author edge fingerprint? Blend. (conf 0.7)
    3. Check subcategory → subcategory edge centroid? Use it. (conf 0.6)
    4. Check category → category edge centroid? Use it. (conf 0.5)
    5. Check domain → domain edge centroid? Use it. (conf 0.3)

Each level narrows the prediction. CNN/Politics articles have different
edge profiles from CNN/Entertainment. Within Politics, articles by
Author X have a consistently different tone than Author Y.

The taxonomy is LEARNED, not hardcoded. The system extracts category
structure from URL paths + HTML structured data (JSON-LD, meta tags,
breadcrumbs), then accumulates edge-dimension observations at each
level until statistical patterns emerge.

Storage:
    informativ:taxonomy:{domain}                       → domain config + category list
    informativ:taxonomy:{domain}:cat:{category}        → category edge centroid
    informativ:taxonomy:{domain}:sub:{cat}/{subcat}    → subcategory edge centroid
    informativ:taxonomy:{domain}:author:{author_slug}  → author edge fingerprint
    informativ:taxonomy:{domain}:patterns              → learned patterns + consistency scores
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# The 20 edge dimensions — same space as BRAND_CONVERTED bilateral edges.
# NDF (7 dims) is NO LONGER used. All centroids stored in edge space.
EDGE_DIMENSIONS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire", "interoceptive_awareness",
    "cooperative_framing_fit", "decision_entropy",
]

_REDIS_PREFIX = "informativ:taxonomy:"
_TAXONOMY_TTL = 86400 * 14  # 14 days


# ============================================================================
# ARTICLE METADATA — what we extract from each scored page
# ============================================================================

@dataclass
class ArticleMetadata:
    """Structured metadata extracted from an article page."""

    url: str = ""
    domain: str = ""
    category: str = ""             # e.g., "politics", "business", "health"
    subcategory: str = ""          # e.g., "congress", "markets", "life-but-better"
    title: str = ""
    authors: List[str] = field(default_factory=list)
    date_published: str = ""
    keywords: List[str] = field(default_factory=list)
    content_type: str = ""         # news, opinion, review, sponsored, etc.
    word_count: int = 0

    edge_dimensions: Dict[str, float] = field(default_factory=dict)
    """Full 20-dim edge profile in same space as bilateral edges."""

    # Legacy NDF — kept for backward compatibility only
    ndf_vector: Dict[str, float] = field(default_factory=dict)
    mechanism_adjustments: Dict[str, float] = field(default_factory=dict)
    mindset: str = ""
    confidence: float = 0.0

    @property
    def author_slug(self) -> str:
        """Normalized author identifier for consistent keying."""
        if not self.authors:
            return ""
        # Use first author, normalize to slug
        name = self.authors[0].lower().strip()
        name = re.sub(r"[^a-z0-9\s]", "", name)
        return re.sub(r"\s+", "_", name).strip("_")

    @property
    def taxonomy_path(self) -> str:
        """Full taxonomy path: domain/category/subcategory."""
        parts = [self.domain]
        if self.category:
            parts.append(self.category)
        if self.subcategory:
            parts.append(self.subcategory)
        return "/".join(parts)


# ============================================================================
# METADATA EXTRACTION — pull article metadata from HTML
# ============================================================================

def extract_article_metadata(url: str, html: str) -> ArticleMetadata:
    """Extract structured article metadata from HTML.

    Uses multiple signals in priority order:
    1. JSON-LD structured data (most reliable)
    2. OpenGraph / meta tags
    3. URL path parsing (fallback)
    4. HTML heading/byline patterns
    """
    meta = ArticleMetadata(url=url)

    # Domain from URL
    from adam.intelligence.page_intelligence import _extract_domain
    meta.domain = _extract_domain(url) or ""

    # Category from URL path
    _extract_category_from_url(url, meta)

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
    except ImportError:
        return meta

    # ── JSON-LD Structured Data (highest quality) ──
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = next((d for d in data if isinstance(d, dict)
                             and d.get("@type") in (
                                 "NewsArticle", "Article", "ReportageNewsArticle",
                                 "BlogPosting", "Review", "OpinionNewsArticle",
                             )), None)
                if not data:
                    continue
            if not isinstance(data, dict):
                continue

            schema_type = data.get("@type", "")
            if schema_type not in (
                "NewsArticle", "Article", "ReportageNewsArticle",
                "BlogPosting", "Review", "OpinionNewsArticle",
            ):
                continue

            # Title
            meta.title = meta.title or data.get("headline", "")

            # Authors
            if not meta.authors:
                author_data = data.get("author", [])
                if isinstance(author_data, dict):
                    author_data = [author_data]
                if isinstance(author_data, list):
                    for a in author_data:
                        if isinstance(a, dict):
                            name = a.get("name", "")
                            if name:
                                meta.authors.append(name)
                        elif isinstance(a, str):
                            meta.authors.append(a)

            # Section/Category from structured data
            section = data.get("articleSection", "")
            if section and not meta.category:
                if isinstance(section, list):
                    section = section[0] if section else ""
                meta.category = _normalize_category(str(section))

            # Date
            meta.date_published = meta.date_published or data.get("datePublished", "")

            # Keywords
            keywords = data.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",")]
            if isinstance(keywords, list):
                meta.keywords = keywords[:20]

            # Content type from schema
            if schema_type == "OpinionNewsArticle":
                meta.content_type = "opinion"
            elif schema_type == "Review":
                meta.content_type = "review"
            elif schema_type == "ReportageNewsArticle":
                meta.content_type = "reportage"
            elif "sponsored" in str(data.get("isPartOf", "")).lower():
                meta.content_type = "sponsored"
            else:
                meta.content_type = "news"

        except (json.JSONDecodeError, TypeError, StopIteration):
            continue

    # ── Meta Tags (fallback) ──
    if not meta.title:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            meta.title = og_title["content"]
        elif soup.title and soup.title.string:
            meta.title = soup.title.string.strip()

    if not meta.authors:
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            # Handle "By Author Name" or "Author1 and Author2"
            author_str = author_meta["content"]
            author_str = re.sub(r"^by\s+", "", author_str, flags=re.IGNORECASE)
            meta.authors = [a.strip() for a in re.split(r"\s+and\s+|,\s*", author_str)
                           if a.strip()]

    if not meta.category:
        section_meta = soup.find("meta", attrs={"name": "article:section"})
        if not section_meta:
            section_meta = soup.find("meta", property="article:section")
        if section_meta and section_meta.get("content"):
            meta.category = _normalize_category(section_meta["content"])

    if not meta.keywords:
        kw_meta = soup.find("meta", attrs={"name": "news_keywords"})
        if not kw_meta:
            kw_meta = soup.find("meta", attrs={"name": "keywords"})
        if kw_meta and kw_meta.get("content"):
            meta.keywords = [k.strip() for k in kw_meta["content"].split(",")][:20]

    # ── Byline from HTML (last resort for authors) ──
    if not meta.authors:
        byline = (
            soup.find(class_=re.compile(r"byline|author", re.I))
            or soup.find("address")
            or soup.find(attrs={"rel": "author"})
        )
        if byline:
            text = byline.get_text(strip=True)
            text = re.sub(r"^by\s+", "", text, flags=re.IGNORECASE)
            if len(text) < 100:  # Sanity check — not a whole paragraph
                meta.authors = [a.strip() for a in re.split(r"\s+and\s+|,\s*", text)
                               if a.strip() and len(a.strip()) > 2]

    # ── Breadcrumb for subcategory ──
    if not meta.subcategory:
        breadcrumb = soup.find("nav", attrs={"aria-label": re.compile(r"breadcrumb", re.I)})
        if not breadcrumb:
            breadcrumb = soup.find(class_=re.compile(r"breadcrumb", re.I))
        if breadcrumb:
            crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
            if len(crumbs) >= 3:
                # Typically: Home > Category > Subcategory
                meta.subcategory = _normalize_category(crumbs[-1])
                if not meta.category:
                    meta.category = _normalize_category(crumbs[-2])

    # ── Word count ──
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.find("body")
    if main:
        text = main.get_text(separator=" ", strip=True)
        meta.word_count = len(text.split())

    return meta


def _extract_category_from_url(url: str, meta: ArticleMetadata) -> None:
    """Extract category and subcategory from URL path structure.

    Common patterns:
        /politics/congress/article-slug → cat=politics, sub=congress
        /2026/03/19/business/article-slug → cat=business
        /sport/football/article-slug → cat=sport, sub=football
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")
    except Exception:
        return

    parts = path.split("/")
    if not parts:
        return

    # Skip date segments (2026, 03, 19)
    content_parts = [p for p in parts if not re.match(r"^\d{1,4}$", p)]

    # Known top-level category names (common across publishers)
    _KNOWN_CATEGORIES = {
        "us", "world", "politics", "business", "health", "entertainment",
        "style", "travel", "sports", "sport", "science", "climate",
        "weather", "technology", "tech", "opinion", "lifestyle", "food",
        "money", "media", "culture", "arts", "education", "real-estate",
        "autos", "markets", "economy", "personal-finance", "investing",
    }

    for i, part in enumerate(content_parts):
        part_lower = part.lower()
        if part_lower in _KNOWN_CATEGORIES:
            meta.category = meta.category or _normalize_category(part_lower)
            # Next non-date segment might be subcategory
            if i + 1 < len(content_parts):
                next_part = content_parts[i + 1]
                # If it's short and not the article slug, it's likely a subcategory
                if len(next_part) < 30 and not re.match(r".*-.*-.*-.*", next_part):
                    meta.subcategory = meta.subcategory or _normalize_category(next_part)
            break


def _normalize_category(raw: str) -> str:
    """Normalize category name to consistent format."""
    normalized = raw.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s_-]", "", normalized)
    normalized = re.sub(r"[\s-]+", "_", normalized)
    return normalized


# ============================================================================
# DOMAIN TAXONOMY — hierarchical NDF model per publisher
# ============================================================================

class DomainTaxonomy:
    """Hierarchical psychological model for a publisher domain.

    Maintains 20-dim edge centroids and consistency scores at each level:
    - Domain level: overall psychological fingerprint
    - Category level: per-section psychological shift
    - Subcategory level: finer-grained refinement
    - Author level: writer-specific voice/tone fingerprint

    Consistency scores (0-1) indicate how predictable the edge profile is
    at each level. High consistency = reliable prior for unscored articles.
    """

    def __init__(self, domain: str):
        self.domain = domain
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.Redis(
                host="localhost", port=6379, decode_responses=True,
            )
            self._redis.ping()
            return self._redis
        except Exception:
            return None

    # ── Observation Recording ──────────────────────────────────────

    def record_article(self, meta: ArticleMetadata) -> Dict[str, Any]:
        """Record a scored article's edge dimensions into the taxonomy.

        This is called after every article is profiled. It updates
        the running centroids and consistency scores at each level.
        """
        # Prefer edge dimensions (20-dim); fall back to NDF (7-dim) if needed
        dims_to_record = meta.edge_dimensions if meta.edge_dimensions else meta.ndf_vector
        if not dims_to_record:
            return {"recorded": False, "reason": "no edge dimensions or NDF vector"}

        updates = {}

        # Update domain centroid
        updates["domain"] = self._update_centroid(
            f"{_REDIS_PREFIX}{self.domain}",
            dims_to_record,
            meta.mechanism_adjustments,
            meta.mindset,
        )

        # Update category centroid
        if meta.category:
            updates["category"] = self._update_centroid(
                f"{_REDIS_PREFIX}{self.domain}:cat:{meta.category}",
                dims_to_record,
                meta.mechanism_adjustments,
                meta.mindset,
            )

        # Update subcategory centroid
        if meta.category and meta.subcategory:
            subkey = f"{meta.category}/{meta.subcategory}"
            updates["subcategory"] = self._update_centroid(
                f"{_REDIS_PREFIX}{self.domain}:sub:{subkey}",
                dims_to_record,
                meta.mechanism_adjustments,
                meta.mindset,
            )

        # Update author fingerprint
        if meta.author_slug:
            updates["author"] = self._update_centroid(
                f"{_REDIS_PREFIX}{self.domain}:author:{meta.author_slug}",
                dims_to_record,
                meta.mechanism_adjustments,
                meta.mindset,
                extra={"author_name": meta.authors[0] if meta.authors else ""},
            )

        # Update domain category list
        self._update_category_list(meta)

        return {"recorded": True, "updates": updates}

    def _update_centroid(
        self,
        key: str,
        ndf: Dict[str, float],
        mechanisms: Dict[str, float],
        mindset: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update running edge centroid using Welford's online algorithm.

        Tracks:
        - Running mean (centroid) per edge dimension
        - Running variance (consistency) per dimension
        - Observation count
        - Mindset distribution
        """
        r = self._get_redis()
        if not r:
            return {"stored": False}

        try:
            # Read existing state
            existing = r.hgetall(key)
            n = int(existing.get("observation_count", 0))

            # Current centroid
            centroid = {}
            variance_sum = {}
            for dim in EDGE_DIMENSIONS:
                centroid[dim] = float(existing.get(f"centroid_{dim}", 0.5))
                variance_sum[dim] = float(existing.get(f"variance_sum_{dim}", 0.0))

            # Welford's update
            n += 1
            new_centroid = {}
            new_variance_sum = {}
            for dim in EDGE_DIMENSIONS:
                x = ndf.get(dim, 0.5)
                old_mean = centroid[dim]
                new_mean = old_mean + (x - old_mean) / n
                new_centroid[dim] = round(new_mean, 5)
                # M2 update for variance
                new_variance_sum[dim] = round(
                    variance_sum[dim] + (x - old_mean) * (x - new_mean), 6
                )

            # Mechanism centroid (simple running average)
            mech_centroid = {}
            for mech, val in mechanisms.items():
                old_val = float(existing.get(f"mech_{mech}", val))
                mech_centroid[mech] = round(old_val + (val - old_val) / n, 4)

            # Mindset distribution
            mindset_dist_raw = existing.get("mindset_distribution", "{}")
            try:
                mindset_dist = json.loads(mindset_dist_raw)
            except (json.JSONDecodeError, TypeError):
                mindset_dist = {}
            mindset_dist[mindset] = mindset_dist.get(mindset, 0) + 1

            # Compute consistency scores (1 - normalized std dev)
            consistency = {}
            for dim in EDGE_DIMENSIONS:
                if n >= 3:
                    var = new_variance_sum[dim] / (n - 1)
                    std = math.sqrt(max(0, var))
                    # Edge dim range is roughly [0, 1], so std > 0.3 is high variance
                    consistency[dim] = round(max(0.0, 1.0 - std * 3.0), 3)
                else:
                    consistency[dim] = 0.5  # Not enough data

            # Overall consistency = mean of dimension consistencies
            overall_consistency = round(
                sum(consistency.values()) / len(consistency), 3
            ) if consistency else 0.5

            # Build storage dict
            store = {
                "domain": self.domain,
                "observation_count": n,
                "overall_consistency": overall_consistency,
                "mindset_distribution": json.dumps(mindset_dist),
                "updated_at": time.time(),
            }
            for dim in EDGE_DIMENSIONS:
                store[f"centroid_{dim}"] = new_centroid[dim]
                store[f"variance_sum_{dim}"] = new_variance_sum[dim]
                store[f"consistency_{dim}"] = consistency[dim]
            for mech, val in mech_centroid.items():
                store[f"mech_{mech}"] = val
            if extra:
                for k, v in extra.items():
                    store[k] = v

            r.hset(key, mapping=store)
            r.expire(key, _TAXONOMY_TTL)

            return {
                "stored": True,
                "observation_count": n,
                "consistency": overall_consistency,
            }

        except Exception as e:
            logger.debug("Centroid update failed for %s: %s", key, e)
            return {"stored": False, "error": str(e)}

    def _update_category_list(self, meta: ArticleMetadata) -> None:
        """Maintain the list of known categories for this domain."""
        r = self._get_redis()
        if not r or not meta.category:
            return

        key = f"{_REDIS_PREFIX}{self.domain}"
        try:
            existing = r.hget(key, "categories")
            cats = set()
            if existing:
                try:
                    cats = set(json.loads(existing))
                except (json.JSONDecodeError, TypeError):
                    pass
            cats.add(meta.category)
            if meta.subcategory:
                cats.add(f"{meta.category}/{meta.subcategory}")
            r.hset(key, "categories", json.dumps(sorted(cats)))

            # Track authors
            if meta.author_slug:
                existing_authors = r.hget(key, "authors")
                authors = set()
                if existing_authors:
                    try:
                        authors = set(json.loads(existing_authors))
                    except (json.JSONDecodeError, TypeError):
                        pass
                authors.add(meta.author_slug)
                r.hset(key, "authors", json.dumps(sorted(list(authors)[:200])))

        except Exception:
            pass

    # ── Inference (Bid-Time Lookup) ────────────────────────────────

    def infer_psychology(
        self,
        url: str,
        category: str = "",
        subcategory: str = "",
        author: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Infer psychological profile for an unscored article.

        Hierarchical fallback:
        1. Author × Category (if both known) → blend author + category
        2. Subcategory → subcategory centroid
        3. Category → category centroid
        4. Domain → domain centroid

        Returns edge dimensions, mechanism adjustments, confidence, and
        the taxonomy level used for inference.
        """
        r = self._get_redis()
        if not r:
            return None

        # Normalize inputs
        if not category:
            meta = ArticleMetadata(url=url)
            _extract_category_from_url(url, meta)
            category = meta.category
            subcategory = meta.subcategory

        author_slug = ""
        if author:
            author_slug = re.sub(r"[^a-z0-9\s]", "", author.lower())
            author_slug = re.sub(r"\s+", "_", author_slug).strip("_")

        # Level 1: Author × Category blend
        if author_slug and category:
            author_data = self._read_centroid(
                f"{_REDIS_PREFIX}{self.domain}:author:{author_slug}"
            )
            cat_data = self._read_centroid(
                f"{_REDIS_PREFIX}{self.domain}:cat:{category}"
            )
            if author_data and cat_data:
                # Blend: 60% author (voice), 40% category (topic)
                blended = self._blend_centroids(author_data, cat_data, 0.6, 0.4)
                blended["inference_level"] = "author_x_category"
                blended["confidence"] = min(0.75,
                    0.4 * author_data.get("consistency", 0.5)
                    + 0.3 * cat_data.get("consistency", 0.5)
                    + 0.05 * min(1.0, author_data.get("observations", 0) / 10)
                    + 0.05 * min(1.0, cat_data.get("observations", 0) / 20)
                )
                return blended

        # Level 2: Subcategory
        if category and subcategory:
            subkey = f"{category}/{subcategory}"
            sub_data = self._read_centroid(
                f"{_REDIS_PREFIX}{self.domain}:sub:{subkey}"
            )
            if sub_data and sub_data.get("observations", 0) >= 3:
                sub_data["inference_level"] = "subcategory"
                sub_data["confidence"] = min(0.65,
                    0.5 * sub_data.get("consistency", 0.5)
                    + 0.15 * min(1.0, sub_data.get("observations", 0) / 10)
                )
                return sub_data

        # Level 3: Category
        if category:
            cat_data = self._read_centroid(
                f"{_REDIS_PREFIX}{self.domain}:cat:{category}"
            )
            if cat_data and cat_data.get("observations", 0) >= 3:
                cat_data["inference_level"] = "category"
                cat_data["confidence"] = min(0.55,
                    0.4 * cat_data.get("consistency", 0.5)
                    + 0.15 * min(1.0, cat_data.get("observations", 0) / 20)
                )
                return cat_data

        # Level 4: Domain
        domain_data = self._read_centroid(f"{_REDIS_PREFIX}{self.domain}")
        if domain_data and domain_data.get("observations", 0) >= 3:
            domain_data["inference_level"] = "domain"
            domain_data["confidence"] = min(0.35,
                0.3 * domain_data.get("consistency", 0.5)
                + 0.05 * min(1.0, domain_data.get("observations", 0) / 50)
            )
            return domain_data

        return None

    def _read_centroid(self, key: str) -> Optional[Dict[str, Any]]:
        """Read a centroid from Redis and unpack into usable format."""
        r = self._get_redis()
        if not r:
            return None

        try:
            data = r.hgetall(key)
            if not data or "observation_count" not in data:
                return None

            n = int(data.get("observation_count", 0))
            if n == 0:
                return None

            edge_dims = {}
            consistency_scores = {}
            for dim in EDGE_DIMENSIONS:
                edge_dims[dim] = float(data.get(f"centroid_{dim}", 0.5))
                consistency_scores[dim] = float(data.get(f"consistency_{dim}", 0.5))

            mechanisms = {}
            for k, v in data.items():
                if k.startswith("mech_"):
                    mechanisms[k[5:]] = float(v)

            mindset_dist = {}
            try:
                mindset_dist = json.loads(data.get("mindset_distribution", "{}"))
            except (json.JSONDecodeError, TypeError):
                pass

            # Dominant mindset
            dominant_mindset = max(mindset_dist, key=mindset_dist.get) if mindset_dist else "unknown"

            overall_consistency = float(data.get("overall_consistency", 0.5))

            return {
                "edge_dimensions": edge_dims,
                "mechanism_adjustments": mechanisms,
                "mindset": dominant_mindset,
                "mindset_distribution": mindset_dist,
                "consistency": overall_consistency,
                "consistency_per_dim": consistency_scores,
                "observations": n,
            }

        except Exception as e:
            logger.debug("Centroid read failed for %s: %s", key, e)
            return None

    def _blend_centroids(
        self,
        a: Dict[str, Any],
        b: Dict[str, Any],
        weight_a: float,
        weight_b: float,
    ) -> Dict[str, Any]:
        """Blend two centroids with given weights."""
        blended_dims = {}
        for dim in EDGE_DIMENSIONS:
            va = a.get("edge_dimensions", {}).get(dim, 0.5)
            vb = b.get("edge_dimensions", {}).get(dim, 0.5)
            blended_dims[dim] = round(va * weight_a + vb * weight_b, 4)

        mechanisms = {}
        all_mechs = set(
            list(a.get("mechanism_adjustments", {}).keys())
            + list(b.get("mechanism_adjustments", {}).keys())
        )
        for mech in all_mechs:
            va = a.get("mechanism_adjustments", {}).get(mech, 1.0)
            vb = b.get("mechanism_adjustments", {}).get(mech, 1.0)
            mechanisms[mech] = round(va * weight_a + vb * weight_b, 4)

        return {
            "edge_dimensions": blended_dims,
            "mechanism_adjustments": mechanisms,
            "mindset": a.get("mindset", b.get("mindset", "unknown")),
            "observations": a.get("observations", 0) + b.get("observations", 0),
            "consistency": round(
                a.get("consistency", 0.5) * weight_a
                + b.get("consistency", 0.5) * weight_b,
                3,
            ),
        }

    # ── Taxonomy Report ────────────────────────────────────────────

    def get_taxonomy_report(self) -> Dict[str, Any]:
        """Get a full report of the learned taxonomy for this domain."""
        r = self._get_redis()
        if not r:
            return {"domain": self.domain, "error": "Redis unavailable"}

        report = {
            "domain": self.domain,
            "categories": [],
            "authors": [],
            "total_observations": 0,
            "overall_consistency": 0.0,
        }

        # Domain level
        domain_data = self._read_centroid(f"{_REDIS_PREFIX}{self.domain}")
        if domain_data:
            report["total_observations"] = domain_data.get("observations", 0)
            report["overall_consistency"] = domain_data.get("consistency", 0.0)
            report["domain_edge_dimensions"] = domain_data.get("edge_dimensions", {})
            report["dominant_mindset"] = domain_data.get("mindset", "")

        # Categories
        try:
            cats_raw = r.hget(f"{_REDIS_PREFIX}{self.domain}", "categories")
            if cats_raw:
                cats = json.loads(cats_raw)
                for cat in cats:
                    if "/" in cat:
                        continue  # Skip subcategories in this list
                    cat_data = self._read_centroid(
                        f"{_REDIS_PREFIX}{self.domain}:cat:{cat}"
                    )
                    if cat_data:
                        report["categories"].append({
                            "name": cat,
                            "observations": cat_data.get("observations", 0),
                            "consistency": cat_data.get("consistency", 0),
                            "dominant_mindset": cat_data.get("mindset", ""),
                            "edge_centroid": cat_data.get("edge_dimensions", {}),
                        })
        except Exception:
            pass

        # Authors
        try:
            authors_raw = r.hget(f"{_REDIS_PREFIX}{self.domain}", "authors")
            if authors_raw:
                authors = json.loads(authors_raw)
                for author_slug in authors[:20]:
                    author_data = self._read_centroid(
                        f"{_REDIS_PREFIX}{self.domain}:author:{author_slug}"
                    )
                    if author_data:
                        author_name = r.hget(
                            f"{_REDIS_PREFIX}{self.domain}:author:{author_slug}",
                            "author_name",
                        ) or author_slug
                        report["authors"].append({
                            "slug": author_slug,
                            "name": author_name,
                            "observations": author_data.get("observations", 0),
                            "consistency": author_data.get("consistency", 0),
                            "edge_fingerprint": author_data.get("edge_dimensions", {}),
                        })
        except Exception:
            pass

        return report


# ============================================================================
# SINGLETON + CACHE
# ============================================================================

_taxonomies: Dict[str, DomainTaxonomy] = {}


def get_domain_taxonomy(domain: str) -> DomainTaxonomy:
    """Get or create a DomainTaxonomy instance for a domain."""
    if domain not in _taxonomies:
        _taxonomies[domain] = DomainTaxonomy(domain)
    return _taxonomies[domain]
