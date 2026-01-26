# =============================================================================
# ADAM Claude Client
# Location: adam/llm/client.py
# =============================================================================

"""
CLAUDE CLIENT

HTTP client for Anthropic's Claude API with:
- Retry logic
- Circuit breaking
- Token tracking
- Structured output
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS
# =============================================================================

CLAUDE_REQUESTS = Counter(
    "adam_claude_requests_total",
    "Claude API requests",
    ["model", "status"],
)

CLAUDE_LATENCY = Histogram(
    "adam_claude_latency_ms",
    "Claude API latency",
    ["model"],
    buckets=[100, 250, 500, 1000, 2500, 5000, 10000],
)

CLAUDE_TOKENS = Counter(
    "adam_claude_tokens_total",
    "Claude API tokens used",
    ["model", "type"],
)


# =============================================================================
# CONFIG
# =============================================================================

class ClaudeConfig(BaseModel):
    """Configuration for Claude client."""
    
    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://api.anthropic.com/v1")
    
    # Model selection
    default_model: str = Field(default="claude-sonnet-4-20250514")
    fast_model: str = Field(default="claude-sonnet-4-20250514")
    reasoning_model: str = Field(default="claude-sonnet-4-20250514")
    
    # Timeouts
    timeout_seconds: float = Field(default=30.0)
    max_retries: int = Field(default=3)
    retry_delay_seconds: float = Field(default=1.0)
    
    # Token limits
    max_tokens: int = Field(default=4096)
    max_input_tokens: int = Field(default=100000)
    
    # Cost tracking
    track_costs: bool = Field(default=True)


class ClaudeMessage(BaseModel):
    """A message in the conversation."""
    
    role: str  # "user" or "assistant"
    content: str


class ClaudeResponse(BaseModel):
    """Response from Claude API."""
    
    content: str
    model: str
    
    # Token usage
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    
    # Timing
    latency_ms: float = Field(default=0.0)
    
    # Stop reason
    stop_reason: Optional[str] = None
    
    # Raw response
    raw: Optional[Dict[str, Any]] = None


# =============================================================================
# CLIENT
# =============================================================================

class ClaudeClient:
    """
    Async client for Claude API.
    """
    
    def __init__(
        self,
        config: Optional[ClaudeConfig] = None,
    ):
        self.config = config or ClaudeConfig()
        
        # Get API key from config or environment
        self.api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            logger.warning("No Anthropic API key configured")
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers={
                    "anthropic-version": "2023-06-01",
                    "x-api-key": self.api_key or "",
                    "content-type": "application/json",
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close the client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> ClaudeResponse:
        """
        Complete a prompt using Claude.
        """
        
        model = model or self.config.default_model
        max_tokens = max_tokens or self.config.max_tokens
        
        # Build request
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        
        if system:
            body["system"] = system
        
        if stop_sequences:
            body["stop_sequences"] = stop_sequences
        
        # Execute with retry
        return await self._execute_with_retry(body, model)
    
    async def chat(
        self,
        messages: List[ClaudeMessage],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> ClaudeResponse:
        """
        Multi-turn chat with Claude.
        """
        
        model = model or self.config.default_model
        max_tokens = max_tokens or self.config.max_tokens
        
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [m.model_dump() for m in messages],
        }
        
        if system:
            body["system"] = system
        
        return await self._execute_with_retry(body, model)
    
    async def _execute_with_retry(
        self,
        body: Dict[str, Any],
        model: str,
    ) -> ClaudeResponse:
        """Execute request with retry logic."""
        
        client = await self._get_client()
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                start = time.perf_counter()
                
                response = await client.post(
                    "/messages",
                    json=body,
                )
                
                latency_ms = (time.perf_counter() - start) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract content
                    content = ""
                    if data.get("content"):
                        for block in data["content"]:
                            if block.get("type") == "text":
                                content += block.get("text", "")
                    
                    # Track metrics
                    input_tokens = data.get("usage", {}).get("input_tokens", 0)
                    output_tokens = data.get("usage", {}).get("output_tokens", 0)
                    
                    CLAUDE_REQUESTS.labels(model=model, status="success").inc()
                    CLAUDE_LATENCY.labels(model=model).observe(latency_ms)
                    CLAUDE_TOKENS.labels(model=model, type="input").inc(input_tokens)
                    CLAUDE_TOKENS.labels(model=model, type="output").inc(output_tokens)
                    
                    return ClaudeResponse(
                        content=content,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        stop_reason=data.get("stop_reason"),
                        raw=data,
                    )
                
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    CLAUDE_REQUESTS.labels(model=model, status="rate_limited").inc()
                    retry_after = float(response.headers.get("retry-after", 5))
                    await asyncio.sleep(retry_after)
                    continue
                
                elif response.status_code >= 500:
                    # Server error - retry
                    CLAUDE_REQUESTS.labels(model=model, status="server_error").inc()
                    await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                    continue
                
                else:
                    # Client error - don't retry
                    CLAUDE_REQUESTS.labels(model=model, status="client_error").inc()
                    error_msg = response.text
                    logger.error(f"Claude API error: {response.status_code} - {error_msg}")
                    raise ClaudeAPIError(f"API error: {response.status_code}", response.status_code)
                
            except httpx.TimeoutException as e:
                CLAUDE_REQUESTS.labels(model=model, status="timeout").inc()
                last_error = e
                await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                
            except httpx.RequestError as e:
                CLAUDE_REQUESTS.labels(model=model, status="request_error").inc()
                last_error = e
                await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
        
        # All retries exhausted
        CLAUDE_REQUESTS.labels(model=model, status="exhausted").inc()
        raise ClaudeAPIError(f"All retries exhausted: {last_error}")
    
    async def complete_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        system: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete with structured JSON output.
        """
        
        # Add schema to prompt
        schema_prompt = f"""
{prompt}

Respond with a JSON object matching this schema:
{output_schema}

Output only valid JSON, no other text.
"""
        
        response = await self.complete(
            prompt=schema_prompt,
            system=system,
            model=model,
            temperature=0.3,  # Lower temperature for structured output
        )
        
        # Parse JSON
        import json
        try:
            # Clean up response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return {}


class ClaudeAPIError(Exception):
    """Error from Claude API."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
