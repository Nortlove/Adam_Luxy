# =============================================================================
# Therapeutic Retargeting Engine — Claude Argument Generation Engine
# Location: adam/retargeting/engines/claude_argument_engine.py
# Spec: Enhancement #33, Section E.6 + Domain 16
# =============================================================================

"""
Claude Argument Generation Engine — The Most Powerful Mechanism.

Unlike all other mechanisms which select from pre-existing creative templates,
this generates a NOVEL factual argument tailored to the specific
barrier x personality x touch history. It exploits:

- Salvi (2024): LLM persuasion derives from factual argument quality
- Bozdag (2025): Multi-turn coherence across 4+ turns amplifies effectiveness
- Hackenburg & Margetts (2024): Only deep psychological personalization works

Three operating modes:
1. FULL: Complete ad copy from scratch (~500ms). High-value sequences.
2. INSERTION: Single key argument inserted into template (~200ms). Medium-value.
3. RANKING: Rank pre-generated arguments by effectiveness (~100ms). High-volume.

INFORMATIV's deepest moat: no competitor has bilateral psychological
intelligence + LLM reasoning generating barrier-specific factual
arguments in real time.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from adam.retargeting.prompts.argument_generation import (
    build_full_generation_prompt,
    build_argument_insertion_prompt,
    build_argument_ranking_prompt,
)

logger = logging.getLogger(__name__)


class ArgumentMode(str, Enum):
    """Operating modes for the argument engine."""

    FULL = "full"            # Complete ad copy (~500ms)
    INSERTION = "insertion"  # Single argument into template (~200ms)
    RANKING = "ranking"      # Rank pre-generated arguments (~100ms)


@dataclass
class GeneratedArgument:
    """Output of the Claude Argument Engine."""

    mode: ArgumentMode
    headline: str = ""
    body: str = ""
    cta: str = ""
    factual_claim: str = ""
    argument_type: str = ""  # comparison, testimonial, evidence, narrative, value_proposition
    barrier_addressed: str = ""
    confidence: float = 0.5

    # For insertion mode
    inserted_argument: str = ""

    # For ranking mode
    ranked_indices: List[int] = field(default_factory=list)

    # Metadata
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    model_used: str = ""


class ClaudeArgumentEngine:
    """Generates barrier-specific factual arguments via Claude.

    Uses the existing ClaudeClient (adam/llm/client.py) for API calls.
    Maintains "conversation memory" across the retargeting sequence for
    multi-turn coherence (Bozdag 2025).
    """

    # Memory bounds — prevents OOM from long-running sequences
    _MAX_MEMORY_PER_SEQUENCE = 20  # Max turns per sequence
    _MAX_SEQUENCES = 5000          # Max concurrent sequences in memory
    _STALE_SECONDS = 3600          # Evict sequences unused for 1hr

    def __init__(self, claude_client=None):
        self._client = claude_client
        # Conversation memory: sequence_id → list of (prompt, response) pairs
        self._memory: Dict[str, List[Dict[str, str]]] = {}
        self._memory_ts: Dict[str, float] = {}  # Last access timestamps

    async def generate(
        self,
        mode: ArgumentMode,
        barrier: str,
        archetype_id: str,
        brand_name: str = "",
        bilateral_edge: Optional[Dict[str, float]] = None,
        brand_data: Optional[Dict] = None,
        touch_history: Optional[List[Dict]] = None,
        narrative_chapter: int = 1,
        scaffold_level: int = 2,
        construal_level: str = "concrete",
        template_text: str = "",
        arguments_to_rank: Optional[List[str]] = None,
        sequence_id: str = "",
    ) -> GeneratedArgument:
        """Generate a barrier-specific argument using Claude.

        Dispatches to the appropriate mode handler.
        """
        brand_data = brand_data or {}
        touch_history = touch_history or []
        bilateral_edge = bilateral_edge or {}

        if mode == ArgumentMode.FULL:
            return await self._generate_full(
                barrier, archetype_id, brand_name, brand_data,
                bilateral_edge, touch_history, narrative_chapter,
                scaffold_level, construal_level, sequence_id,
            )
        elif mode == ArgumentMode.INSERTION:
            return await self._generate_insertion(
                barrier, archetype_id, brand_name, brand_data,
                bilateral_edge, template_text,
            )
        elif mode == ArgumentMode.RANKING:
            return await self._rank_arguments(
                barrier, archetype_id, bilateral_edge,
                arguments_to_rank or [],
            )
        else:
            logger.warning("Unknown argument mode: %s", mode)
            return GeneratedArgument(mode=mode)

    async def _generate_full(
        self,
        barrier: str,
        archetype_id: str,
        brand_name: str,
        brand_data: Dict,
        bilateral_edge: Dict[str, float],
        touch_history: List[Dict],
        narrative_chapter: int,
        scaffold_level: int,
        construal_level: str,
        sequence_id: str,
    ) -> GeneratedArgument:
        """FULL mode: Complete ad copy generation."""
        prompt = build_full_generation_prompt(
            barrier=barrier,
            archetype_id=archetype_id,
            brand_name=brand_name,
            brand_data=brand_data,
            bilateral_edge=bilateral_edge,
            touch_history=touch_history,
            narrative_chapter=narrative_chapter,
            scaffold_level=scaffold_level,
            construal_level=construal_level,
        )

        response_text = await self._call_claude(prompt, sequence_id)

        # Parse JSON response
        result = self._parse_full_response(response_text)
        result.mode = ArgumentMode.FULL
        result.barrier_addressed = barrier
        return result

    async def _generate_insertion(
        self,
        barrier: str,
        archetype_id: str,
        brand_name: str,
        brand_data: Dict,
        bilateral_edge: Dict[str, float],
        template_text: str,
    ) -> GeneratedArgument:
        """INSERTION mode: Single argument for template insertion."""
        prompt = build_argument_insertion_prompt(
            barrier=barrier,
            archetype_id=archetype_id,
            brand_name=brand_name,
            brand_data=brand_data,
            bilateral_edge=bilateral_edge,
            template_text=template_text,
        )

        response_text = await self._call_claude(prompt)

        # Extract plain text from response (may be JSON from fallback)
        argument_text = response_text.strip()
        try:
            data = json.loads(argument_text)
            if isinstance(data, dict):
                # Extract the most relevant text field
                argument_text = (
                    data.get("factual_claim")
                    or data.get("body")
                    or data.get("headline")
                    or argument_text
                )
        except (json.JSONDecodeError, ValueError):
            pass  # Response is already plain text

        return GeneratedArgument(
            mode=ArgumentMode.INSERTION,
            inserted_argument=argument_text,
            barrier_addressed=barrier,
            confidence=0.7,
        )

    async def _rank_arguments(
        self,
        barrier: str,
        archetype_id: str,
        bilateral_edge: Dict[str, float],
        arguments: List[str],
    ) -> GeneratedArgument:
        """RANKING mode: Rank pre-generated arguments."""
        if not arguments:
            return GeneratedArgument(
                mode=ArgumentMode.RANKING, ranked_indices=[]
            )

        prompt = build_argument_ranking_prompt(
            barrier=barrier,
            archetype_id=archetype_id,
            arguments=arguments,
            bilateral_edge=bilateral_edge,
        )

        response_text = await self._call_claude(prompt)

        # Parse comma-separated indices
        indices = self._parse_ranking_response(response_text, len(arguments))

        return GeneratedArgument(
            mode=ArgumentMode.RANKING,
            ranked_indices=indices,
            barrier_addressed=barrier,
            confidence=0.6,
        )

    async def _call_claude(
        self, prompt: str, sequence_id: str = ""
    ) -> str:
        """Call Claude API with optional conversation memory.

        Uses the existing ClaudeClient if available, otherwise returns
        a structured fallback for testing/development.
        """
        import time
        start = time.time()

        # Append to conversation memory for multi-turn coherence
        if sequence_id:
            self._evict_stale_memory()
            if sequence_id not in self._memory:
                self._memory[sequence_id] = []
            self._memory[sequence_id].append({"role": "user", "content": prompt})
            # Enforce per-sequence bound (keep most recent turns)
            if len(self._memory[sequence_id]) > self._MAX_MEMORY_PER_SEQUENCE:
                self._memory[sequence_id] = self._memory[sequence_id][-self._MAX_MEMORY_PER_SEQUENCE:]
            self._memory_ts[sequence_id] = time.time()

        if self._client is not None:
            try:
                # Use existing ClaudeClient pattern
                response = await self._client.complete(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.7,
                )
                response_text = response.get("text", "") if isinstance(response, dict) else str(response)

                elapsed = (time.time() - start) * 1000
                logger.debug(
                    "Claude argument generated in %.0fms (%d chars)",
                    elapsed, len(response_text),
                )

                if sequence_id:
                    self._memory[sequence_id].append(
                        {"role": "assistant", "content": response_text}
                    )

                return response_text
            except Exception as e:
                logger.warning("Claude API call failed: %s", e)

        # Fallback: structured response for development/testing
        return self._generate_fallback(prompt)

    def _parse_full_response(self, text: str) -> GeneratedArgument:
        """Parse JSON response from full generation mode."""
        try:
            # Try to extract JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return GeneratedArgument(
                    mode=ArgumentMode.FULL,
                    headline=data.get("headline", ""),
                    body=data.get("body", ""),
                    cta=data.get("cta", ""),
                    factual_claim=data.get("factual_claim", ""),
                    argument_type=data.get("argument_type", "evidence"),
                    confidence=0.8,
                )
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug("Failed to parse Claude JSON response: %s", e)

        # Fallback: use raw text as body
        return GeneratedArgument(
            mode=ArgumentMode.FULL,
            body=text.strip(),
            confidence=0.4,
        )

    def _parse_ranking_response(
        self, text: str, n_arguments: int
    ) -> List[int]:
        """Parse comma-separated ranking indices."""
        try:
            parts = text.strip().split(",")
            indices = [int(p.strip()) for p in parts if p.strip().isdigit()]
            # Validate: all within range, no duplicates
            valid = [i for i in indices if 1 <= i <= n_arguments]
            if len(valid) == len(set(valid)):
                return valid
        except (ValueError, AttributeError):
            pass

        # Fallback: original order
        return list(range(1, n_arguments + 1))

    def _generate_fallback(self, prompt: str) -> str:
        """Generate structured fallback when Claude is unavailable.

        Used in development/testing. Produces plausible JSON output
        that downstream consumers can process.

        NOTE: Default copy uses LUXY Ride (launch brand) as baseline creative.
        For new brands, override via brand_copy parameter in the prompt context
        or by passing brand-specific creative from the campaign config.
        When the real Claude API is available, all copy is generated dynamically
        from the brand context — this fallback only fires without API access.
        """
        # Extract barrier from prompt
        barrier = "trust_deficit"
        if "price_friction" in prompt:
            barrier = "price_friction"
        elif "emotional_disconnect" in prompt:
            barrier = "emotional_disconnect"
        elif "negativity_block" in prompt:
            barrier = "negativity_block"

        fallback_copy = {
            "trust_deficit": {
                "headline": "4.8 stars across 3,247 rides",
                "body": "Every LUXY Ride driver has 3+ years experience and a verified background check. Our fleet is 100% Mercedes S-Class. Cancel free up to 24 hours before.",
                "cta": "See driver profiles",
                "factual_claim": "3,247 completed rides with 4.8 average rating",
                "argument_type": "evidence",
            },
            "regulatory_mismatch": {
                "headline": "You've earned this.",
                "body": "After the quarter you just delivered, the ride to the airport shouldn't be another thing to manage. LUXY Ride handles the details so you can focus on what's next.",
                "cta": "Reward yourself",
                "factual_claim": "Premium service designed for high-performers",
                "argument_type": "narrative",
            },
            "processing_overload": {
                "headline": "LUXY Ride. Tap. Book. Arrive.",
                "body": "Three steps. That's it.",
                "cta": "Book now",
                "factual_claim": "Booking takes under 30 seconds",
                "argument_type": "value_proposition",
            },
            "emotional_disconnect": {
                "headline": "Tuesday morning. 5:47 AM. Your driver David is already waiting.",
                "body": "Black Mercedes. Engine running. Your name on the screen. You review your deck on the way to JFK. You arrive at Terminal 4 at 6:23 — exactly when you planned.",
                "cta": "Book your next ride",
                "factual_claim": "Drivers arrive early, confirmed by GPS tracking",
                "argument_type": "narrative",
            },
            "price_friction": {
                "headline": "$65 guaranteed. No surge. Ever.",
                "body": "JFK to Manhattan: Uber Black surge at 9 PM costs $85-120. LUXY Ride costs $65. Same route. Same comfort. No surprises.",
                "cta": "Compare prices",
                "factual_claim": "LUXY Ride is $65 guaranteed vs Uber Black surge pricing",
                "argument_type": "comparison",
            },
            "motive_mismatch": {
                "headline": "Your next client meeting starts at the curb.",
                "body": "First impressions begin before the handshake. Arrive in a chauffeured Mercedes S-Class and set the tone before you walk through the door.",
                "cta": "Make an entrance",
                "factual_claim": "100% Mercedes S-Class fleet",
                "argument_type": "narrative",
            },
            "negativity_block": {
                "headline": "After 2 no-shows with other services, I was done.",
                "body": "My colleague insisted I try LUXY Ride. Driver was early. Car was spotless. I've used them 11 times since. — Sarah M., verified rider",
                "cta": "Read more reviews",
                "factual_claim": "Testimonial from verified repeat customer",
                "argument_type": "testimonial",
            },
            "reactance_triggered": {
                "headline": "We know you have options.",
                "body": "No pressure. No countdown timers. No 'limited availability' tricks. Just a reliable car service when you're ready. If that's today, great. If not, we'll be here.",
                "cta": "Learn more whenever you'd like",
                "factual_claim": "No-pressure booking with free cancellation",
                "argument_type": "value_proposition",
            },
            "identity_misalignment": {
                "headline": "Not just a car service. A standard.",
                "body": "The executives who use LUXY Ride don't think of it as transportation. They think of it as how they move through the world. Purposefully. Precisely. Without compromise.",
                "cta": "Join them",
                "factual_claim": "400+ corporate accounts",
                "argument_type": "narrative",
            },
            "intention_action_gap": {
                "headline": "Your next airport ride: sorted.",
                "body": "When your flight confirmation arrives, book your LUXY Ride. One tap. Driver confirmed instantly. One less thing between you and the gate.",
                "cta": "Book in 30 seconds",
                "factual_claim": "Instant driver confirmation",
                "argument_type": "value_proposition",
            },
        }

        data = fallback_copy.get(barrier, fallback_copy["trust_deficit"])
        data["barrier_addressed"] = barrier
        return json.dumps(data)

    def clear_memory(self, sequence_id: str) -> None:
        """Clear conversation memory for a completed sequence."""
        self._memory.pop(sequence_id, None)
        self._memory_ts.pop(sequence_id, None)

    def _evict_stale_memory(self) -> None:
        """Evict stale sequences and enforce max concurrent sequences."""
        import time as _time
        now = _time.time()

        # Evict sequences unused for > _STALE_SECONDS
        stale = [
            sid for sid, ts in self._memory_ts.items()
            if now - ts > self._STALE_SECONDS
        ]
        for sid in stale:
            self._memory.pop(sid, None)
            self._memory_ts.pop(sid, None)

        # If still over limit, evict oldest
        if len(self._memory) > self._MAX_SEQUENCES:
            sorted_by_age = sorted(self._memory_ts.items(), key=lambda x: x[1])
            to_evict = len(self._memory) - self._MAX_SEQUENCES
            for sid, _ in sorted_by_age[:to_evict]:
                self._memory.pop(sid, None)
                self._memory_ts.pop(sid, None)

        if stale:
            logger.debug("Evicted %d stale argument memory sequences", len(stale))

    @property
    def memory_stats(self) -> Dict[str, Any]:
        """Statistics about conversation memory usage."""
        return {
            "active_sequences": len(self._memory),
            "total_turns": sum(len(v) for v in self._memory.values()),
            "max_sequences": self._MAX_SEQUENCES,
            "max_turns_per_seq": self._MAX_MEMORY_PER_SEQUENCE,
        }
