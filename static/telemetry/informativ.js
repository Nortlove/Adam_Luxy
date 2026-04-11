/**
 * INFORMATIV Site Telemetry Script
 * Enhancement #34: Nonconscious Signal Intelligence Layer
 *
 * Lightweight instrumentation for advertiser sites (e.g., luxyride.com).
 * Captures behavioral signals that feed the 6 nonconscious signal engines:
 *
 *   1. Section-level dwell via IntersectionObserver
 *   2. Scroll velocity + direction changes via requestAnimationFrame
 *   3. URL parameter parsing for StackAdapt click macros (sapid, cid, crid, etc.)
 *   4. Referral classification (ad-attributed vs organic vs direct)
 *   5. First-party cookie for return visit detection
 *   6. Page navigation tracking (multi-page sessions)
 *   7. Micro-interactions (clicks, expands, video plays) per section
 *   8. Session aggregation + beacon emission on unload
 *
 * Deploy: add <script src="https://{INFORMATIV_HOST}/static/telemetry/informativ.js"
 *         data-endpoint="https://{INFORMATIV_HOST}/api/v1/signals/session"></script>
 *
 * Size target: <4KB gzipped. No dependencies.
 */
(function () {
  "use strict";

  // ═══════════════════════════════════════════════════════════════════
  // CONFIGURATION
  // ═══════════════════════════════════════════════════════════════════

  var SCRIPT_TAG = document.currentScript;
  var ENDPOINT =
    (SCRIPT_TAG && SCRIPT_TAG.getAttribute("data-endpoint")) ||
    "/api/v1/signals/session";
  var COOKIE_NAME = "informativ_vid";
  var COOKIE_DAYS = 90;
  var SCROLL_SAMPLE_INTERVAL_MS = 250; // ~4Hz scroll sampling (battery-friendly)
  var MIN_SESSION_SECONDS = 1; // don't emit sessions under 1s (bot filter)
  var SECTION_SELECTOR = "[data-informativ-section], [id^='section-']";

  // ═══════════════════════════════════════════════════════════════════
  // VISITOR ID (first-party cookie)
  // ═══════════════════════════════════════════════════════════════════

  function generateId() {
    // Compact random ID: timestamp + random suffix
    return (
      Date.now().toString(36) +
      Math.random().toString(36).substring(2, 8)
    );
  }

  function getCookie(name) {
    var match = document.cookie.match(
      new RegExp("(^| )" + name + "=([^;]+)")
    );
    return match ? match[2] : null;
  }

  function setCookie(name, value, days) {
    var expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie =
      name +
      "=" +
      value +
      "; expires=" +
      expires +
      "; path=/; SameSite=Lax; Secure";
  }

  var existingVid = getCookie(COOKIE_NAME);
  var isReturnVisit = !!existingVid;
  var visitorId = existingVid || generateId();
  setCookie(COOKIE_NAME, visitorId, COOKIE_DAYS);

  // Count previous visits from a separate counter cookie
  var visitCountCookie = getCookie(COOKIE_NAME + "_n");
  var previousVisitCount = visitCountCookie ? parseInt(visitCountCookie, 10) : 0;
  setCookie(COOKIE_NAME + "_n", String(previousVisitCount + 1), COOKIE_DAYS);

  // ═══════════════════════════════════════════════════════════════════
  // URL PARAMETER PARSING (StackAdapt macros)
  // ═══════════════════════════════════════════════════════════════════

  function getParam(name) {
    var match = location.search.match(
      new RegExp("[?&]" + name + "=([^&#]*)")
    );
    return match ? decodeURIComponent(match[1]) : null;
  }

  var sapid = getParam("sapid");
  var campaignId = getParam("cid");
  var creativeId = getParam("crid");
  var publisherDomain = getParam("domain");
  var impressionTs = getParam("ts");

  // ═══════════════════════════════════════════════════════════════════
  // REFERRAL CLASSIFICATION
  // ═══════════════════════════════════════════════════════════════════

  function classifyReferral() {
    if (sapid) return "ad_click";
    var ref = document.referrer;
    if (!ref) return "direct";
    try {
      var host = new URL(ref).hostname;
      if (/google|bing|yahoo|duckduckgo|baidu/.test(host))
        return "organic_search";
      if (/facebook|twitter|instagram|linkedin|tiktok|reddit/.test(host))
        return "social";
    } catch (e) {
      // malformed referrer
    }
    return "unknown";
  }

  var referralType = classifyReferral();

  // ═══════════════════════════════════════════════════════════════════
  // DEVICE CLASSIFICATION
  // ═══════════════════════════════════════════════════════════════════

  function classifyDevice() {
    var w = window.innerWidth;
    if (w < 768) return "mobile";
    if (w < 1024) return "tablet";
    return "desktop";
  }

  // ═══════════════════════════════════════════════════════════════════
  // SESSION STATE
  // ═══════════════════════════════════════════════════════════════════

  var sessionId = generateId();
  var arrivalTimestamp = Date.now() / 1000; // unix seconds
  var firstInteractionTimestamp = null;
  var pagesVisited = [
    {
      url: location.pathname,
      dwell_seconds: 0,
      scroll_depth_pct: 0,
      timestamp: arrivalTimestamp,
    },
  ];

  // ═══════════════════════════════════════════════════════════════════
  // SECTION DWELL TRACKING (IntersectionObserver)
  // ═══════════════════════════════════════════════════════════════════

  var sectionState = {}; // section_id -> {enterTime, totalDwell, scrollDepth, interactions, firstVisible}

  function initSectionTracking() {
    var sections = document.querySelectorAll(SECTION_SELECTOR);
    if (!sections.length) return;

    var observer = new IntersectionObserver(
      function (entries) {
        var now = performance.now();
        entries.forEach(function (entry) {
          var id =
            entry.target.getAttribute("data-informativ-section") ||
            entry.target.id;
          if (!id) return;

          if (!sectionState[id]) {
            sectionState[id] = {
              enterTime: null,
              totalDwell: 0,
              scrollDepth: 0,
              interactions: 0,
              firstVisible: null,
            };
          }
          var s = sectionState[id];

          if (entry.isIntersecting) {
            s.enterTime = now;
            if (!s.firstVisible) s.firstVisible = Date.now() / 1000;
            // Track max intersection ratio as scroll depth through section
            if (entry.intersectionRatio > s.scrollDepth) {
              s.scrollDepth = entry.intersectionRatio;
            }
          } else if (s.enterTime) {
            s.totalDwell += (now - s.enterTime) / 1000;
            s.enterTime = null;
          }
        });
      },
      { threshold: [0, 0.25, 0.5, 0.75, 1.0] }
    );

    sections.forEach(function (el) {
      observer.observe(el);
    });

    // Track clicks within sections
    document.addEventListener(
      "click",
      function (e) {
        var target = e.target.closest(SECTION_SELECTOR);
        if (target) {
          var id =
            target.getAttribute("data-informativ-section") || target.id;
          if (sectionState[id]) {
            sectionState[id].interactions++;
          }
        }
      },
      true
    );
  }

  // ═══════════════════════════════════════════════════════════════════
  // SCROLL METRICS (requestAnimationFrame sampling)
  // ═══════════════════════════════════════════════════════════════════

  var scrollMetrics = {
    maxDepth: 0,
    velocities: [],
    directionChanges: 0,
    scrollBacks: 0,
    lastScrollY: 0,
    lastDirection: 0, // 1=down, -1=up, 0=none
    lastSampleTime: 0,
  };

  function sampleScroll() {
    var now = performance.now();
    if (now - scrollMetrics.lastSampleTime < SCROLL_SAMPLE_INTERVAL_MS) return;
    scrollMetrics.lastSampleTime = now;

    var scrollY = window.scrollY || window.pageYOffset;
    var docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight
    );
    var viewHeight = window.innerHeight;
    var maxScroll = docHeight - viewHeight;
    var depth = maxScroll > 0 ? scrollY / maxScroll : 0;

    if (depth > scrollMetrics.maxDepth) scrollMetrics.maxDepth = depth;

    var delta = scrollY - scrollMetrics.lastScrollY;
    if (Math.abs(delta) > 2) {
      // ignore sub-pixel jitter
      var elapsed =
        (now - (scrollMetrics.lastSampleTime || now)) / 1000 || 0.25;
      var velocity = Math.abs(delta) / Math.max(elapsed, 0.01);
      scrollMetrics.velocities.push(velocity);

      var dir = delta > 0 ? 1 : -1;
      if (scrollMetrics.lastDirection !== 0 && dir !== scrollMetrics.lastDirection) {
        scrollMetrics.directionChanges++;
        if (dir === -1) scrollMetrics.scrollBacks++;
      }
      scrollMetrics.lastDirection = dir;
    }
    scrollMetrics.lastScrollY = scrollY;
  }

  var scrollRafId = null;
  function scrollLoop() {
    sampleScroll();
    scrollRafId = requestAnimationFrame(scrollLoop);
  }

  // ═══════════════════════════════════════════════════════════════════
  // FIRST INTERACTION DETECTION
  // ═══════════════════════════════════════════════════════════════════

  function onFirstInteraction() {
    if (!firstInteractionTimestamp) {
      firstInteractionTimestamp = Date.now() / 1000;
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // SESSION EMISSION
  // ═══════════════════════════════════════════════════════════════════

  function finalizeSections() {
    // Close any sections still in viewport
    var now = performance.now();
    var engagements = [];
    for (var id in sectionState) {
      var s = sectionState[id];
      if (s.enterTime) {
        s.totalDwell += (now - s.enterTime) / 1000;
        s.enterTime = null;
      }
      if (s.totalDwell > 0 || s.interactions > 0) {
        engagements.push({
          section_id: id,
          dwell_seconds: Math.round(s.totalDwell * 100) / 100,
          scroll_depth_pct: Math.round(s.scrollDepth * 100) / 100,
          interactions: s.interactions,
          first_visible_ts: s.firstVisible,
        });
      }
    }
    return engagements;
  }

  function buildPayload() {
    var departureTimestamp = Date.now() / 1000;

    // Update landing page dwell
    if (pagesVisited.length > 0) {
      var last = pagesVisited[pagesVisited.length - 1];
      last.dwell_seconds =
        Math.round((departureTimestamp - last.timestamp) * 100) / 100;
      last.scroll_depth_pct =
        Math.round(scrollMetrics.maxDepth * 100) / 100;
    }

    var avgVelocity = 0;
    if (scrollMetrics.velocities.length > 0) {
      var sum = 0;
      for (var i = 0; i < scrollMetrics.velocities.length; i++) {
        sum += scrollMetrics.velocities[i];
      }
      avgVelocity = Math.round(sum / scrollMetrics.velocities.length);
    }

    return {
      visitor_id: visitorId,
      session_id: sessionId,
      sapid: sapid || null,
      campaign_id: campaignId || null,
      creative_id: creativeId || null,
      domain: publisherDomain || null,
      device_type: classifyDevice(),
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
      user_agent: navigator.userAgent,
      referral_type: referralType,
      referrer_url: document.referrer || null,
      arrival_timestamp: arrivalTimestamp,
      first_interaction_timestamp: firstInteractionTimestamp,
      departure_timestamp: departureTimestamp,
      landing_page: location.pathname,
      pages_visited: pagesVisited,
      section_engagements: finalizeSections(),
      scroll_metrics: {
        max_depth_pct: Math.round(scrollMetrics.maxDepth * 100) / 100,
        avg_velocity_px_per_sec: avgVelocity,
        direction_changes: scrollMetrics.directionChanges,
        scroll_backs: scrollMetrics.scrollBacks,
      },
      is_return_visit: isReturnVisit,
      previous_visit_count: previousVisitCount,
    };
  }

  var emitted = false;

  function emitSession() {
    if (emitted) return;

    var departureTimestamp = Date.now() / 1000;
    var sessionSeconds = departureTimestamp - arrivalTimestamp;
    if (sessionSeconds < MIN_SESSION_SECONDS) return;

    emitted = true;

    // Cancel scroll sampling
    if (scrollRafId) cancelAnimationFrame(scrollRafId);

    var payload = buildPayload();
    var json = JSON.stringify(payload);

    // Prefer sendBeacon (survives page unload), fall back to sync XHR
    if (navigator.sendBeacon) {
      var blob = new Blob([json], { type: "application/json" });
      var sent = navigator.sendBeacon(ENDPOINT, blob);
      if (sent) return;
    }

    // Fallback: synchronous XHR (blocks unload briefly but guarantees delivery)
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", ENDPOINT, false); // synchronous
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(json);
    } catch (e) {
      // Best effort — telemetry loss is acceptable
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ═══════════════════════════════════════════════════════════════════

  function init() {
    // Section tracking
    if ("IntersectionObserver" in window) {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initSectionTracking);
      } else {
        initSectionTracking();
      }
    }

    // Scroll sampling
    scrollLoop();

    // First interaction detection
    document.addEventListener("click", onFirstInteraction, { once: true });
    document.addEventListener("scroll", onFirstInteraction, { once: true });

    // Session emission on unload
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") emitSession();
    });
    window.addEventListener("pagehide", emitSession);

    // SPA navigation support: listen for pushState/popState
    var origPushState = history.pushState;
    history.pushState = function () {
      origPushState.apply(this, arguments);
      onNavigate();
    };
    window.addEventListener("popstate", onNavigate);
  }

  function onNavigate() {
    // Record the new page in the navigation path
    var now = Date.now() / 1000;
    // Update previous page dwell
    if (pagesVisited.length > 0) {
      var prev = pagesVisited[pagesVisited.length - 1];
      prev.dwell_seconds = Math.round((now - prev.timestamp) * 100) / 100;
    }
    pagesVisited.push({
      url: location.pathname,
      dwell_seconds: 0,
      scroll_depth_pct: 0,
      timestamp: now,
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  // CONVERSION TRACKING
  // ═══════════════════════════════════════════════════════════════════

  var CONVERSION_ENDPOINT =
    (SCRIPT_TAG && SCRIPT_TAG.getAttribute("data-conversion-endpoint")) ||
    ENDPOINT.replace("/session", "/conversion");

  // URL patterns that indicate a booking conversion
  var CONVERSION_URL_PATTERNS = [
    "/confirmation",
    "/booking-confirmed",
    "/thank-you",
    "/booking/complete",
    "/success",
  ];

  function checkAutoConversion() {
    var path = location.pathname.toLowerCase();
    for (var i = 0; i < CONVERSION_URL_PATTERNS.length; i++) {
      if (path.indexOf(CONVERSION_URL_PATTERNS[i]) !== -1) {
        sendConversion("booking_complete", { auto_detected: true, url: path });
        return;
      }
    }
  }

  function sendConversion(conversionType, metadata) {
    var payload = {
      visitor_id: visitorId,
      session_id: sessionId,
      sapid: sapid || null,
      campaign_id: campaignId || null,
      creative_id: creativeId || null,
      conversion_type: conversionType || "booking_complete",
      timestamp: Date.now() / 1000,
      device_type: classifyDevice(),
      referral_type: referralType,
      landing_page: location.pathname,
      is_return_visit: isReturnVisit,
      previous_visit_count: previousVisitCount,
      metadata: metadata || {},
    };

    var json = JSON.stringify(payload);

    if (navigator.sendBeacon) {
      var blob = new Blob([json], { type: "application/json" });
      if (navigator.sendBeacon(CONVERSION_ENDPOINT, blob)) return;
    }

    try {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", CONVERSION_ENDPOINT, true);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(json);
    } catch (e) {
      // Best effort
    }
  }

  // Expose global conversion function for manual triggering
  // Usage on booking confirmation page:
  //   window.informativ.convert("booking_complete", { revenue: 125, order_id: "ABC123" });
  window.informativ = {
    convert: sendConversion,
    getVisitorId: function () { return visitorId; },
    getSessionId: function () { return sessionId; },
  };

  init();

  // Auto-detect conversion from URL on page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", checkAutoConversion);
  } else {
    checkAutoConversion();
  }
})();
