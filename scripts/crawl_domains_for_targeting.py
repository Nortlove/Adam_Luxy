#!/usr/bin/env python3
"""
Domain & Article Crawler for Goal Activation Targeting

Crawls real page content from domains in the domain universe,
scores each article through the Goal Activation Model, and
generates per-archetype whitelist CSVs for StackAdapt.

Usage:
    python3 scripts/crawl_domains_for_targeting.py

Outputs:
    data/domain_universe.json          — Domain list by category
    data/domain_crawl_results.json     — Homepage-level crawl results
    data/deep_article_crawl.json       — Article-level crawl results
    campaigns/ridelux_v6/stackadapt_whitelist_*.csv  — Per-archetype whitelists
    campaigns/ridelux_v6/domain_archetype_mapping.json — Crossover score mapping

To add more domains: edit DOMAIN_UNIVERSE below.
To adjust thresholds: edit MIN_ARTICLES and MIN_CROSSOVER.
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# CONFIGURATION
# =============================================================================

MIN_ARTICLES = 2       # Minimum articles crawled per domain for whitelist inclusion
MIN_CROSSOVER = 0.08   # Minimum average crossover score for whitelist inclusion
MAX_ARTICLES_PER_DOMAIN = 8  # How many articles to crawl per domain
CRAWL_DELAY = 0.3      # Seconds between requests (be polite)
FETCH_TIMEOUT = 8      # Seconds per request

OUTPUT_DIR = Path("data")
CAMPAIGN_DIR = Path("campaigns/ridelux_v6")

# =============================================================================
# DOMAIN UNIVERSE — Add/remove domains here
# =============================================================================

DOMAIN_UNIVERSE = {
    "business_finance": [
        "forbes.com", "fortune.com", "bloomberg.com", "wsj.com", "ft.com",
        "cnbc.com", "barrons.com", "economist.com", "hbr.org", "inc.com",
        "fastcompany.com", "businessinsider.com", "reuters.com", "marketwatch.com",
        "seekingalpha.com", "investopedia.com", "kiplinger.com", "thestreet.com",
        "fool.com", "morningstar.com", "crunchbase.com", "pitchbook.com",
    ],
    "travel_luxury": [
        "cntraveler.com", "travelandleisure.com", "afar.com", "departures.com",
        "robbreport.com", "elitetraveler.com", "luxurytravelmagazine.com",
        "pursuitist.com", "jamesedition.com", "bespokemagazine.com",
        "townandcountrymag.com", "architecturaldigest.com", "dwell.com",
        "vogue.com", "gq.com", "esquire.com", "vanityfair.com",
        "thecut.com", "manofmany.com", "uncrate.com",
    ],
    "travel_planning": [
        "booking.com", "expedia.com", "kayak.com", "tripadvisor.com",
        "hotels.com", "priceline.com", "travelocity.com", "orbitz.com",
        "google.com/travel", "skyscanner.com", "momondo.com",
        "flightaware.com", "flightradar24.com", "seatguru.com",
        "thepointsguy.com", "onemileatatime.com", "upgradedpoints.com",
        "nerdwallet.com/travel", "theinfatuation.com", "opentable.com",
    ],
    "news_current": [
        "nytimes.com", "washingtonpost.com", "cnn.com", "bbc.com",
        "npr.org", "apnews.com", "axios.com", "politico.com",
        "theatlantic.com", "newyorker.com", "slate.com", "vox.com",
        "usatoday.com", "time.com", "newsweek.com",
    ],
    "professional": [
        "linkedin.com", "glassdoor.com", "indeed.com",
        "medium.com", "substack.com", "techcrunch.com",
        "wired.com", "theverge.com", "arstechnica.com",
    ],
    "lifestyle_events": [
        "brides.com", "theknot.com", "weddingwire.com", "zola.com",
        "marthastewart.com", "people.com", "ew.com",
        "eater.com", "timeout.com", "eventbrite.com",
    ],
    "safety_official": [
        "tsa.gov", "weather.com", "miserymap.com",
        "consumerreports.com", "bbb.org", "nhtsa.gov",
    ],
    "sports_entertainment": [
        "espn.com", "bleacherreport.com", "si.com",
        "golfdigest.com", "tennis.com", "skimagazine.com",
    ],
}

TARGET_ARCHETYPES = [
    "trusting_loyalist", "reliable_cooperator", "careful_truster",
    "explorer", "prevention_planner", "dependable_loyalist",
    "consensus_seeker",
]


# =============================================================================
# HTML TEXT EXTRACTOR
# =============================================================================

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False
        self.in_title = False
        self.title = ""
        self.meta_desc = ""
        self.headings = []
        self._tag = ""

    def handle_starttag(self, tag, attrs):
        self._tag = tag
        if tag in ("script", "noscript", "style", "nav", "footer", "header"):
            self.skip = True
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            d = dict(attrs)
            if d.get("name", "").lower() == "description":
                self.meta_desc = d.get("content", "")[:500]
            elif d.get("property", "").lower() == "og:description" and not self.meta_desc:
                self.meta_desc = d.get("content", "")[:500]

    def handle_endtag(self, tag):
        if tag in ("script", "noscript", "style", "nav", "footer", "header"):
            self.skip = False
        elif tag == "title":
            self.in_title = False
        self._tag = ""

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_title:
            self.title += data
        t = data.strip()
        if t and len(t) > 5:
            self.parts.append(t)
            if self._tag in ("h1", "h2", "h3"):
                self.headings.append(t)


# =============================================================================
# FETCH UTILITIES
# =============================================================================

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
}


def fetch(url, timeout=FETCH_TIMEOUT):
    """Fetch a URL and return the HTML text, or None on failure."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
        return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def find_article_urls(domain, html):
    """Extract article-like URLs from a page's HTML."""
    urls = set()
    clean_domain = domain.replace("www.", "")
    for match in re.findall(r'href=["\']?(https?://(?:www\.)?[^"\'>\s]+)', html):
        if clean_domain in match:
            path = match.split(clean_domain)[-1]
            segments = [s for s in path.split("/") if s and s != "#"]
            skip_patterns = [
                ".css", ".js", ".png", ".jpg", ".gif", ".svg",
                "login", "signup", "subscribe", "account", "cart",
                "privacy", "terms", "cookie", "advertise", "about-us",
                "contact", "sitemap", "rss", "feed", "tag/", "category/",
                "author/", "page/", "wp-content", "wp-admin",
            ]
            if (
                len(segments) >= 2
                and "?" not in match
                and not any(x in path.lower() for x in skip_patterns)
            ):
                urls.add(match)
    return list(urls)


def try_rss(domain):
    """Try common RSS feed URLs to find article links."""
    for path in ["/feed", "/rss", "/feed/rss", "/rss.xml", "/atom.xml", "/feeds/all.rss.xml"]:
        xml = fetch(f"https://{domain}{path}", timeout=5)
        if xml and ("<rss" in xml[:500] or "<feed" in xml[:500] or "<item" in xml[:1000]):
            urls = re.findall(r"<link>([^<]+)</link>", xml)
            urls += re.findall(r'<link[^>]*href="([^"]+)"', xml)
            article_urls = [
                u for u in urls
                if domain.replace("www.", "") in u and len(u.split("/")) > 4
            ]
            if article_urls:
                return article_urls[:10]
    return []


def estimate_affect(text):
    """Estimate emotional valence of text content."""
    tl = text.lower()
    pos = sum(
        1
        for w in [
            "success", "luxury", "best", "top", "award", "excellent", "amazing",
            "discover", "innovative", "premium", "trusted", "proven", "exclusive",
            "inspiring", "beautiful", "remarkable", "breakthrough", "experience",
            "elegant", "world-class", "finest", "superior", "curated",
        ]
        if w in tl
    )
    neg = sum(
        1
        for w in [
            "risk", "danger", "warning", "crisis", "fail", "loss", "threat",
            "problem", "concern", "anxiety", "fear", "crash", "decline",
            "war", "attack", "killed", "arrested", "charged",
        ]
        if w in tl
    )
    return min(1.0, max(-1.0, (pos - neg) / 5.0))


# =============================================================================
# MAIN CRAWL
# =============================================================================

def main():
    from adam.intelligence.goal_activation import (
        ARCHETYPE_GOAL_FULFILLMENT,
        compute_crossover_score,
        score_page_goal_activation,
    )

    # Step 1: Save domain universe
    OUTPUT_DIR.mkdir(exist_ok=True)
    CAMPAIGN_DIR.mkdir(parents=True, exist_ok=True)

    total_domains = sum(len(d) for d in DOMAIN_UNIVERSE.values())
    print(f"Domain universe: {total_domains} domains across {len(DOMAIN_UNIVERSE)} categories")
    with open(OUTPUT_DIR / "domain_universe.json", "w") as f:
        json.dump(DOMAIN_UNIVERSE, f, indent=2)

    # Step 2: Crawl homepages
    print(f"\n=== PHASE 1: HOMEPAGE CRAWL ===\n")
    homepage_results = {}
    for category, domains in DOMAIN_UNIVERSE.items():
        for domain in domains:
            print(f"  {domain}...", end=" ", flush=True)
            html = fetch(f"https://{domain}")
            if html:
                homepage_results[domain] = {"category": category, "html_length": len(html)}
                print("OK")
            else:
                homepage_results[domain] = {"category": category, "failed": True}
                print("FAILED")
            time.sleep(CRAWL_DELAY)

    successful = [d for d, r in homepage_results.items() if not r.get("failed")]
    print(f"\nHomepages crawled: {len(successful)} / {total_domains}")

    # Step 3: Article-level crawl
    print(f"\n=== PHASE 2: ARTICLE CRAWL ({len(successful)} domains) ===\n")
    all_articles = []
    domain_stats = {}

    for domain in successful:
        cat = homepage_results[domain]["category"]
        print(f"\n--- {domain} ({cat}) ---", flush=True)

        # Try RSS first, fall back to link extraction
        rss_urls = try_rss(domain)
        if rss_urls:
            print(f"  RSS: {len(rss_urls)} URLs", flush=True)
            candidate_urls = rss_urls
        else:
            homepage_html = fetch(f"https://{domain}")
            if not homepage_html:
                continue
            candidate_urls = find_article_urls(domain, homepage_html)
            print(f"  Links: {len(candidate_urls)} candidates", flush=True)

        domain_articles = []
        for url in candidate_urls[: MAX_ARTICLES_PER_DOMAIN + 4]:
            if len(domain_articles) >= MAX_ARTICLES_PER_DOMAIN:
                break

            html = fetch(url)
            if not html or len(html) < 2000:
                continue

            p = TextExtractor()
            try:
                p.feed(html)
            except Exception:
                continue

            text = " ".join(p.parts)
            if len(text) < 300:
                continue

            scoring_text = f"{p.title} {p.meta_desc} {' '.join(p.headings[:10])} {text[:4000]}"
            affect = estimate_affect(scoring_text)
            goal_result = score_page_goal_activation(scoring_text, affect)

            archetype_scores = {}
            for arch in ARCHETYPE_GOAL_FULFILLMENT:
                archetype_scores[arch] = round(
                    compute_crossover_score(goal_result, arch), 4
                )

            best_arch = max(archetype_scores, key=archetype_scores.get)

            article = {
                "domain": domain,
                "category": cat,
                "url": url[:250],
                "title": p.title.strip()[:200],
                "text_length": len(text),
                "affect": round(affect, 2),
                "dominant_goal": goal_result.dominant_goal,
                "dominant_strength": round(goal_result.dominant_strength, 4),
                "goal_scores": {
                    k: round(v, 4)
                    for k, v in goal_result.goal_scores.items()
                    if v > 0.01
                },
                "archetype_scores": archetype_scores,
                "best_archetype": best_arch,
                "best_crossover": archetype_scores[best_arch],
            }
            domain_articles.append(article)
            all_articles.append(article)

            short = p.title.strip()[:50]
            print(
                f"  [{len(domain_articles)}] {short}... → {best_arch}({archetype_scores[best_arch]:.3f})",
                flush=True,
            )

        if domain_articles:
            avg_xover = sum(a["best_crossover"] for a in domain_articles) / len(
                domain_articles
            )
            arch_totals = {}
            for a in domain_articles:
                for arch, score in a["archetype_scores"].items():
                    arch_totals[arch] = arch_totals.get(arch, 0) + score
            for arch in arch_totals:
                arch_totals[arch] /= len(domain_articles)

            domain_stats[domain] = {
                "category": cat,
                "articles_crawled": len(domain_articles),
                "avg_crossover": round(avg_xover, 4),
                "archetype_avg_scores": {k: round(v, 4) for k, v in arch_totals.items()},
            }

        time.sleep(CRAWL_DELAY)

    # Save crawl results
    with open(OUTPUT_DIR / "deep_article_crawl.json", "w") as f:
        json.dump(
            {
                "total_articles": len(all_articles),
                "domains_crawled": len(domain_stats),
                "articles": all_articles,
                "domain_stats": domain_stats,
            },
            f,
            indent=2,
        )
    print(f"\n\nCrawled {len(all_articles)} articles from {len(domain_stats)} domains")

    # Step 4: Generate per-archetype whitelists
    print(f"\n=== PHASE 3: GENERATE WHITELISTS ===\n")
    mapping = {}

    for arch in TARGET_ARCHETYPES:
        ranked = []
        for domain, stats in domain_stats.items():
            if stats["articles_crawled"] < MIN_ARTICLES:
                continue
            score = stats["archetype_avg_scores"].get(arch, 0)
            if score >= MIN_CROSSOVER:
                articles_for_domain = [a for a in all_articles if a["domain"] == domain]
                goal_counts = {}
                for a in articles_for_domain:
                    g = a["dominant_goal"]
                    goal_counts[g] = goal_counts.get(g, 0) + 1
                dominant_goal = max(goal_counts, key=goal_counts.get) if goal_counts else "unknown"

                ranked.append(
                    {
                        "domain": domain,
                        "crossover_score": round(score, 4),
                        "dominant_goal": dominant_goal,
                        "articles_analyzed": stats["articles_crawled"],
                        "category": stats["category"],
                    }
                )

        ranked.sort(key=lambda x: -x["crossover_score"])
        mapping[arch] = ranked

        # Write CSV
        csv_path = CAMPAIGN_DIR / f"stackadapt_whitelist_{arch}.csv"
        with open(csv_path, "w") as f:
            for entry in ranked:
                f.write(f"{entry['domain']}\n")

        print(f"{arch}: {len(ranked)} domains → {csv_path.name}")
        for entry in ranked[:5]:
            print(f"  {entry['domain']:<28} {entry['crossover_score']:.4f} ({entry['dominant_goal']})")

    # Save mapping
    with open(CAMPAIGN_DIR / "domain_archetype_mapping.json", "w") as f:
        json.dump(
            {
                "method": "deep_article_crawl",
                "min_articles": MIN_ARTICLES,
                "min_crossover": MIN_CROSSOVER,
                "total_articles_analyzed": len(all_articles),
                "total_domains_analyzed": len(domain_stats),
                "archetype_domain_lists": mapping,
            },
            f,
            indent=2,
        )

    print(f"\n=== COMPLETE ===")
    print(f"Articles crawled: {len(all_articles)}")
    print(f"Domains analyzed: {len(domain_stats)}")
    print(f"Whitelists written to {CAMPAIGN_DIR}/")


if __name__ == "__main__":
    main()
