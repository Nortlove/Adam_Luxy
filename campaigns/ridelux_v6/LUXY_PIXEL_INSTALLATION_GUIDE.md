# LUXY Ride Pixel Installation Guide
## Booking Confirmation Page + Landing Page Setup

**For:** Whoever manages luxyride.com (dev team or GTM admin)
**From:** INFORMATIV (Chris Nocera, CNocera@rebelliongroup.com)
**Date:** April 15, 2026

---

## Overview

Two scripts need to be installed on luxyride.com:

1. **StackAdapt Universal Pixel** -- tracks ad impressions and conversions for campaign optimization
2. **INFORMATIV Behavioral Intelligence** -- captures psychological engagement signals that make the ads smarter over time

Both scripts are lightweight, async, and will not slow down your pages.

---

## PART 1: All Pages (Landing Pages, Browse Pages, etc.)

Place both of these tags on **every page** of luxyride.com. If you use Google Tag Manager, add each as a Custom HTML tag that fires on "All Pages."

### Tag A: StackAdapt Universal Pixel

```html
<!-- StackAdapt Universal Pixel — All Pages -->
<script>
  !function(s,a,e,v,n,t,z){if(s.saq)return;n=s.saq=function(){
  n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!s._saq)s._saq=n;n.push=n;n.loaded=!0;n.version='1.0';n.queue=[];
  t=a.createElement(e);t.async=!0;t.src=v;z=a.getElementsByTagName(e)[0];
  z.parentNode.insertBefore(t,z)}(window,document,'script',
  'https://tags.srv.stackadapt.com/events.js');
  saq('ts', 'YOUR_UNIVERSAL_PIXEL_ID');
</script>
```

> **Action required:** Replace `YOUR_UNIVERSAL_PIXEL_ID` with the actual pixel ID from your StackAdapt account. Ask Becca (Zero Gravity Marketing) for this value if you do not have it.

### Tag B: INFORMATIV Behavioral Intelligence

```html
<!-- INFORMATIV Behavioral Intelligence — All Pages -->
<script src="https://focused-encouragement-production.up.railway.app/static/telemetry/informativ.js"
        data-endpoint="https://focused-encouragement-production.up.railway.app/api/v1/signals/session"
        data-conversion-endpoint="https://focused-encouragement-production.up.railway.app/api/v1/signals/conversion"
        defer></script>
```

This tag is copy-paste ready. No values to replace.

**What it does (no action needed, just FYI):**
- Assigns each visitor a first-party cookie ID (90-day lifetime)
- Tracks scroll depth, dwell time per section, and navigation path
- Reads StackAdapt click parameters from the URL (`sapid`, `cid`, `crid`, `domain`)
- Classifies the visit source (ad click, organic search, direct, social)
- Sends a single beacon on page exit -- no continuous network requests

---

## PART 2: Booking Confirmation Page ONLY

This is the most important part. When a booking is completed and the user lands on the confirmation/thank-you page, we need to fire a conversion event with full context.

**Where to install this:** The page that displays after a successful booking. This is typically a URL like `/confirmation`, `/booking-confirmed`, `/thank-you`, `/booking/complete`, or `/success`.

### Option A: Automatic Detection (Simplest)

If your confirmation page URL contains any of these strings, the INFORMATIV script from Part 1 will **automatically detect the conversion** -- no extra code needed:

- `/confirmation`
- `/booking-confirmed`
- `/thank-you`
- `/booking/complete`
- `/success`

If your confirmation page URL matches one of these patterns, skip to Part 3 (StackAdapt conversion event). The INFORMATIV side is handled automatically.

### Option B: Manual Conversion Fire (If Your URL Does Not Match Above)

If your confirmation page has a different URL pattern, or if you want to pass revenue and order details, add this script **on the confirmation page only**, **after** the two tags from Part 1:

```html
<!-- INFORMATIV Conversion — Booking Confirmation Page Only -->
<script>
(function() {
  // Wait for informativ.js to initialize
  function fireConversion() {
    if (window.informativ && window.informativ.convert) {
      window.informativ.convert("booking_complete", {
        // Replace these with real values from your booking system.
        // Use your template engine's variables (e.g., Liquid, Jinja, PHP, etc.)
        revenue: 0,         // e.g., {{ booking.total_price }}
        order_id: "",       // e.g., "{{ booking.confirmation_number }}"
        currency: "USD"
      });
    } else {
      // Retry once after 500ms if informativ.js hasn't loaded yet
      setTimeout(fireConversion, 500);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fireConversion);
  } else {
    fireConversion();
  }
})();
</script>
```

**Replace the placeholder values:**

| Placeholder | What to put there | Example |
|---|---|---|
| `revenue: 0` | The booking total in dollars | `revenue: 245.00` |
| `order_id: ""` | The booking confirmation number | `order_id: "LUX-2026-A1B2C3"` |

If you cannot dynamically inject revenue/order_id, just leave them as `0` and `""`. The conversion will still be tracked.

---

### Part 2B: StackAdapt Conversion Event (Required)

In addition to the INFORMATIV conversion above, StackAdapt needs its own conversion event to attribute the booking to the ad campaign. Add this on the confirmation page, **after** the Universal Pixel from Part 1:

```html
<!-- StackAdapt Conversion — Booking Confirmation Page Only -->
<script>
(function() {
  function fireStackAdaptConversion() {
    if (typeof saq === "function") {
      // Read the INFORMATIV visitor and session IDs so the conversion
      // can be linked back to the full behavioral session
      var visitorId = (window.informativ && window.informativ.getVisitorId)
        ? window.informativ.getVisitorId() : "";
      var sessionId = (window.informativ && window.informativ.getSessionId)
        ? window.informativ.getSessionId() : "";

      // Read the segment_id and decision_id from URL parameters
      // (these are passed through from the ad click URL)
      function getParam(name) {
        var match = location.search.match(new RegExp("[?&]" + name + "=([^&#]*)"));
        return match ? decodeURIComponent(match[1]) : "";
      }

      saq("conv", "luxy_booking_complete", {
        // Revenue — replace with your template variable
        "revenue": 0,               // e.g., {{ booking.total_price }}
        "order_id": "",              // e.g., "{{ booking.confirmation_number }}"
        "currency": "USD",

        // INFORMATIV enrichment fields — DO NOT REMOVE
        // These link the conversion back to the psychological decision context
        "informativ_segment_id": getParam("segment_id") || getParam("informativ_segment_id") || "",
        "decision_id": getParam("decision_id") || getParam("informativ_decision_id") || "",
        "informativ_visitor_id": visitorId,
        "informativ_session_id": sessionId,
        "page_url": window.location.href,
        "uid": getParam("sapid") || ""
      });
    } else {
      setTimeout(fireStackAdaptConversion, 500);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fireStackAdaptConversion);
  } else {
    fireStackAdaptConversion();
  }
})();
</script>
```

**Same replacement as before:** Put your real `revenue` and `order_id` values in place of the placeholders. Everything else is automatic.

---

## PART 3: URL Parameter Passthrough (Critical)

For all of this to work, the ad click URLs in StackAdapt must pass through the right parameters, and those parameters must survive through to the confirmation page.

### StackAdapt Click URL Macros

The agency (Becca / Zero Gravity) will configure this in StackAdapt, but for reference, the click-through URL for each campaign should look like:

```
https://luxyride.com/your-landing-page?sapid={{CLICK_ID}}&cid={{CAMPAIGN_ID}}&crid={{CREATIVE_ID}}&domain={{DOMAIN}}&ts={{TIMESTAMP}}&segment_id=SEGMENT_ID_HERE&decision_id={{DECISION_ID}}
```

Where:
- `{{CLICK_ID}}`, `{{CAMPAIGN_ID}}`, `{{CREATIVE_ID}}`, `{{DOMAIN}}`, `{{TIMESTAMP}}` are StackAdapt macros (they auto-populate)
- `SEGMENT_ID_HERE` is the literal segment ID for that campaign (e.g., `informativ_careful_truster_authority_luxury_transportation_t1`)
- `{{DECISION_ID}}` is the INFORMATIV decision ID macro (if StackAdapt supports echoing it; otherwise omit)

### Parameter Persistence Across Pages

The `informativ.js` script reads URL parameters on the landing page and holds them in memory for the session. However, if the user navigates through multiple pages before reaching the confirmation page, the URL parameters may be lost from the address bar.

**You must do ONE of the following** to ensure the parameters reach the confirmation page:

**Option 1 (Recommended): Store in sessionStorage**

Add this snippet to your site's global JavaScript (runs on every page):

```html
<!-- Parameter persistence — All Pages, before other scripts -->
<script>
(function() {
  // On landing (URL has params), store them
  var params = ["sapid", "cid", "crid", "domain", "ts", "segment_id", "decision_id"];
  var search = window.location.search;
  if (search) {
    params.forEach(function(p) {
      var match = search.match(new RegExp("[?&]" + p + "=([^&#]*)"));
      if (match) {
        try { sessionStorage.setItem("informativ_" + p, decodeURIComponent(match[1])); } catch(e) {}
      }
    });
  }

  // Expose a helper for the conversion script to read stored params
  window._informativ_param = function(name) {
    var match = location.search.match(new RegExp("[?&]" + name + "=([^&#]*)"));
    if (match) return decodeURIComponent(match[1]);
    try { return sessionStorage.getItem("informativ_" + name) || ""; } catch(e) { return ""; }
  };
})();
</script>
```

Then in the StackAdapt conversion script (Part 2B), replace the `getParam` calls with `window._informativ_param`:

```javascript
// Instead of: getParam("segment_id")
// Use:        window._informativ_param("segment_id")
```

**Option 2: Append parameters to all internal links**

If sessionStorage is not an option, ensure your booking flow passes the URL parameters forward through each step (e.g., as hidden form fields or query parameters on each page transition).

---

## PART 4: Section Tagging (Optional, Improves Intelligence)

The INFORMATIV script can track how long visitors spend on specific sections of the page. This is optional but highly recommended for landing pages.

Add a `data-informativ-section` attribute to key content blocks:

```html
<section data-informativ-section="hero">
  <!-- Hero banner content -->
</section>

<section data-informativ-section="fleet">
  <!-- Fleet/vehicle gallery -->
</section>

<section data-informativ-section="pricing">
  <!-- Pricing information -->
</section>

<section data-informativ-section="corporate-program">
  <!-- Corporate program details -->
</section>

<section data-informativ-section="testimonials">
  <!-- Customer testimonials -->
</section>

<section data-informativ-section="booking-cta">
  <!-- Book now call-to-action -->
</section>
```

The script will automatically track:
- How long each section was visible (dwell time)
- How much of each section was scrolled through
- How many clicks occurred within each section

This data feeds back into the ad optimization system. The more sections you tag, the better the system learns which content resonates with which audience.

---

## Complete Installation Summary

| Where | What to Install |
|---|---|
| **All pages** (via GTM or direct) | Tag A: StackAdapt Universal Pixel |
| **All pages** (via GTM or direct) | Tag B: INFORMATIV informativ.js |
| **All pages** (via GTM or direct) | Parameter persistence script (Part 3) |
| **Confirmation page only** | INFORMATIV conversion call (Part 2, Option B) -- unless URL auto-detects |
| **Confirmation page only** | StackAdapt conversion event (Part 2B) |
| **Landing pages** (optional) | Section tagging attributes (Part 4) |

---

## Testing Checklist

After installation, verify the following:

1. **Visit a landing page with ad parameters:**
   ```
   https://luxyride.com/?sapid=test123&cid=campaign1&crid=creative1&segment_id=informativ_careful_truster_authority_luxury_transportation_t1
   ```

2. **Open browser DevTools > Network tab** and confirm:
   - [ ] `informativ.js` loads successfully (200 status)
   - [ ] `events.js` (StackAdapt) loads successfully (200 status)

3. **Navigate to the confirmation page** and confirm:
   - [ ] A POST request fires to `https://focused-encouragement-production.up.railway.app/api/v1/signals/conversion` (INFORMATIV conversion)
   - [ ] A StackAdapt `conv` event fires (visible in the Network tab as a request to `tags.srv.stackadapt.com`)

4. **Check the browser console** for errors -- there should be none from either script.

5. **Verify parameter persistence:** Navigate from the landing page to another page, then to the confirmation page. Open DevTools and run:
   ```javascript
   console.log(window._informativ_param("segment_id"));
   // Should print the segment_id from step 1
   ```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `informativ.js` returns 404 | Script URL wrong | Verify URL is exactly `https://focused-encouragement-production.up.railway.app/static/telemetry/informativ.js` |
| No conversion fires on confirmation page | URL pattern not matched | Use Option B (manual fire) from Part 2 |
| `segment_id` is empty on confirmation page | Parameters lost during navigation | Install the sessionStorage script from Part 3 |
| `saq is not defined` | StackAdapt pixel not loaded | Ensure Tag A is installed before the conversion script |
| `window.informativ` is undefined | informativ.js not loaded yet | The scripts include retry logic; check that Tag B is on the page |

---

## Questions?

Contact Chris Nocera: CNocera@rebelliongroup.com

For StackAdapt-specific setup (pixel ID, campaign configuration, bid strategy): contact Becca at Zero Gravity Marketing.
