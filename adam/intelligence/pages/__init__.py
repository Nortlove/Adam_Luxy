"""
Page Intelligence Subsystem
===========================

Operationalizes the theoretical foundation's §4.2 commitment: the page is the
third side of the bilateral transaction — the environmental prime that
activates goal structures in the reader before the ad ever loads.

Current contents (Phase A):
    entity_graph.py — Neo4j shadow-write service for Author, Publication,
                      Section, Topic, and Article entities with accumulating
                      hierarchical posteriors.

Planned (subsequent phases):
    metadata_trinity.py — RSS + Open Graph + Schema.org JSON-LD parser (Phase C)
    lexicon_ensemble.py — Empath + NRC-VAD + NRC-EmoLex + eMFD + RF + CLT (Phase D)
    bayesian_aggregator.py — hierarchical-Bayes construct inference (Phase D)
    feed_ingestion.py — proactive RSS/Atom daily pull (Phase F)
"""

from adam.intelligence.pages.entity_graph import (
    ArticleObservation,
    AuthorUpsert,
    PageEntityGraph,
    PublicationUpsert,
    SectionUpsert,
    TopicUpsert,
    get_page_entity_graph,
)

__all__ = [
    "ArticleObservation",
    "AuthorUpsert",
    "PageEntityGraph",
    "PublicationUpsert",
    "SectionUpsert",
    "TopicUpsert",
    "get_page_entity_graph",
]
