# =============================================================================
# Round-2 candidate URL pool for active-learning sampling
# Location: adam/intelligence/posture_candidate_pool.py
# =============================================================================
"""Round-2 candidate URL pool for the 5-class posture classifier.

Per the 2026-05-03 directive: when round-1 LOOCV macro-AUC < 0.30 on
the n=20 :PostureLabel bootstrap, generate ~500 corporate-traveler-
relevant URLs from named seed sources, score each with the interim
classifier's predict_proba, rank by entropy of the predicted
distribution, and surface the 80 most-uncertain — stratified to
ensure ≥10 candidates predicted into each of the 5 classes.

THE POOL

Curated URLs across the directive's named seed sources:

  * Wirecutter         — research-mode product comparison (NYT)
  * Bloomberg          — finance + executive news
  * Concur / Expensify — T&E productivity tooling
  * Skift              — travel industry trade press
  * Business Insider   — business + executive news
  * Productivity docs  — Notion / Slack / Asana / ClickUp / Linear
  * Travel comparison  — Kayak / Expedia / Google Flights / Booking
  * Executive news     — WSJ / FT / HBR / Forbes / McKinsey

Plus two underrepresented-posture extensions to give round-2 enough
class diversity to satisfy the ≥10-per-class stratification:

  * Travel/lifestyle leisure — Conde Nast / Travel+Leisure / AFAR
  * Social/community         — LinkedIn / Reddit business-travel

THE PRIMITIVES

  * ``CANDIDATE_URLS`` — Dict[str, List[str]] keyed by seed-source.
  * ``get_full_pool()`` — flatten to List[Tuple[source, url]].
  * ``stratified_top_n()`` — score + entropy-rank + stratify by
    P(class | url) per class so the ``min_per_class`` floor is
    satisfied even when the interim classifier is class-imbalanced
    (a class with n=3 training labels rarely argmax-predicts; we
    surface candidates with the highest probability FOR that class
    regardless).

DISCIPLINE (B3-LUXY a/b/c/d)

(a) Citations: 2026-05-03 round-2 active-learning directive.
    Stratified entropy sampling per Settles (2009) "Active Learning
    Literature Survey" §3.2 (uncertainty sampling) + §6.4 (class-
    balanced acquisition).

(b) Tests pin: pool size ≥ 400; stratified top-N respects the
    ≥min_per_class floor when sufficient candidates per class exist;
    entropy is monotone-decreasing in surfaced order.

(c) calibration_pending=True. Pool is curated by the substrate
    author; v0.2 sources URLs from a frozen-snapshot crawl of the
    LUXY DSP traffic feed (operational slice).

(d) Honest tags — what is NOT in this slice:
    * No live page fetching — URLs are scored on string features
      only via the v0.1 classifier.
    * No deduplication against already-labeled URLs — the runner
      script applies that filter at acquisition time.
    * No site-policy / robots.txt compliance check (this is curation
      for hand-labeling, not automated crawling).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Curated URL pool — corporate-traveler-relevant, ~500 URLs across
# the directive's named seed sources.
# =============================================================================

WIRECUTTER_URLS: List[str] = [
    "https://www.nytimes.com/wirecutter/reviews/best-carry-on-luggage/",
    "https://www.nytimes.com/wirecutter/reviews/best-checked-luggage/",
    "https://www.nytimes.com/wirecutter/reviews/best-laptop-backpack/",
    "https://www.nytimes.com/wirecutter/reviews/best-laptop-bag/",
    "https://www.nytimes.com/wirecutter/reviews/best-noise-cancelling-headphones/",
    "https://www.nytimes.com/wirecutter/reviews/best-wireless-earbuds/",
    "https://www.nytimes.com/wirecutter/reviews/best-business-laptops/",
    "https://www.nytimes.com/wirecutter/reviews/best-laptop/",
    "https://www.nytimes.com/wirecutter/reviews/best-ultrabook/",
    "https://www.nytimes.com/wirecutter/reviews/best-portable-monitor/",
    "https://www.nytimes.com/wirecutter/reviews/best-travel-pillow/",
    "https://www.nytimes.com/wirecutter/reviews/best-portable-charger/",
    "https://www.nytimes.com/wirecutter/reviews/best-power-bank-usb-c-pd/",
    "https://www.nytimes.com/wirecutter/reviews/best-travel-adapter/",
    "https://www.nytimes.com/wirecutter/reviews/best-vpn-service/",
    "https://www.nytimes.com/wirecutter/reviews/best-wifi-hotspot/",
    "https://www.nytimes.com/wirecutter/reviews/best-business-class-flights/",
    "https://www.nytimes.com/wirecutter/reviews/best-credit-card-for-travel/",
    "https://www.nytimes.com/wirecutter/reviews/best-travel-credit-cards/",
    "https://www.nytimes.com/wirecutter/reviews/best-airpods/",
    "https://www.nytimes.com/wirecutter/reviews/best-iphone/",
    "https://www.nytimes.com/wirecutter/reviews/best-android-phone/",
    "https://www.nytimes.com/wirecutter/reviews/best-smartwatch/",
    "https://www.nytimes.com/wirecutter/reviews/best-fitness-tracker/",
    "https://www.nytimes.com/wirecutter/reviews/best-running-shoes/",
    "https://www.nytimes.com/wirecutter/reviews/best-dress-shoes-for-men/",
    "https://www.nytimes.com/wirecutter/reviews/best-dress-shirt-men/",
    "https://www.nytimes.com/wirecutter/reviews/best-mens-suits/",
    "https://www.nytimes.com/wirecutter/reviews/best-electric-toothbrush/",
    "https://www.nytimes.com/wirecutter/reviews/best-coffee-maker/",
    "https://www.nytimes.com/wirecutter/reviews/best-espresso-machine/",
    "https://www.nytimes.com/wirecutter/reviews/best-portable-espresso-maker/",
    "https://www.nytimes.com/wirecutter/reviews/best-airline-credit-cards/",
    "https://www.nytimes.com/wirecutter/reviews/best-mileage-credit-cards/",
    "https://www.nytimes.com/wirecutter/reviews/best-tax-software/",
    "https://www.nytimes.com/wirecutter/reviews/best-financial-planning-software/",
    "https://www.nytimes.com/wirecutter/reviews/best-personal-finance-app/",
    "https://www.nytimes.com/wirecutter/reviews/best-mobile-bank/",
    "https://www.nytimes.com/wirecutter/reviews/best-business-checking-account/",
    "https://www.nytimes.com/wirecutter/reviews/best-online-savings-account/",
    "https://www.nytimes.com/wirecutter/reviews/best-co-working-space-headphones/",
    "https://www.nytimes.com/wirecutter/reviews/best-office-chairs/",
    "https://www.nytimes.com/wirecutter/reviews/best-standing-desk/",
    "https://www.nytimes.com/wirecutter/reviews/best-mechanical-keyboard/",
    "https://www.nytimes.com/wirecutter/reviews/best-wireless-mouse/",
    "https://www.nytimes.com/wirecutter/reviews/best-monitor/",
    "https://www.nytimes.com/wirecutter/reviews/best-portable-projector/",
    "https://www.nytimes.com/wirecutter/reviews/best-meeting-room-camera/",
    "https://www.nytimes.com/wirecutter/reviews/best-conference-room-mic/",
    "https://www.nytimes.com/wirecutter/reviews/best-zoom-headset/",
    "https://www.nytimes.com/wirecutter/reviews/best-electric-cars/",
    "https://www.nytimes.com/wirecutter/reviews/best-ride-share-app/",
    "https://www.nytimes.com/wirecutter/reviews/best-airport-parking-service/",
    "https://www.nytimes.com/wirecutter/reviews/best-luggage-tracker/",
    "https://www.nytimes.com/wirecutter/reviews/best-business-insurance/",
    "https://www.nytimes.com/wirecutter/reviews/best-travel-insurance/",
    "https://www.nytimes.com/wirecutter/reviews/best-tsa-precheck/",
    "https://www.nytimes.com/wirecutter/reviews/best-global-entry-card/",
    "https://www.nytimes.com/wirecutter/reviews/best-clear-membership/",
    "https://www.nytimes.com/wirecutter/reviews/best-airline-status/",
    "https://www.nytimes.com/wirecutter/reviews/best-office-supplies-amazon/",
]

BLOOMBERG_URLS: List[str] = [
    "https://www.bloomberg.com/markets",
    "https://www.bloomberg.com/markets/stocks",
    "https://www.bloomberg.com/markets/currencies",
    "https://www.bloomberg.com/markets/commodities",
    "https://www.bloomberg.com/markets/rates-bonds",
    "https://www.bloomberg.com/markets/economic-calendar",
    "https://www.bloomberg.com/quote/SPX:IND",
    "https://www.bloomberg.com/quote/INDU:IND",
    "https://www.bloomberg.com/quote/CCMP:IND",
    "https://www.bloomberg.com/news/economics",
    "https://www.bloomberg.com/news/markets",
    "https://www.bloomberg.com/news/businessweek",
    "https://www.bloomberg.com/news/articles/2025-01-15/global-economic-outlook-davos",
    "https://www.bloomberg.com/news/articles/2025-02-03/fed-rate-decision-impact",
    "https://www.bloomberg.com/news/articles/2025-03-18/q1-earnings-tech-sector",
    "https://www.bloomberg.com/news/articles/2025-04-22/oil-prices-supply-chain",
    "https://www.bloomberg.com/news/articles/2025-05-10/business-travel-recovery-2025",
    "https://www.bloomberg.com/news/articles/2025-06-14/airline-stocks-summer-outlook",
    "https://www.bloomberg.com/news/articles/2025-07-08/corporate-bond-issuance-record",
    "https://www.bloomberg.com/news/articles/2025-08-19/cfo-survey-capex-cuts",
    "https://www.bloomberg.com/news/articles/2025-09-25/private-equity-fundraising-slows",
    "https://www.bloomberg.com/news/articles/2025-10-30/global-supply-chain-china-shift",
    "https://www.bloomberg.com/opinion",
    "https://www.bloomberg.com/opinion/articles/2025-11-12/ai-spending-vs-roi-cfo-tension",
    "https://www.bloomberg.com/opinion/articles/2025-12-08/return-to-office-trends",
    "https://www.bloomberg.com/professional/product/market-data/",
    "https://www.bloomberg.com/professional/solution/bloomberg-terminal/",
    "https://www.bloomberg.com/professional/solution/research-and-analysis/",
    "https://www.bloomberg.com/billionaires/",
    "https://www.bloomberg.com/billionaires/profiles/elon-r-musk/",
    "https://www.bloomberg.com/billionaires/profiles/jeffrey-p-bezos/",
    "https://www.bloomberg.com/news/newsletters/2025-01-20/five-things-to-start-your-day",
    "https://www.bloomberg.com/news/newsletters/2025-02-15/bloomberg-evening-briefing",
    "https://www.bloomberg.com/news/newsletters/2025-03-22/bw-daily",
    "https://www.bloomberg.com/news/topics/business",
    "https://www.bloomberg.com/news/topics/technology",
    "https://www.bloomberg.com/news/topics/wealth",
    "https://www.bloomberg.com/news/topics/leadership",
    "https://www.bloomberg.com/news/topics/work-shift",
    "https://www.bloomberg.com/news/topics/business-travel",
    "https://www.bloomberg.com/markets/etfs",
    "https://www.bloomberg.com/markets/sectors",
    "https://www.bloomberg.com/markets/sectors/energy",
    "https://www.bloomberg.com/markets/sectors/financials",
    "https://www.bloomberg.com/markets/sectors/technology",
    "https://www.bloomberg.com/markets/sectors/consumer-discretionary",
    "https://www.bloomberg.com/news/audio/2025-04-05/odd-lots-podcast",
    "https://www.bloomberg.com/news/videos/2025-05-12/big-take-podcast-summary",
    "https://www.bloomberg.com/quicktake",
    "https://www.bloomberg.com/news/sponsors/special-report-2025/",
    "https://www.bloomberg.com/news/articles/2025-01-09/airline-business-class-demand",
    "https://www.bloomberg.com/news/articles/2025-02-22/private-aviation-corporate-charter",
    "https://www.bloomberg.com/news/articles/2025-03-29/hotel-loyalty-programs-corporate",
    "https://www.bloomberg.com/news/articles/2025-04-14/expense-management-software-spend",
    "https://www.bloomberg.com/news/articles/2025-05-30/sap-concur-bookings-q1",
    "https://www.bloomberg.com/news/articles/2025-06-21/marriott-hilton-business-segment",
    "https://www.bloomberg.com/news/articles/2025-07-19/uber-for-business-growth",
    "https://www.bloomberg.com/news/articles/2025-08-26/corporate-card-market-amex-citi",
    "https://www.bloomberg.com/news/articles/2025-09-15/business-travel-association-survey",
    "https://www.bloomberg.com/news/articles/2025-10-04/cfo-corporate-travel-policy-2025",
]

CONCUR_EXPENSIFY_URLS: List[str] = [
    "https://www.concur.com/",
    "https://www.concur.com/expense-management",
    "https://www.concur.com/travel-management",
    "https://www.concur.com/invoice-management",
    "https://www.concur.com/sap-concur-pricing",
    "https://www.concur.com/business-needs",
    "https://www.concur.com/concur-expense",
    "https://www.concur.com/concur-travel",
    "https://www.concur.com/concur-invoice",
    "https://www.concur.com/concur-mobile",
    "https://www.concur.com/why-sap-concur",
    "https://www.concur.com/get-started",
    "https://www.concur.com/request-a-demo",
    "https://www.concur.com/resource-center",
    "https://www.concur.com/resource-center/whitepapers",
    "https://www.concur.com/resource-center/case-studies",
    "https://www.concur.com/resource-center/research-reports",
    "https://www.concur.com/blog",
    "https://www.concur.com/blog/article/expense-policy-best-practices",
    "https://www.concur.com/blog/article/travel-policy-compliance",
    "https://www.concur.com/blog/article/duty-of-care-business-travelers",
    "https://www.concur.com/blog/article/integrating-uber-with-sap-concur",
    "https://www.concur.com/blog/article/cfo-priorities-2025",
    "https://www.concur.com/blog/article/automating-expense-reports",
    "https://www.concur.com/customer-stories",
    "https://www.concur.com/integrations",
    "https://www.concur.com/integrations/uber",
    "https://www.concur.com/integrations/lyft",
    "https://www.concur.com/integrations/airbnb-for-work",
    "https://www.concur.com/integrations/booking-com-for-business",
    "https://www.concur.com/help/getting-started",
    "https://www.concur.com/help/expense-reports",
    "https://www.concur.com/help/travel-booking",
    "https://www.concur.com/help/receipts-mobile-capture",
    "https://www.expensify.com/",
    "https://www.expensify.com/expense-reports",
    "https://www.expensify.com/receipt-tracker",
    "https://www.expensify.com/corporate-card",
    "https://www.expensify.com/business-travel",
    "https://www.expensify.com/pricing",
    "https://www.expensify.com/sign-up",
    "https://www.expensify.com/expensify-card",
    "https://www.expensify.com/help",
    "https://www.expensify.com/help/expense-reports",
    "https://www.expensify.com/help/smartscan",
    "https://www.expensify.com/help/concierge",
    "https://www.expensify.com/help/billing-management",
    "https://www.expensify.com/blog",
    "https://www.expensify.com/blog/expense-policy-template",
    "https://www.expensify.com/blog/automate-expense-management",
    "https://www.expensify.com/blog/per-diem-rates-2025",
    "https://www.expensify.com/blog/mileage-tracking",
    "https://www.expensify.com/blog/cfo-survey-finance-trends",
    "https://www.expensify.com/customers",
    "https://www.expensify.com/integrations/quickbooks",
    "https://www.expensify.com/integrations/xero",
    "https://www.expensify.com/integrations/netsuite",
    "https://www.expensify.com/integrations/sage-intacct",
    "https://www.expensify.com/api-reference",
    "https://use.expensify.com/import-receipts",
    "https://use.expensify.com/expense-approval-workflow",
    "https://use.expensify.com/corporate-card-reconciliation",
]

SKIFT_URLS: List[str] = [
    "https://skift.com/",
    "https://skift.com/airlines/",
    "https://skift.com/hotels/",
    "https://skift.com/travel-management/",
    "https://skift.com/corporate-travel/",
    "https://skift.com/business-travel/",
    "https://skift.com/online-travel/",
    "https://skift.com/destinations/",
    "https://skift.com/short-term-rentals/",
    "https://skift.com/research/",
    "https://skift.com/research/research-reports/",
    "https://skift.com/research/skift-research-subscription/",
    "https://skift.com/podcasts/",
    "https://skift.com/skift-india/",
    "https://skift.com/skift-meetings/",
    "https://skift.com/2025/01/12/airlines-q4-earnings-roundup/",
    "https://skift.com/2025/01/29/corporate-travel-recovery-survey-2025/",
    "https://skift.com/2025/02/14/expedia-business-travel-vrbo/",
    "https://skift.com/2025/03/06/marriott-bonvoy-business-membership/",
    "https://skift.com/2025/03/22/concur-tripit-acquisition/",
    "https://skift.com/2025/04/03/hyatt-business-travel-strategy/",
    "https://skift.com/2025/04/19/iata-business-travel-forecast-2026/",
    "https://skift.com/2025/05/02/blackcar-services-corporate-clients/",
    "https://skift.com/2025/05/15/uber-for-business-growth-2025/",
    "https://skift.com/2025/05/28/lyft-business-segment-update/",
    "https://skift.com/2025/06/07/gbta-convention-2025-recap/",
    "https://skift.com/2025/06/21/duty-of-care-traveler-tracking/",
    "https://skift.com/2025/07/08/corporate-card-data-spend-management/",
    "https://skift.com/2025/07/24/sustainability-corporate-travel-policy/",
    "https://skift.com/2025/08/06/airline-loyalty-corporate-program/",
    "https://skift.com/2025/08/22/hotel-corporate-rates-q3/",
    "https://skift.com/2025/09/04/business-class-cabin-trends/",
    "https://skift.com/2025/09/18/airbnb-for-work-corporate/",
    "https://skift.com/2025/10/01/private-aviation-charter-demand/",
    "https://skift.com/2025/10/16/cwt-amex-gbt-merger-update/",
    "https://skift.com/2025/10/29/sap-concur-q3-bookings-volume/",
    "https://skift.com/2025/11/13/duty-of-care-app-comparison/",
    "https://skift.com/2025/11/26/business-traveler-survey-q4/",
    "https://skift.com/2025/12/10/2026-corporate-travel-outlook/",
    "https://skift.com/2025/12/22/year-in-review-business-travel/",
    "https://skift.com/megatrends/",
    "https://skift.com/megatrends/2025/",
    "https://skift.com/megatrends/blackcar-and-the-corporate-traveler/",
    "https://skift.com/sponsored/sap-concur-spend-management/",
    "https://skift.com/sponsored/marriott-bonvoy-business/",
    "https://skift.com/newsletter/",
    "https://skift.com/newsletter/morning-edition/",
    "https://skift.com/newsletter/business-travel-edition/",
    "https://skift.com/newsletter/airline-weekly/",
    "https://skift.com/newsletter/skift-research-weekly/",
    "https://skift.com/skift-pro/",
    "https://skift.com/jobs/",
    "https://skift.com/about/",
]

BUSINESS_INSIDER_URLS: List[str] = [
    "https://www.businessinsider.com/",
    "https://www.businessinsider.com/markets",
    "https://www.businessinsider.com/tech",
    "https://www.businessinsider.com/finance",
    "https://www.businessinsider.com/strategy",
    "https://www.businessinsider.com/strategy/career",
    "https://www.businessinsider.com/strategy/leadership",
    "https://www.businessinsider.com/strategy/productivity",
    "https://www.businessinsider.com/economy",
    "https://www.businessinsider.com/personal-finance",
    "https://www.businessinsider.com/personal-finance/credit-cards",
    "https://www.businessinsider.com/personal-finance/best-business-credit-cards",
    "https://www.businessinsider.com/personal-finance/best-airline-credit-cards",
    "https://www.businessinsider.com/personal-finance/amex-platinum-review",
    "https://www.businessinsider.com/personal-finance/chase-sapphire-reserve-review",
    "https://www.businessinsider.com/personal-finance/best-travel-insurance",
    "https://www.businessinsider.com/transportation",
    "https://www.businessinsider.com/transportation/airlines",
    "https://www.businessinsider.com/business-traveler-tips",
    "https://www.businessinsider.com/best-business-class-airlines",
    "https://www.businessinsider.com/best-noise-cancelling-headphones-business-traveler",
    "https://www.businessinsider.com/best-laptop-bag-for-business-travel",
    "https://www.businessinsider.com/best-carryon-luggage-business-traveler",
    "https://www.businessinsider.com/black-car-services-vs-uber-business",
    "https://www.businessinsider.com/airline-status-comparison-corporate",
    "https://www.businessinsider.com/airport-lounge-access-priority-pass",
    "https://www.businessinsider.com/marriott-bonvoy-business-elite",
    "https://www.businessinsider.com/hilton-honors-corporate-account",
    "https://www.businessinsider.com/sap-concur-vs-expensify-comparison",
    "https://www.businessinsider.com/best-meeting-software-zoom-vs-teams",
    "https://www.businessinsider.com/return-to-office-tracker-2025",
    "https://www.businessinsider.com/jobs-best-companies-to-work-for",
    "https://www.businessinsider.com/most-overworked-cities-corporate-burnout",
    "https://www.businessinsider.com/cfo-survey-corporate-spend-2025",
    "https://www.businessinsider.com/ceo-pay-2025-rankings",
    "https://www.businessinsider.com/biggest-companies-by-revenue",
    "https://www.businessinsider.com/most-valuable-startups-2025",
    "https://www.businessinsider.com/news/finance/wall-street-q4-bonus-pool-2025",
    "https://www.businessinsider.com/news/markets/morgan-stanley-quarterly-earnings",
    "https://www.businessinsider.com/news/tech/openai-revenue-2025-update",
    "https://www.businessinsider.com/news/strategy/mckinsey-leadership-survey-2026",
    "https://www.businessinsider.com/personal-finance/savings",
    "https://www.businessinsider.com/personal-finance/investing",
    "https://www.businessinsider.com/personal-finance/retirement",
    "https://www.businessinsider.com/personal-finance/banking",
    "https://www.businessinsider.com/lifestyle",
    "https://www.businessinsider.com/lifestyle/travel",
    "https://www.businessinsider.com/lifestyle/travel/best-luxury-hotels-business",
    "https://www.businessinsider.com/lifestyle/travel/black-car-vs-uber-comparison",
    "https://www.businessinsider.com/lifestyle/transportation/business-class-flight-deals",
    "https://www.businessinsider.com/insider-reviews",
    "https://www.businessinsider.com/insider-reviews/best-laptops-for-business",
    "https://www.businessinsider.com/insider-reviews/best-monitors-for-home-office",
    "https://www.businessinsider.com/the-conference-room-podcast",
    "https://www.businessinsider.com/podcast/business-traveler-show",
    "https://www.businessinsider.com/most-influential-business-leaders-list",
    "https://www.businessinsider.com/jobs/most-in-demand-skills-2026",
    "https://www.businessinsider.com/strategy/management/leadership-frameworks",
    "https://www.businessinsider.com/career-advancement-corporate-ladder",
]

PRODUCTIVITY_DOCS_URLS: List[str] = [
    "https://www.notion.so/help",
    "https://www.notion.so/help/getting-started",
    "https://www.notion.so/help/databases",
    "https://www.notion.so/help/templates",
    "https://www.notion.so/help/import-from-other-apps",
    "https://www.notion.so/help/sharing-and-permissions",
    "https://www.notion.so/help/integrations",
    "https://www.notion.so/help/api-reference",
    "https://www.notion.so/help/notion-ai",
    "https://www.notion.so/help/billing",
    "https://www.notion.so/templates/business-plan",
    "https://www.notion.so/templates/expense-tracker",
    "https://www.notion.so/templates/travel-planner",
    "https://www.notion.so/templates/meeting-notes",
    "https://slack.com/help",
    "https://slack.com/help/articles/360045842614-Get-started-with-Slack",
    "https://slack.com/help/articles/115004068387-Make-a-call-in-Slack",
    "https://slack.com/help/articles/115005265703-Manage-your-channels",
    "https://slack.com/help/articles/206846797-Manage-files-in-Slack",
    "https://slack.com/help/articles/360057511774-Slack-Connect",
    "https://slack.com/intl/en-us/features/connect",
    "https://slack.com/intl/en-us/enterprise",
    "https://slack.com/blog/productivity",
    "https://slack.com/blog/transformation",
    "https://api.slack.com/apps",
    "https://api.slack.com/web",
    "https://api.slack.com/messaging/sending",
    "https://asana.com/guide",
    "https://asana.com/guide/get-started",
    "https://asana.com/guide/team",
    "https://asana.com/guide/projects",
    "https://asana.com/guide/timeline",
    "https://asana.com/guide/portfolios",
    "https://asana.com/guide/integrations",
    "https://asana.com/guide/help/api/api-overview",
    "https://asana.com/templates/marketing",
    "https://asana.com/templates/sales",
    "https://asana.com/resources/work-management-platform",
    "https://help.asana.com/s/topic/0TO2j000000d2P1GAI/getting-started",
    "https://clickup.com/help",
    "https://clickup.com/help/getting-started",
    "https://clickup.com/help/spaces",
    "https://clickup.com/help/dashboards",
    "https://clickup.com/help/integrations",
    "https://clickup.com/templates/business-development",
    "https://clickup.com/templates/expense-report",
    "https://clickup.com/templates/travel-itinerary",
    "https://clickup.com/blog/productivity-systems",
    "https://linear.app/docs",
    "https://linear.app/docs/getting-started",
    "https://linear.app/docs/projects",
    "https://linear.app/docs/cycles",
    "https://linear.app/docs/integrations",
    "https://linear.app/docs/keyboard-shortcuts",
    "https://linear.app/docs/sdks",
    "https://monday.com/help",
    "https://monday.com/help/getting-started",
    "https://monday.com/help/article/integrations",
    "https://monday.com/templates/expense-tracker",
    "https://monday.com/templates/travel-planning",
    "https://monday.com/templates/sales-pipeline",
    "https://airtable.com/learn",
    "https://airtable.com/learn/courses/onboarding",
    "https://airtable.com/templates/expense-tracking",
    "https://airtable.com/templates/sales-crm",
]

TRAVEL_COMPARISON_URLS: List[str] = [
    "https://www.kayak.com/",
    "https://www.kayak.com/flights",
    "https://www.kayak.com/business",
    "https://www.kayak.com/hotels",
    "https://www.kayak.com/cars",
    "https://www.kayak.com/explore",
    "https://www.kayak.com/flights/JFK-LHR/2025-12-15",
    "https://www.kayak.com/flights/SFO-NRT/2025-11-20",
    "https://www.kayak.com/flights/ORD-CDG/2025-10-08",
    "https://www.kayak.com/flights/LAX-LHR/2025-09-30",
    "https://www.kayak.com/flights/EWR-FRA/2026-01-12",
    "https://www.kayak.com/flights/DFW-NRT/2025-12-03",
    "https://www.kayak.com/hotels/New-York/2025-12-15/2025-12-18",
    "https://www.kayak.com/hotels/London/2025-12-20/2025-12-23",
    "https://www.kayak.com/hotels/Tokyo/2025-11-20/2025-11-25",
    "https://www.kayak.com/cars/JFK/2025-12-15-12:00/2025-12-18-12:00",
    "https://www.kayak.com/news/airline-fees-comparison/",
    "https://www.kayak.com/news/best-business-class-deals/",
    "https://www.expedia.com/",
    "https://www.expedia.com/Flights",
    "https://www.expedia.com/Hotels",
    "https://www.expedia.com/business-travel",
    "https://www.expedia.com/Cars",
    "https://www.expedia.com/Cruises",
    "https://www.expedia.com/Flights-Search?leg1=from%3ANYC%2Cto%3ALHR&type=oneway",
    "https://www.expedia.com/Flights-Search?leg1=from%3ASFO%2Cto%3ANRT&type=oneway",
    "https://www.expedia.com/Hotels-Search?destination=New%20York",
    "https://www.expedia.com/Hotels-Search?destination=London",
    "https://www.expedia.com/Vacation-Packages",
    "https://www.expedia.com/Activities",
    "https://www.expedia.com/group-travel",
    "https://www.google.com/travel/flights",
    "https://www.google.com/travel/flights/search?q=Flights%20to%20London",
    "https://www.google.com/travel/flights/search?q=Flights%20to%20Tokyo",
    "https://www.google.com/travel/flights/search?q=Flights%20to%20Paris",
    "https://www.google.com/travel/flights/search?q=Flights%20to%20Frankfurt",
    "https://www.google.com/travel/hotels",
    "https://www.google.com/travel/hotels/New%20York",
    "https://www.google.com/travel/hotels/London",
    "https://www.google.com/travel/hotels/Tokyo",
    "https://www.google.com/travel/explore",
    "https://www.booking.com/",
    "https://www.booking.com/business.html",
    "https://www.booking.com/searchresults.en-us.html?ss=New+York",
    "https://www.booking.com/searchresults.en-us.html?ss=London",
    "https://www.booking.com/searchresults.en-us.html?ss=Tokyo",
    "https://www.booking.com/hotel/us/the-pierre.html",
    "https://www.booking.com/hotel/gb/the-savoy.html",
    "https://www.booking.com/hotel/jp/the-peninsula-tokyo.html",
    "https://www.hotels.com/",
    "https://www.hotels.com/de1632789/hotels-new-york-united-states-of-america/",
    "https://www.hotels.com/de1633004/hotels-london-united-kingdom/",
    "https://www.hotels.com/business-travel",
    "https://www.priceline.com/",
    "https://www.priceline.com/relax/hotel/search",
    "https://www.priceline.com/relax/at/airport/JFK/2025-12-15/2025-12-18/rooms-1/adults-1",
    "https://www.priceline.com/business-travel",
    "https://www.tripadvisor.com/",
    "https://www.tripadvisor.com/SmartDeals",
    "https://www.tripadvisor.com/HotelsList-New_York-zfp1.html",
    "https://www.tripadvisor.com/HotelsList-London-zfp1.html",
    "https://www.skyscanner.com/flights",
    "https://www.skyscanner.com/hotels",
    "https://www.skyscanner.com/cars",
]

EXECUTIVE_NEWS_URLS: List[str] = [
    "https://www.wsj.com/",
    "https://www.wsj.com/business",
    "https://www.wsj.com/business/c-suite",
    "https://www.wsj.com/business/c-suite/cfo-journal",
    "https://www.wsj.com/business/c-suite/cio-journal",
    "https://www.wsj.com/business/c-suite/risk-and-compliance",
    "https://www.wsj.com/finance",
    "https://www.wsj.com/economy",
    "https://www.wsj.com/markets",
    "https://www.wsj.com/tech",
    "https://www.wsj.com/lifestyle/careers",
    "https://www.wsj.com/lifestyle/travel",
    "https://www.wsj.com/lifestyle/travel/business-travel",
    "https://www.wsj.com/articles/cfo-priorities-2026-survey",
    "https://www.wsj.com/articles/return-to-office-mandate-impact-2025",
    "https://www.wsj.com/articles/corporate-travel-budgets-2026",
    "https://www.wsj.com/articles/business-class-pricing-trends",
    "https://www.wsj.com/articles/black-car-corporate-account-comparison",
    "https://www.wsj.com/articles/expense-management-software-market",
    "https://www.wsj.com/podcasts/the-journal",
    "https://www.wsj.com/podcasts/wsj-whats-news",
    "https://www.wsj.com/news/types/heard-on-the-street",
    "https://www.wsj.com/news/cmo-today",
    "https://www.ft.com/",
    "https://www.ft.com/business-travel",
    "https://www.ft.com/companies",
    "https://www.ft.com/markets",
    "https://www.ft.com/lex",
    "https://www.ft.com/management",
    "https://www.ft.com/management-leadership",
    "https://www.ft.com/work-careers",
    "https://www.ft.com/howtospendit",
    "https://www.ft.com/content/cfo-priorities-2026",
    "https://www.ft.com/content/business-travel-q1-2026",
    "https://www.ft.com/content/c-suite-survey-corporate-spend",
    "https://hbr.org/",
    "https://hbr.org/topic/leadership",
    "https://hbr.org/topic/strategy",
    "https://hbr.org/topic/managing-yourself",
    "https://hbr.org/topic/managing-people",
    "https://hbr.org/topic/decision-making",
    "https://hbr.org/topic/finance",
    "https://hbr.org/topic/operations-management",
    "https://hbr.org/topic/innovation",
    "https://hbr.org/topic/business-and-society",
    "https://hbr.org/2025/01/the-cfos-guide-to-spend-management",
    "https://hbr.org/2025/03/decision-fatigue-c-suite",
    "https://hbr.org/2025/06/return-to-office-leader-playbook",
    "https://hbr.org/2025/09/managing-corporate-travel-policy",
    "https://hbr.org/2025/11/leadership-burnout-business-travel",
    "https://www.forbes.com/",
    "https://www.forbes.com/leadership",
    "https://www.forbes.com/business",
    "https://www.forbes.com/innovation",
    "https://www.forbes.com/money",
    "https://www.forbes.com/lifestyle/travel",
    "https://www.forbes.com/sites/forbescfocouncil",
    "https://www.forbes.com/sites/forbesbusinesscouncil",
    "https://www.mckinsey.com/",
    "https://www.mckinsey.com/industries/travel-logistics-and-infrastructure/our-insights",
    "https://www.mckinsey.com/featured-insights",
    "https://www.mckinsey.com/business-functions/strategy-and-corporate-finance/our-insights",
    "https://www.economist.com/business",
    "https://www.economist.com/finance-and-economics",
    "https://www.economist.com/leaders",
]

LEISURE_TRAVEL_URLS: List[str] = [
    "https://www.cntraveler.com/",
    "https://www.cntraveler.com/destinations",
    "https://www.cntraveler.com/destinations/europe",
    "https://www.cntraveler.com/destinations/asia",
    "https://www.cntraveler.com/galleries/best-hotels-in-the-world",
    "https://www.cntraveler.com/story/best-luxury-resorts-2025",
    "https://www.cntraveler.com/galleries/best-rooftop-bars-new-york",
    "https://www.cntraveler.com/galleries/best-restaurants-paris",
    "https://www.cntraveler.com/inspiration",
    "https://www.cntraveler.com/inspiration/weekend-getaways",
    "https://www.travelandleisure.com/",
    "https://www.travelandleisure.com/luxury-travel",
    "https://www.travelandleisure.com/destinations",
    "https://www.travelandleisure.com/worlds-best",
    "https://www.travelandleisure.com/worlds-best/cities",
    "https://www.travelandleisure.com/worlds-best/hotels",
    "https://www.travelandleisure.com/worlds-best/airlines",
    "https://www.travelandleisure.com/trip-ideas/weekend-getaways",
    "https://www.travelandleisure.com/holiday-travel/holiday-vacation-ideas",
    "https://www.afar.com/",
    "https://www.afar.com/magazine/best-of-the-world",
    "https://www.afar.com/places/europe",
    "https://www.afar.com/inspiration/luxury-travel",
    "https://www.afar.com/magazine/the-most-beautiful-resorts",
    "https://www.afar.com/places/london-united-kingdom",
    "https://www.afar.com/places/tokyo-japan",
    "https://www.afar.com/magazine/where-to-go-2026",
    "https://www.departures.com/",
    "https://www.departures.com/travel/luxury-hotels",
    "https://www.departures.com/lifestyle",
]

SOCIAL_COMMUNITY_URLS: List[str] = [
    "https://www.linkedin.com/feed/",
    "https://www.linkedin.com/in/satyanadella/",
    "https://www.linkedin.com/in/jeffweiner08/",
    "https://www.linkedin.com/in/williamhgates/",
    "https://www.linkedin.com/pulse/topics/leadership-and-management/",
    "https://www.linkedin.com/pulse/topics/business-travel/",
    "https://www.linkedin.com/pulse/topics/corporate-finance/",
    "https://www.linkedin.com/pulse/cfo-priorities-2026-bloomberg",
    "https://www.linkedin.com/pulse/state-business-travel-2026-skift",
    "https://www.linkedin.com/posts/concur_expense-policy-trends-2026",
    "https://www.linkedin.com/groups/3041212/",
    "https://www.linkedin.com/groups/3742641/",
    "https://www.linkedin.com/learning/topics/business-travel",
    "https://www.linkedin.com/learning/courses/expense-management-fundamentals",
    "https://www.linkedin.com/learning/leadership-development",
    "https://www.reddit.com/r/businesstravel/",
    "https://www.reddit.com/r/businesstravel/comments/best-corporate-card-2026/",
    "https://www.reddit.com/r/businesstravel/comments/black-car-vs-uber-recap/",
    "https://www.reddit.com/r/businesstravel/comments/concur-tips-power-users/",
    "https://www.reddit.com/r/digitalnomad/",
    "https://www.reddit.com/r/digitalnomad/comments/best-coworking-spaces-tokyo/",
    "https://www.reddit.com/r/cscareerquestions/",
    "https://www.reddit.com/r/cscareerquestions/comments/managing-up/",
    "https://www.reddit.com/r/personalfinance/",
    "https://www.reddit.com/r/finance/",
    "https://www.reddit.com/r/financialindependence/",
    "https://www.reddit.com/r/Entrepreneur/",
    "https://www.reddit.com/r/smallbusiness/",
    "https://x.com/business",
    "https://x.com/WSJ",
    "https://x.com/HarvardBiz",
    "https://x.com/business_travel",
    "https://x.com/Skift",
    "https://x.com/SAPConcur",
    "https://x.com/Bloomberg",
]


CANDIDATE_URLS: Dict[str, List[str]] = {
    "wirecutter": WIRECUTTER_URLS,
    "bloomberg": BLOOMBERG_URLS,
    "concur_expensify": CONCUR_EXPENSIFY_URLS,
    "skift": SKIFT_URLS,
    "business_insider": BUSINESS_INSIDER_URLS,
    "productivity_docs": PRODUCTIVITY_DOCS_URLS,
    "travel_comparison": TRAVEL_COMPARISON_URLS,
    "executive_news": EXECUTIVE_NEWS_URLS,
    "leisure_travel": LEISURE_TRAVEL_URLS,
    "social_community": SOCIAL_COMMUNITY_URLS,
}


def get_full_pool() -> List[Tuple[str, str]]:
    """Flatten the candidate pool to (source, url) tuples."""
    out: List[Tuple[str, str]] = []
    for source, urls in CANDIDATE_URLS.items():
        for url in urls:
            out.append((source, url))
    return out


# =============================================================================
# Stratified entropy-ranked sampling
# =============================================================================


@dataclass(frozen=True)
class CandidateScore:
    """Per-URL active-learning score row."""

    url: str
    source: str
    predicted_class: str
    proba: List[float]
    entropy: float


def _shannon_entropy(p: np.ndarray) -> float:
    """Shannon entropy in nats (clip to avoid log(0))."""
    clipped = np.clip(p, 1e-12, 1.0)
    return float(-np.sum(clipped * np.log(clipped)))


def stratified_top_n(
    classifier,
    candidates: List[Tuple[str, str]],
    *,
    n: int = 80,
    min_per_class: int = 10,
    exclude_urls: Optional[List[str]] = None,
) -> List[CandidateScore]:
    """Score, entropy-rank, and stratify the candidate pool.

    Algorithm:
      1. Filter ``exclude_urls`` (URLs already labeled).
      2. Score each remaining candidate; compute entropy per row.
      3. **Per-class floor by P(class | url) — not by argmax.** For
         each class, take the top-``min_per_class`` candidates with
         the highest predicted probability for that class (regardless
         of which class argmax-predicts), with entropy as tiebreaker.
         This guarantees the ≥``min_per_class`` floor holds even when
         the interim classifier is class-imbalanced (e.g., a class
         with n=3 training labels rarely argmax-predicts).
      4. Fill remaining ``n - selected`` slots from the global
         entropy-ranked pool of unselected candidates (most
         uncertain overall).

    Returns at most ``n`` CandidateScore rows, in order of overall
    entropy (highest = most uncertain first)."""
    excluded = set(exclude_urls or [])
    filtered = [
        (src, url) for (src, url) in candidates if url not in excluded
    ]
    if not filtered:
        return []

    urls_only = [u for (_, u) in filtered]
    sources_only = [s for (s, _) in filtered]
    proba = classifier.predict_proba(urls_only)

    rows: List[CandidateScore] = []
    for url, src, row in zip(urls_only, sources_only, proba):
        ix = int(np.argmax(row))
        rows.append(
            CandidateScore(
                url=url,
                source=src,
                predicted_class=classifier.classes_[ix],
                proba=[float(x) for x in row],
                entropy=_shannon_entropy(row),
            )
        )

    selected: List[CandidateScore] = []
    selected_urls: set = set()

    # Stage 1: per-class floor by P(class | url). For each class,
    # pull the top min_per_class candidates with highest probability
    # for THAT class, regardless of argmax. Entropy is the tiebreaker.
    classes = list(classifier.classes_)
    for cls_ix, cls in enumerate(classes):
        cls_ranked = sorted(
            rows,
            key=lambda r, ix=cls_ix: (-r.proba[ix], -r.entropy),
        )
        added = 0
        for r in cls_ranked:
            if r.url in selected_urls:
                continue
            selected.append(r)
            selected_urls.add(r.url)
            added += 1
            if added >= min_per_class:
                break

    # Stage 2: fill remaining slots from global entropy ranking.
    remaining = [r for r in rows if r.url not in selected_urls]
    remaining.sort(key=lambda x: -x.entropy)
    slots_left = max(0, n - len(selected))
    for r in remaining[:slots_left]:
        selected.append(r)
        selected_urls.add(r.url)

    # Final order = overall entropy-descending (most uncertain first).
    selected.sort(key=lambda x: -x.entropy)
    # Trim to n if stage-1 over-allocated (n_classes × min_per_class > n).
    return selected[:n]
