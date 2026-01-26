# ADAM Enhancement #26: Observability & Debugging
## Complete Enterprise Implementation Specification

**Document Purpose**: Comprehensive observability and debugging infrastructure for ADAM's psychological intelligence system, enabling full-stack tracing from raw signals through psychological inference to persuasion outcomes.

**Date**: January 2026  
**Version**: 2.0 (Complete Rebuild)  
**Status**: Production Ready  
**Estimated Effort**: 12-14 person-weeks

---

## Executive Summary

ADAM's competitive advantage lies in its ability to transform behavioral signals into psychological intelligence for hyper-personalized persuasion. However, this multi-layered reasoning—spanning graph queries, personality inference, cognitive mechanism selection, Atom of Thought decomposition, and real-time optimization—creates unprecedented debugging complexity.

This specification establishes ADAM's **Psychological Intelligence Observability Platform (PIOP)**, providing:

1. **Psychological Construct Tracing** - Track Big Five, regulatory focus, moral foundations, construal level through the reasoning pipeline
2. **Atom of Thought DAG Visualization** - Observe and debug the dependency-aware reasoning decomposition
3. **Cross-Component Learning Signal Debugging** - Trace how learning signals flow through the Gradient Bridge
4. **Blackboard State Observability** - Monitor shared state changes and cross-component communication
5. **Cognitive Mechanism Attribution** - Understand which persuasion mechanisms drove outcomes
6. **Causal Chain Visualization** - End-to-end tracing from signal → inference → mechanism → outcome
7. **Contextual Bandit Exploration Debugging** - Observe Thompson Sampling decisions and arm selection
8. **Real-Time Signal Debugging** - Debug supraliminal signal aggregation and timing
9. **Personality Inference Path Tracing** - Trace exactly how personality was inferred
10. **Decision Replay with Counterfactual Analysis** - "What if" debugging for optimization

### Strategic Differentiator

| Platform | Decision Transparency | Psychological Tracing | Mechanism Attribution |
|----------|----------------------|----------------------|----------------------|
| Google Ads | Black box | None | None |
| Meta Ads | Limited insights | None | None |
| Amazon DSP | Attribution only | None | None |
| Spotify Ad Studio | Basic targeting | None | None |
| **ADAM PIOP** | Full transparency | Complete | Real-time |

---

## Part 1: Core Architecture

### 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADAM PSYCHOLOGICAL INTELLIGENCE                          │
│                      OBSERVABILITY PLATFORM (PIOP)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  Psychological  │  │    Atom of      │  │   Gradient      │            │
│  │    Construct    │──│    Thought      │──│    Bridge       │            │
│  │     Tracer      │  │   DAG Tracer    │  │    Tracer       │            │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘            │
│           │                    │                    │                      │
│           └────────────────────┼────────────────────┘                      │
│                                │                                           │
│                    ┌───────────┴───────────┐                              │
│                    │     Unified Trace     │                              │
│                    │        Store          │                              │
│                    └───────────┬───────────┘                              │
│                                │                                           │
│           ┌────────────────────┼────────────────────┐                     │
│           │                    │                    │                      │
│  ┌────────┴────────┐  ┌───────┴───────┐  ┌────────┴────────┐            │
│  │    Causal       │  │  Blackboard   │  │  Psychological  │            │
│  │    Chain        │  │    State      │  │     Replay      │            │
│  │   Builder       │  │   Observer    │  │     Engine      │            │
│  └─────────────────┘  └───────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         API LAYER                                    │  │
│  │  /trace  /dag  /causal  /replay  /analytics  /stream  /export       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                 │
│  │   LangSmith   │  │   LangFuse    │  │  Prometheus   │                 │
│  │  Integration  │  │  Integration  │  │   Metrics     │                 │
│  └───────────────┘  └───────────────┘  └───────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
Raw Signals                 Psychological               Mechanism              Decision
(Text, Audio,    ────────►  Inference        ────────►  Selection   ────────►  & Outcome
 Behavior)                  (Big Five, etc.)            (Social Proof, etc.)
     │                           │                           │                    │
     ▼                           ▼                           ▼                    ▼
┌─────────┐               ┌─────────┐               ┌─────────┐            ┌─────────┐
│ Signal  │               │Inference│               │Mechanism│            │ Decision│
│  Trace  │──────────────►│  Trace  │──────────────►│  Trace  │───────────►│  Trace  │
└─────────┘               └─────────┘               └─────────┘            └─────────┘
     │                           │                           │                    │
     └───────────────────────────┴───────────────────────────┴────────────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │   Causal Chain        │
                              │   (Full Provenance)   │
                              └───────────────────────┘
```

---

## Part 2: Psychological Construct Tracing

### 2.1 Core Data Models

```python
"""
Psychological construct tracing for ADAM.
Tracks the complete lifecycle of psychological inference.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import json


class PsychologicalDomain(Enum):
    """Domains of psychological constructs ADAM tracks."""
    PERSONALITY = "personality"
    REGULATORY = "regulatory"
    MORAL = "moral"
    CONSTRUAL = "construal"
    TEMPORAL = "temporal"
    SOCIAL = "social"
    COGNITIVE = "cognitive"
    EMOTIONAL = "emotional"
    MOTIVATIONAL = "motivational"


class PersonalityTrait(Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class InferenceSource(Enum):
    """Sources of psychological inference."""
    TEXT_EMBEDDING = "text_embedding"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    AUDIO_PROSODY = "audio_prosody"
    VISUAL_ANALYSIS = "visual_analysis"
    GRAPH_RELATIONSHIP = "graph_relationship"
    EXPLICIT_PREFERENCE = "explicit_preference"
    TEMPORAL_PATTERN = "temporal_pattern"
    CROSS_MODAL_FUSION = "cross_modal_fusion"
    COLD_START_PRIOR = "cold_start_prior"


@dataclass
class PsychologicalSignal:
    """Raw signal that contributes to psychological inference."""
    signal_id: str
    signal_type: str
    source: InferenceSource
    timestamp: datetime
    raw_value: Any
    processed_value: Optional[Any] = None
    embedding_vector: Optional[List[float]] = None
    confidence: float = 0.0
    data_source: str = ""
    data_id: Optional[str] = None
    model_used: Optional[str] = None
    model_version: Optional[str] = None
    processing_latency_ms: float = 0.0


@dataclass
class ConstructInference:
    """Single inference step for a psychological construct."""
    inference_id: str
    domain: PsychologicalDomain
    construct_name: str
    input_signals: List[str]
    inferred_value: float
    confidence: float
    uncertainty: float
    inference_method: str
    model_name: str
    model_version: str
    user_id_hash: str
    session_id: str
    timestamp: datetime
    prior_value: Optional[float] = None
    prior_confidence: Optional[float] = None
    posterior_value: Optional[float] = None
    feature_importances: Dict[str, float] = field(default_factory=dict)
    shap_values: Optional[Dict[str, float]] = None


@dataclass
class MechanismActivation:
    """Activation of a cognitive/persuasion mechanism."""
    activation_id: str
    mechanism_name: str
    triggering_constructs: Dict[str, float] = field(default_factory=dict)
    construct_weights: Dict[str, float] = field(default_factory=dict)
    activation_strength: float = 0.0
    predicted_impact: float = 0.0
    confidence: float = 0.0
    user_profile_id: str = ""
    content_context: Dict[str, Any] = field(default_factory=dict)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    actual_impact: Optional[float] = None
    outcome_observed: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PsychologicalTraceCollector:
    """
    Collect and store psychological reasoning traces.
    """
    
    def __init__(
        self,
        neo4j_client,
        redis_client,
        trace_storage,
        sampling_rate: float = 1.0
    ):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.storage = trace_storage
        self.sampling_rate = sampling_rate
        self._active_traces: Dict[str, Dict] = {}
        self.construct_definitions = self._load_construct_definitions()
    
    def _load_construct_definitions(self) -> Dict:
        """Load psychological construct definitions with effect sizes."""
        return {
            "personality": {
                "traits": ["openness", "conscientiousness", "extraversion", 
                          "agreeableness", "neuroticism"],
                "effect_sizes": {
                    "text_embedding": 0.38,
                    "behavioral_pattern": 0.32,
                    "cross_modal": 0.43
                }
            },
            "regulatory_focus": {
                "orientations": ["promotion", "prevention"],
                "effect_sizes": {
                    "linguistic_markers": 0.41,
                    "behavioral_patterns": 0.35
                }
            },
            "moral_foundations": {
                "foundations": ["care", "fairness", "loyalty", "authority", 
                               "sanctity", "liberty"],
                "effect_sizes": {
                    "text_analysis": 0.36,
                    "behavioral_inference": 0.28
                }
            },
            "construal_level": {
                "levels": ["concrete", "abstract"],
                "effect_sizes": {
                    "linguistic_markers": 0.29,
                    "temporal_distance": 0.34
                }
            }
        }
    
    def record_signal(
        self,
        trace_id: str,
        signal_type: str,
        source: InferenceSource,
        raw_value: Any,
        data_source: str,
        data_id: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        model_used: Optional[str] = None,
        model_version: Optional[str] = None,
        confidence: float = 1.0
    ) -> str:
        """Record a psychological signal."""
        
        signal_id = str(uuid.uuid4())
        
        signal = PsychologicalSignal(
            signal_id=signal_id,
            signal_type=signal_type,
            source=source,
            timestamp=datetime.utcnow(),
            raw_value=self._sanitize_value(raw_value),
            embedding_vector=embedding[:50] if embedding else None,
            data_source=data_source,
            data_id=data_id,
            model_used=model_used,
            model_version=model_version,
            confidence=confidence
        )
        
        if trace_id in self._active_traces:
            self._active_traces[trace_id].setdefault("signals", []).append(signal)
        
        cache_key = f"psych_signal:{trace_id}:{signal_id}"
        self.redis.setex(cache_key, 86400, json.dumps(self._serialize_signal(signal)))
        
        return signal_id
    
    def record_inference(
        self,
        trace_id: str,
        domain: PsychologicalDomain,
        construct_name: str,
        input_signal_ids: List[str],
        inferred_value: float,
        confidence: float,
        inference_method: str,
        model_name: str,
        model_version: str,
        user_id_hash: str,
        session_id: str,
        prior_value: Optional[float] = None,
        prior_confidence: Optional[float] = None,
        feature_importances: Optional[Dict[str, float]] = None
    ) -> str:
        """Record a psychological construct inference."""
        
        inference_id = str(uuid.uuid4())
        
        posterior_value = None
        if prior_value is not None:
            posterior_value = self._bayesian_update(
                prior_value, prior_confidence or 0.5,
                inferred_value, confidence
            )
        
        inference = ConstructInference(
            inference_id=inference_id,
            domain=domain,
            construct_name=construct_name,
            input_signals=input_signal_ids,
            inferred_value=inferred_value,
            confidence=confidence,
            uncertainty=1.0 - confidence,
            inference_method=inference_method,
            model_name=model_name,
            model_version=model_version,
            user_id_hash=user_id_hash,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            prior_value=prior_value,
            prior_confidence=prior_confidence,
            posterior_value=posterior_value,
            feature_importances=feature_importances or {}
        )
        
        if trace_id in self._active_traces:
            self._active_traces[trace_id].setdefault("inferences", []).append(inference)
        
        self._store_inference(inference)
        
        return inference_id
    
    def record_mechanism_activation(
        self,
        trace_id: str,
        mechanism_name: str,
        triggering_constructs: Dict[str, float],
        activation_strength: float,
        predicted_impact: float,
        confidence: float,
        user_profile_id: str,
        content_context: Dict[str, Any]
    ) -> str:
        """Record activation of a persuasion mechanism."""
        
        activation_id = str(uuid.uuid4())
        
        construct_weights = self._calculate_mechanism_weights(
            mechanism_name, triggering_constructs
        )
        
        activation = MechanismActivation(
            activation_id=activation_id,
            mechanism_name=mechanism_name,
            triggering_constructs=triggering_constructs,
            construct_weights=construct_weights,
            activation_strength=activation_strength,
            predicted_impact=predicted_impact,
            confidence=confidence,
            user_profile_id=user_profile_id,
            content_context=content_context,
            timestamp=datetime.utcnow()
        )
        
        if trace_id in self._active_traces:
            self._active_traces[trace_id].setdefault("mechanism_activations", []).append(activation)
        
        self._store_mechanism_activation(activation)
        
        return activation_id
    
    def record_outcome(
        self,
        trace_id: str,
        activation_id: str,
        actual_impact: float,
        outcome_type: str,
        outcome_value: Any
    ):
        """Record actual outcome for a mechanism activation."""
        
        if trace_id in self._active_traces:
            for activation in self._active_traces[trace_id].get("mechanism_activations", []):
                if activation.activation_id == activation_id:
                    activation.actual_impact = actual_impact
                    activation.outcome_observed = True
        
        query = """
        MATCH (ma:MechanismActivation {activation_id: $activation_id})
        SET ma.actual_impact = $actual_impact,
            ma.outcome_observed = true,
            ma.outcome_type = $outcome_type,
            ma.outcome_value = $outcome_value,
            ma.outcome_recorded_at = datetime()
        RETURN ma.activation_id
        """
        
        self.neo4j.run(query, {
            "activation_id": activation_id,
            "actual_impact": actual_impact,
            "outcome_type": outcome_type,
            "outcome_value": str(outcome_value)[:500]
        })
    
    def _bayesian_update(
        self,
        prior_mean: float,
        prior_confidence: float,
        observation: float,
        observation_confidence: float
    ) -> float:
        """Bayesian update of belief given observation."""
        prior_precision = prior_confidence / (1 - prior_confidence + 1e-6)
        obs_precision = observation_confidence / (1 - observation_confidence + 1e-6)
        
        posterior_precision = prior_precision + obs_precision
        posterior_mean = (
            prior_precision * prior_mean + obs_precision * observation
        ) / posterior_precision
        
        return max(0.0, min(1.0, posterior_mean))
    
    def _calculate_mechanism_weights(
        self,
        mechanism_name: str,
        constructs: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate how much each construct contributes to mechanism."""
        
        mechanism_construct_affinities = {
            "social_proof": {
                "extraversion": 0.3, "agreeableness": 0.4, "neuroticism": 0.2
            },
            "scarcity": {
                "neuroticism": 0.3, "promotion_focus": 0.3, "construal_concrete": 0.3
            },
            "authority": {
                "conscientiousness": 0.3, "agreeableness": 0.3, "authority_foundation": 0.4
            },
            "reciprocity": {
                "agreeableness": 0.4, "fairness_foundation": 0.4, "care_foundation": 0.2
            },
            "commitment": {
                "conscientiousness": 0.5, "prevention_focus": 0.3, "loyalty_foundation": 0.2
            },
            "liking": {
                "extraversion": 0.3, "agreeableness": 0.4, "care_foundation": 0.3
            }
        }
        
        affinities = mechanism_construct_affinities.get(mechanism_name, {})
        weights = {}
        
        for construct, affinity in affinities.items():
            if construct in constructs:
                weights[construct] = affinity * constructs[construct]
        
        total = sum(weights.values()) + 1e-6
        return {k: v / total for k, v in weights.items()}
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize value for storage."""
        if isinstance(value, (str, int, float, bool, type(None))):
            if isinstance(value, str):
                return value[:1000]
            return value
        elif isinstance(value, (list, tuple)):
            return [self._sanitize_value(v) for v in value[:100]]
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in list(value.items())[:50]}
        else:
            return str(value)[:500]
    
    def _serialize_signal(self, signal: PsychologicalSignal) -> Dict:
        """Serialize signal for storage."""
        return {
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "source": signal.source.value,
            "timestamp": signal.timestamp.isoformat(),
            "raw_value": signal.raw_value,
            "data_source": signal.data_source,
            "data_id": signal.data_id,
            "model_used": signal.model_used,
            "model_version": signal.model_version,
            "confidence": signal.confidence
        }
    
    def _store_inference(self, inference: ConstructInference):
        """Store inference in Neo4j graph."""
        
        query = """
        CREATE (ci:ConstructInference {
            inference_id: $inference_id,
            domain: $domain,
            construct_name: $construct_name,
            inferred_value: $inferred_value,
            confidence: $confidence,
            inference_method: $inference_method,
            model_name: $model_name,
            model_version: $model_version,
            user_id_hash: $user_id_hash,
            timestamp: datetime($timestamp),
            prior_value: $prior_value,
            posterior_value: $posterior_value
        })
        RETURN ci.inference_id
        """
        
        self.neo4j.run(query, {
            "inference_id": inference.inference_id,
            "domain": inference.domain.value,
            "construct_name": inference.construct_name,
            "inferred_value": inference.inferred_value,
            "confidence": inference.confidence,
            "inference_method": inference.inference_method,
            "model_name": inference.model_name,
            "model_version": inference.model_version,
            "user_id_hash": inference.user_id_hash,
            "timestamp": inference.timestamp.isoformat(),
            "prior_value": inference.prior_value,
            "posterior_value": inference.posterior_value
        })
    
    def _store_mechanism_activation(self, activation: MechanismActivation):
        """Store mechanism activation in Neo4j graph."""
        
        query = """
        CREATE (ma:MechanismActivation {
            activation_id: $activation_id,
            mechanism_name: $mechanism_name,
            activation_strength: $activation_strength,
            predicted_impact: $predicted_impact,
            confidence: $confidence,
            timestamp: datetime($timestamp),
            outcome_observed: false
        })
        RETURN ma.activation_id
        """
        
        self.neo4j.run(query, {
            "activation_id": activation.activation_id,
            "mechanism_name": activation.mechanism_name,
            "activation_strength": activation.activation_strength,
            "predicted_impact": activation.predicted_impact,
            "confidence": activation.confidence,
            "timestamp": activation.timestamp.isoformat()
        })
```

---

## Part 3: Atom of Thought DAG Visualization

### 3.1 DAG Trace Infrastructure

```python
"""
Atom of Thought DAG Visualization and Debugging.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import uuid


class AtomStatus(Enum):
    """Status of an atom in the DAG."""
    PENDING = "pending"
    WAITING_DEPENDENCIES = "waiting_dependencies"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOMPUTING = "recomputing"


class AtomType(Enum):
    """Types of atoms in ADAM's psychological reasoning."""
    SIGNAL_EXTRACTION = "signal_extraction"
    PERSONALITY_INFERENCE = "personality_inference"
    STATE_DETECTION = "state_detection"
    MECHANISM_MATCHING = "mechanism_matching"
    AD_SCORING = "ad_scoring"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    EXPLANATION = "explanation"


@dataclass
class AtomNode:
    """Node in the Atom of Thought DAG."""
    atom_id: str
    atom_type: AtomType
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    status: AtomStatus = AtomStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    prompt: Optional[str] = None
    response: Optional[str] = None
    confidence: float = 0.0
    tokens_used: int = 0
    recomputation_count: int = 0


@dataclass
class DAGExecution:
    """Complete DAG execution record."""
    dag_id: str
    trace_id: str
    timestamp: datetime
    atoms: Dict[str, AtomNode] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    total_duration_ms: float = 0.0
    critical_path_duration_ms: float = 0.0
    parallelism_factor: float = 1.0
    final_output: Optional[Dict] = None
    status: str = "pending"


class AtomOfThoughtTracer:
    """Trace Atom of Thought DAG execution."""
    
    PSYCHOLOGICAL_DAG = {
        "extract_text_signals": {
            "type": AtomType.SIGNAL_EXTRACTION,
            "description": "Extract linguistic patterns from text",
            "dependencies": []
        },
        "extract_behavioral_signals": {
            "type": AtomType.SIGNAL_EXTRACTION,
            "description": "Extract behavioral patterns from history",
            "dependencies": []
        },
        "infer_big_five": {
            "type": AtomType.PERSONALITY_INFERENCE,
            "description": "Infer Big Five personality traits",
            "dependencies": ["extract_text_signals", "extract_behavioral_signals"]
        },
        "infer_regulatory_focus": {
            "type": AtomType.PERSONALITY_INFERENCE,
            "description": "Infer promotion/prevention orientation",
            "dependencies": ["extract_text_signals"]
        },
        "detect_construal_level": {
            "type": AtomType.STATE_DETECTION,
            "description": "Detect current construal level",
            "dependencies": ["extract_text_signals"]
        },
        "detect_emotional_state": {
            "type": AtomType.STATE_DETECTION,
            "description": "Detect current emotional state",
            "dependencies": ["extract_text_signals"]
        },
        "match_mechanisms": {
            "type": AtomType.MECHANISM_MATCHING,
            "description": "Match profile to persuasion mechanisms",
            "dependencies": ["infer_big_five", "infer_regulatory_focus", "detect_construal_level"]
        },
        "score_ads": {
            "type": AtomType.AD_SCORING,
            "description": "Score ad candidates",
            "dependencies": ["match_mechanisms", "detect_emotional_state"]
        },
        "synthesize_decision": {
            "type": AtomType.SYNTHESIS,
            "description": "Synthesize final ad selection",
            "dependencies": ["score_ads"]
        },
        "verify_decision": {
            "type": AtomType.VERIFICATION,
            "description": "Verify decision quality",
            "dependencies": ["synthesize_decision"]
        }
    }
    
    def __init__(self, neo4j_client, redis_client, base_collector):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.base_collector = base_collector
        self._active_dags: Dict[str, DAGExecution] = {}
    
    def start_dag_execution(self, trace_id: str, context: Dict[str, Any]) -> str:
        """Start tracking a DAG execution."""
        
        dag_id = str(uuid.uuid4())
        atoms = {}
        edges = []
        
        for name, definition in self.PSYCHOLOGICAL_DAG.items():
            atom = AtomNode(
                atom_id=f"{dag_id}:{name}",
                atom_type=definition["type"],
                name=name,
                description=definition["description"],
                dependencies=[f"{dag_id}:{d}" for d in definition["dependencies"]],
                inputs=context
            )
            atoms[atom.atom_id] = atom
            
            for dep in definition["dependencies"]:
                edges.append((f"{dag_id}:{dep}", atom.atom_id))
        
        for atom_id, atom in atoms.items():
            for other_id, other in atoms.items():
                if atom_id in other.dependencies:
                    atom.dependents.append(other_id)
        
        execution_order = self._topological_sort(atoms)
        parallel_groups = self._calculate_parallel_groups(atoms, execution_order)
        
        dag_execution = DAGExecution(
            dag_id=dag_id,
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            atoms=atoms,
            edges=edges,
            execution_order=execution_order,
            parallel_groups=parallel_groups
        )
        
        self._active_dags[dag_id] = dag_execution
        return dag_id
    
    def start_atom(self, dag_id: str, atom_name: str, inputs: Dict[str, Any]) -> str:
        """Record start of atom execution."""
        
        dag = self._active_dags.get(dag_id)
        if not dag:
            return None
        
        atom_id = f"{dag_id}:{atom_name}"
        atom = dag.atoms.get(atom_id)
        
        if atom:
            atom.status = AtomStatus.EXECUTING
            atom.start_time = datetime.utcnow()
            atom.inputs = inputs
        
        return atom_id
    
    def end_atom(
        self,
        dag_id: str,
        atom_name: str,
        outputs: Dict[str, Any],
        confidence: float = 1.0,
        status: AtomStatus = AtomStatus.COMPLETED
    ):
        """Record completion of atom execution."""
        
        dag = self._active_dags.get(dag_id)
        if not dag:
            return
        
        atom_id = f"{dag_id}:{atom_name}"
        atom = dag.atoms.get(atom_id)
        
        if atom:
            atom.status = status
            atom.end_time = datetime.utcnow()
            atom.duration_ms = (atom.end_time - atom.start_time).total_seconds() * 1000
            atom.outputs = outputs
            atom.confidence = confidence
    
    def get_dag_visualization(self, dag_id: str) -> Dict:
        """Get visualization-ready DAG representation."""
        
        dag = self._active_dags.get(dag_id)
        if not dag:
            return {"error": "DAG not found"}
        
        nodes = []
        links = []
        
        layers = self._calculate_layers(dag.atoms)
        
        for atom_id, atom in dag.atoms.items():
            layer = layers.get(atom_id, 0)
            layer_nodes = [n for n, l in layers.items() if l == layer]
            position_in_layer = layer_nodes.index(atom_id)
            
            nodes.append({
                "id": atom_id,
                "name": atom.name,
                "type": atom.atom_type.value,
                "status": atom.status.value,
                "duration_ms": atom.duration_ms or 0,
                "confidence": atom.confidence,
                "x": layer * 200,
                "y": (position_in_layer - len(layer_nodes) / 2) * 80
            })
        
        for source, target in dag.edges:
            links.append({
                "source": source,
                "target": target,
                "value": dag.atoms[source].confidence if source in dag.atoms else 0
            })
        
        return {
            "dag_id": dag_id,
            "nodes": nodes,
            "links": links,
            "execution_order": dag.execution_order,
            "parallel_groups": dag.parallel_groups,
            "critical_path": self._find_critical_path(dag),
            "metrics": {
                "total_duration_ms": dag.total_duration_ms,
                "parallelism_factor": dag.parallelism_factor,
                "total_tokens": sum(a.tokens_used for a in dag.atoms.values())
            }
        }
    
    def _topological_sort(self, atoms: Dict[str, AtomNode]) -> List[str]:
        """Topological sort of atoms."""
        visited = set()
        order = []
        
        def visit(atom_id: str):
            if atom_id in visited:
                return
            visited.add(atom_id)
            atom = atoms.get(atom_id)
            if atom:
                for dep in atom.dependencies:
                    visit(dep)
                order.append(atom_id)
        
        for atom_id in atoms:
            visit(atom_id)
        
        return order
    
    def _calculate_parallel_groups(
        self,
        atoms: Dict[str, AtomNode],
        execution_order: List[str]
    ) -> List[List[str]]:
        """Group atoms that can execute in parallel."""
        
        groups = []
        completed = set()
        
        while len(completed) < len(atoms):
            ready = []
            for atom_id in execution_order:
                if atom_id in completed:
                    continue
                atom = atoms.get(atom_id)
                if atom and all(d in completed for d in atom.dependencies):
                    ready.append(atom_id)
            
            if not ready:
                break
            
            groups.append(ready)
            completed.update(ready)
        
        return groups
    
    def _calculate_layers(self, atoms: Dict[str, AtomNode]) -> Dict[str, int]:
        """Calculate layer for each node."""
        layers = {}
        
        for atom_id, atom in atoms.items():
            if not atom.dependencies:
                layers[atom_id] = 0
        
        changed = True
        while changed:
            changed = False
            for atom_id, atom in atoms.items():
                if atom_id not in layers:
                    if atom.dependencies and all(c in layers for c in atom.dependencies):
                        layers[atom_id] = max(layers[c] for c in atom.dependencies) + 1
                        changed = True
        
        return layers
    
    def _find_critical_path(self, dag: DAGExecution) -> List[str]:
        """Find path with longest duration."""
        
        duration = {}
        predecessor = {}
        
        for atom_id in dag.execution_order:
            atom = dag.atoms.get(atom_id)
            if not atom:
                continue
            
            max_dep = None
            max_dur = 0
            
            for dep in atom.dependencies:
                if duration.get(dep, 0) > max_dur:
                    max_dur = duration[dep]
                    max_dep = dep
            
            duration[atom_id] = max_dur + (atom.duration_ms or 0)
            predecessor[atom_id] = max_dep
        
        if not duration:
            return []
        
        end_node = max(duration.items(), key=lambda x: x[1])[0]
        
        path = []
        current = end_node
        while current:
            path.append(current)
            current = predecessor.get(current)
        
        return list(reversed(path))
```

---

## Part 4: Causal Chain Visualization

### 4.1 End-to-End Causal Tracing

```python
"""
Causal Chain Visualization.
End-to-end tracing from signal to outcome.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


@dataclass
class CausalNode:
    """Node in a causal chain."""
    node_id: str
    node_type: str
    timestamp: datetime
    label: str
    description: str
    value: Any
    confidence: float
    causes: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    causal_strength: Dict[str, float] = field(default_factory=dict)
    component: str = ""
    trace_id: str = ""


@dataclass
class CausalChain:
    """Complete causal chain from signal to outcome."""
    chain_id: str
    trace_id: str
    timestamp: datetime
    nodes: Dict[str, CausalNode] = field(default_factory=dict)
    root_nodes: List[str] = field(default_factory=list)
    terminal_nodes: List[str] = field(default_factory=list)
    total_causal_paths: int = 0
    critical_path: List[str] = field(default_factory=list)
    mechanism_attributions: Dict[str, float] = field(default_factory=dict)
    construct_attributions: Dict[str, float] = field(default_factory=dict)


class CausalChainBuilder:
    """Build and visualize causal chains."""
    
    def __init__(self, neo4j_client, psychological_tracer, aot_tracer, gradient_tracer):
        self.neo4j = neo4j_client
        self.psych_tracer = psychological_tracer
        self.aot_tracer = aot_tracer
        self.gradient_tracer = gradient_tracer
    
    def build_causal_chain(self, trace_id: str) -> CausalChain:
        """Build complete causal chain for a decision trace."""
        
        chain_id = str(uuid.uuid4())
        nodes = {}
        
        # 1. Signal nodes
        signals = self._get_signals(trace_id)
        for signal in signals:
            node = CausalNode(
                node_id=f"signal:{signal['signal_id']}",
                node_type="signal",
                timestamp=signal['timestamp'],
                label=f"{signal['signal_type']} from {signal['data_source']}",
                description=f"Raw signal: {str(signal['raw_value'])[:100]}",
                value=signal['raw_value'],
                confidence=signal['confidence'],
                component="signal_extractor",
                trace_id=trace_id
            )
            nodes[node.node_id] = node
        
        # 2. Inference nodes
        inferences = self._get_inferences(trace_id)
        for inference in inferences:
            node = CausalNode(
                node_id=f"inference:{inference['inference_id']}",
                node_type="inference",
                timestamp=inference['timestamp'],
                label=f"{inference['construct_name']} inference",
                description=f"Inferred = {inference['inferred_value']:.2f}",
                value=inference['inferred_value'],
                confidence=inference['confidence'],
                component="psychological_profiler",
                trace_id=trace_id
            )
            
            for signal_id in inference.get('input_signals', []):
                signal_node_id = f"signal:{signal_id}"
                if signal_node_id in nodes:
                    node.causes.append(signal_node_id)
                    nodes[signal_node_id].effects.append(node.node_id)
            
            nodes[node.node_id] = node
        
        # 3. Mechanism nodes
        mechanisms = self._get_mechanism_activations(trace_id)
        for mechanism in mechanisms:
            node = CausalNode(
                node_id=f"mechanism:{mechanism['activation_id']}",
                node_type="mechanism",
                timestamp=mechanism['timestamp'],
                label=f"{mechanism['mechanism_name']} activation",
                description=f"Strength: {mechanism['activation_strength']:.2f}",
                value=mechanism['activation_strength'],
                confidence=mechanism['confidence'],
                component="mechanism_matcher",
                trace_id=trace_id
            )
            nodes[node.node_id] = node
        
        # 4. Decision node
        decision = self._get_decision(trace_id)
        if decision:
            node = CausalNode(
                node_id=f"decision:{trace_id}",
                node_type="decision",
                timestamp=decision['timestamp'],
                label=f"Ad: {decision.get('selected_ad', 'unknown')}",
                description=f"Confidence: {decision['confidence']:.2f}",
                value=decision.get('selected_ad'),
                confidence=decision['confidence'],
                component="ad_scorer",
                trace_id=trace_id
            )
            
            for mech_node_id, mech_node in nodes.items():
                if mech_node.node_type == "mechanism":
                    node.causes.append(mech_node_id)
                    mech_node.effects.append(node.node_id)
            
            nodes[node.node_id] = node
        
        # 5. Outcome node
        outcome = self._get_outcome(trace_id)
        if outcome:
            node = CausalNode(
                node_id=f"outcome:{trace_id}",
                node_type="outcome",
                timestamp=outcome['timestamp'],
                label=f"Outcome: {outcome['outcome_type']}",
                description=f"Value: {outcome['outcome_value']}",
                value=outcome['outcome_value'],
                confidence=1.0,
                component="outcome_collector",
                trace_id=trace_id
            )
            
            decision_node_id = f"decision:{trace_id}"
            if decision_node_id in nodes:
                node.causes.append(decision_node_id)
                nodes[decision_node_id].effects.append(node.node_id)
            
            nodes[node.node_id] = node
        
        root_nodes = [n.node_id for n in nodes.values() if not n.causes]
        terminal_nodes = [n.node_id for n in nodes.values() if not n.effects]
        
        chain = CausalChain(
            chain_id=chain_id,
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            nodes=nodes,
            root_nodes=root_nodes,
            terminal_nodes=terminal_nodes
        )
        
        return chain
    
    def get_visualization(self, chain: CausalChain) -> Dict:
        """Get visualization-ready representation."""
        
        nodes = []
        links = []
        
        layers = self._calculate_layers(chain.nodes)
        
        for node_id, node in chain.nodes.items():
            layer = layers.get(node_id, 0)
            layer_nodes = [n for n, l in layers.items() if l == layer]
            position = layer_nodes.index(node_id) if node_id in layer_nodes else 0
            
            nodes.append({
                "id": node_id,
                "type": node.node_type,
                "label": node.label,
                "confidence": node.confidence,
                "x": layer * 200,
                "y": (position - len(layer_nodes) / 2) * 80,
                "is_root": node_id in chain.root_nodes,
                "is_terminal": node_id in chain.terminal_nodes
            })
        
        for node_id, node in chain.nodes.items():
            for cause_id in node.causes:
                links.append({
                    "source": cause_id,
                    "target": node_id,
                    "strength": node.causal_strength.get(cause_id, 0.5)
                })
        
        return {
            "chain_id": chain.chain_id,
            "trace_id": chain.trace_id,
            "nodes": nodes,
            "links": links,
            "summary": {
                "total_nodes": len(nodes),
                "total_links": len(links)
            }
        }
    
    def export_for_audit(self, chain: CausalChain) -> Dict:
        """Export causal chain for compliance audit."""
        
        return {
            "audit_export": True,
            "export_timestamp": datetime.utcnow().isoformat(),
            "chain_id": chain.chain_id,
            "trace_id": chain.trace_id,
            "data_sources": [
                {"signal_id": n.node_id, "source": n.description}
                for n in chain.nodes.values() if n.node_type == "signal"
            ],
            "psychological_inferences": [
                {"inference_id": n.node_id, "construct": n.label, "value": n.value}
                for n in chain.nodes.values() if n.node_type == "inference"
            ],
            "mechanism_activations": [
                {"activation_id": n.node_id, "mechanism": n.label, "strength": n.value}
                for n in chain.nodes.values() if n.node_type == "mechanism"
            ],
            "compliance_notes": {
                "automated_decision": True,
                "human_review_available": True,
                "legal_basis": "legitimate_interest"
            }
        }
    
    def _calculate_layers(self, nodes: Dict[str, CausalNode]) -> Dict[str, int]:
        """Calculate layer for each node."""
        layers = {}
        
        for node_id, node in nodes.items():
            if not node.causes:
                layers[node_id] = 0
        
        changed = True
        while changed:
            changed = False
            for node_id, node in nodes.items():
                if node_id not in layers:
                    if node.causes and all(c in layers for c in node.causes):
                        layers[node_id] = max(layers[c] for c in node.causes) + 1
                        changed = True
        
        return layers
    
    def _get_signals(self, trace_id: str) -> List[Dict]:
        """Get signals for trace."""
        query = """
        MATCH (ps:PsychologicalSignal {trace_id: $trace_id})
        RETURN ps.signal_id AS signal_id, ps.signal_type AS signal_type,
               ps.timestamp AS timestamp, ps.data_source AS data_source,
               ps.raw_value AS raw_value, ps.confidence AS confidence
        """
        return list(self.neo4j.run(query, {"trace_id": trace_id}))
    
    def _get_inferences(self, trace_id: str) -> List[Dict]:
        """Get inferences for trace."""
        query = """
        MATCH (ci:ConstructInference {trace_id: $trace_id})
        RETURN ci.inference_id AS inference_id, ci.construct_name AS construct_name,
               ci.inferred_value AS inferred_value, ci.confidence AS confidence,
               ci.timestamp AS timestamp, ci.input_signals AS input_signals
        """
        return list(self.neo4j.run(query, {"trace_id": trace_id}))
    
    def _get_mechanism_activations(self, trace_id: str) -> List[Dict]:
        """Get mechanism activations for trace."""
        query = """
        MATCH (ma:MechanismActivation {trace_id: $trace_id})
        RETURN ma.activation_id AS activation_id, ma.mechanism_name AS mechanism_name,
               ma.activation_strength AS activation_strength, ma.confidence AS confidence,
               ma.timestamp AS timestamp
        """
        return list(self.neo4j.run(query, {"trace_id": trace_id}))
    
    def _get_decision(self, trace_id: str) -> Optional[Dict]:
        """Get decision for trace."""
        query = """
        MATCH (t:ReasoningTrace {trace_id: $trace_id})
        RETURN t.outcome AS selected_ad, t.confidence AS confidence, t.timestamp AS timestamp
        """
        result = self.neo4j.run(query, {"trace_id": trace_id}).single()
        return dict(result) if result else None
    
    def _get_outcome(self, trace_id: str) -> Optional[Dict]:
        """Get outcome for trace."""
        query = """
        MATCH (ls:LearningSignal {trigger_trace_id: $trace_id})
        RETURN ls.outcome_type AS outcome_type, ls.outcome_value AS outcome_value,
               ls.timestamp AS timestamp
        """
        result = self.neo4j.run(query, {"trace_id": trace_id}).single()
        return dict(result) if result else None
```

---

## Part 5: Cross-Component Learning Signal Debugging

### 5.1 Gradient Bridge Observability

```python
"""
Cross-Component Learning Signal Debugging.
Traces learning signals through the Gradient Bridge.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class LearningSignalType(Enum):
    OUTCOME_OBSERVATION = "outcome_observation"
    CREDIT_ATTRIBUTION = "credit_attribution"
    BANDIT_REWARD = "bandit_reward"
    MECHANISM_FEEDBACK = "mechanism_feedback"
    PROFILE_UPDATE = "profile_update"


class ComponentType(Enum):
    PSYCHOLOGICAL_PROFILER = "psychological_profiler"
    MECHANISM_MATCHER = "mechanism_matcher"
    AD_SCORER = "ad_scorer"
    CONTEXTUAL_BANDIT = "contextual_bandit"
    META_LEARNER = "meta_learner"
    GRAPH_STORE = "graph_store"


@dataclass
class LearningSignal:
    """Individual learning signal."""
    signal_id: str
    signal_type: LearningSignalType
    timestamp: datetime
    source_component: ComponentType
    destination_components: List[ComponentType]
    trigger_event: str
    trigger_trace_id: str
    credit_assignment: Dict[str, float] = field(default_factory=dict)
    mechanism_credits: Dict[str, float] = field(default_factory=dict)
    construct_credits: Dict[str, float] = field(default_factory=dict)
    outcome_type: Optional[str] = None
    outcome_value: Optional[float] = None
    propagation_path: List[str] = field(default_factory=list)
    propagation_complete: bool = False


@dataclass
class BanditArmSelection:
    """Record of contextual bandit arm selection."""
    selection_id: str
    timestamp: datetime
    user_id_hash: str
    context_features: Dict[str, float]
    psychological_context: Dict[str, float]
    arms_considered: List[str]
    arm_scores: Dict[str, float]
    exploration_bonus: Dict[str, float]
    selected_arm: str
    selection_reason: str
    exploitation_probability: float
    reward_observed: bool = False
    reward_value: Optional[float] = None


class GradientBridgeTracer:
    """Trace learning signals across ADAM components."""
    
    def __init__(self, neo4j_client, redis_client, event_bus):
        self.neo4j = neo4j_client
        self.redis = redis_client
        self.event_bus = event_bus
        self._active_signals: Dict[str, LearningSignal] = {}
        self._bandit_selections: Dict[str, BanditArmSelection] = {}
    
    def record_outcome(
        self,
        trace_id: str,
        outcome_type: str,
        outcome_value: float,
        trigger_event: str
    ) -> str:
        """Record an outcome that will generate learning signals."""
        
        signal_id = str(uuid.uuid4())
        
        signal = LearningSignal(
            signal_id=signal_id,
            signal_type=LearningSignalType.OUTCOME_OBSERVATION,
            timestamp=datetime.utcnow(),
            source_component=ComponentType.AD_SCORER,
            destination_components=[
                ComponentType.CONTEXTUAL_BANDIT,
                ComponentType.META_LEARNER,
                ComponentType.PSYCHOLOGICAL_PROFILER,
                ComponentType.GRAPH_STORE
            ],
            trigger_event=trigger_event,
            trigger_trace_id=trace_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            propagation_path=[ComponentType.AD_SCORER.value]
        )
        
        self._active_signals[signal_id] = signal
        return signal_id
    
    def record_credit_attribution(
        self,
        signal_id: str,
        mechanism_credits: Dict[str, float],
        construct_credits: Dict[str, float],
        attribution_method: str
    ):
        """Record credit attribution for an outcome."""
        
        signal = self._active_signals.get(signal_id)
        if not signal:
            return
        
        signal.mechanism_credits = mechanism_credits
        signal.construct_credits = construct_credits
        signal.credit_assignment["attribution_method"] = attribution_method
        signal.credit_assignment["mechanism_total"] = sum(mechanism_credits.values())
        signal.credit_assignment["construct_total"] = sum(construct_credits.values())
    
    def record_bandit_selection(
        self,
        user_id_hash: str,
        context_features: Dict[str, float],
        psychological_context: Dict[str, float],
        arms: List[str],
        arm_scores: Dict[str, float],
        exploration_bonus: Dict[str, float],
        selected_arm: str,
        selection_reason: str,
        exploitation_probability: float
    ) -> str:
        """Record contextual bandit arm selection."""
        
        selection_id = str(uuid.uuid4())
        
        selection = BanditArmSelection(
            selection_id=selection_id,
            timestamp=datetime.utcnow(),
            user_id_hash=user_id_hash,
            context_features=context_features,
            psychological_context=psychological_context,
            arms_considered=arms,
            arm_scores=arm_scores,
            exploration_bonus=exploration_bonus,
            selected_arm=selected_arm,
            selection_reason=selection_reason,
            exploitation_probability=exploitation_probability
        )
        
        self._bandit_selections[selection_id] = selection
        return selection_id
    
    def record_bandit_reward(self, selection_id: str, reward_value: float):
        """Record reward for bandit selection."""
        
        selection = self._bandit_selections.get(selection_id)
        if selection:
            selection.reward_observed = True
            selection.reward_value = reward_value
    
    def analyze_credit_attribution(self, time_range_hours: int = 24) -> Dict:
        """Analyze credit attribution patterns."""
        
        query = """
        MATCH (ls:LearningSignal)
        WHERE ls.timestamp > datetime() - duration({hours: $hours})
        UNWIND keys(ls.mechanism_credits) AS mechanism
        WITH mechanism, 
             avg(ls.mechanism_credits[mechanism]) AS avg_credit,
             sum(ls.mechanism_credits[mechanism] * ls.outcome_value) AS weighted_impact,
             count(*) AS sample_size
        WHERE sample_size > 10
        RETURN mechanism, avg_credit, weighted_impact, sample_size
        ORDER BY weighted_impact DESC
        """
        
        results = list(self.neo4j.run(query, {"hours": time_range_hours}))
        
        return {
            "time_range_hours": time_range_hours,
            "mechanisms": [
                {
                    "mechanism": r["mechanism"],
                    "avg_credit": r["avg_credit"],
                    "weighted_impact": r["weighted_impact"],
                    "sample_size": r["sample_size"]
                }
                for r in results
            ]
        }
    
    def analyze_bandit_exploration(self, time_range_hours: int = 24) -> Dict:
        """Analyze bandit exploration patterns."""
        
        query = """
        MATCH (bas:BanditArmSelection)
        WHERE bas.timestamp > datetime() - duration({hours: $hours})
          AND bas.reward_observed = true
        WITH bas.selection_reason AS reason,
             avg(bas.exploitation_probability) AS avg_exploit_prob,
             avg(bas.reward_value) AS avg_reward,
             count(*) AS selection_count
        RETURN reason, avg_exploit_prob, avg_reward, selection_count
        ORDER BY selection_count DESC
        """
        
        results = list(self.neo4j.run(query, {"hours": time_range_hours}))
        
        total_selections = sum(r["selection_count"] for r in results)
        exploration_rate = sum(
            r["selection_count"] for r in results 
            if "thompson" in r["reason"] or "explore" in r["reason"]
        ) / (total_selections + 1e-6)
        
        return {
            "time_range_hours": time_range_hours,
            "total_selections": total_selections,
            "exploration_rate": exploration_rate,
            "by_reason": results
        }
```

---

## Part 6: API Endpoints

### 6.1 Observability API

```python
"""
Comprehensive Observability API for ADAM.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

app = FastAPI(
    title="ADAM Psychological Intelligence Observability API",
    version="2.0.0"
)


class PsychologicalTraceResponse(BaseModel):
    trace_id: str
    timestamp: str
    signals: List[Dict]
    inferences: List[Dict]
    profile: Dict
    mechanism_activations: List[Dict]
    decision: Dict
    outcome: Optional[Dict]
    causal_chain: Optional[Dict]


@app.get("/v2/trace/{trace_id}/psychological")
async def get_psychological_trace(
    trace_id: str,
    include_signals: bool = True,
    include_inferences: bool = True,
    include_mechanisms: bool = True,
    include_causal_chain: bool = True
):
    """Get complete psychological trace for a decision."""
    
    trace = trace_store.get_trace(trace_id)
    if not trace:
        raise HTTPException(404, f"Trace not found: {trace_id}")
    
    result = {
        "trace_id": trace_id,
        "timestamp": trace.timestamp.isoformat(),
        "signals": psych_tracer.get_signals(trace_id) if include_signals else [],
        "inferences": psych_tracer.get_inferences(trace_id) if include_inferences else [],
        "profile": psych_tracer.get_profile(trace_id),
        "mechanism_activations": psych_tracer.get_mechanism_activations(trace_id) if include_mechanisms else [],
        "decision": {"selected_ad": trace.outcome, "confidence": trace.confidence},
        "outcome": gradient_tracer.get_outcome(trace_id),
        "causal_chain": causal_builder.get_visualization(
            causal_builder.build_causal_chain(trace_id)
        ) if include_causal_chain else None
    }
    
    return result


@app.get("/v2/trace/{trace_id}/dag")
async def get_dag_visualization(trace_id: str):
    """Get Atom of Thought DAG visualization."""
    
    dag_id = aot_tracer.get_dag_for_trace(trace_id)
    if not dag_id:
        raise HTTPException(404, f"DAG not found for trace: {trace_id}")
    
    return aot_tracer.get_dag_visualization(dag_id)


@app.get("/v2/trace/{trace_id}/causal-chain")
async def get_causal_chain(trace_id: str):
    """Get complete causal chain visualization."""
    
    chain = causal_builder.build_causal_chain(trace_id)
    return causal_builder.get_visualization(chain)


@app.post("/v2/trace/{trace_id}/causal-chain/export")
async def export_causal_chain(trace_id: str, format: str = "json"):
    """Export causal chain for audit/compliance."""
    
    chain = causal_builder.build_causal_chain(trace_id)
    return causal_builder.export_for_audit(chain)


@app.get("/v2/analytics/learning-signals")
async def get_learning_signal_analytics(hours: int = Query(default=24, ge=1, le=168)):
    """Get learning signal analytics."""
    
    return {
        "mechanism_attributions": gradient_tracer.analyze_credit_attribution(hours),
        "bandit_exploration": gradient_tracer.analyze_bandit_exploration(hours)
    }


@app.get("/v2/analytics/psychological-constructs")
async def get_construct_analytics(
    construct: Optional[str] = None,
    hours: int = Query(default=24, ge=1, le=168)
):
    """Get psychological construct analytics."""
    
    query = """
    MATCH (ci:ConstructInference)
    WHERE ci.timestamp > datetime() - duration({hours: $hours})
    """
    
    params = {"hours": hours}
    if construct:
        query += " AND ci.construct_name = $construct"
        params["construct"] = construct
    
    query += """
    WITH ci.construct_name AS construct,
         avg(ci.inferred_value) AS avg_value,
         avg(ci.confidence) AS avg_confidence,
         stdev(ci.inferred_value) AS value_std,
         count(ci) AS count
    RETURN construct, avg_value, avg_confidence, value_std, count
    ORDER BY count DESC
    """
    
    results = list(neo4j_client.run(query, params))
    
    return {
        "time_range_hours": hours,
        "constructs": [
            {
                "construct": r["construct"],
                "avg_value": r["avg_value"],
                "stability": 1.0 - min(1.0, (r["value_std"] or 0) * 2),
                "sample_size": r["count"]
            }
            for r in results
        ]
    }


@app.get("/v2/analytics/mechanisms")
async def get_mechanism_analytics(hours: int = Query(default=24, ge=1, le=168)):
    """Get mechanism effectiveness analytics."""
    
    query = """
    MATCH (ma:MechanismActivation)
    WHERE ma.timestamp > datetime() - duration({hours: $hours})
      AND ma.outcome_observed = true
    WITH ma.mechanism_name AS mechanism,
         avg(ma.activation_strength) AS avg_activation,
         avg(ma.predicted_impact) AS avg_predicted,
         avg(ma.actual_impact) AS avg_actual,
         count(ma) AS count
    RETURN mechanism, avg_activation, avg_predicted, avg_actual, count
    ORDER BY count DESC
    """
    
    results = list(neo4j_client.run(query, {"hours": hours}))
    
    return {
        "mechanisms": [
            {
                "mechanism": r["mechanism"],
                "avg_activation_strength": r["avg_activation"],
                "prediction_accuracy": 1.0 - abs((r["avg_predicted"] or 0) - (r["avg_actual"] or 0)),
                "sample_size": r["count"]
            }
            for r in results
        ]
    }


@app.get("/v2/health")
async def health_check():
    """Comprehensive health check."""
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "psychological_tracer": "healthy",
            "aot_tracer": "healthy",
            "gradient_bridge_tracer": "healthy",
            "causal_chain_builder": "healthy"
        }
    }
```

---

## Part 7: Success Metrics

### 7.1 Observability KPIs

| Metric | Target | Business Impact |
|--------|--------|-----------------|
| Trace capture rate | >99.9% | Debug completeness |
| Psychological inference visibility | 100% | Audit readiness |
| Mechanism attribution accuracy | >90% | Optimization quality |
| DAG visualization latency | <500ms | Engineer productivity |
| Causal chain completeness | >95% | Compliance reporting |
| API response latency p95 | <200ms | Usability |

### 7.2 Debugging Efficiency

| Metric | Before PIOP | Target |
|--------|-------------|--------|
| Time to identify root cause | 2-4 hours | <15 minutes |
| Time to generate audit report | 1 day | <5 minutes |
| Time to run sensitivity analysis | Manual | <30 seconds |

---

## Part 8: Implementation Timeline

```
Week 1-2: Foundation
├── Deploy PsychologicalTraceCollector
├── Implement signal/inference recording
└── Set up Redis and Neo4j schemas

Week 3-4: Atom of Thought Tracing
├── Deploy AtomOfThoughtTracer
├── Implement DAG visualization
└── Add critical path analysis

Week 5-6: Learning Signal Debugging
├── Deploy GradientBridgeTracer
├── Implement credit attribution
└── Add bandit exploration tracing

Week 7-8: Causal Chain Visualization
├── Deploy CausalChainBuilder
├── Implement end-to-end tracing
└── Add audit export functionality

Week 9-10: API & Integration
├── Deploy API endpoints
├── Integration testing
└── Performance optimization

Week 11-12: Production Hardening
├── Load testing
├── Alerting configuration
└── Documentation
```

---

## Part 9: Research Foundation

**Explainable AI:**
1. Ribeiro et al. (2016). "Why Should I Trust You?" KDD.
2. Lundberg & Lee (2017). "A Unified Approach to Interpreting Model Predictions." NeurIPS.

**Psychological Measurement:**
3. Kosinski et al. (2013). "Private traits predictable from digital records." PNAS.
4. Matz et al. (2017). "Psychological targeting for digital mass persuasion." PNAS.

**Distributed Tracing:**
5. Sigelman et al. (2010). "Dapper: Large-Scale Distributed Systems Tracing." Google.

---

*End of ADAM Gap 26: Observability & Debugging Complete Specification*

**Document Statistics:**
- Total sections: 9 main parts
- Code implementations: 5 major classes
- API endpoints: 10+
- Neo4j queries: 10+
- Implementation timeline: 12 weeks
- Estimated effort: 12-14 person-weeks
