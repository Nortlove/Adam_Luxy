#!/usr/bin/env python3
"""
Generate LUXY Ride ad copy using the FULL INFORMATIV intelligence pipeline.

This is NOT template filling. This script:

1. Queries Neo4j for bilateral edge dimensions for each (archetype, LUXY Ride)
2. Computes gradient field priorities (which dims matter most for conversion)
3. Extracts mechanism-barrier-construal parameters from the creative spec
4. Builds a full CopyRequest with edge_dimensions, gradient_priorities,
   mechanism, barrier, construal, tone, narrative chapter
5. Calls CopyGenerationService.generate_with_claude() which:
   a. Applies edge-dimension-to-copy-params mapping
   b. Applies gradient field creative direction
   c. Applies construct creative engine reasoning
   d. Applies corpus fusion constraints (from 941M reviews)
   e. Builds a psychologically-informed Claude prompt
   f. Generates headline, body, CTA, and variants

Each touch's copy is grounded in:
- The actual bilateral edge profile for that archetype x LUXY Ride
- The gradient field showing which psychological dimensions drive conversion
- The narrative arc position (Ch2=complication, Ch3=rising, Ch4=resolution, Ch5=epilogue)
- The mechanism-barrier pairing from the therapeutic retargeting spec
- Frustrated dimension awareness (avoid triggering dimension conflicts)

Prerequisites:
- Neo4j running with LUXY Ride data (3,103 bilateral edges)
- ANTHROPIC_API_KEY environment variable set
- Redis running (for prefetch caching)

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/generate_luxy_copy.py

Falls back to template generation if Claude API is unavailable.
"""

import asyncio
import json
import logging
import sys
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("generate_luxy_copy")

CREATIVES_PATH = "campaigns/ridelux_v6/luxy_ride_creatives.json"
ASIN = "lux_luxy_ride"
CATEGORY = "luxury_transportation"

# Archetype → INFORMATIV segment ID for prefetch
ARCHETYPE_SEGMENTS = {
    "careful_truster": "informativ_corporate_executive_luxury_transportation_t1",
    "status_seeker": "informativ_airport_anxiety_luxury_transportation_t1",
    "easy_decider": "informativ_repeat_loyal_luxury_transportation_t1",
}


async def generate_all():
    """Generate copy for all 15 LUXY Ride touches using full system intelligence."""

    # Load creative specs
    with open(CREATIVES_PATH) as f:
        creatives = json.load(f)

    logger.info("Loaded %d creative entries", len(creatives))

    # Initialize prefetch service for bilateral intelligence
    from adam.orchestrator.intelligence_prefetch import IntelligencePrefetchService
    prefetcher = IntelligencePrefetchService()

    # Initialize copy generation service
    try:
        from adam.output.copy_generation.service import CopyGenerationService
        from adam.output.copy_generation.models import CopyRequest, CopyType
        copy_service = CopyGenerationService()
        has_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
        logger.info("Copy service initialized (Claude: %s)", "YES" if has_claude else "NO — template fallback")
    except Exception as e:
        logger.error("Cannot initialize copy service: %s", e)
        sys.exit(1)

    # Cache prefetch results per archetype (avoid redundant Neo4j queries)
    archetype_contexts = {}

    for archetype, segment in ARCHETYPE_SEGMENTS.items():
        logger.info("Prefetching intelligence for %s...", archetype)
        from adam.api.stackadapt.bilateral_cascade import _parse_segment_id, resolve_archetype
        arch_id, _, cat = _parse_segment_id(segment)
        arch_id = resolve_archetype(arch_id)

        ad_context = await prefetcher.prefetch(
            archetype=arch_id,
            category=cat or CATEGORY,
            asin=ASIN,
        )

        meta = ad_context.get("_prefetch_meta", {})
        edge_dims = ad_context.get("edge_dimensions", {})
        logger.info(
            "  %s: %d sources, %d edge dimensions",
            archetype, meta.get("sources_count", 0), len(edge_dims),
        )

        # Also run cascade for gradient intelligence
        from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
        cascade = run_bilateral_cascade(segment_id=segment, asin=ASIN)
        logger.info(
            "  Cascade: L%d, mechanism=%s, confidence=%.2f",
            cascade.cascade_level, cascade.primary_mechanism, cascade.confidence,
        )

        archetype_contexts[archetype] = {
            "ad_context": ad_context,
            "edge_dimensions": edge_dims,
            "gradient_priorities": cascade.gradient_intelligence or {},
            "cascade": cascade,
        }

    # Generate copy for each touch
    generated = 0
    for entry in creatives:
        archetype = entry["archetype"]
        touch = entry["touch_position"]
        mechanism = entry["mechanism"]
        barrier = entry["barrier_targeted"]
        tone = entry.get("tone", "warm")
        construal = entry.get("construal_level", "moderate")
        chapter = entry.get("narrative_chapter", 2)
        headline_direction = entry.get("headline_direction", "")
        frustrated = entry.get("frustrated_dimensions", [])

        ctx = archetype_contexts.get(archetype, {})
        edge_dims = ctx.get("edge_dimensions", {})
        gradient = ctx.get("gradient_priorities", {})

        # Map construal to abstraction_level
        abstraction = {"abstract": 0.75, "moderate": 0.5, "concrete": 0.25}.get(construal, 0.5)

        # Map tone to emotional_appeal
        emotional = {"warm": 0.65, "authoritative": 0.4}.get(tone, 0.5)

        # Map narrative chapter to urgency
        urgency = {2: 0.2, 3: 0.4, 4: 0.6, 5: 0.3}.get(chapter, 0.3)

        # Build request with FULL bilateral intelligence
        request = CopyRequest(
            brand_id=ASIN,
            product_id=ASIN,
            product_name="LUXY Ride",
            product_description="Premium chauffeur-driven transportation for business travelers and luxury consumers",
            product_category=CATEGORY,
            copy_type=CopyType.FULL_AD,
            mechanisms=[mechanism],
            gain_emphasis=0.6 if "loss" not in mechanism else 0.3,
            abstraction_level=abstraction,
            emotional_appeal=emotional,
            urgency_level=urgency,
            tone=tone,
            gradient_priorities=gradient,
            edge_dimensions=edge_dims,
            # Full retargeting context
            archetype=archetype,
            barrier_targeted=barrier,
            touch_position=touch,
            narrative_chapter=chapter,
            narrative_function=entry.get("narrative_function", ""),
            frustrated_dimensions=frustrated,
            headline_direction=headline_direction,
        )

        logger.info(
            "Generating %s T%d: mech=%s, barrier=%s, ch=%d",
            archetype, touch, mechanism, barrier, chapter,
        )

        try:
            if has_claude:
                result = await copy_service.generate_with_claude(request)
            else:
                result = await copy_service.generate(request)

            # Extract copy
            primary = result.primary_text if hasattr(result, "primary_text") else ""

            # Parse headline/body/CTA from generated text
            # The generator returns structured output
            if hasattr(result, "text_variants") and result.text_variants:
                best = result.text_variants[0]
                entry["headline"] = (best.text[:50] if hasattr(best, "text") else primary[:50]).strip()
            else:
                entry["headline"] = primary[:50].strip()

            # Body from primary text
            entry["body"] = primary[:120].strip()

            # CTA
            entry["cta"] = "Learn More"  # Default, override from result if available
            if hasattr(result, "text_variants"):
                for v in result.text_variants:
                    if hasattr(v, "mechanism") and v.mechanism == "cta":
                        entry["cta"] = v.text[:10].strip()

            entry["copy_generated_by"] = "INFORMATIV bilateral pipeline"
            entry["copy_edge_dims_available"] = len(edge_dims) > 0
            entry["copy_gradient_available"] = len(gradient) > 0
            entry["copy_confidence"] = getattr(result, "overall_confidence", 0.5)
            generated += 1

            logger.info("  → headline: \"%s\"", entry["headline"])

        except Exception as e:
            logger.warning("  Copy generation failed for %s T%d: %s", archetype, touch, e)
            entry["copy_generated_by"] = "FAILED"
            entry["copy_error"] = str(e)

    # Write back
    with open(CREATIVES_PATH, "w") as f:
        json.dump(creatives, f, indent=2, ensure_ascii=False)

    logger.info("Generated copy for %d/%d touches", generated, len(creatives))
    logger.info("Output: %s", CREATIVES_PATH)

    # Summary
    for entry in creatives:
        status = "OK" if entry.get("headline") else "MISSING"
        edges = "edges" if entry.get("copy_edge_dims_available") else "no-edges"
        print(
            f"  [{status}] {entry['archetype']:18s} T{entry['touch_position']} "
            f"({edges}): \"{entry.get('headline', 'N/A')}\""
        )


if __name__ == "__main__":
    asyncio.run(generate_all())
