# =============================================================================
# ADAM LLM Integration Package
# =============================================================================

"""
LLM INTEGRATION

Claude API integration for psychological reasoning.

Components:
- Claude client with retry and circuit breaking
- Prompt templates for psychological constructs
- Structured output parsing
- Token management and cost tracking
"""

from adam.llm.client import ClaudeClient, ClaudeConfig
from adam.llm.prompts import (
    PromptTemplate,
    PsychologicalPromptBuilder,
)
from adam.llm.fusion import ClaudeFusionEngine
from adam.llm.service import LLMService

__all__ = [
    "ClaudeClient",
    "ClaudeConfig",
    "PromptTemplate",
    "PsychologicalPromptBuilder",
    "ClaudeFusionEngine",
    "LLMService",
]
