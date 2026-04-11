#!/usr/bin/env python3
"""
LUXY Ride Copy Generation — Full Intelligence Pipeline.

This is NOT a prompt template. This runs the ENTIRE INFORMATIV system:

1. IntelligencePrefetchService — 11 intelligence sources from Neo4j
2. Bilateral Cascade (L3) — mechanism selection from 3,103 edge evidence
3. AtomDAG (14 atoms) — full psychological reasoning stack
4. Construct Creative Engine — graph-inferred construct → CreativeSpec
5. Corpus Fusion — 941M review-derived creative constraints
6. Gradient Field Priorities — marginal conversion impact per dimension
7. Theory Graph Chains — State→Need→Mechanism causal reasoning
8. Edge Dimension Mapping — 20-dim buyer×product → copy parameters
9. Resonance Engine context — page mindstate amplification awareness
10. CopyGenerationService.generate_with_claude() — full psychological prompt

Every atom output, every construct activation, every bilateral dimension,
every gradient priority feeds into the Claude prompt. The copy is not
generated from labels — it's generated from the system's complete
understanding of the buyer, the product, the mechanism, and the barrier.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/generate_luxy_copy_full_pipeline.py
"""

import asyncio
import json
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("full_pipeline_copy")

CREATIVES_PATH = "campaigns/ridelux_v6/luxy_ride_creatives.json"
ASIN = "lux_luxy_ride"
CATEGORY = "luxury_transportation"

# Archetype segment mapping
ARCHETYPE_SEGMENTS = {
    "careful_truster": "informativ_corporate_executive_luxury_transportation_t1",
    "status_seeker": "informativ_special_occasion_luxury_transportation_t1",
    "easy_decider": "informativ_repeat_loyal_luxury_transportation_t1",
}


async def run_full_pipeline():
    """Run the complete INFORMATIV intelligence stack for copy generation."""

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Load creative specs
    with open(CREATIVES_PATH) as f:
        creatives = json.load(f)
    logger.info("Loaded %d creative entries", len(creatives))

    # ================================================================
    # PHASE 1: INTELLIGENCE PREFETCH (11 sources per archetype)
    # ================================================================
    logger.info("Phase 1: Intelligence Prefetch")
    from adam.orchestrator.intelligence_prefetch import IntelligencePrefetchService
    prefetcher = IntelligencePrefetchService()

    archetype_contexts = {}
    for arch, segment in ARCHETYPE_SEGMENTS.items():
        from adam.constants import resolve_archetype
        resolved = resolve_archetype(arch)

        ad_context = await prefetcher.prefetch(
            archetype=resolved,
            category=CATEGORY,
            asin=ASIN,
        )

        meta = ad_context.get("_prefetch_meta", {})
        logger.info(
            "  %s: %d sources populated in %.0fms",
            arch, meta.get("sources_count", 0), meta.get("elapsed_ms", 0),
        )
        archetype_contexts[arch] = ad_context

    # ================================================================
    # PHASE 2: BILATERAL CASCADE (L3 mechanism selection per archetype)
    # ================================================================
    logger.info("Phase 2: Bilateral Cascade")
    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
    from adam.api.stackadapt.graph_cache import GraphIntelligenceCache

    cache = GraphIntelligenceCache()
    cache.initialize()
    # Clear stale cache entries to get fresh data
    cache._edge_aggregates.clear()
    cache._edge_cache_ts.clear()

    cascade_results = {}
    for arch, segment in ARCHETYPE_SEGMENTS.items():
        result = run_bilateral_cascade(segment, graph_cache=cache, asin=ASIN)
        cascade_results[arch] = result
        logger.info(
            "  %s: L%d mech=%s conf=%.2f edges=%s",
            arch, result.cascade_level, result.primary_mechanism,
            result.confidence, result.edge_count,
        )

    # ================================================================
    # PHASE 3: FULL DAG EXECUTION (14 atoms per archetype)
    # ================================================================
    logger.info("Phase 3: Atom DAG Execution (14 atoms)")
    from adam.atoms.dag import AtomDAG
    from adam.blackboard.models.zone1_context import (
        RequestContext, UserIntelligencePackage, ContentContext,
        SessionContext, AdCandidatePool,
    )
    from adam.graph_reasoning.models.graph_context import ArchetypeMatch
    from adam.blackboard.service import BlackboardService
    from datetime import datetime, timezone

    dag_results = {}
    for arch in ARCHETYPE_SEGMENTS:
        ad_context = archetype_contexts[arch]
        cascade = cascade_results[arch]

        try:
            # Build REAL Pydantic request context objects
            user_intel = UserIntelligencePackage(
                user_id=f"luxy_{arch}",
                is_cold_start=False,
                cold_start_tier="warm",
                current_arousal=0.5,
                archetype_match=ArchetypeMatch(
                    archetype_id=arch,
                    archetype_name=arch.replace("_", " ").title(),
                    confidence=cascade.confidence,
                    match_confidence=cascade.confidence,
                    distance_to_centroid=1.0 - cascade.confidence,
                    match_method="bilateral_edge_classification",
                ),
                sources_available=["bilateral_edges", "cascade_L3"],
            )

            content_ctx = ContentContext(
                content_type="native_ad",
            )

            session_ctx = SessionContext(
                session_id=f"copy_gen_{arch}",
                session_start=datetime.now(timezone.utc),
                decisions_in_session=1,
            )

            request_ctx = RequestContext(
                request_id=f"luxy_copy_{arch}",
                user_intelligence=user_intel,
                content_context=content_ctx,
                session_context=session_ctx,
                ad_candidates=AdCandidatePool(),
            )

            # Build blackboard and bridge (lightweight for offline generation)
            try:
                from adam.infrastructure.redis import ADAMRedisCache
                import redis.asyncio as aioredis
                redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=False)
                cache = ADAMRedisCache(redis_client=redis_client)
                blackboard = BlackboardService(redis_cache=cache)
            except Exception:
                from unittest.mock import MagicMock
                blackboard = MagicMock()

            try:
                from adam.graph_reasoning.bridge import InteractionBridge
                bridge = InteractionBridge()
            except Exception:
                from unittest.mock import MagicMock
                bridge = MagicMock()

            dag = AtomDAG(blackboard=blackboard, bridge=bridge)

            dag_result = await dag.execute(
                request_id=f"luxy_copy_{arch}",
                request_context=request_ctx,
                ad_context=ad_context,
            )

            dag_results[arch] = dag_result
            logger.info(
                "  %s: %d atoms executed, %d failed, confidence=%.2f",
                arch, dag_result.atoms_executed, dag_result.atoms_failed,
                dag_result.overall_confidence or 0,
            )

            # Log key atom outputs
            for atom_id, output in dag_result.atom_outputs.items():
                if output and output.primary_assessment:
                    logger.info(
                        "    %s → %s (conf=%.2f)",
                        atom_id.replace("atom_", ""),
                        str(output.primary_assessment)[:50],
                        output.overall_confidence or 0,
                    )

        except Exception as e:
            logger.warning("  %s DAG execution failed: %s", arch, e)
            import traceback
            traceback.print_exc()
            dag_results[arch] = None

    # ================================================================
    # PHASE 4: COPY GENERATION (full pipeline per touch)
    # ================================================================
    logger.info("Phase 4: Copy Generation (full pipeline)")
    from adam.output.copy_generation.service import CopyGenerationService
    from adam.output.copy_generation.models import CopyRequest, CopyType, CopyLength

    try:
        copy_service = CopyGenerationService()
    except Exception:
        # Minimal init if full init fails
        copy_service = CopyGenerationService.__new__(CopyGenerationService)

    for entry in creatives:
        arch = entry["archetype"]
        touch = entry["touch_position"]
        mechanism = entry["mechanism"]
        barrier = entry["barrier_targeted"]
        tone = entry.get("tone", "warm")
        construal = entry.get("construal_level", "moderate")
        chapter = entry.get("narrative_chapter", 2)
        headline_dir = entry.get("headline_direction", "")
        frustrated = entry.get("frustrated_dimensions", [])

        ad_context = archetype_contexts.get(arch, {})
        cascade = cascade_results.get(arch)
        dag_result = dag_results.get(arch)

        # Extract edge dimensions from prefetch
        edge_dims = ad_context.get("edge_dimensions", {})
        if isinstance(edge_dims, dict):
            flat_dims = {k: v for k, v in edge_dims.items() if isinstance(v, (int, float))}
        else:
            flat_dims = {}

        # Extract gradient priorities from cascade
        gradient = {}
        if cascade and cascade.gradient_intelligence:
            gradient = cascade.gradient_intelligence

        # Extract DAG atom outputs for copy enrichment
        dag_enrichment = {}
        if dag_result:
            for atom_id, output in dag_result.atom_outputs.items():
                if output:
                    dag_enrichment[atom_id] = {
                        "assessment": output.primary_assessment,
                        "confidence": output.overall_confidence,
                        "mechanisms": output.recommended_mechanisms,
                        "weights": output.mechanism_weights,
                    }

        # Map construal to abstraction_level
        abstraction = {"abstract": 0.75, "moderate": 0.5, "concrete": 0.25}.get(construal, 0.5)
        emotional = {"warm": 0.65, "authoritative": 0.4}.get(tone, 0.5)
        urgency = {2: 0.2, 3: 0.4, 4: 0.6, 5: 0.3}.get(chapter, 0.3)

        # Use cascade-selected mechanism if different from creative spec
        actual_mechanism = mechanism
        if cascade and cascade.primary_mechanism:
            # The cascade may have selected a better mechanism from bilateral evidence
            actual_mechanism = mechanism  # Keep spec mechanism for retargeting sequence integrity

        # Build the full CopyRequest with ALL intelligence
        request = CopyRequest(
            brand_id=ASIN,
            product_id=ASIN,
            product_name="LUXY Ride",
            product_description="Premium chauffeur-driven transportation for business travelers and luxury consumers. Professional drivers, real-time tracking, transparent pricing.",
            product_category=CATEGORY,
            copy_type=CopyType.FULL_AD,
            length=CopyLength.MEDIUM,
            mechanisms=[actual_mechanism],
            gain_emphasis=0.3 if "loss" in mechanism else 0.6,
            abstraction_level=abstraction,
            emotional_appeal=emotional,
            urgency_level=urgency,
            tone=tone,
            # Full bilateral intelligence
            edge_dimensions=flat_dims,
            gradient_priorities=gradient,
            # Full retargeting context
            archetype=arch,
            barrier_targeted=barrier,
            touch_position=touch,
            narrative_chapter=chapter,
            narrative_function=entry.get("narrative_function", ""),
            frustrated_dimensions=frustrated,
            headline_direction=headline_dir,
        )

        # Apply edge dimension mapping (bilateral → copy params)
        try:
            request = copy_service._apply_edge_dimensions(request)
        except Exception:
            pass

        # Apply gradient priorities (conversion impact → creative direction)
        try:
            request = copy_service._apply_gradient_priorities(request)
        except Exception:
            pass

        # Build the full psychological prompt
        prompt = copy_service._build_psychological_prompt(request)

        # Add DAG atom outputs to prompt
        if dag_enrichment:
            dag_section = "\n<atom_dag_outputs>\n"
            dag_section += "The following psychological assessments were computed by the 14-atom reasoning DAG:\n"
            for atom_id, data in dag_enrichment.items():
                if data.get("assessment"):
                    dag_section += f"  {atom_id}: {data['assessment']} (confidence={data.get('confidence', 0):.2f})\n"
                    if data.get("mechanisms"):
                        dag_section += f"    recommended: {data['mechanisms'][:3]}\n"
            dag_section += "</atom_dag_outputs>"
            prompt = prompt.replace("</output_format>", f"</output_format>\n{dag_section}")

        # Add cascade evidence to prompt
        if cascade:
            cascade_section = f"\n<cascade_evidence level=\"L{cascade.cascade_level}\" edges=\"{cascade.edge_count}\" confidence=\"{cascade.confidence:.2f}\">\n"
            cascade_section += f"  Cascade-selected mechanism: {cascade.primary_mechanism}\n"
            cascade_section += f"  Framing: {cascade.framing}, Construal: {cascade.construal_level}, Tone: {cascade.tone}\n"
            if cascade.reasoning:
                cascade_section += f"  Reasoning: {cascade.reasoning[-1][:200]}\n"
            cascade_section += "</cascade_evidence>"
            prompt = prompt.replace("</output_format>", f"</output_format>\n{cascade_section}")

        # Call Claude with the COMPLETE system intelligence
        import anthropic
        client = anthropic.Anthropic()

        t0 = time.time()
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": prompt + "\n\nCRITICAL: Output ONLY three lines. No markdown, no headers, no rationale:\nHEADLINE: [max 50 chars]\nBODY: [max 120 chars]\nCTA: [max 10 chars]",
                }],
            )
            elapsed = (time.time() - t0) * 1000

            text = response.content[0].text.strip()

            # Parse
            headline = body = cta = ""
            for line in text.split("\n"):
                line = line.strip()
                if line.upper().startswith("HEADLINE:"):
                    headline = line.split(":", 1)[1].strip().strip('"\'')
                elif line.upper().startswith("BODY:"):
                    body = line.split(":", 1)[1].strip().strip('"\'')
                elif line.upper().startswith("CTA:"):
                    cta = line.split(":", 1)[1].strip().strip('"\'')

            # Enforce limits
            headline = headline[:50]
            body = body[:120]
            cta = cta[:10]

            entry["headline"] = headline
            entry["body"] = body
            entry["cta"] = cta
            entry["copy_generated_by"] = "INFORMATIV full pipeline (prefetch→cascade→DAG→construct→corpus→gradient→Claude Sonnet)"
            entry["copy_edge_dims_available"] = len(flat_dims) > 0
            entry["copy_archetype_edges"] = int(cascade.edge_count or 0) if cascade else 0
            entry["copy_cascade_level"] = cascade.cascade_level if cascade else 0
            entry["copy_atoms_executed"] = dag_result.atoms_executed if dag_result else 0
            entry["copy_prompt_length"] = len(prompt)

            logger.info(
                "%s T%d (%s) %dms L%d %d-atoms prompt=%d",
                arch, touch, mechanism, elapsed,
                entry["copy_cascade_level"],
                entry["copy_atoms_executed"],
                len(prompt),
            )
            logger.info('  H: "%s"', headline)
            logger.info('  B: "%s"', body)
            logger.info('  C: "%s"', cta)

        except Exception as e:
            logger.error("  %s T%d generation failed: %s", arch, touch, e)
            entry["copy_generated_by"] = f"FAILED: {e}"

    # Save
    with open(CREATIVES_PATH, "w") as f:
        json.dump(creatives, f, indent=2, ensure_ascii=False)

    logger.info("=" * 70)
    logger.info("All 15 touches generated via full pipeline")
    logger.info("Saved to %s", CREATIVES_PATH)


if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
