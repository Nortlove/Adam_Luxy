"""
Auto-Guidance Intelligence Engine.

Computes the Intelligence Capability Score after Phase 3,
ranks return types for Phase 4, and generates upgrade hints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from adam.platform.onboarding.models import (
    InboundDataRequest,
    IntelligenceProduct,
    RETURN_TYPE_REGISTRY,
)


class IntelligenceCapabilityScore:
    """
    Computed after Phase 3. Determines the ceiling of what ADAM can provide
    based on the inbound data the tenant has committed to sharing.
    """

    def __init__(self, inbound: InboundDataRequest, blueprint_id: str):
        self.inbound = inbound
        self.blueprint_id = blueprint_id
        self._ceiling = self._compute_ceiling()

    @property
    def ceiling(self) -> Dict[str, float]:
        return self._ceiling

    def _compute_ceiling(self) -> Dict[str, float]:
        ib = self.inbound
        c: Dict[str, float] = {
            "content_psychology": 0.0,
            "persistent_profiles": 0.0,
            "learning_loop": 0.0,
            "creative_matching": 0.0,
            "sequential_persuasion": 0.0,
            "contextual_fusion": 0.0,
        }

        has_content = bool(
            ib.content_access_method
            or "content_url" in ib.user_signals
            or ib.content_types
        )
        has_user_id = "user_id" in ib.user_signals
        has_outcome = ib.has_outcome_data
        has_creative = ib.has_creative_metadata
        has_audio = any(t in ib.content_types for t in ("audio", "podcast"))
        has_amazon = ib.amazon_products
        has_behavioral = "behavioral" in ib.user_signals
        has_listener = bool(ib.listener_behavior_data)

        if has_content:
            c["content_psychology"] = 0.85

        if has_user_id:
            c["persistent_profiles"] = 0.90
            c["content_psychology"] = min(c["content_psychology"] + 0.10, 1.0)

        if has_outcome:
            for key in c:
                c[key] = min(c[key] * 1.4, 1.0)
            c["learning_loop"] = 0.95

        if has_creative:
            c["creative_matching"] = 0.90

        if has_audio or has_listener:
            c["content_psychology"] = min(c["content_psychology"] + 0.15, 1.0)

        if has_amazon:
            c["content_psychology"] = 1.0

        if has_behavioral:
            c["persistent_profiles"] = min(c["persistent_profiles"] + 0.15, 1.0)
            c["sequential_persuasion"] = max(c["sequential_persuasion"], 0.65)

        if has_content and has_user_id:
            c["contextual_fusion"] = 0.85
        elif has_content:
            c["contextual_fusion"] = 0.40

        if has_user_id and has_outcome:
            c["sequential_persuasion"] = min(c["sequential_persuasion"] + 0.30, 1.0)

        # round all
        return {k: round(v, 2) for k, v in c.items()}

    def get_available_return_types(self) -> List[Dict[str, Any]]:
        """Return ranked list of available intelligence products."""
        registry = RETURN_TYPE_REGISTRY.get(self.blueprint_id, [])
        result = []

        for rt in registry:
            power = self._compute_power_for_type(rt)
            result.append({
                "id": rt["id"],
                "name": rt["name"],
                "description": rt["description"],
                "power_level": power,
                "pricing": rt["pricing"],
                "recommended": False,
                "upgrade_available": power < rt["base_power"] * 0.7,
                "upgrade_hint": self._get_upgrade_hint(rt, power),
            })

        result.sort(key=lambda x: x["power_level"], reverse=True)

        if result:
            result[0]["recommended"] = True

        return result

    def _compute_power_for_type(self, rt: Dict[str, Any]) -> float:
        """Compute power level for a specific return type based on available data."""
        base = rt["base_power"]
        ib = self.inbound
        requires = rt.get("requires", [])

        penalty = 0.0
        for req in requires:
            if req == "content_url" and "content_url" not in ib.user_signals and not ib.content_access_method:
                penalty += 0.35
            elif req == "creative_metadata" and not ib.has_creative_metadata:
                penalty += 0.30
            elif req == "outcome_data" and not ib.has_outcome_data:
                penalty += 0.25
            elif req == "user_id" and "user_id" not in ib.user_signals:
                penalty += 0.25
            elif req == "content_access" and not ib.content_access_method:
                penalty += 0.30
            elif req == "listener_behavior" and not ib.listener_behavior_data:
                penalty += 0.20

        if ib.has_outcome_data:
            base = min(base * 1.1, 1.0)

        return round(max(0.10, base - penalty), 2)

    def _get_upgrade_hint(self, rt: Dict[str, Any], current_power: float) -> str:
        if current_power >= rt["base_power"] * 0.9:
            return ""

        ib = self.inbound
        requires = rt.get("requires", [])
        hints = []

        for req in requires:
            if req == "content_url" and "content_url" not in ib.user_signals:
                hints.append("Share content URLs to unlock full content psychology analysis.")
            elif req == "creative_metadata" and not ib.has_creative_metadata:
                hints.append("Share creative metadata to enable creative-audience matching.")
            elif req == "outcome_data" and not ib.has_outcome_data:
                hints.append("Add outcome data to activate all 9 learning systems — every campaign improves the next.")
            elif req == "user_id" and "user_id" not in ib.user_signals:
                hints.append("Share any user identifier to enable persistent profiles that compound over time.")
            elif req == "listener_behavior" and not ib.listener_behavior_data:
                hints.append("Share listener behavior data to enable personality inference from listening patterns.")

        if not hints and not ib.has_outcome_data:
            hints.append("Add outcome data to boost all capabilities by up to 40%.")

        return " ".join(hints)

    def get_upgrade_hints(self) -> List[Dict[str, Any]]:
        """Show what the user could unlock by sharing additional data."""
        max_ceiling = self._compute_max_ceiling()
        hints = []

        for cap, current in self._ceiling.items():
            max_val = max_ceiling.get(cap, current)
            gap = max_val - current
            if gap > 0.15:
                hints.append({
                    "capability": cap,
                    "current": current,
                    "potential": max_val,
                    "gap_pct": round(gap * 100),
                    "what_to_share": _DATA_FOR_CAPABILITY.get(cap, "Share additional data."),
                })

        hints.sort(key=lambda x: x["gap_pct"], reverse=True)
        return hints

    def _compute_max_ceiling(self) -> Dict[str, float]:
        """Maximum possible ceiling if all data were shared."""
        return {
            "content_psychology": 1.0,
            "persistent_profiles": 1.0,
            "learning_loop": 0.95,
            "creative_matching": 0.90,
            "sequential_persuasion": 0.95,
            "contextual_fusion": 0.95,
        }

    def get_recommended_type(self) -> str:
        types = self.get_available_return_types()
        return types[0]["id"] if types else "segments"


_DATA_FOR_CAPABILITY = {
    "content_psychology": "Share content URLs or configure a content connector (RSS, sitemap, CMS API).",
    "persistent_profiles": "Share any user identifier (UID2, cookie, device ID) to enable profiles that compound.",
    "learning_loop": "Configure outcome data feedback (conversions, clicks). This activates 9 learning systems simultaneously.",
    "creative_matching": "Share creative metadata (ad copy, images, landing pages) for creative-audience matching.",
    "sequential_persuasion": "Share user IDs + outcome data to enable multi-touch journey optimization.",
    "contextual_fusion": "Share content URLs with each request for context x psychology compound signals.",
}


class OnboardingGuidance:
    """
    Runs after each phase to compute recommendations.
    Provides role-based auto-guidance and capability scoring.
    """

    @staticmethod
    def suggest_blueprint_from_role(contact_role: str) -> Optional[str]:
        """Auto-suggest a business type from the contact's job title."""
        role_lower = contact_role.lower()
        if any(kw in role_lower for kw in ("trading desk", "programmatic", "media buyer", "dsp")):
            return "dsp_targeting"
        if any(kw in role_lower for kw in ("publisher", "content", "editorial", "ad ops")):
            return "publisher"
        if any(kw in role_lower for kw in ("podcast", "audio", "radio", "listener")):
            return "audio_podcast"
        if any(kw in role_lower for kw in ("brand", "cmo", "marketing", "ecommerce", "e-commerce")):
            return "brand_advertiser"
        if any(kw in role_lower for kw in ("agency", "account", "planning", "strategy")):
            return "agency"
        if any(kw in role_lower for kw in ("ssp", "supply", "inventory", "yield")):
            return "ssp_enrich"
        if any(kw in role_lower for kw in ("ctv", "streaming", "ott", "connected tv")):
            return "ctv_streaming"
        if any(kw in role_lower for kw in ("retail", "commerce", "shop")):
            return "retail_media"
        if any(kw in role_lower for kw in ("exchange", "marketplace")):
            return "ad_exchange"
        if any(kw in role_lower for kw in ("social", "ugc", "community")):
            return "social_ugc"
        return None

    @staticmethod
    def get_phase3_questions(blueprint_id: str) -> List[Dict[str, Any]]:
        """Return the dynamic question set for Phase 3 based on blueprint."""
        questions = _COMMON_QUESTIONS.copy()

        bp_specific = _BLUEPRINT_QUESTIONS.get(blueprint_id, [])
        questions.extend(bp_specific)

        return questions

    @staticmethod
    def compute_intelligence_products(
        inbound: InboundDataRequest,
        blueprint_id: str,
    ) -> List[IntelligenceProduct]:
        """Compute ranked intelligence products for Phase 4."""
        scorer = IntelligenceCapabilityScore(inbound, blueprint_id)
        raw = scorer.get_available_return_types()

        return [
            IntelligenceProduct(
                id=rt["id"],
                name=rt["name"],
                description=rt["description"],
                power_level=rt["power_level"],
                pricing=rt["pricing"],
                recommended=rt["recommended"],
                upgrade_available=rt["upgrade_available"],
                upgrade_hint=rt["upgrade_hint"],
            )
            for rt in raw
        ]

    @staticmethod
    def generate_improvement_timeline() -> List[Dict[str, str]]:
        return [
            {"week": "Week 1", "description": "Baseline psychological targeting (already powerful from 937M+ review corpus)."},
            {"week": "Week 2", "description": "First outcome signals processed — mechanism priors begin updating."},
            {"week": "Week 4", "description": "Thompson sampling identifies top-performing mechanisms for YOUR audience."},
            {"week": "Week 8", "description": "Bayesian priors tightened — segment recommendations increasingly precise."},
            {"week": "Week 12", "description": "Cross-category transfer learning kicks in — patterns from similar advertisers improve your targeting."},
            {"week": "Ongoing", "description": "Every campaign compounds. Campaign 10 is dramatically more effective than Campaign 1."},
        ]


# ── Phase 3 Question Definitions ──────────────────────────────────────

_COMMON_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "outcome_data",
        "question": "Can you share campaign outcome data?",
        "type": "single_select",
        "field": "has_outcome_data",
        "options": [
            {"value": True, "label": "Yes — real-time conversion pixels / postback URLs", "method": "realtime_postback"},
            {"value": True, "label": "Yes — daily batch reports", "method": "batch"},
            {"value": "limited", "label": "Limited — click data only", "method": "batch"},
            {"value": False, "label": "Not yet — but we plan to"},
            {"value": False, "label": "No"},
        ],
        "guidance": "Outcome data is what makes ADAM get smarter over time. With conversion data, ADAM's 9 learning systems update simultaneously — every campaign improves the next.",
    },
]

_BLUEPRINT_QUESTIONS: Dict[str, List[Dict[str, Any]]] = {
    "DSP-TGT": [
        {
            "id": "user_signals",
            "question": "What user signals can you share with each ad request?",
            "type": "multi_select",
            "field": "user_signals",
            "options": [
                {"value": "user_id", "label": "User ID (UID2, RampID, device ID, cookie)", "unlocks": "Persistent psychological profiles that compound over time"},
                {"value": "content_url", "label": "Content URL (page where the ad shows)", "unlocks": "Content psychology analysis (ADAM's core advantage)"},
                {"value": "page_category", "label": "Page category / IAB content taxonomy"},
                {"value": "device_env", "label": "Device type and environment (web/app/CTV)"},
                {"value": "geo", "label": "Geographic location"},
                {"value": "time_context", "label": "Time of day / day of week"},
                {"value": "behavioral", "label": "User behavioral signals (site visits, search history)", "unlocks": "Progressive personality inference"},
                {"value": "demographic", "label": "User demographic segments (age, gender, income)"},
                {"value": "contextual_only", "label": "None — contextual only", "unlocks": "Full targeting from content analysis alone — no PII, no cookies, no consent walls"},
            ],
        },
        {
            "id": "signal_delivery",
            "question": "How will you send this data?",
            "type": "single_select",
            "field": "signal_delivery_method",
            "options": [
                {"value": "realtime_api", "label": "Real-time API call per ad request"},
                {"value": "batch", "label": "Batch file upload (daily/hourly)"},
                {"value": "bidstream", "label": "Bidstream integration (ADAM reads your OpenRTB bid requests)"},
                {"value": "webhook", "label": "Server-side webhook"},
            ],
        },
        {
            "id": "creative_metadata",
            "question": "Can you share creative metadata?",
            "type": "single_select",
            "field": "has_creative_metadata",
            "options": [
                {"value": True, "label": "Yes — ad copy text, image descriptions, landing page URLs"},
                {"value": "partial", "label": "Partial — ad copy text only"},
                {"value": False, "label": "No"},
            ],
            "unlocks_if_yes": "Creative-Audience Matching — ADAM will score how well each ad matches the psychological profile.",
        },
    ],
    "PUB-ENR": [
        {
            "id": "content_types",
            "question": "What content do you publish?",
            "type": "multi_select",
            "field": "content_types",
            "options": [
                {"value": "text", "label": "Text articles / blog posts"},
                {"value": "audio", "label": "Podcasts / audio content"},
                {"value": "video", "label": "Video content"},
                {"value": "music", "label": "Music / audio streaming"},
            ],
        },
        {
            "id": "content_access",
            "question": "How should ADAM access your content?",
            "type": "single_select",
            "field": "content_access_method",
            "options": [
                {"value": "rss", "label": "RSS / Atom feed"},
                {"value": "sitemap", "label": "Sitemap URL"},
                {"value": "cms_api", "label": "CMS API (WordPress REST, GraphQL, etc.)"},
                {"value": "webhook", "label": "Webhook — we'll push new content to you"},
                {"value": "s3_audio", "label": "Audio file storage (S3 / GCS bucket)"},
                {"value": "transcript_db", "label": "Transcript database"},
            ],
        },
        {
            "id": "ssp_platforms",
            "question": "What SSP(s) do you use?",
            "type": "multi_select",
            "field": "ssp_platforms",
            "options": [
                {"value": "magnite", "label": "Magnite (Rubicon)"},
                {"value": "pubmatic", "label": "PubMatic"},
                {"value": "index_exchange", "label": "Index Exchange"},
                {"value": "google_adx", "label": "Google Ad Manager / AdX"},
                {"value": "triton", "label": "Triton Digital (audio)"},
                {"value": "freewheel", "label": "FreeWheel (video/CTV)"},
                {"value": "openx", "label": "OpenX"},
                {"value": "sovrn", "label": "Sovrn"},
            ],
        },
        {
            "id": "prebid",
            "question": "Do you use Prebid.js?",
            "type": "single_select",
            "field": "uses_prebid",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": False, "label": "No"},
                {"value": None, "label": "Not sure"},
            ],
            "guidance": "Mode B (offline push) is the fastest way to start — segments appear in your SSP within hours, zero impact on your ad stack. Mode A (real-time) is more powerful but requires Prebid integration.",
        },
        {
            "id": "first_party",
            "question": "What first-party audience data do you have?",
            "type": "multi_select",
            "field": "first_party_data",
            "options": [
                {"value": "login", "label": "Login / registration data", "unlocks": "Persistent user profiles — much more powerful over time"},
                {"value": "dmp_segments", "label": "DMP / CDP audience segments"},
                {"value": "engagement", "label": "Engagement metrics (time on page, scroll depth)", "unlocks": "Psychological state inference from behavior"},
                {"value": "subscription", "label": "Subscription / paywall data"},
                {"value": "social_sharing", "label": "Social sharing data"},
                {"value": "none", "label": "Nothing beyond what's in our content"},
            ],
        },
    ],
    "BRD-INT": [
        {
            "id": "amazon_products",
            "question": "Are your products sold on Amazon?",
            "type": "single_select",
            "field": "amazon_products",
            "options": [
                {"value": True, "label": "Yes"},
                {"value": "some", "label": "Some products are"},
                {"value": False, "label": "No"},
            ],
            "guidance": "ADAM will analyze your product reviews from our 937M+ review corpus. Empirically measured psychology from real purchase behavior — not LLM-generated guesses.",
        },
        {
            "id": "brand_names",
            "question": "What are your brand and product names?",
            "type": "text_list",
            "field": "brand_names",
        },
        {
            "id": "product_category",
            "question": "What product category?",
            "type": "single_select",
            "field": "product_category",
            "options": [
                {"value": "all_beauty", "label": "Beauty & Personal Care"},
                {"value": "electronics", "label": "Electronics"},
                {"value": "health", "label": "Health & Household"},
                {"value": "fashion", "label": "Fashion & Apparel"},
                {"value": "home", "label": "Home & Kitchen"},
                {"value": "automotive", "label": "Automotive"},
                {"value": "food", "label": "Food & Beverage"},
                {"value": "toys", "label": "Toys & Games"},
                {"value": "sports", "label": "Sports & Outdoors"},
                {"value": "books", "label": "Books & Media"},
                {"value": "pets", "label": "Pet Supplies"},
                {"value": "baby", "label": "Baby Products"},
                {"value": "financial", "label": "Financial Services"},
                {"value": "travel", "label": "Travel & Hospitality"},
                {"value": "education", "label": "Education"},
                {"value": "other", "label": "Other"},
            ],
        },
        {
            "id": "advertising_channels",
            "question": "What advertising channels do you currently use?",
            "type": "multi_select",
            "field": "advertising_channels",
            "options": [
                {"value": "programmatic", "label": "Programmatic display/video"},
                {"value": "social", "label": "Social (Meta, TikTok, etc.)"},
                {"value": "audio", "label": "Audio / podcast"},
                {"value": "ctv", "label": "CTV / streaming"},
                {"value": "search", "label": "Search (Google, Bing)"},
                {"value": "direct", "label": "Direct publisher buys"},
                {"value": "email", "label": "Email marketing"},
            ],
        },
    ],
    "AUD-LST": [
        {
            "id": "audio_types",
            "question": "What type of audio content?",
            "type": "multi_select",
            "field": "audio_content_types",
            "options": [
                {"value": "music", "label": "Music streaming"},
                {"value": "podcasts", "label": "Podcasts"},
                {"value": "live_radio", "label": "Live radio / talk"},
                {"value": "audiobooks", "label": "Audiobooks"},
            ],
        },
        {
            "id": "listener_data",
            "question": "What listener behavior data can you share?",
            "type": "multi_select",
            "field": "listener_behavior_data",
            "options": [
                {"value": "genre_prefs", "label": "Genre/station preferences", "unlocks": "Enables MUSIC model personality inference (r = .77-.89)"},
                {"value": "skip_behavior", "label": "Skip / seek behavior", "unlocks": "Correlates with neuroticism (r = .20)"},
                {"value": "listen_duration", "label": "Listen duration per session", "unlocks": "Correlates with conscientiousness + openness"},
                {"value": "playlist_activity", "label": "Playlist creation activity"},
                {"value": "time_patterns", "label": "Time-of-day listening patterns", "unlocks": "Morning → conscientiousness; late-night → openness"},
                {"value": "device_context", "label": "Device / location context"},
                {"value": "subscription_tier", "label": "Subscription tier (free vs premium)"},
            ],
        },
        {
            "id": "ad_tech",
            "question": "What ad serving technology do you use?",
            "type": "single_select",
            "field": "ad_serving_technology",
            "options": [
                {"value": "triton", "label": "Triton Digital"},
                {"value": "megaphone", "label": "Megaphone"},
                {"value": "google_adm_audio", "label": "Google Ad Manager (audio)"},
                {"value": "spotify_ad_studio", "label": "Spotify Ad Studio"},
                {"value": "adswizz", "label": "AdsWizz"},
                {"value": "custom", "label": "Custom / proprietary"},
            ],
        },
        {
            "id": "catalog_size",
            "question": "How many shows/stations in your catalog?",
            "type": "single_select",
            "field": "catalog_size",
            "options": [
                {"value": "under_100", "label": "Under 100"},
                {"value": "100_1000", "label": "100 - 1,000"},
                {"value": "1000_10000", "label": "1,000 - 10,000"},
                {"value": "10000_plus", "label": "10,000+"},
            ],
        },
    ],
}

# Add default questions for blueprints not explicitly listed
for _bp_key in ["PUB-YLD", "DSP-CRE", "AGY-PLN", "CTV-AUD", "RET-PSY", "SOC-AUD", "EXC-DAT"]:
    if _bp_key not in _BLUEPRINT_QUESTIONS:
        _BLUEPRINT_QUESTIONS[_bp_key] = []
