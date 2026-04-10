# =============================================================================
# Therapeutic Retargeting Engine — Cypher Query Templates
# Location: adam/retargeting/schema/queries.py
# Spec: Enhancement #33, Section D.3
# =============================================================================

"""
Key Cypher query templates for the Therapeutic Retargeting Engine.

All queries use parameterized inputs ($param) for safety and performance.
"""

QUERIES = {
    # ------------------------------------------------------------------
    # Sequence queries
    # ------------------------------------------------------------------
    "get_active_sequences_for_user": """
        MATCH (ts:TherapeuticSequence {user_id: $user_id, status: 'active'})
        OPTIONAL MATCH (ts)<-[:PART_OF]-(tt:TherapeuticTouch)
        WITH ts, collect(tt) AS touches
        RETURN ts, touches
        ORDER BY ts.started_at DESC
    """,
    "get_sequence_by_id": """
        MATCH (ts:TherapeuticSequence {sequence_id: $sequence_id})
        OPTIONAL MATCH (ts)<-[:PART_OF]-(tt:TherapeuticTouch)
        WITH ts, collect(tt) AS touches
        ORDER BY tt.position_in_sequence
        RETURN ts, touches
    """,
    "create_sequence": """
        CREATE (ts:TherapeuticSequence {
            sequence_id: $sequence_id,
            user_id: $user_id,
            brand_id: $brand_id,
            archetype_id: $archetype_id,
            max_touches: $max_touches,
            max_duration_days: $max_duration_days,
            status: 'active',
            cumulative_reactance: 0.0,
            narrative_arc_type: $narrative_arc_type,
            started_at: datetime()
        })
        RETURN ts
    """,
    "update_sequence_status": """
        MATCH (ts:TherapeuticSequence {sequence_id: $sequence_id})
        SET ts.status = $status,
            ts.cumulative_reactance = $cumulative_reactance,
            ts.completed_at = CASE WHEN $status IN ['converted', 'suppressed', 'exhausted']
                THEN datetime() ELSE ts.completed_at END
        RETURN ts
    """,

    # ------------------------------------------------------------------
    # Mechanism prior queries (Thompson Sampling)
    # ------------------------------------------------------------------
    "get_mechanism_prior": """
        MATCH (mp:MechanismPrior {
            mechanism: $mechanism,
            barrier_category: $barrier_category,
            archetype_id: $archetype_id
        })
        RETURN mp.alpha, mp.beta, mp.sample_count, mp.last_updated, mp.prior_id
    """,
    "upsert_mechanism_prior": """
        MERGE (mp:MechanismPrior {
            mechanism: $mechanism,
            barrier_category: $barrier_category,
            archetype_id: $archetype_id
        })
        ON CREATE SET
            mp.prior_id = $prior_id,
            mp.alpha = $alpha,
            mp.beta = $beta,
            mp.sample_count = 0,
            mp.last_updated = datetime()
        ON MATCH SET
            mp.alpha = $alpha,
            mp.beta = $beta,
            mp.sample_count = mp.sample_count,
            mp.last_updated = datetime()
        RETURN mp
    """,
    "update_mechanism_prior_thompson": """
        MATCH (mp:MechanismPrior {prior_id: $prior_id})
        SET mp.alpha = mp.alpha + $success_count,
            mp.beta = mp.beta + $failure_count,
            mp.sample_count = mp.sample_count + $total_count,
            mp.last_updated = datetime()
        RETURN mp
    """,
    "get_all_priors_for_barrier": """
        MATCH (mp:MechanismPrior {
            barrier_category: $barrier_category,
            archetype_id: $archetype_id
        })
        RETURN mp.mechanism AS mechanism,
               mp.alpha AS alpha,
               mp.beta AS beta,
               mp.sample_count AS sample_count
        ORDER BY toFloat(mp.alpha) / (mp.alpha + mp.beta) DESC
    """,

    # ------------------------------------------------------------------
    # Diagnosis queries
    # ------------------------------------------------------------------
    "store_diagnosis": """
        CREATE (bd:BarrierDiagnosis {
            diagnosis_id: $diagnosis_id,
            user_id: $user_id,
            brand_id: $brand_id,
            archetype_id: $archetype_id,
            diagnosed_at: datetime(),
            conversion_stage: $conversion_stage,
            stage_confidence: $stage_confidence,
            primary_barrier: $primary_barrier,
            primary_barrier_confidence: $primary_barrier_confidence,
            rupture_type: $rupture_type,
            rupture_severity: $rupture_severity,
            estimated_reactance_level: $estimated_reactance_level,
            reactance_budget_remaining: $reactance_budget_remaining,
            persuasion_knowledge_phase: $persuasion_knowledge_phase,
            ownership_level: $ownership_level,
            recommended_mechanism: $recommended_mechanism,
            mechanism_confidence: $mechanism_confidence
        })
        RETURN bd
    """,
    "get_recent_diagnoses_for_user": """
        MATCH (bd:BarrierDiagnosis {user_id: $user_id})
        RETURN bd
        ORDER BY bd.diagnosed_at DESC
        LIMIT $limit
    """,

    # ------------------------------------------------------------------
    # Site profile queries
    # ------------------------------------------------------------------
    "get_site_whitelist_for_archetype": """
        MATCH (sp:SitePsychProfile)-[a:ALIGNS_WITH]->(ca:CustomerArchetype {archetype_id: $archetype_id})
        WHERE a.score >= $min_alignment_score
        RETURN sp.domain, a.score
        ORDER BY a.score DESC
        LIMIT $max_domains
    """,
    "upsert_site_profile": """
        MERGE (sp:SitePsychProfile {domain: $domain})
        SET sp.url_analyzed = $url_analyzed,
            sp.analyzed_at = datetime(),
            sp.trust_signaling = $trust_signaling,
            sp.emotional_warmth = $emotional_warmth,
            sp.rational_density = $rational_density,
            sp.aspirational_level = $aspirational_level,
            sp.simplicity = $simplicity,
            sp.urgency_pressure = $urgency_pressure,
            sp.social_proof_density = $social_proof_density,
            sp.narrative_richness = $narrative_richness,
            sp.autonomy_respect = $autonomy_respect,
            sp.processing_route = $processing_route,
            sp.regulatory_framing = $regulatory_framing,
            sp.construal_level = $construal_level,
            sp.page_category = $page_category,
            sp.content_quality_score = $content_quality_score
        RETURN sp
    """,

    # ------------------------------------------------------------------
    # Learning / analytics queries
    # ------------------------------------------------------------------
    "get_barrier_resolution_rate": """
        MATCH (tt:TherapeuticTouch {mechanism: $mechanism})-[:PRODUCED]->(bro:BarrierResolutionOutcome)
        MATCH (tt)-[:RESPONDS_TO]->(bd:BarrierDiagnosis {primary_barrier: $barrier_category})
        WHERE bd.archetype_id = $archetype_id
        WITH count(bro) AS total,
             sum(CASE WHEN bro.barrier_resolved = true THEN 1 ELSE 0 END) AS resolved
        RETURN total, resolved,
               CASE WHEN total > 0 THEN toFloat(resolved) / total ELSE 0.0 END AS resolution_rate
    """,
    "get_barrier_prevalence_by_archetype": """
        MATCH (bd:BarrierDiagnosis {archetype_id: $archetype_id})
        RETURN bd.primary_barrier AS barrier,
               count(*) AS occurrences,
               avg(bd.primary_barrier_confidence) AS avg_confidence
        ORDER BY occurrences DESC
    """,
    "learning_query_mechanism_personality_interaction": """
        MATCH (tt:TherapeuticTouch {mechanism: $mechanism})-[:PRODUCED]->(bro:BarrierResolutionOutcome)
        MATCH (tt)-[:RESPONDS_TO]->(bd:BarrierDiagnosis)
        WHERE bro.converted = true
        RETURN bd.archetype_id AS archetype,
               count(*) AS n_successes,
               avg(bd.primary_barrier_confidence) AS avg_barrier_confidence
    """,
}
