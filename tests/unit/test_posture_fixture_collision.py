"""Pin held-out fixture isolation rule (binding rule:
feedback_heldout_fixture_isolation.md).

Two pure helpers in adam.intelligence.posture_five_class enforce the
rule at persist-time:

  * registrable_domain(url)  — last-2 hostname labels (or last-3 for
    multi-suffix TLDs like co.uk). Drops scheme/port/userinfo/sub-
    domains. Lowercase. Returns "" on malformed input.
  * find_url_fixture_collision(candidate_url, fixture_urls)  —
    returns (collision_domain, first_colliding_fixture_url) on hit
    or None on miss.

These tests pin behavior on the edge cases that mattered when the
rule was first violated (subdomain-stripping for google.com, and
the round-3 v1 → v2 swap of slack/zoom/salesforce/figma/airtable
for TASK plus expedia/booking/amazon/zillow/cars/carvana for
TRANSACTIONAL plus vogue/gq/atlasobscura/smithsonianmag for LEISURE).
"""

from __future__ import annotations

import pytest

from adam.intelligence.posture_five_class import (
    find_url_fixture_collision,
    registrable_domain,
)


# =============================================================================
# registrable_domain — basic cases
# =============================================================================

class TestRegistrableDomainBasic:
    def test_simple_com_url(self):
        assert registrable_domain("https://www.example.com/path") == "example.com"

    def test_subdomain_stripped(self):
        assert registrable_domain("https://app.slack.com/client/T01") == "slack.com"

    def test_deeply_nested_subdomain_stripped(self):
        assert registrable_domain("https://api.v2.team.example.com/x") == "example.com"

    def test_lowercases_hostname(self):
        assert registrable_domain("https://Vogue.COM/article") == "vogue.com"

    def test_strips_port(self):
        assert registrable_domain("https://example.com:8080/x") == "example.com"

    def test_strips_userinfo(self):
        assert registrable_domain("https://user:pass@example.com/x") == "example.com"

    def test_no_path_required(self):
        assert registrable_domain("https://www.npr.org") == "npr.org"


# =============================================================================
# registrable_domain — multi-suffix TLDs (co.uk, co.jp, etc.)
# =============================================================================

class TestRegistrableDomainMultiSuffix:
    def test_co_uk(self):
        assert registrable_domain("https://www.bbc.co.uk/news") == "bbc.co.uk"

    def test_co_jp(self):
        assert registrable_domain("https://www.asahi.co.jp/article") == "asahi.co.jp"

    def test_com_au(self):
        assert registrable_domain("https://www.smh.com.au/national") == "smh.com.au"

    def test_co_uk_with_subdomain(self):
        assert registrable_domain("https://m.bbc.co.uk/news") == "bbc.co.uk"


# =============================================================================
# registrable_domain — malformed / edge cases
# =============================================================================

class TestRegistrableDomainEdgeCases:
    def test_empty_string(self):
        assert registrable_domain("") == ""

    def test_no_scheme(self):
        # urlparse without scheme puts "example.com/x" in path; netloc
        # is empty. The helper returns "" — that's the documented
        # contract. Persist script's pydantic validator catches such
        # malformed inputs upstream.
        assert registrable_domain("example.com/x") == ""

    def test_single_label_hostname(self):
        # Treats single-label as the registrable form (rare but valid
        # for intranet-style URLs). Doesn't crash.
        assert registrable_domain("https://localhost/x") == "localhost"

    def test_handles_trailing_dot(self):
        # urllib normalizes; trailing-dot hostnames get an empty
        # final label which we filter out.
        assert registrable_domain("https://www.example.com./x") == "example.com"


# =============================================================================
# find_url_fixture_collision — hit / miss
# =============================================================================

class TestFindUrlFixtureCollision:
    def test_returns_none_on_miss(self):
        fixture = ["https://www.npr.org/sections/news/", "https://x.com/home"]
        result = find_url_fixture_collision(
            "https://www.example.com/x", fixture,
        )
        assert result is None

    def test_returns_collision_on_exact_domain_match(self):
        fixture = ["https://twitter.com/home", "https://www.npr.org/news"]
        result = find_url_fixture_collision(
            "https://twitter.com/explore", fixture,
        )
        assert result == ("twitter.com", "https://twitter.com/home")

    def test_collision_via_subdomain_difference(self):
        # Persist-side has app.slack.com; fixture has different
        # subdomain m.slack.com. Both share registrable slack.com →
        # collision. This is the central case — the rule is about
        # registrable domain, not URL equality.
        fixture = ["https://m.slack.com/messages"]
        result = find_url_fixture_collision(
            "https://app.slack.com/client/T01", fixture,
        )
        assert result == ("slack.com", "https://m.slack.com/messages")

    def test_first_colliding_fixture_url_wins(self):
        # When multiple fixture URLs share the candidate's domain,
        # first-by-iteration wins. Determinism matters for the
        # operator-facing error message.
        fixture = [
            "https://twitter.com/home",
            "https://twitter.com/explore",
        ]
        result = find_url_fixture_collision(
            "https://twitter.com/messages", fixture,
        )
        assert result == ("twitter.com", "https://twitter.com/home")

    def test_empty_fixture_returns_none(self):
        result = find_url_fixture_collision(
            "https://anywhere.com/x", [],
        )
        assert result is None

    def test_empty_candidate_returns_none(self):
        # Documented soft behavior — pydantic catches malformed URLs
        # at the entry boundary, and an empty registrable_domain is
        # semantically "not a real URL".
        fixture = ["https://x.com/home"]
        result = find_url_fixture_collision("", fixture)
        assert result is None

    def test_different_tlds_do_not_collide(self):
        # example.com and example.org are distinct registrable
        # domains. The rule does not prohibit using one when the
        # other is in fixture.
        fixture = ["https://www.example.com/x"]
        result = find_url_fixture_collision(
            "https://www.example.org/y", fixture,
        )
        assert result is None

    def test_multi_suffix_collision(self):
        # co.uk hosts get last-3-labels treatment. bbc.co.uk in
        # fixture and a different bbc.co.uk URL in candidate →
        # collision.
        fixture = ["https://www.bbc.co.uk/news/world"]
        result = find_url_fixture_collision(
            "https://www.bbc.co.uk/sport", fixture,
        )
        assert result == ("bbc.co.uk", "https://www.bbc.co.uk/news/world")

    def test_multi_suffix_does_not_overcollide(self):
        # bbc.co.uk and itv.co.uk share the suffix "co.uk" but are
        # distinct registrable domains; no collision.
        fixture = ["https://www.itv.co.uk/news"]
        result = find_url_fixture_collision(
            "https://www.bbc.co.uk/news", fixture,
        )
        assert result is None


# =============================================================================
# Regression — the specific overlaps that motivated the rule
#
# These are the 15 round-3 v1 ↔ held-out collisions that the
# 2026-05-03 rotation pass resolved + the 1 training ↔ held-out
# google.com collision that prompted the held-out swap. If any of
# these regressions silently lose the collision check, the gate
# becomes contaminated.
# =============================================================================

class TestRegressionRotationCases:
    @pytest.mark.parametrize(
        "candidate_url, fixture_url, expected_domain",
        [
            # Round-3 v1 TASK collisions (5 domains)
            ("https://app.slack.com/client/T0/D1234",
             "https://app.slack.com/client/T01ABC/CXX1234", "slack.com"),
            ("https://app.zoom.us/wc/start",
             "https://app.zoom.us/wc/join/12345", "zoom.us"),
            ("https://app.salesforce.com/lightning/o/Opportunity/list",
             "https://app.salesforce.com/lightning/o/Lead/list",
             "salesforce.com"),
            ("https://www.figma.com/file/abc123/MyDesign",
             "https://app.figma.com/files/recent", "figma.com"),
            ("https://airtable.com/appXYZ/tblABC",
             "https://app.airtable.com/workspace", "airtable.com"),

            # Round-3 v1 TRANSACTIONAL collisions (6 domains)
            ("https://www.amazon.com/s?k=laptop",
             "https://www.amazon.com/dp/B09G9HD6PD", "amazon.com"),
            ("https://www.booking.com/hotel/fr/x.html",
             "https://www.booking.com/searchresults.html?dest_id=-2601889",
             "booking.com"),
            ("https://www.cars.com/research/toyota-camry/",
             "https://www.cars.com/shopping/results/?stock_type=used",
             "cars.com"),
            ("https://www.carvana.com/cars/honda-civic",
             "https://www.carvana.com/cars/toyota-camry", "carvana.com"),
            ("https://www.expedia.com/Flights-Search?from=JFK&to=LHR",
             "https://www.expedia.com/Hotels-Search?destination=Paris",
             "expedia.com"),
            ("https://www.zillow.com/homes/for_sale/Manhattan-NY/",
             "https://www.zillow.com/homes/for_sale/Brooklyn-NY/",
             "zillow.com"),

            # Round-3 v1 LEISURE collisions (4 domains)
            ("https://www.atlasobscura.com/articles/iceland",
             "https://www.atlasobscura.com/places/hidden-gems-paris",
             "atlasobscura.com"),
            ("https://www.gq.com/style/menswear",
             "https://www.gq.com/story/best-watches-2025", "gq.com"),
            ("https://www.smithsonianmag.com/history/civil-war",
             "https://www.smithsonianmag.com/travel/best-museums-world",
             "smithsonianmag.com"),
            ("https://www.vogue.com/fashion/trends",
             "https://www.vogue.com/article/met-gala-2025-best-dressed",
             "vogue.com"),

            # Training ↔ held-out google.com collision (the one that
            # forced the basecamp.com fixture swap)
            ("https://calendar.google.com/calendar/u/0/r",
             "https://docs.google.com/document/d/abc123/edit",
             "google.com"),
        ],
    )
    def test_regression_each_known_collision(
        self, candidate_url, fixture_url, expected_domain,
    ):
        result = find_url_fixture_collision(candidate_url, [fixture_url])
        assert result is not None
        domain, returned_fixture = result
        assert domain == expected_domain
        assert returned_fixture == fixture_url


# =============================================================================
# Integration — the real held-out fixture should refuse a same-domain
# candidate and accept a never-trained one.
# =============================================================================

class TestAgainstLiveHeldoutFixture:
    def test_live_fixture_loads_and_refuses_collision(self):
        # The persist script imports HELDOUT_URLS from the gate
        # script at runtime. Verify the live fixture catches a
        # candidate constructed against one of its own domains.
        from scripts.heldout_eval_posture_classifier import HELDOUT_URLS

        fixture = [u for u, _, _ in HELDOUT_URLS]
        # NPR is in the live fixture (SOCIAL); a same-domain
        # candidate must collide.
        result = find_url_fixture_collision(
            "https://www.npr.org/programs/morning-edition/", fixture,
        )
        assert result is not None
        domain, _ = result
        assert domain == "npr.org"

    def test_live_fixture_accepts_non_overlapping_domain(self):
        # A round-3 v2 domain (basecamp / mattermost / hotwire / etc.)
        # must NOT collide.
        from scripts.heldout_eval_posture_classifier import HELDOUT_URLS

        fixture = [u for u, _, _ in HELDOUT_URLS]
        for fresh_url in [
            "https://app.mattermost.com/myteam/channels/town-square",
            "https://www.hotwire.com/Hotels-Search?destination=Paris",
            "https://www.harpersbazaar.com/fashion/trends-2025",
            "https://www.threads.net/following",
        ]:
            assert find_url_fixture_collision(fresh_url, fixture) is None, (
                f"unexpected collision for {fresh_url}"
            )
