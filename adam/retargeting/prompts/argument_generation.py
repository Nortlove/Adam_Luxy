# =============================================================================
# Therapeutic Retargeting Engine — Claude Argument Generation Prompts
# Location: adam/retargeting/prompts/argument_generation.py
# Spec: Enhancement #33, Domain 16
# =============================================================================

"""
Structured Claude prompts for barrier-specific factual argument generation.

Key research findings driving the prompt design:
- Salvi et al. (2024, Nature Human Behaviour): LLM persuasion derives from
  FACTUAL ARGUMENT QUALITY, not psychological technique selection.
- Bozdag et al. (2025): Multi-turn coherence across 4+ turns dramatically
  increases persuasiveness.
- Hackenburg & Margetts (2024, PNAS): Surface demographic personalization
  produces NO effect — only deep psychological personalization works.

These prompts exploit INFORMATIV's unique advantage: bilateral edge data
provides the deep psychological context that makes LLM-generated arguments
effective where demographic targeting fails.
"""

import re
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Input sanitization — prevents prompt injection
# ---------------------------------------------------------------------------

_MAX_INPUT_LEN = 500  # Truncate any single input field

def _sanitize(value: str) -> str:
    """Sanitize user-controlled input before prompt interpolation.

    1. Truncate to MAX_INPUT_LEN
    2. Strip common injection patterns (role overrides, system/assistant markers)
    3. Wrap in XML tags so Claude treats it as data, not instructions
    """
    if not isinstance(value, str):
        return str(value)[:_MAX_INPUT_LEN]
    s = value[:_MAX_INPUT_LEN]
    # Strip role-override attempts
    s = re.sub(r'(?i)(system|assistant|human|user)\s*:', '', s)
    # Strip XML-like instruction tags
    s = re.sub(r'<\s*/?\s*(system|instructions?|override|ignore)\s*>', '', s, flags=re.IGNORECASE)
    return s


def build_full_generation_prompt(
    barrier: str,
    archetype_id: str,
    brand_name: str,
    brand_data: Dict,
    bilateral_edge: Dict[str, float],
    touch_history: List[Dict],
    narrative_chapter: int,
    scaffold_level: int,
    construal_level: str,
) -> str:
    """Build prompt for FULL creative generation (~500ms).

    Claude generates complete ad copy (headline, body, CTA) from scratch,
    tailored to the specific barrier x personality x touch history.
    """
    # Format touch history as "conversation memory"
    history_str = _format_touch_history(touch_history)
    edge_str = _format_bilateral_edge(bilateral_edge)
    safe_brand = _sanitize(brand_name)
    safe_barrier = _sanitize(barrier)
    safe_archetype = _sanitize(archetype_id)

    return f"""You are generating advertising copy for INFORMATIV's Therapeutic Retargeting Engine.

CRITICAL CONTEXT: This is NOT template-based ad copy. You are generating a NOVEL factual argument specifically designed to resolve a diagnosed psychological barrier for a specific buyer profile. Your argument must be based on FACTS about the brand, not psychological manipulation techniques.

<brand_context>
Name: {safe_brand}
Key data: {_format_brand_data(brand_data)}
</brand_context>

<buyer_psychology>
Archetype: {safe_archetype}
Bilateral alignment dimensions:
{edge_str}
</buyer_psychology>

<diagnosed_barrier>
Primary barrier: {safe_barrier}
- This means: {_barrier_explanation(barrier)}

## Retargeting Sequence Context
- This is touch #{len(touch_history) + 1} in the sequence
- Narrative chapter: {narrative_chapter}/5 ({_chapter_name(narrative_chapter)})
- Scaffold level: {scaffold_level}/5
- Construal level: {construal_level}
{history_str}

## Your Task
Generate ad copy that:
1. Addresses the SPECIFIC barrier ({barrier}) with a FACTUAL argument
2. Builds on the previous touches (multi-turn coherence)
3. Matches the construal level ({construal_level}) — {"abstract 'why' framing" if construal_level == "abstract" else "concrete 'how' framing with specifics"}
4. Uses autonomy-supporting language ("consider", "perhaps", "you might find")
5. Does NOT use high-pressure tactics, false urgency, or manipulative framing

## Output Format (JSON)
{{
    "headline": "...",
    "body": "...",
    "cta": "...",
    "factual_claim": "The single most important fact in this copy",
    "barrier_addressed": "{barrier}",
    "argument_type": "comparison|testimonial|evidence|narrative|value_proposition"
}}"""


def build_argument_insertion_prompt(
    barrier: str,
    archetype_id: str,
    brand_name: str,
    brand_data: Dict,
    bilateral_edge: Dict[str, float],
    template_text: str,
) -> str:
    """Build prompt for ARGUMENT INSERTION mode (~200ms).

    Claude generates a single key factual argument that gets inserted
    into a pre-existing creative template.
    """
    edge_str = _format_bilateral_edge(bilateral_edge)

    return f"""Generate ONE factual argument to insert into advertising copy.

Brand: {brand_name}
Buyer archetype: {archetype_id}
Barrier to resolve: {barrier} — {_barrier_explanation(barrier)}
Key bilateral dimensions:
{edge_str}

Template (insert your argument where [ARGUMENT] appears):
{template_text}

Requirements:
- The argument must be a SPECIFIC FACT about {brand_name}
- It must directly address the {barrier} barrier
- Maximum 25 words
- No superlatives, no unverifiable claims

Output the argument text only, nothing else."""


def build_argument_ranking_prompt(
    barrier: str,
    archetype_id: str,
    arguments: List[str],
    bilateral_edge: Dict[str, float],
) -> str:
    """Build prompt for ARGUMENT RANKING mode (~100ms).

    Claude ranks pre-generated arguments by likely effectiveness
    for this specific barrier x profile combination.
    """
    args_str = "\n".join(f"{i+1}. {arg}" for i, arg in enumerate(arguments))
    edge_str = _format_bilateral_edge(bilateral_edge)

    return f"""Rank these advertising arguments by effectiveness for this buyer.

Buyer archetype: {archetype_id}
Barrier to resolve: {barrier}
Key dimensions:
{edge_str}

Arguments to rank:
{args_str}

Output ONLY the numbers in order from most to least effective, comma-separated.
Example: 3,1,4,2"""


# ---------------------------------------------------------------------------
# Helper formatters
# ---------------------------------------------------------------------------

def _format_touch_history(touches: List[Dict]) -> str:
    """Format touch history as conversation memory for multi-turn coherence."""
    if not touches:
        return "- This is the FIRST touch — no prior conversation."

    lines = ["## Previous Touches (conversation memory)"]
    for i, t in enumerate(touches[:20], 1):  # Cap at 20 touches
        mech = _sanitize(str(t.get("mechanism", "unknown")))
        outcome = _sanitize(str(t.get("outcome", "unknown")))
        lines.append(
            f"- Touch {i}: Used {mech} → {outcome}"
        )

    lines.append(
        "\nIMPORTANT: Reference and build upon the previous touches. "
        "Do NOT repeat the same argument. Each touch should feel like "
        "the next chapter of a conversation, not a standalone ad."
    )
    return "\n".join(lines)


def _format_bilateral_edge(edge: Dict[str, float]) -> str:
    """Format bilateral edge dimensions as readable context."""
    if not edge:
        return "  (no edge data available)"

    lines = []
    for dim, val in sorted(edge.items(), key=lambda x: x[1], reverse=True):
        label = dim.replace("_", " ").title()
        bar = "+" * int(val * 10) if val > 0 else ""
        lines.append(f"  {label:40s} {val:.3f} {bar}")
    return "\n".join(lines[:10])  # Top 10 dimensions


def _format_brand_data(data: Dict) -> str:
    """Format brand data for prompt context."""
    if not data:
        return "(no brand data provided)"
    parts = []
    for k, v in data.items():
        if isinstance(v, (str, int, float)):
            parts.append(f"{_sanitize(str(k))}: {_sanitize(str(v))}")
    return "; ".join(parts[:8])  # Limit to 8 fields


def _barrier_explanation(barrier: str) -> str:
    """Human-readable explanation of each barrier type."""
    explanations = {
        "trust_deficit": (
            "The buyer does not trust the brand enough. "
            "Address with verifiable facts, credentials, and evidence."
        ),
        "regulatory_mismatch": (
            "The messaging framing (gain vs loss) doesn't match the buyer's "
            "regulatory orientation. Reframe to match their natural style."
        ),
        "processing_overload": (
            "The messaging is too complex for this buyer's processing style. "
            "Simplify radically — fewer words, clearer structure."
        ),
        "emotional_disconnect": (
            "The messaging feels transactional, not human. "
            "Create emotional resonance through vivid scenarios or narratives."
        ),
        "price_friction": (
            "The buyer perceives the price as too high relative to value. "
            "Address with value comparisons, not discounts."
        ),
        "motive_mismatch": (
            "The ad speaks to the wrong need. "
            "Identify and address the buyer's actual motivation."
        ),
        "negativity_block": (
            "The buyer has encountered negative information and can't get past it. "
            "Address specific concerns with counter-evidence."
        ),
        "reactance_triggered": (
            "The buyer feels pushed and is resisting. "
            "Back off pressure, restore autonomy, use indirect approaches."
        ),
        "identity_misalignment": (
            "The brand doesn't match the buyer's self-concept. "
            "Show how the brand aligns with who they are or aspire to be."
        ),
        "intention_action_gap": (
            "The buyer wants the product but hasn't acted. "
            "Provide specific if-then implementation plans."
        ),
    }
    return explanations.get(barrier, "Unknown barrier type.")


def _chapter_name(chapter: int) -> str:
    """Human name for narrative chapter."""
    names = {
        1: "Introduction",
        2: "Complication",
        3: "Rising Action",
        4: "Resolution",
        5: "Epilogue",
    }
    return names.get(chapter, f"Chapter {chapter}")
