"""
INFORMATIV ↔ StackAdapt Integration
======================================

Three-layer integration architecture:

    Layer 1 — Audience Taxonomy (Data Partner):
        taxonomy_generator.py   — generates ~260 psychological segments
        data_taxonomy_client.py — pushes metadata via Data Taxonomy API + S3

    Layer 2 — Creative Intelligence (Real-Time):
        See adam.api.stackadapt — <50ms creative parameter endpoint

    Layer 3 — Outcome Learning Loop:
        See adam.api.stackadapt.webhook — conversion event receiver

    Platform Adapter:
        adapter.py — GraphQL campaign/audience/creative management
"""
