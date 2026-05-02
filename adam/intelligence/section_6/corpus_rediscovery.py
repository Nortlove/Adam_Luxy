# =============================================================================
# Section 6.2 monthly cadence — corpus mechanism re-discovery (Spine #12)
# Location: adam/intelligence/section_6/corpus_rediscovery.py
# =============================================================================
"""Per directive Section 6.2 monthly cadence (line 765-771):

    Full corpus-level mechanism re-discovery.
    Claude API runs over a stratified slice of the Amazon corpus
    (not the full 1.2B; sampled for tractability).
    Proposes new mechanism atoms, new construct interactions,
    new primary metaphors.
    Knockoff-filtered.
    Constitutional-AI critic (M6, repurposed): Opus critiques
    Sonnet's proposals against corpus evidence and existing
    taxonomy.
    Surviving proposals enter the candidate-mechanism pool, gated
    for human approval before promotion to active use.

For LUXY's wrap-out calibration, the "corpus" is operator-curated
LUXY-positioning text snippets that span the directive's named
primary metaphors (CONTAINMENT/CONTROL, RELIABILITY-AS-WEIGHT,
FORWARD-MOTION/PROGRESS, STATUS-AS-VERTICALITY, TIME-AS-RESOURCE).
The full Amazon-corpus pipeline is sibling slice — operationally
blocked on corpus stratification + sampling infrastructure.

THE PRIMITIVE

  * ``MechanismProposal`` — frozen dataclass with name, evidence
    quotes, supporting metaphors, FDR p-value.
  * ``PrimaryMetaphorProposal`` — frozen dataclass with axis name,
    evidence text, supporting tokens, FDR p-value.
  * ``CorpusRediscoveryResult`` — versioned inventory output:
    proposed mechanisms + metaphors + survival flag (True iff
    passed BH-FDR control).
  * ``rediscover_from_corpus(corpus, *, claude_client, fdr_alpha,
    inventory_version)`` — pipeline entry point. Soft-fails on no
    Claude client; returns empty inventory.

KNOCKOFF-FILTER FDR

v0.1 uses Benjamini-Hochberg FDR control (matches existing
``iac_fdr_selection.py`` substrate). Full model-X knockoff per
Candès et al. 2018 is sibling — needs the design matrix +
knockoff-construction infrastructure.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.2 lines 765-771 + Spine #12
    + 2026-05-02 wrap-out hard-stop criterion (iii) + existing
    BH-FDR substrate at iac_fdr_selection.py:87-112.

(b) Tests pin: rediscover with no client returns empty inventory;
    Claude returns malformed → soft-fail with error in result;
    Claude returns valid → proposals parsed into typed objects;
    BH-FDR survival flag set per alpha; versioned inventory
    JSON-serializable; dataclasses frozen.

(c) calibration_pending=True. v0.1 uses BH-FDR (sibling: full
    model-X knockoff). Constitutional AI critic step is honest-
    tagged sibling. A14 flag: SECTION_6_2_REDISCOVERY_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Constitutional AI critic (M6 repurposed) — Opus critiques
      Sonnet proposals. v0.1 does single-pass Sonnet. Critic
      pass is sibling.
    * Full model-X knockoff (Candès 2018) — v0.1 BH-FDR is the
      defensible interim.
    * Stratified sampling over the 937M-review Amazon corpus —
      v0.1 takes any caller-supplied corpus; production corpus
      stratification is sibling.
    * Auto-promotion of surviving proposals to active mechanism
      taxonomy. v0.1 produces inventory; promotion is gated for
      human approval per directive line 770.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# A14 SECTION_6_2_REDISCOVERY_PILOT_PENDING
DEFAULT_FDR_ALPHA: float = 0.10  # directive line 768 ("FDR < 0.1")


@dataclass(frozen=True)
class MechanismProposal:
    """One Claude-proposed mechanism atom."""

    name: str
    evidence_quotes: List[str] = field(default_factory=list)
    supporting_metaphors: List[str] = field(default_factory=list)
    raw_p_value: float = 1.0
    survives_fdr: bool = False


@dataclass(frozen=True)
class PrimaryMetaphorProposal:
    """One Claude-proposed primary metaphor axis (per
    claude_feature_scoring.PRIMARY_METAPHOR_AXIS_NAMES vocabulary
    when known; novel proposals get a free-form name)."""

    axis_name: str
    evidence_quotes: List[str] = field(default_factory=list)
    supporting_tokens: List[str] = field(default_factory=list)
    raw_p_value: float = 1.0
    survives_fdr: bool = False


@dataclass(frozen=True)
class CorpusRediscoveryResult:
    """One run's output. Persisted as a versioned-inventory artifact."""

    inventory_version: str
    corpus_n_documents: int
    proposed_mechanisms: List[MechanismProposal] = field(
        default_factory=list,
    )
    proposed_metaphors: List[PrimaryMetaphorProposal] = field(
        default_factory=list,
    )
    fdr_alpha: float = DEFAULT_FDR_ALPHA
    surviving_mechanism_count: int = 0
    surviving_metaphor_count: int = 0
    started_at_ts: float = field(default_factory=time.time)
    finished_at_ts: float = 0.0
    errors: List[str] = field(default_factory=list)


# =============================================================================
# Claude prompt — directive Section 6.2 + Spine #12 phrasing
# =============================================================================


_REDISCOVERY_PROMPT_TEMPLATE: str = (
    "You are the offline mechanism-discovery system for ADAM "
    "(Bargh-lineage cognitive architecture for advertising). Your "
    "task: read the corpus snippets below and propose:\n\n"
    "  (1) Persuasion mechanism atoms exhibited in the corpus "
    "(beyond the existing 8 canonical: social_proof, scarcity, "
    "authority, reciprocity, commitment, liking, unity, "
    "reason_why). New atoms should be psychologically distinct from "
    "the 8 and supported by ≥2 corpus quotes.\n"
    "  (2) Primary metaphor frames invoked in the corpus (beyond "
    "the canonical 8: warmth, distance, vertical, solidity, "
    "containment, force, path, closeness). Novel frames should be "
    "supported by ≥2 quotes + a coherent source-target mapping.\n\n"
    "Use cross-linguistic primary-metaphor theory (Lakoff & "
    "Johnson 1980; Grady 1997) — neural-recycling-grade; not "
    "ad-hoc surface metaphors.\n\n"
    "CORPUS:\n{corpus_block}\n\n"
    "Return JSON only:\n"
    "{{\n"
    '  "proposed_mechanisms": [\n'
    "    {{\n"
    '      "name": "<snake_case_mechanism>",\n'
    '      "evidence_quotes": ["<quote 1>", "<quote 2>"],\n'
    '      "supporting_metaphors": ["<frame_a>"],\n'
    '      "raw_p_value": <0..1>\n'
    "    }}\n"
    "  ],\n"
    '  "proposed_metaphors": [\n'
    "    {{\n"
    '      "axis_name": "<snake_case_axis>",\n'
    '      "evidence_quotes": ["<quote 1>", "<quote 2>"],\n'
    '      "supporting_tokens": ["<token>"],\n'
    '      "raw_p_value": <0..1>\n'
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "raw_p_value reflects your confidence the pattern reflects a "
    "real psychological mechanism / metaphor frame in the corpus, "
    "NOT a surface artifact. Lower = stronger signal. Be "
    "calibrated; do not produce p<0.01 unless evidence is "
    "overwhelming."
)


def _build_corpus_block(corpus: List[str], max_documents: int = 50) -> str:
    """Compose the corpus block for the Claude prompt. Caps at
    max_documents to bound prompt size; longer corpora should be
    stratified-sampled by the caller."""
    snippets = corpus[: max(0, max_documents)]
    return "\n\n".join(
        f"[{i + 1}] {snippet.strip()}"
        for i, snippet in enumerate(snippets)
        if snippet and snippet.strip()
    )


# =============================================================================
# BH-FDR control (Benjamini-Hochberg)
# =============================================================================


def _bh_survival_flags(
    p_values: List[float], alpha: float,
) -> List[bool]:
    """Return per-proposal survival flags under BH-FDR at level
    ``alpha``. v0.1 substrate; full model-X knockoff is sibling."""
    if not p_values:
        return []
    n = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    survives = [False] * n
    # Find largest k such that p_(k) ≤ k/n × alpha.
    k_star = -1
    for rank, (orig_idx, p) in enumerate(indexed):
        threshold = ((rank + 1) / n) * alpha
        if p <= threshold:
            k_star = rank
    if k_star >= 0:
        for rank, (orig_idx, p) in enumerate(indexed):
            if rank <= k_star:
                survives[orig_idx] = True
    return survives


# =============================================================================
# Pipeline
# =============================================================================


def _parse_claude_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse Claude's JSON response with fence stripping (matches
    creative_variant_generator pattern)."""
    if not content:
        return None
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


async def rediscover_from_corpus(
    corpus: List[str],
    *,
    claude_client: Optional[Any] = None,
    inventory_version: str = "v0.1-calibration",
    fdr_alpha: float = DEFAULT_FDR_ALPHA,
    max_documents_per_call: int = 50,
    temperature: float = 0.4,
) -> CorpusRediscoveryResult:
    """Run the corpus mechanism re-discovery pipeline.

    Args:
        corpus: list of LUXY-plausible text snippets (paragraph-
            length each).
        claude_client: a ClaudeClient with async .complete(prompt,
            temperature). None → returns empty inventory + error.
        inventory_version: stamped on the result for artifact
            versioning.
        fdr_alpha: BH-FDR control level. Default 0.10 per directive
            line 768.
        max_documents_per_call: caps prompt size.
        temperature: Claude temperature. Default 0.4 — exploratory
            but not noisy.

    Returns:
        ``CorpusRediscoveryResult`` with proposals + survival flags.
    """
    started_at = time.time()
    n_docs = len(corpus)
    errors: List[str] = []

    if claude_client is None:
        errors.append("no_claude_client")
        return CorpusRediscoveryResult(
            inventory_version=inventory_version,
            corpus_n_documents=n_docs,
            fdr_alpha=fdr_alpha,
            started_at_ts=started_at,
            finished_at_ts=time.time(),
            errors=errors,
        )

    if not corpus:
        errors.append("empty_corpus")
        return CorpusRediscoveryResult(
            inventory_version=inventory_version,
            corpus_n_documents=0,
            fdr_alpha=fdr_alpha,
            started_at_ts=started_at,
            finished_at_ts=time.time(),
            errors=errors,
        )

    corpus_block = _build_corpus_block(
        corpus, max_documents=max_documents_per_call,
    )
    prompt = _REDISCOVERY_PROMPT_TEMPLATE.format(corpus_block=corpus_block)

    try:
        response = await claude_client.complete(
            prompt=prompt, temperature=temperature,
        )
    except Exception as exc:
        errors.append(f"claude_api_raised: {exc!r}")
        return CorpusRediscoveryResult(
            inventory_version=inventory_version,
            corpus_n_documents=n_docs,
            fdr_alpha=fdr_alpha,
            started_at_ts=started_at,
            finished_at_ts=time.time(),
            errors=errors,
        )

    content = getattr(response, "content", "") if response else ""
    parsed = _parse_claude_response(content)
    if parsed is None:
        errors.append("claude_response_parse_failed")
        return CorpusRediscoveryResult(
            inventory_version=inventory_version,
            corpus_n_documents=n_docs,
            fdr_alpha=fdr_alpha,
            started_at_ts=started_at,
            finished_at_ts=time.time(),
            errors=errors,
        )

    raw_mechs = parsed.get("proposed_mechanisms", []) or []
    raw_metas = parsed.get("proposed_metaphors", []) or []

    mech_pvals: List[float] = []
    mech_records: List[Tuple[str, List[str], List[str], float]] = []
    for m in raw_mechs:
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or "").strip()
        if not name:
            continue
        quotes = [str(q) for q in (m.get("evidence_quotes") or []) if q]
        metaphors = [str(s) for s in (m.get("supporting_metaphors") or []) if s]
        try:
            p = float(m.get("raw_p_value", 1.0))
        except (TypeError, ValueError):
            p = 1.0
        p = max(0.0, min(1.0, p))
        mech_records.append((name, quotes, metaphors, p))
        mech_pvals.append(p)

    metaphor_pvals: List[float] = []
    metaphor_records: List[Tuple[str, List[str], List[str], float]] = []
    for x in raw_metas:
        if not isinstance(x, dict):
            continue
        axis_name = str(x.get("axis_name") or "").strip()
        if not axis_name:
            continue
        quotes = [str(q) for q in (x.get("evidence_quotes") or []) if q]
        tokens = [str(t) for t in (x.get("supporting_tokens") or []) if t]
        try:
            p = float(x.get("raw_p_value", 1.0))
        except (TypeError, ValueError):
            p = 1.0
        p = max(0.0, min(1.0, p))
        metaphor_records.append((axis_name, quotes, tokens, p))
        metaphor_pvals.append(p)

    mech_survives = _bh_survival_flags(mech_pvals, fdr_alpha)
    meta_survives = _bh_survival_flags(metaphor_pvals, fdr_alpha)

    proposed_mechanisms = [
        MechanismProposal(
            name=name,
            evidence_quotes=quotes,
            supporting_metaphors=metaphors,
            raw_p_value=p,
            survives_fdr=bool(survives),
        )
        for (name, quotes, metaphors, p), survives in zip(
            mech_records, mech_survives,
        )
    ]
    proposed_metaphors = [
        PrimaryMetaphorProposal(
            axis_name=axis_name,
            evidence_quotes=quotes,
            supporting_tokens=tokens,
            raw_p_value=p,
            survives_fdr=bool(survives),
        )
        for (axis_name, quotes, tokens, p), survives in zip(
            metaphor_records, meta_survives,
        )
    ]

    return CorpusRediscoveryResult(
        inventory_version=inventory_version,
        corpus_n_documents=n_docs,
        proposed_mechanisms=proposed_mechanisms,
        proposed_metaphors=proposed_metaphors,
        fdr_alpha=fdr_alpha,
        surviving_mechanism_count=sum(
            1 for p in proposed_mechanisms if p.survives_fdr
        ),
        surviving_metaphor_count=sum(
            1 for p in proposed_metaphors if p.survives_fdr
        ),
        started_at_ts=started_at,
        finished_at_ts=time.time(),
        errors=errors,
    )
