"""
Base annotator with shared Claude calling logic, retry, rate limiting.

All annotators inherit from this and implement their specific prompts.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Optional

import anthropic

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for Claude API calls."""

    def __init__(self, calls_per_second: float = 10.0, burst: int = 20):
        self._rate = calls_per_second
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
            self._last_refill = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


class BaseAnnotator:
    """Base class for all Claude-based annotators."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Provide via parameter or environment variable."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.model = model or self.MODEL

        # Stats
        self._calls = 0
        self._errors = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "calls": self._calls,
            "errors": self._errors,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
        }

    async def call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Call Claude with retry and rate limiting. Returns parsed JSON."""
        await self.rate_limiter.acquire()

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self.async_client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens or self.MAX_TOKENS,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt,
                )
                self._calls += 1
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens

                # Extract text content
                text = response.content[0].text.strip()

                # Parse JSON — handle markdown code fences
                if text.startswith("```"):
                    # Remove ```json ... ``` wrapper
                    lines = text.split("\n")
                    text = "\n".join(
                        line for line in lines
                        if not line.strip().startswith("```")
                    )

                return json.loads(text)

            except anthropic.RateLimitError:
                delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Rate limited, waiting {delay}s (attempt {attempt})")
                await asyncio.sleep(delay)
            except anthropic.APIStatusError as e:
                if e.status_code >= 500 and attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(f"API error {e.status_code}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    self._errors += 1
                    raise
            except json.JSONDecodeError as e:
                self._errors += 1
                logger.error(f"JSON parse error: {e}. Raw text: {text[:200]}")
                if attempt < self.MAX_RETRIES:
                    continue
                raise

        self._errors += 1
        raise RuntimeError(f"Max retries ({self.MAX_RETRIES}) exceeded")

    def call_claude_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Synchronous Claude call for non-async contexts."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens or self.MAX_TOKENS,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt,
                )
                self._calls += 1
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens

                text = response.content[0].text.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(
                        line for line in lines
                        if not line.strip().startswith("```")
                    )

                return json.loads(text)

            except anthropic.RateLimitError:
                delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(f"Rate limited, waiting {delay}s (attempt {attempt})")
                time.sleep(delay)
            except anthropic.APIStatusError as e:
                if e.status_code >= 500 and attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    time.sleep(delay)
                else:
                    self._errors += 1
                    raise
            except json.JSONDecodeError:
                self._errors += 1
                if attempt < self.MAX_RETRIES:
                    continue
                raise

        self._errors += 1
        raise RuntimeError(f"Max retries ({self.MAX_RETRIES}) exceeded")
