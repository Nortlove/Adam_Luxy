# ADAM: Claude Code + Cursor Implementation Guide
## Practical Patterns for Effective Implementation

**Purpose**: Maximize productivity when implementing ADAM in Claude Code via Cursor  
**Version**: 1.0  
**Date**: January 20, 2026

---

# PART 1: UNDERSTANDING CLAUDE CODE'S CONSTRAINTS

## 1.1 Context Window Management

Claude Code has a context limit. You cannot load 1.5MB of specs at once. Work strategically:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ CONTEXT BUDGET STRATEGY                                                         │
│                                                                                 │
│ TYPICAL SESSION BUDGET: ~200KB usable context                                   │
│                                                                                 │
│ ALLOCATION:                                                                     │
│ ├── Master Package (reference sections): ~10KB                                  │
│ ├── Primary spec for this session: ~80-150KB                                   │
│ ├── Code patterns reference: ~30-50KB                                          │
│ └── Working code/conversation: ~50KB                                           │
│                                                                                 │
│ RULE: Load specs in SECTIONS, not whole files                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 What Claude Code Does Well

- **File creation and editing**: Excellent at creating well-structured Python files
- **Following specifications**: Give it a spec, it implements accurately
- **Refactoring**: Can restructure code while maintaining functionality
- **Test generation**: Generates comprehensive tests from implementations
- **Pattern replication**: Show it one example, it replicates the pattern

## 1.3 What Requires Human Guidance

- **Architectural decisions**: You need to guide overall structure
- **Cross-file dependencies**: Explicitly state what exists where
- **Integration testing**: You'll need to run and verify
- **Performance tuning**: Measure, then guide optimization
- **Business logic validation**: Verify psychological mechanisms are correct

---

# PART 2: CURSOR-SPECIFIC SETUP

## 2.1 Recommended Cursor Settings

```json
// .cursor/settings.json
{
  "editor.formatOnSave": true,
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/node_modules": true,
    "**/.git": true
  }
}
```

## 2.2 Project Structure for Cursor

Create this structure BEFORE starting implementation:

```
adam-platform/
├── .cursor/
│   └── settings.json
├── docs/                          # Put your specs here
│   ├── master/
│   │   ├── ADAM_MASTER_IMPLEMENTATION_PACKAGE.md
│   │   ├── ADAM_DOCUMENT_INDEX.md
│   │   └── ADAM_SESSION_TEMPLATES.md
│   ├── specs/                     # Enhancement specs
│   │   ├── enhancement_02_blackboard.md
│   │   ├── enhancement_06_gradient_bridge.md
│   │   └── ... (copy relevant specs as needed)
│   └── platform/                  # Platform specs
│       ├── iheart_integration.md
│       ├── amazon_pipeline.md
│       └── wpp_alignment.md
├── adam/                          # Implementation code
│   ├── __init__.py
│   ├── core/
│   ├── user/
│   ├── output/
│   ├── platform/
│   ├── learning/
│   ├── data/
│   └── infrastructure/
├── tests/
├── scripts/
├── pyproject.toml
└── README.md
```

## 2.3 Initial pyproject.toml

```toml
[project]
name = "adam-platform"
version = "0.1.0"
description = "ADAM Psychological Intelligence Platform"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "neo4j>=5.0",
    "redis>=4.5",
    "kafka-python>=2.0",
    "numpy>=1.24",
    "scipy>=1.10",
    "scikit-learn>=1.3",
    "httpx>=0.24",
    "structlog>=23.1",
    "prometheus-client>=0.17",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.1",
    "black>=23.7",
    "ruff>=0.0.280",
    "mypy>=1.4",
]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = true
```

---

# PART 3: SESSION WORKFLOW PATTERNS

## 3.1 The Optimal Session Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ OPTIMAL CLAUDE CODE SESSION FLOW                                                │
│                                                                                 │
│ PHASE 1: SETUP (5 minutes)                                                      │
│ ──────────────────────────────                                                  │
│ 1. Open Cursor with adam-platform/ as root                                     │
│ 2. Open the relevant spec file in docs/                                        │
│ 3. Open Claude Code panel                                                      │
│ 4. Start with context-setting message (see templates below)                    │
│                                                                                 │
│ PHASE 2: MODELS FIRST (20 minutes)                                             │
│ ──────────────────────────────                                                  │
│ 1. Ask Claude to create Pydantic models                                        │
│ 2. Review and refine                                                           │
│ 3. Create models.py file                                                       │
│                                                                                 │
│ PHASE 3: SERVICE IMPLEMENTATION (30 minutes)                                   │
│ ──────────────────────────────                                                  │
│ 1. Ask Claude to implement core service                                        │
│ 2. Implement in chunks (not all at once)                                       │
│ 3. Review each chunk before proceeding                                         │
│                                                                                 │
│ PHASE 4: INTEGRATION POINTS (15 minutes)                                       │
│ ──────────────────────────────                                                  │
│ 1. Implement connections to other components                                   │
│ 2. Verify imports work                                                         │
│ 3. Add any missing dependencies                                                │
│                                                                                 │
│ PHASE 5: TESTS (20 minutes)                                                    │
│ ──────────────────────────────                                                  │
│ 1. Ask Claude to generate unit tests                                           │
│ 2. Run tests, fix failures                                                     │
│ 3. Add integration tests if time                                               │
│                                                                                 │
│ PHASE 6: VERIFICATION (10 minutes)                                             │
│ ──────────────────────────────                                                  │
│ 1. Run all tests                                                               │
│ 2. Check imports resolve                                                       │
│ 3. Update session checklist                                                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Context-Setting Messages

### Starting a New Component

```
I'm implementing ADAM's [Component Name] based on Enhancement #[XX].

PROJECT STRUCTURE:
- Root: adam-platform/
- Target: adam/[category]/[component]/
- Specs in: docs/specs/

WHAT EXISTS:
- [List implemented dependencies]
- [List available imports]

WHAT I NEED:
1. Pydantic models in models.py
2. Core service in service.py
3. [Any additional files per spec]

SPEC HIGHLIGHTS:
[Paste the most critical 500-1000 words from the spec]

Let's start with the models.
```

### Continuing a Session

```
Continuing ADAM [Component Name] implementation.

COMPLETED:
- models.py (User profile, mechanisms)
- service.py (core logic)

REMAINING:
- Neo4j queries
- API endpoints
- Tests

CURRENT FILE: adam/[path]/[file].py

Let's implement the Neo4j integration.
```

### Debugging

```
I'm debugging ADAM [Component Name].

ERROR:
[Paste exact error message]

CONTEXT:
- File: adam/[path]/[file].py
- Function: [function_name]
- Line: [line number]

RELATED CODE:
[Paste relevant code snippet]

What's causing this and how do I fix it?
```

## 3.3 Effective Prompting Patterns

### Pattern 1: Spec-to-Code

```
Based on this spec section:

"""
[Paste relevant spec section, 500-1500 words]
"""

Implement the [ClassName] class in Python with:
- Full type hints
- Docstrings
- Pydantic models where appropriate
- Async methods where I/O is involved
```

### Pattern 2: Example-Driven

```
Here's how we implemented the Blackboard zone:

"""python
[Paste example code, ~50-100 lines]
"""

Now implement the [NewComponent] following the same patterns:
- Same error handling style
- Same logging approach
- Same async patterns
```

### Pattern 3: Incremental Building

```
I have this base class:

"""python
[Paste base class]
"""

Add these methods:
1. [method_name]: [brief description]
2. [method_name]: [brief description]

Don't rewrite the whole class, just add the new methods.
```

### Pattern 4: Integration Request

```
I need to connect [Component A] to [Component B].

Component A exposes:
- [method/interface]

Component B needs:
- [what it consumes]

Show me the integration code and any adapter needed.
```

---

# PART 4: FILE-BY-FILE IMPLEMENTATION

## 4.1 Recommended Order Within Each Component

```
ORDER OF IMPLEMENTATION:

1. models.py          # Data structures first
   └── Pydantic models, enums, type definitions

2. exceptions.py      # Custom exceptions (if needed)
   └── Component-specific error types

3. service.py         # Core business logic
   └── Main service class with primary methods

4. storage.py         # Data persistence (if needed)
   └── Neo4j queries, Redis operations

5. api.py             # FastAPI endpoints (if needed)
   └── HTTP interface

6. __init__.py        # Exports
   └── Public interface definition

7. tests/test_*.py    # Tests last
   └── Unit and integration tests
```

## 4.2 File Templates to Request

### Request Models File

```
Create adam/[category]/[component]/models.py with:

1. All enums from the spec
2. All Pydantic models from the spec
3. Full type hints
4. Field validators where needed
5. model_config for JSON serialization

Use these imports:
- from pydantic import BaseModel, Field, field_validator
- from enum import Enum
- from typing import Dict, List, Optional, Any
- from datetime import datetime
```

### Request Service File

```
Create adam/[category]/[component]/service.py with:

1. Main [ComponentName]Service class
2. Constructor with dependency injection
3. All methods from the spec
4. Async methods for I/O operations
5. Structured logging with structlog
6. Prometheus metrics hooks

Dependencies to inject:
- [list dependencies from other components]
```

### Request Test File

```
Create tests/[category]/test_[component].py with:

1. Pytest fixtures for service setup
2. Unit tests for each public method
3. Edge case tests
4. Mock external dependencies
5. Use pytest-asyncio for async tests

Test these scenarios:
- [list key scenarios from spec]
```

---

# PART 5: MANAGING DEPENDENCIES BETWEEN COMPONENTS

## 5.1 Import Strategy

Create a clear import hierarchy:

```python
# adam/__init__.py - Top-level exports

from adam.core.blackboard import BlackboardService
from adam.core.gradient_bridge import GradientBridgeService
# ... etc

__all__ = [
    "BlackboardService",
    "GradientBridgeService",
    # ... etc
]
```

```python
# adam/core/__init__.py - Category exports

from adam.core.blackboard.service import BlackboardService
from adam.core.gradient_bridge.service import GradientBridgeService

__all__ = ["BlackboardService", "GradientBridgeService"]
```

## 5.2 Dependency Injection Pattern

Use this pattern consistently:

```python
# adam/core/gradient_bridge/service.py

from typing import Protocol

class BlackboardProtocol(Protocol):
    """Protocol for Blackboard dependency."""
    async def read_zone(self, request_id: str, zone: str) -> dict: ...
    async def write_zone(self, request_id: str, zone: str, data: dict) -> None: ...


class GradientBridgeService:
    """Gradient Bridge with injected dependencies."""
    
    def __init__(
        self,
        blackboard: BlackboardProtocol,
        neo4j_driver: AsyncDriver,
        redis_client: Redis,
    ):
        self._blackboard = blackboard
        self._neo4j = neo4j_driver
        self._redis = redis_client
```

## 5.3 Telling Claude About Dependencies

When implementing a component, always state what's available:

```
AVAILABLE IMPORTS (already implemented):

from adam.core.blackboard import BlackboardService
# Methods: read_zone(), write_zone(), subscribe()

from adam.core.gradient_bridge import GradientBridgeService  
# Methods: route_signal(), inject_priors()

from adam.infrastructure.neo4j import get_driver
from adam.infrastructure.redis import get_redis_client

Use these in your implementation. Don't recreate them.
```

---

# PART 6: TESTING STRATEGIES

## 6.1 Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── core/
│   │   ├── test_blackboard.py
│   │   └── test_gradient_bridge.py
│   ├── user/
│   │   └── test_cold_start.py
│   └── ...
├── integration/
│   ├── test_blackboard_gradient.py
│   └── test_full_pipeline.py
└── e2e/
    ├── test_iheart_flow.py
    └── test_wpp_flow.py
```

## 6.2 Fixture Pattern

```python
# tests/conftest.py

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for unit tests."""
    driver = MagicMock()
    driver.session = MagicMock(return_value=AsyncMock())
    return driver

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for unit tests."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    return client

@pytest.fixture
def mock_blackboard(mock_redis_client):
    """Mock Blackboard service."""
    from adam.core.blackboard import BlackboardService
    return BlackboardService(redis_client=mock_redis_client)
```

## 6.3 Asking Claude for Tests

```
Generate pytest tests for adam/core/[component]/service.py

Requirements:
1. Use pytest-asyncio for async tests
2. Mock all external dependencies (Neo4j, Redis, other services)
3. Test happy path for each method
4. Test error cases (invalid input, connection failures)
5. Test edge cases from the spec

Use fixtures from conftest.py:
- mock_neo4j_driver
- mock_redis_client
- mock_blackboard
```

---

# PART 7: COMMON PITFALLS & SOLUTIONS

## 7.1 Context Overflow

**Problem**: Claude loses track of earlier conversation

**Solution**: 
```
Let me reset context. Here's where we are:

IMPLEMENTED:
- adam/core/blackboard/models.py ✓
- adam/core/blackboard/service.py ✓

CURRENT FILE: adam/core/blackboard/storage.py
CURRENT TASK: Implement Redis storage backend

[Paste current file content if partially done]

Continue from here.
```

## 7.2 Inconsistent Patterns

**Problem**: Different components use different patterns

**Solution**: Create a patterns document and reference it:
```
Follow these ADAM patterns (from our patterns doc):

LOGGING:
```python
import structlog
logger = structlog.get_logger(__name__)
```

ERROR HANDLING:
```python
from adam.exceptions import ADAMError
raise ADAMError(f"Context: {details}")
```

ASYNC:
```python
async def method(self) -> Result:
    async with self._lock:
        ...
```
```

## 7.3 Missing Imports

**Problem**: Generated code has missing imports

**Solution**: Always specify imports explicitly:
```
Use these exact imports:

```python
from typing import Dict, List, Optional, Any, Protocol
from datetime import datetime
from pydantic import BaseModel, Field
from adam.core.blackboard import BlackboardService
from adam.infrastructure.neo4j import get_driver
```

Do not use any imports not listed above without asking.
```

## 7.4 Over-Engineering

**Problem**: Claude generates overly complex solutions

**Solution**: Be explicit about simplicity:
```
Implement the SIMPLEST solution that:
1. Meets the spec requirements
2. Has proper error handling
3. Is testable

Do NOT add:
- Extra abstraction layers
- Unused configuration options
- "Future-proofing" code

We can refactor later if needed.
```

## 7.5 Hallucinated Dependencies

**Problem**: Claude assumes libraries or methods exist that don't

**Solution**: 
```
AVAILABLE LIBRARIES (from pyproject.toml):
- pydantic>=2.0
- fastapi>=0.100
- neo4j>=5.0
- redis>=4.5

AVAILABLE ADAM MODULES (already implemented):
- adam.core.blackboard
- adam.infrastructure.neo4j

Do NOT use any other libraries or assume any other adam modules exist.
```

---

# PART 8: PRODUCTIVITY TIPS

## 8.1 Cursor Shortcuts

| Action | Shortcut | Use For |
|--------|----------|---------|
| Open Claude Code | Cmd+L (Mac) / Ctrl+L | Start conversation |
| Add file to context | Cmd+Shift+L | Include file in chat |
| Accept suggestion | Tab | Apply Claude's code |
| Reject suggestion | Esc | Skip suggestion |
| Inline edit | Cmd+K | Quick edits in file |

## 8.2 Batch File Creation

Instead of creating files one at a time:

```
Create the complete directory structure for adam/core/gradient_bridge/:

1. __init__.py - exports GradientBridgeService
2. models.py - all Pydantic models from spec
3. service.py - main service class
4. routing.py - signal routing logic
5. handlers/__init__.py - handler exports
6. handlers/base.py - BaseSignalHandler
7. handlers/outcome.py - OutcomeHandler

Generate all files with proper imports and docstrings.
For service.py, include method stubs with docstrings but not full implementation yet.
```

## 8.3 Review Checkpoints

Build in review points:

```
CHECKPOINT: Review models before continuing

I've generated the models. Before implementing the service:

1. Do these models match the spec?
2. Are the field types correct?
3. Any missing validators?

Reply "proceed" to continue or tell me what to fix.
```

## 8.4 Session Handoff

When ending a session:

```
SESSION SUMMARY for next time:

COMPLETED:
- adam/core/gradient_bridge/models.py ✓
- adam/core/gradient_bridge/service.py ✓ (partial - 3 of 7 methods)

NEXT SESSION:
1. Complete service.py methods: route_signal(), inject_priors(), process_outcome()
2. Implement handlers/
3. Write tests

OPEN QUESTIONS:
- [Any unresolved decisions]

NOTES:
- [Any gotchas discovered]
```

---

# PART 9: ADAM-SPECIFIC GUIDANCE

## 9.1 Psychological Constructs Are First-Class

Always model psychological constructs explicitly:

```python
# CORRECT - Mechanism as entity
class CognitiveMechanism(BaseModel):
    mechanism_id: str
    mechanism_type: MechanismType
    effectiveness_score: float
    confidence: float
    
# WRONG - Mechanism as attribute
class Decision(BaseModel):
    mechanism: str  # Just a string label
```

## 9.2 Learning Signals Everywhere

Every component should emit learning signals:

```python
# CORRECT - Emits learning signal
async def make_decision(self, request: AdRequest) -> AdDecision:
    decision = await self._compute_decision(request)
    
    # Emit learning signal
    await self._gradient_bridge.emit_signal(
        signal_type=SignalType.DECISION_MADE,
        payload={
            "user_id": request.user_id,
            "mechanisms_used": decision.mechanisms,
            "confidence": decision.confidence,
        }
    )
    
    return decision

# WRONG - No learning signal
async def make_decision(self, request: AdRequest) -> AdDecision:
    return await self._compute_decision(request)  # Lost learning opportunity
```

## 9.3 Latency Budget Tracking

For production paths, track latency:

```python
# CORRECT - Latency tracked
async def serve_ad(self, request: AdRequest) -> AdResponse:
    start = time.monotonic()
    
    decision = await self._make_decision(request)
    
    elapsed_ms = (time.monotonic() - start) * 1000
    self._metrics.observe_latency("ad_decision", elapsed_ms)
    
    if elapsed_ms > 100:
        logger.warning("latency_exceeded", elapsed_ms=elapsed_ms)
    
    return decision
```

## 9.4 Cross-Platform Awareness

Always consider both iHeart and WPP:

```python
# CORRECT - Platform-aware
class UserProfileService:
    async def get_profile(self, user_id: str, platform: Platform) -> UserProfile:
        # Check platform-specific cache first
        cached = await self._cache.get(f"{platform.value}:{user_id}")
        if cached:
            return cached
        
        # Fall back to unified profile
        return await self._get_unified_profile(user_id)

# WRONG - Single platform assumption
class UserProfileService:
    async def get_profile(self, user_id: str) -> UserProfile:
        # Assumes single platform
        return await self._cache.get(user_id)
```

---

# PART 10: QUICK REFERENCE CARD

## Session Checklist

```
□ Spec file loaded in docs/
□ Context-setting message sent
□ Dependencies verified
□ Models implemented
□ Service implemented
□ Integration points connected
□ Tests written
□ Tests passing
□ Session summary created
```

## Effective Prompts

| Need | Prompt Start |
|------|--------------|
| New file | "Create adam/[path]/[file].py with..." |
| Add method | "Add this method to [ClassName]..." |
| Fix bug | "This error occurs: [error]. Fix it." |
| Generate tests | "Generate pytest tests for..." |
| Explain code | "Explain what this does: [code]" |
| Refactor | "Refactor this to [goal]: [code]" |

## Don't Forget

1. **Models first** - Always implement Pydantic models before services
2. **State dependencies** - Tell Claude what exists
3. **Learning signals** - Every component should emit them
4. **Latency budget** - Track in production paths
5. **Platform awareness** - Consider iHeart + WPP
6. **Test as you go** - Don't leave tests for the end

---

**END OF CLAUDE CODE + CURSOR GUIDE**
