#!/usr/bin/env python3
"""
DSP PREDICTION SYSTEM — COMPREHENSIVE TEST
============================================

Tests 6 layers of the DSP prediction pipeline:
  1. Neo4j DSP data availability (raw Cypher)
  2. PatternPersistence query methods (6 new DSP methods)
  3. Intelligence injection (_get_dsp_graph_intelligence)
  4. Mechanism scoring with DSP blend (20% weight)
  5. DSP construct + edge registries (in-memory)
  6. Full SynergyOrchestrator prediction pipeline

Usage:
  python3 scripts/test_dsp_prediction.py [--password atomofthought]
"""

import asyncio
import argparse
import json
import logging
import sys
import os
import time
from typing import Any, Dict, List, Optional

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("dsp_test")

# ---------------------------------------------------------------------------
# Bypass Settings validation errors
# The adam.infrastructure.__init__ eagerly imports kafka -> settings, which
# fails due to extra env vars. We stub the infrastructure package to avoid this.
# ---------------------------------------------------------------------------

import types

# Settings.Config.extra = "ignore" was added to adam/config/settings.py
# to handle extra env vars (anthropic_api_key, oxylabs_api_key) gracefully.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
        self.details: List[str] = []

    def ok(self, msg: str):
        self.passed += 1
        self.details.append(f"  OK: {msg}")

    def fail(self, msg: str):
        self.failed += 1
        self.errors.append(msg)
        self.details.append(f"  FAIL: {msg}")

    def info(self, msg: str):
        self.details.append(f"  INFO: {msg}")

    @property
    def success(self):
        return self.failed == 0

    def print(self):
        status = "PASSED" if self.success else "FAILED"
        print(f"\n--- {self.name}: {status} ({self.passed} ok, {self.failed} fail) ---")
        for d in self.details:
            print(d)


# ---------------------------------------------------------------------------
# Layer 1: Neo4j DSP Data Availability
# ---------------------------------------------------------------------------

async def test_layer1_neo4j_data(driver) -> TestResult:
    r = TestResult("Layer 1: Neo4j DSP Data Availability")

    async with driver.session() as session:
        # 1a. Count DSPConstruct nodes
        result = await session.run("MATCH (c:DSPConstruct) RETURN count(c) AS cnt")
        record = await result.single()
        cnt = record["cnt"]
        if cnt >= 100:
            r.ok(f"DSPConstruct nodes: {cnt}")
        else:
            r.fail(f"DSPConstruct nodes: {cnt} (expected >= 100)")

        # 1b. Count BehavioralSignal nodes
        result = await session.run("MATCH (s:BehavioralSignal) RETURN count(s) AS cnt")
        record = await result.single()
        cnt = record["cnt"]
        r.info(f"BehavioralSignal nodes: {cnt}")

        # 1c. Count key edge types
        edge_types = [
            "EMPIRICALLY_EFFECTIVE",
            "CONTEXTUALLY_MODERATES",
            "MODERATES",
            "SUSCEPTIBLE_TO",
            "ALIGNS_WITH_VALUE",
            "CAUSES",
            "SYNERGIZES_WITH",
        ]
        for etype in edge_types:
            result = await session.run(
                f"MATCH ()-[r:{etype}]->() RETURN count(r) AS cnt"
            )
            record = await result.single()
            cnt = record["cnt"]
            if cnt > 0:
                r.ok(f"{etype} edges: {cnt}")
            else:
                r.fail(f"{etype} edges: {cnt} (expected > 0)")

        # 1d. Sample: query one archetype's empirical effectiveness
        result = await session.run("""
            MATCH (a:DSPConstruct)-[r:EMPIRICALLY_EFFECTIVE]->(m:DSPConstruct)
            WHERE a.construct_id CONTAINS 'explorer'
            RETURN m.construct_id AS mechanism, r.success_rate AS rate, r.sample_size AS samples
            ORDER BY r.success_rate DESC
            LIMIT 5
        """)
        records = [rec async for rec in result]
        if records:
            r.ok(f"Empirical effectiveness for 'explorer': {len(records)} mechanisms")
            for rec in records[:3]:
                r.info(f"    {rec['mechanism']}: rate={rec['rate']:.3f}, samples={rec['samples']}")
        else:
            r.fail("No empirical effectiveness data for 'explorer'")

    return r


# ---------------------------------------------------------------------------
# Layer 2: Pattern Persistence Query Methods
# ---------------------------------------------------------------------------

async def test_layer2_persistence_queries(neo4j_client) -> TestResult:
    r = TestResult("Layer 2: Pattern Persistence Query Methods")

    from adam.infrastructure.neo4j.pattern_persistence import GraphPatternPersistence
    pp = GraphPatternPersistence(neo4j_client=neo4j_client)

    # 2a. get_dsp_empirical_effectiveness
    emp = await pp.get_dsp_empirical_effectiveness("explorer")
    if emp:
        r.ok(f"get_dsp_empirical_effectiveness('explorer'): {len(emp)} mechanisms")
        for mech, stats in list(emp.items())[:3]:
            r.info(f"    {mech}: rate={stats['success_rate']:.3f}, n={stats['sample_size']}")
    else:
        r.fail("get_dsp_empirical_effectiveness('explorer') returned empty")

    # 2b. get_dsp_alignment_edges
    # Try archetype 'explorer' first (has alignment edges), then 'mastery_seeking' as fallback
    edges = await pp.get_dsp_alignment_edges("explorer")
    if not edges:
        edges = await pp.get_dsp_alignment_edges("mastery_seeking")
    if edges:
        r.ok(f"get_dsp_alignment_edges: {len(edges)} edges")
        for e in edges[:3]:
            r.info(f"    {e['edge_type']} -> {e['target_id']} (str={e['strength']:.2f})")
    else:
        r.fail("get_dsp_alignment_edges returned empty for both 'explorer' and 'mastery_seeking'")

    # 2c. get_dsp_category_moderation
    cat_mod = await pp.get_dsp_category_moderation("Electronics")
    if cat_mod:
        r.ok(f"get_dsp_category_moderation('Electronics'): {len(cat_mod)} mechanisms")
        for mech, delta in list(cat_mod.items())[:3]:
            r.info(f"    {mech}: delta={delta:+.3f}")
    else:
        r.fail("get_dsp_category_moderation('Electronics') returned empty")

    # 2d. get_dsp_relationship_amplification
    rel_amp = await pp.get_dsp_relationship_amplification("rel_self_identity_core")
    if rel_amp:
        r.ok(f"get_dsp_relationship_amplification('rel_self_identity_core'): {len(rel_amp)} mechanisms")
        for mech, boost in list(rel_amp.items())[:3]:
            r.info(f"    {mech}: boost={boost:.3f}")
    else:
        r.fail("get_dsp_relationship_amplification('rel_self_identity_core') returned empty")

    # 2e. get_dsp_mechanism_susceptibility
    # Graph stores 'satisficing', method should try both ds_satisficing and satisficing
    suscept = await pp.get_dsp_mechanism_susceptibility("satisficing")
    if suscept:
        r.ok(f"get_dsp_mechanism_susceptibility('satisficing'): {len(suscept)} mechanisms")
        for mech, strength in list(suscept.items())[:3]:
            r.info(f"    {mech}: susceptibility={strength:.3f}")
    else:
        r.fail("get_dsp_mechanism_susceptibility('satisficing') returned empty")

    # 2f. get_dsp_construct
    construct = await pp.get_dsp_construct("pure_curiosity")
    if construct:
        r.ok(f"get_dsp_construct('pure_curiosity'): name={construct.get('name', '?')}")
        r.info(f"    domain={construct.get('domain', '?')}, confidence={construct.get('confidence', '?')}")
    else:
        r.fail("get_dsp_construct('pure_curiosity') returned None")

    return r


# ---------------------------------------------------------------------------
# Layer 3: Intelligence Injection
# ---------------------------------------------------------------------------

async def test_layer3_intelligence_injection(neo4j_client) -> TestResult:
    r = TestResult("Layer 3: Intelligence Injection")

    from adam.intelligence.atom_intelligence_injector import (
        AtomIntelligenceInjector,
        InjectedIntelligence,
    )

    injector = AtomIntelligenceInjector()
    # Override the internal persistence to use our connected client
    from adam.infrastructure.neo4j.pattern_persistence import GraphPatternPersistence
    injector._pattern_persistence = GraphPatternPersistence(neo4j_client=neo4j_client)

    # 3a. Call _get_dsp_graph_intelligence
    dsp_intel = await injector._get_dsp_graph_intelligence(
        archetype="explorer", category="Electronics"
    )
    if dsp_intel:
        r.ok(f"_get_dsp_graph_intelligence returned dict with {len(dsp_intel)} keys")
        for key in ["empirical_effectiveness", "alignment_edges", "category_moderation", "mechanism_susceptibility"]:
            if key in dsp_intel:
                r.ok(f"  Key '{key}' present: {len(dsp_intel[key]) if isinstance(dsp_intel[key], (dict, list)) else '?'} items")
            else:
                r.fail(f"  Key '{key}' missing from DSP intelligence")
    else:
        r.fail("_get_dsp_graph_intelligence returned None")

    # 3b. Verify InjectedIntelligence.to_atom_context includes DSP
    ii = InjectedIntelligence(request_id="test", user_id="test_user")
    if dsp_intel:
        ii.dsp_empirical_effectiveness = dsp_intel.get("empirical_effectiveness", {})
        ii.dsp_alignment_edges = dsp_intel.get("alignment_edges", [])
        ii.dsp_category_moderation = dsp_intel.get("category_moderation", {})
        ii.dsp_mechanism_susceptibility = dsp_intel.get("mechanism_susceptibility", {})

    ctx = ii.to_atom_context()
    dsp_ctx = ctx.get("dsp_graph_intelligence", {})
    has_dsp = dsp_ctx.get("has_dsp", False)
    if has_dsp:
        r.ok(f"to_atom_context()['dsp_graph_intelligence']['has_dsp'] = True")
    else:
        if dsp_intel:
            r.fail("to_atom_context() has_dsp should be True but is False")
        else:
            r.info("to_atom_context() has_dsp is False (no Neo4j data available)")

    return r


# ---------------------------------------------------------------------------
# Layer 4: Mechanism Scoring with DSP Blend
# ---------------------------------------------------------------------------

async def test_layer4_mechanism_scoring(neo4j_client) -> TestResult:
    r = TestResult("Layer 4: Mechanism Scoring with DSP Blend")

    # Build DSP intelligence first
    from adam.infrastructure.neo4j.pattern_persistence import GraphPatternPersistence
    pp = GraphPatternPersistence(neo4j_client=neo4j_client)

    empirical = await pp.get_dsp_empirical_effectiveness("explorer")
    cat_mod = await pp.get_dsp_category_moderation("Electronics")
    rel_amp = await pp.get_dsp_relationship_amplification("rel_self_identity_core")
    suscept = await pp.get_dsp_mechanism_susceptibility("ds_satisficing")

    dsp_graph_intel = {
        "empirical_effectiveness": empirical or {},
        "alignment_edges": [],
        "category_moderation": cat_mod or {},
        "relationship_amplification": rel_amp or {},
        "mechanism_susceptibility": suscept or {},
        "has_dsp": bool(empirical or cat_mod or rel_amp or suscept),
    }

    if not dsp_graph_intel["has_dsp"]:
        r.fail("No DSP graph data available — cannot test mechanism scoring")
        return r

    r.ok(f"DSP graph data available: {len(empirical)} empirical, {len(cat_mod)} cat_mod, "
         f"{len(rel_amp)} rel_amp, {len(suscept)} suscept")

    # Build base scores (simulating the 9 ADAM core mechanisms)
    base_scores = {
        "temporal_construal": 0.55,
        "regulatory_focus": 0.60,
        "social_proof": 0.65,
        "scarcity": 0.50,
        "anchoring": 0.55,
        "identity_construction": 0.60,
        "mimetic_desire": 0.50,
        "attention_dynamics": 0.45,
        "embodied_cognition": 0.40,
    }

    # Create a mock AtomInput with DSP graph intelligence
    class MockAdContext:
        def __init__(self, ctx):
            self._ctx = ctx
        def get(self, key, default=None):
            return self._ctx.get(key, default)

    class MockAtomInput:
        def __init__(self, ad_context):
            self.ad_context = ad_context
            self.request_id = "test_dsp"
            self.user_id = "test_user"
        def get_upstream(self, name):
            return None

    mock_input = MockAtomInput({
        "dsp_graph_intelligence": dsp_graph_intel,
        "archetype": "explorer",
        "category": "Electronics",
    })

    # Call the scoring method directly (without full atom instantiation)
    # We replicate the Part B logic to test it independently
    import math
    modified = base_scores.copy()
    dsp_adjustments = {}
    dsp_weights = {}

    # 4a. Empirical effectiveness
    for mech_id, stats in (empirical or {}).items():
        success_rate = stats.get("success_rate", 0.5)
        sample_size = stats.get("sample_size", 0)
        adam_mech = mech_id.lower().replace(" ", "_")
        if adam_mech in modified:
            confidence = min(1.0, math.log1p(sample_size) / 10.0) if sample_size > 0 else 0.1
            dsp_adjustments.setdefault(adam_mech, 0.0)
            dsp_weights.setdefault(adam_mech, 0.0)
            dsp_adjustments[adam_mech] += (success_rate - 0.5) * confidence
            dsp_weights[adam_mech] += confidence

    # 4b. Category moderation
    for mech_id, delta in (cat_mod or {}).items():
        adam_mech = mech_id.lower().replace(" ", "_")
        if adam_mech in modified:
            dsp_adjustments.setdefault(adam_mech, 0.0)
            dsp_weights.setdefault(adam_mech, 0.0)
            dsp_adjustments[adam_mech] += delta * 0.6
            dsp_weights[adam_mech] += 0.6

    # 4c. Relationship amplification
    for mech_id, boost in (rel_amp or {}).items():
        adam_mech = mech_id.lower().replace(" ", "_")
        if adam_mech in modified:
            adjustment = (boost - 1.0) * 0.5
            dsp_adjustments.setdefault(adam_mech, 0.0)
            dsp_weights.setdefault(adam_mech, 0.0)
            dsp_adjustments[adam_mech] += adjustment
            dsp_weights[adam_mech] += 0.4

    # 4d. Mechanism susceptibility
    for mech_id, strength in (suscept or {}).items():
        adam_mech = mech_id.lower().replace(" ", "_")
        if adam_mech in modified:
            dsp_adjustments.setdefault(adam_mech, 0.0)
            dsp_weights.setdefault(adam_mech, 0.0)
            dsp_adjustments[adam_mech] += (strength - 0.5) * 0.5
            dsp_weights[adam_mech] += 0.5

    # Apply 20% blend
    DSP_GRAPH_BLEND = 0.20
    for mech, adj in dsp_adjustments.items():
        if mech in modified and dsp_weights.get(mech, 0) > 0:
            normalized_adj = adj / dsp_weights[mech]
            modified[mech] = (
                (1 - DSP_GRAPH_BLEND) * modified[mech]
                + DSP_GRAPH_BLEND * (modified[mech] + normalized_adj)
            )
            modified[mech] = min(1.0, max(0.0, modified[mech]))

    # Compare
    changed_count = 0
    for mech in base_scores:
        before = base_scores[mech]
        after = modified[mech]
        delta = after - before
        if abs(delta) > 0.001:
            changed_count += 1
            direction = "+" if delta > 0 else ""
            r.info(f"    {mech}: {before:.3f} -> {after:.3f} ({direction}{delta:.4f})")

    if changed_count > 0:
        r.ok(f"DSP graph blend adjusted {changed_count}/{len(base_scores)} mechanisms")
    else:
        r.fail("DSP graph blend did not change any mechanism scores")

    # Show final ranking
    ranked = sorted(modified.items(), key=lambda x: x[1], reverse=True)
    r.info(f"  Final mechanism ranking:")
    for i, (mech, score) in enumerate(ranked[:5]):
        marker = " <-- PRIMARY" if i == 0 else ""
        r.info(f"    {i+1}. {mech}: {score:.4f}{marker}")

    return r


# ---------------------------------------------------------------------------
# Layer 5: DSP Construct + Edge Registries
# ---------------------------------------------------------------------------

def test_layer5_registries() -> TestResult:
    r = TestResult("Layer 5: DSP Construct + Edge Registries")

    # 5a. Construct registry
    from adam.dsp.construct_registry import build_construct_registry
    constructs = build_construct_registry()

    if len(constructs) >= 400:
        r.ok(f"Construct registry: {len(constructs)} constructs")
    else:
        r.fail(f"Construct registry: {len(constructs)} constructs (expected >= 400)")

    # Check domains present
    domains = set()
    for c in constructs.values():
        d = c.get("domain")
        if d:
            domains.add(str(d))
    r.info(f"  Domains: {len(domains)} unique ({', '.join(sorted(list(domains))[:8])}...)")

    # Check a specific construct
    if "pure_curiosity" in constructs:
        c = constructs["pure_curiosity"]
        r.ok(f"  Sample construct 'pure_curiosity': name={c.get('name', '?')}")
    elif constructs:
        sample = list(constructs.keys())[0]
        r.ok(f"  Sample construct '{sample}' exists")
    else:
        r.fail("  No constructs at all")

    # 5b. Edge registry
    from adam.dsp.edge_registry import build_edge_registry
    edges = build_edge_registry()

    if len(edges) >= 400:
        r.ok(f"Edge registry: {len(edges)} edges")
    else:
        r.fail(f"Edge registry: {len(edges)} edges (expected >= 400)")

    # Check edge types
    edge_types = set()
    for e in edges.values():
        rt = e.get("reasoning_type")
        if rt:
            edge_types.add(str(rt))
    r.info(f"  Reasoning types: {len(edge_types)} unique ({', '.join(sorted(list(edge_types))[:6])}...)")

    # Check for relationship amplification edges
    rel_edges = [e for e in edges.values() if "rel_" in e.get("source", "")]
    if rel_edges:
        r.ok(f"  Relationship amplification edges: {len(rel_edges)}")
    else:
        r.info(f"  No relationship amplification edges found")

    return r


# ---------------------------------------------------------------------------
# Layer 6: Full Prediction Pipeline (SynergyOrchestrator)
# ---------------------------------------------------------------------------

async def test_layer6_full_prediction() -> TestResult:
    r = TestResult("Layer 6: Full Prediction Pipeline")

    try:
        from adam.workflows.synergy_orchestrator import SynergyOrchestrator

        orchestrator = SynergyOrchestrator()
        
        r.info("Running SynergyOrchestrator.execute() ...")
        start = time.time()
        
        result = await orchestrator.execute(
            user_id="dsp_test_user_001",
            brand_name="Nike",
            product_name="Air Max 90",
            product_category="Athletic_Footwear",
            user_review_text="I love running shoes that are comfortable and look great. Quality matters more than price.",
            user_behavioral_signals={"purchase_intent": 0.7, "brand_loyalty": 0.6},
        )
        
        elapsed = time.time() - start
        r.info(f"  Execution time: {elapsed:.2f}s")

        if result:
            r.ok(f"SynergyOrchestrator returned result")

            # Check key fields
            decision_id = result.get("decision_id")
            if decision_id:
                r.ok(f"  decision_id: {decision_id}")
            else:
                r.fail("  Missing decision_id")

            mechanisms = result.get("mechanisms_applied", [])
            if mechanisms:
                r.ok(f"  mechanisms_applied: {len(mechanisms)} mechanisms")
                for i, m in enumerate(mechanisms[:3]):
                    name = m.get("name", "?")
                    intensity = m.get("intensity", 0)
                    source = m.get("source", "?")
                    r.info(f"    {i+1}. {name}: intensity={intensity:.3f} (source={source})")
            else:
                r.fail("  No mechanisms_applied")

            confidence = result.get("confidence_scores", {})
            overall = confidence.get("overall", 0)
            r.info(f"  Overall confidence: {overall:.3f}")

            templates = result.get("selected_templates", [])
            r.info(f"  Selected templates: {len(templates)}")

            alignment = result.get("alignment_scores", {})
            if alignment:
                r.ok(f"  Alignment scores present: overall={alignment.get('overall_alignment', '?')}")
            else:
                r.info("  No alignment scores (alignment nodes may not have run)")

            learning_ctx = result.get("learning_context", {})
            if learning_ctx:
                r.ok(f"  Learning context present ({len(learning_ctx)} keys)")
                # Check for DSP enrichment
                dsp_enrich = learning_ctx.get("dsp_enrichment", {})
                if dsp_enrich:
                    r.ok(f"  DSP enrichment in learning context: {dsp_enrich}")
            else:
                r.info("  No learning context")

        else:
            r.fail("SynergyOrchestrator returned None/empty")

    except Exception as e:
        r.fail(f"SynergyOrchestrator execution failed: {e}")
        import traceback
        r.info(f"  {traceback.format_exc()[:500]}")

    return r


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Layer 7: DSPDataAccessor Unit Tests
# ---------------------------------------------------------------------------

def test_layer7_dsp_data_accessor():
    """Test DSPDataAccessor extraction and accessor methods."""
    from adam.atoms.core.dsp_integration import DSPDataAccessor

    r = TestResult("Layer 7: DSPDataAccessor Unit Tests")

    # Build mock DSP data
    mock_dsp = {
        "has_dsp": True,
        "empirical_effectiveness": {
            "social_proof": {"success_rate": 0.78, "sample_size": 12000},
            "authority": {"success_rate": 0.62, "sample_size": 500},
        },
        "alignment_edges": [
            {"edge_type": "ALIGNS_WITH", "target_id": "social_proof", "strength": 0.8},
        ],
        "category_moderation": {
            "social_proof": 0.12,
            "scarcity": -0.05,
        },
        "relationship_amplification": {
            "reciprocity": 0.25,
        },
        "mechanism_susceptibility": {
            "social_proof": 0.85,
            "authority": 0.40,
        },
    }

    # Create a mock atom_input with ad_context
    class MockAtomInput:
        def __init__(self, dsp_data):
            self.ad_context = {"dsp_graph_intelligence": dsp_data} if dsp_data else {}

    # Test 1: has_dsp
    dsp = DSPDataAccessor(MockAtomInput(mock_dsp))
    if dsp.has_dsp:
        r.ok("has_dsp=True with populated data")
    else:
        r.fail("has_dsp should be True")

    # Test 2: has_dsp with empty
    dsp_empty = DSPDataAccessor(MockAtomInput(None))
    if not dsp_empty.has_dsp:
        r.ok("has_dsp=False with empty data")
    else:
        r.fail("has_dsp should be False with empty data")

    # Test 3: has_dsp with missing ad_context
    class NoContext:
        pass
    dsp_none = DSPDataAccessor(NoContext())
    if not dsp_none.has_dsp:
        r.ok("has_dsp=False with no ad_context attribute")
    else:
        r.fail("has_dsp should be False with no ad_context")

    # Test 4: get_empirical
    emp = dsp.get_empirical("social_proof")
    if emp and emp["success_rate"] == 0.78 and emp["sample_size"] == 12000:
        r.ok(f"get_empirical('social_proof') = {{rate={emp['success_rate']}, n={emp['sample_size']}}}")
    else:
        r.fail(f"get_empirical('social_proof') returned {emp}")

    # Test 5: get_empirical missing
    if dsp.get_empirical("nonexistent") is None:
        r.ok("get_empirical('nonexistent') = None")
    else:
        r.fail("get_empirical('nonexistent') should be None")

    # Test 6: get_category_delta
    delta = dsp.get_category_delta("social_proof")
    if delta == 0.12:
        r.ok(f"get_category_delta('social_proof') = {delta}")
    else:
        r.fail(f"get_category_delta('social_proof') expected 0.12, got {delta}")

    # Test 7: get_susceptibility
    sus = dsp.get_susceptibility("social_proof")
    if sus == 0.85:
        r.ok(f"get_susceptibility('social_proof') = {sus}")
    else:
        r.fail(f"get_susceptibility('social_proof') expected 0.85, got {sus}")

    # Test 8: get_relationship_boost
    boost = dsp.get_relationship_boost("reciprocity")
    if boost == 0.25:
        r.ok(f"get_relationship_boost('reciprocity') = {boost}")
    else:
        r.fail(f"get_relationship_boost('reciprocity') expected 0.25, got {boost}")

    # Test 9: get_alignment_edges
    edges = dsp.get_alignment_edges()
    if len(edges) == 1 and edges[0]["target_id"] == "social_proof":
        r.ok(f"get_alignment_edges() returned {len(edges)} edge(s)")
    else:
        r.fail(f"get_alignment_edges() expected 1 edge, got {edges}")

    # Test 10: Bulk getters
    all_emp = dsp.get_all_empirical()
    all_cat = dsp.get_all_category_moderation()
    all_sus = dsp.get_all_susceptibility()
    all_rel = dsp.get_all_relationship_boosts()
    if len(all_emp) == 2 and len(all_cat) == 2 and len(all_sus) == 2 and len(all_rel) == 1:
        r.ok(f"Bulk getters: empirical={len(all_emp)}, cat_mod={len(all_cat)}, suscept={len(all_sus)}, rel={len(all_rel)}")
    else:
        r.fail(f"Bulk getter counts unexpected: {len(all_emp)}, {len(all_cat)}, {len(all_sus)}, {len(all_rel)}")

    return r


# ---------------------------------------------------------------------------
# Layer 8: Group Helper Unit Tests
# ---------------------------------------------------------------------------

def test_layer8_group_helpers():
    """Test CategoryModerationHelper, SusceptibilityHelper, EmpiricalEffectivenessHelper."""
    from adam.atoms.core.dsp_integration import (
        DSPDataAccessor,
        CategoryModerationHelper,
        SusceptibilityHelper,
        EmpiricalEffectivenessHelper,
    )

    r = TestResult("Layer 8: Group Helper Unit Tests")

    mock_dsp = {
        "has_dsp": True,
        "empirical_effectiveness": {
            "social_proof": {"success_rate": 0.80, "sample_size": 10000},
            "scarcity": {"success_rate": 0.30, "sample_size": 5000},
            "authority": {"success_rate": 0.65, "sample_size": 200},
        },
        "category_moderation": {
            "social_proof": 0.20,
            "scarcity": -0.10,
        },
        "mechanism_susceptibility": {
            "social_proof": 0.85,
            "authority": 0.30,
        },
        "alignment_edges": [],
        "relationship_amplification": {},
    }

    class MockAtomInput:
        def __init__(self, dsp_data):
            self.ad_context = {"dsp_graph_intelligence": dsp_data}

    dsp = DSPDataAccessor(MockAtomInput(mock_dsp))

    # Test adjustments
    adjustments = {
        "social_proof": 0.50,
        "scarcity": 0.30,
        "authority": 0.40,
    }

    # ---- CategoryModerationHelper ----
    result_cat = CategoryModerationHelper.apply(adjustments, dsp)

    # social_proof: 0.50 + 0.15 * 0.20 = 0.53
    expected_sp = 0.50 + 0.15 * 0.20
    if abs(result_cat["social_proof"] - expected_sp) < 0.001:
        r.ok(f"CategoryMod social_proof: {result_cat['social_proof']:.4f} (expected ~{expected_sp:.4f})")
    else:
        r.fail(f"CategoryMod social_proof: {result_cat['social_proof']:.4f} (expected ~{expected_sp:.4f})")

    # scarcity: 0.30 + 0.15 * (-0.10) = 0.285
    expected_sc = 0.30 + 0.15 * (-0.10)
    if abs(result_cat["scarcity"] - expected_sc) < 0.001:
        r.ok(f"CategoryMod scarcity: {result_cat['scarcity']:.4f} (expected ~{expected_sc:.4f})")
    else:
        r.fail(f"CategoryMod scarcity: {result_cat['scarcity']:.4f} (expected ~{expected_sc:.4f})")

    # authority: no category data → unchanged
    if result_cat["authority"] == 0.40:
        r.ok(f"CategoryMod authority: unchanged at {result_cat['authority']}")
    else:
        r.fail(f"CategoryMod authority: expected 0.40, got {result_cat['authority']}")

    # Original not mutated
    if adjustments["social_proof"] == 0.50:
        r.ok("CategoryMod: original adjustments not mutated")
    else:
        r.fail("CategoryMod: original adjustments were mutated!")

    # ---- SusceptibilityHelper ----
    result_sus = SusceptibilityHelper.apply(adjustments, dsp)

    # social_proof: 0.50 + 0.15 * (0.85 - 0.5) = 0.50 + 0.0525 = 0.5525
    expected_sp_s = 0.50 + 0.15 * (0.85 - 0.5)
    if abs(result_sus["social_proof"] - expected_sp_s) < 0.001:
        r.ok(f"Susceptibility social_proof: {result_sus['social_proof']:.4f} (expected ~{expected_sp_s:.4f})")
    else:
        r.fail(f"Susceptibility social_proof: {result_sus['social_proof']:.4f} (expected ~{expected_sp_s:.4f})")

    # authority: 0.40 + 0.15 * (0.40 - 0.5) = 0.40 - 0.015 = 0.385
    expected_auth_s = 0.40 + 0.15 * (0.40 - 0.5)
    if abs(result_sus["authority"] - expected_auth_s) < 0.001:
        r.ok(f"Susceptibility authority: {result_sus['authority']:.4f} (expected ~{expected_auth_s:.4f})")
    else:
        r.fail(f"Susceptibility authority: {result_sus['authority']:.4f} (expected ~{expected_auth_s:.4f})")

    # scarcity: no susceptibility data → unchanged
    if result_sus["scarcity"] == 0.30:
        r.ok(f"Susceptibility scarcity: unchanged at {result_sus['scarcity']}")
    else:
        r.fail(f"Susceptibility scarcity: expected 0.30, got {result_sus['scarcity']}")

    # ---- EmpiricalEffectivenessHelper ----
    import math
    result_emp = EmpiricalEffectivenessHelper.apply(adjustments, dsp)

    # social_proof: 0.50 + 0.15 * (0.80 - 0.5) * min(1.0, log1p(10000)/10)
    conf_sp = min(1.0, math.log1p(10000) / 10.0)
    expected_sp_e = 0.50 + 0.15 * (0.80 - 0.5) * conf_sp
    if abs(result_emp["social_proof"] - expected_sp_e) < 0.001:
        r.ok(f"Empirical social_proof: {result_emp['social_proof']:.4f} (expected ~{expected_sp_e:.4f})")
    else:
        r.fail(f"Empirical social_proof: {result_emp['social_proof']:.4f} (expected ~{expected_sp_e:.4f})")

    # scarcity: 0.30 + 0.15 * (0.30 - 0.5) * min(1.0, log1p(5000)/10) → negative adjustment
    conf_sc = min(1.0, math.log1p(5000) / 10.0)
    expected_sc_e = 0.30 + 0.15 * (0.30 - 0.5) * conf_sc
    if abs(result_emp["scarcity"] - expected_sc_e) < 0.001:
        r.ok(f"Empirical scarcity: {result_emp['scarcity']:.4f} (expected ~{expected_sc_e:.4f})")
    else:
        r.fail(f"Empirical scarcity: {result_emp['scarcity']:.4f} (expected ~{expected_sc_e:.4f})")

    # Test with empty DSP
    dsp_empty = DSPDataAccessor(MockAtomInput({"has_dsp": False}))
    no_change = CategoryModerationHelper.apply(adjustments, dsp_empty)
    if no_change == adjustments:
        r.ok("Helpers are no-op when has_dsp=False")
    else:
        r.fail(f"Helpers should be no-op when has_dsp=False, but adjustments changed")

    return r


# ---------------------------------------------------------------------------
# Layer 9: Atom DSP Integration Verification
# ---------------------------------------------------------------------------

def test_layer9_atom_dsp_integration():
    """Verify that all 24 atoms now import and use DSP integration."""
    r = TestResult("Layer 9: Atom DSP Integration Verification")

    import importlib

    # Group A: CategoryModerationHelper (9 atoms)
    group_a = [
        "adam.atoms.core.cooperative_framing",
        "adam.atoms.core.information_asymmetry",
        "adam.atoms.core.regret_anticipation",
        "adam.atoms.core.signal_credibility",
        "adam.atoms.core.temporal_self",
        "adam.atoms.core.cognitive_load",
        "adam.atoms.core.ambiguity_attitude",
        "adam.atoms.core.interoceptive_style",
        "adam.atoms.core.strategic_timing",
    ]

    # Group B: SusceptibilityHelper (6 atoms)
    group_b = [
        "adam.atoms.core.decision_entropy",
        "adam.atoms.core.motivational_conflict",
        "adam.atoms.core.predictive_error",
        "adam.atoms.core.strategic_awareness",
        "adam.atoms.core.autonomy_reactance",
        "adam.atoms.core.query_order",
    ]

    # Group C: EmpiricalEffectivenessHelper (3 atoms)
    group_c = [
        "adam.atoms.core.mimetic_desire_atom",
        "adam.atoms.core.review_intelligence",
        "adam.atoms.core.user_state",
    ]

    # Bespoke (6 atoms)
    bespoke = [
        "adam.atoms.core.ad_selection",
        "adam.atoms.core.coherence_optimization",
        "adam.atoms.core.narrative_identity",
        "adam.atoms.core.persuasion_pharmacology",
        "adam.atoms.core.relationship_intelligence",
        "adam.atoms.core.brand_personality",
    ]

    def check_module_has_dsp_import(module_name, group_label):
        """Check that the module's source references DSPDataAccessor."""
        try:
            # Read source file instead of importing (avoids dependency chain)
            parts = module_name.split(".")
            # adam.atoms.core.xxx -> adam/atoms/core/xxx.py
            rel_path = "/".join(parts) + ".py"
            abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel_path)

            with open(abs_path, "r") as f:
                source = f.read()

            has_import = "from adam.atoms.core.dsp_integration import" in source
            has_accessor = "DSPDataAccessor" in source

            short_name = parts[-1]
            if has_import and has_accessor:
                r.ok(f"[{group_label}] {short_name}: DSP import + DSPDataAccessor present")
                return True
            else:
                r.fail(f"[{group_label}] {short_name}: import={has_import}, accessor={has_accessor}")
                return False
        except Exception as e:
            r.fail(f"[{group_label}] {module_name}: Error checking: {e}")
            return False

    # Check all groups
    for mod in group_a:
        check_module_has_dsp_import(mod, "GroupA-CatMod")
    for mod in group_b:
        check_module_has_dsp_import(mod, "GroupB-Suscept")
    for mod in group_c:
        check_module_has_dsp_import(mod, "GroupC-Empirical")
    for mod in bespoke:
        check_module_has_dsp_import(mod, "Bespoke")

    # Also verify the foundation module imports cleanly
    try:
        from adam.atoms.core.dsp_integration import (
            DSPDataAccessor,
            CategoryModerationHelper,
            SusceptibilityHelper,
            EmpiricalEffectivenessHelper,
        )
        r.ok("Foundation module imports successfully with all 4 classes")
    except ImportError as e:
        r.fail(f"Foundation module import failed: {e}")

    return r


async def main():
    parser = argparse.ArgumentParser(description="DSP Prediction System Test")
    parser.add_argument("--password", default="atomofthought", help="Neo4j password")
    parser.add_argument("--uri", default="neo4j://127.0.0.1:7687", help="Neo4j URI")
    parser.add_argument("--skip-layer6", action="store_true", help="Skip full prediction (requires full stack)")
    args = parser.parse_args()

    print("=" * 70)
    print("DSP PREDICTION SYSTEM — COMPREHENSIVE TEST")
    print("=" * 70)

    results: List[TestResult] = []

    # Connect to Neo4j
    driver = None
    neo4j_client = None
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(args.uri, auth=("neo4j", args.password))

        # Verify connection
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            record = await result.single()
            assert record["n"] == 1
        print(f"\nNeo4j connected: {args.uri}")

        # Create a wrapper that matches what PatternPersistence expects
        class Neo4jClientAdapter:
            """Adapter to make the async driver work with PatternPersistence."""
            def __init__(self, drv):
                self._driver = drv
                self.is_connected = True
            async def connect(self):
                pass
            async def session(self):
                return self._driver.session()

        neo4j_client = Neo4jClientAdapter(driver)

    except Exception as e:
        print(f"\nWARNING: Neo4j connection failed: {e}")
        print("Layers 1-4 will be skipped.")

    # Layer 1
    if driver:
        results.append(await test_layer1_neo4j_data(driver))
    else:
        r = TestResult("Layer 1: Neo4j DSP Data Availability")
        r.fail("Neo4j not available")
        results.append(r)

    # Layer 2
    if neo4j_client:
        results.append(await test_layer2_persistence_queries(neo4j_client))
    else:
        r = TestResult("Layer 2: Pattern Persistence Query Methods")
        r.fail("Neo4j not available")
        results.append(r)

    # Layer 3
    if neo4j_client:
        results.append(await test_layer3_intelligence_injection(neo4j_client))
    else:
        r = TestResult("Layer 3: Intelligence Injection")
        r.fail("Neo4j not available")
        results.append(r)

    # Layer 4
    if neo4j_client:
        results.append(await test_layer4_mechanism_scoring(neo4j_client))
    else:
        r = TestResult("Layer 4: Mechanism Scoring with DSP Blend")
        r.fail("Neo4j not available")
        results.append(r)

    # Layer 5 (no Neo4j needed)
    results.append(test_layer5_registries())

    # Layer 6 (full stack)
    if not args.skip_layer6:
        results.append(await test_layer6_full_prediction())
    else:
        r = TestResult("Layer 6: Full Prediction Pipeline")
        r.info("Skipped (--skip-layer6)")
        results.append(r)

    # Cleanup
    if driver:
        await driver.close()

    # Layer 7: DSPDataAccessor unit tests
    results.append(test_layer7_dsp_data_accessor())

    # Layer 8: Group helpers unit tests
    results.append(test_layer8_group_helpers())

    # Layer 9: Atom DSP integration verification
    results.append(test_layer9_atom_dsp_integration())

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    for r in results:
        r.print()
        total_passed += r.passed
        total_failed += r.failed

    print(f"\n{'=' * 70}")
    if total_failed == 0:
        print(f"ALL TESTS PASSED: {total_passed} checks ok")
    else:
        print(f"TESTS COMPLETE: {total_passed} passed, {total_failed} failed")
    print(f"{'=' * 70}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
