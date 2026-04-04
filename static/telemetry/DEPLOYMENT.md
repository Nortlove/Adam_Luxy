# INFORMATIV Telemetry Deployment Guide

## 1. Script Installation

Add to the advertiser's site (e.g., luxyride.com) before `</body>`:

```html
<script src="https://{INFORMATIV_HOST}/static/telemetry/informativ.js"
        data-endpoint="https://{INFORMATIV_HOST}/api/v1/signals/session"
        defer></script>
```

## 2. Section Tagging

The script automatically tracks DOM elements matching:
- Elements with `data-informativ-section` attribute
- Elements with IDs starting with `section-`

For luxyride.com, ensure these section IDs exist:

```html
<section id="section-pricing">...</section>
<section id="section-reviews">...</section>
<section id="section-testimonials">...</section>
<section id="section-how-it-works">...</section>
<section id="section-safety">...</section>
<section id="section-fleet">...</section>
<section id="section-booking">...</section>
<section id="section-faq">...</section>
```

## 3. StackAdapt Click URL Macro Template

Configure in StackAdapt campaign settings as the click-through URL:

```
https://luxyride.com/?sapid={SA_POSTBACK_ID}&cid={CAMPAIGN_ID}&crid={CREATIVE_ID}&domain={DOMAIN}&device={DEVICE_TYPE}&ts={TIMESTAMP}
```

| Macro | Purpose | Signal |
|-------|---------|--------|
| `{SA_POSTBACK_ID}` | Links click to StackAdapt impression | All signals |
| `{CAMPAIGN_ID}` | Campaign attribution | Signal 1, 2 |
| `{CREATIVE_ID}` | Creative attribution | Signal 1, 2 |
| `{DOMAIN}` | Publisher domain | Signal 5 |
| `{DEVICE_TYPE}` | Device classification | Signal 5 |
| `{TIMESTAMP}` | Impression timestamp | Signal 1 (click latency) |

## 4. StackAdapt Universal Pixel

Install the Universal Pixel on luxyride.com with page URL rules:

| Page Type | URL Rule | Purpose |
|-----------|----------|---------|
| Landing | `/` | Arrival tracking |
| Pricing | `/pricing*` | Price friction signal |
| Booking | `/booking*` | Intention-action gap |
| Confirmation | `/confirmation*` | Conversion pixel |

## 5. API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/signals/session` | POST | Receive telemetry (called by JS) |
| `/api/v1/signals/user/{id}` | GET | Retrieve signal profile |
| `/api/v1/signals/population` | GET | Population baselines |
| `/api/v1/signals/health` | GET | Health check |
