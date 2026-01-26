# =============================================================================
# ADAM Prompt Templates
# Location: adam/llm/prompts.py
# =============================================================================

"""
PROMPT TEMPLATES

Templates for psychological reasoning with Claude.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

class PromptTemplate(BaseModel):
    """A reusable prompt template."""
    
    name: str
    system: str
    user_template: str
    
    # Output format
    output_schema: Optional[Dict[str, Any]] = None
    
    # Model preferences
    preferred_model: Optional[str] = None
    max_tokens: int = Field(default=1024)
    temperature: float = Field(default=0.7)
    
    def render(
        self,
        **kwargs,
    ) -> str:
        """Render template with variables."""
        return self.user_template.format(**kwargs)


# =============================================================================
# PSYCHOLOGICAL PROMPT BUILDER
# =============================================================================

class PsychologicalPromptBuilder:
    """
    Builder for psychological reasoning prompts.
    """
    
    # System prompts for different contexts
    SYSTEM_PROMPTS = {
        "psychological_expert": """You are an expert in consumer psychology and behavioral science. 
Your role is to analyze psychological evidence and provide nuanced assessments.
You understand personality psychology (Big Five), regulatory focus theory, construal level theory, 
and cognitive mechanisms that influence decision-making.
Always provide your reasoning and confidence levels.""",

        "fusion_expert": """You are an expert at synthesizing multiple sources of psychological evidence.
Your role is to resolve conflicts between different intelligence sources and produce coherent assessments.
When sources conflict, you should:
1. Identify the nature of the conflict
2. Consider source reliability and recency
3. Apply psychological theory to resolve
4. Provide a synthesized conclusion with confidence.""",

        "mechanism_expert": """You are an expert in cognitive mechanisms and persuasion.
You understand the 9 core mechanisms: automatic evaluation, wanting-liking dissociation,
evolutionary motive, linguistic framing, mimetic desire, embodied cognition,
attention dynamics, identity construction, and temporal construal.
Analyze which mechanisms are most likely to be effective for a given user context.""",
    }
    
    # Templates for different atoms
    ATOM_TEMPLATES = {
        "regulatory_focus": PromptTemplate(
            name="regulatory_focus_assessment",
            system=SYSTEM_PROMPTS["psychological_expert"],
            user_template="""Analyze the following evidence to assess regulatory focus:

User Context:
{user_context}

Evidence from Multiple Sources:
{evidence}

Conflicts Detected:
{conflicts}

Please assess:
1. Promotion focus strength (0-1)
2. Prevention focus strength (0-1)
3. Dominant focus (promotion/prevention/balanced)
4. Confidence in assessment (0-1)
5. Key signals that informed your assessment

Respond in JSON format.""",
            output_schema={
                "promotion_strength": "float 0-1",
                "prevention_strength": "float 0-1",
                "dominant_focus": "string",
                "confidence": "float 0-1",
                "key_signals": ["list of strings"],
                "reasoning": "string",
            },
            temperature=0.5,
        ),
        
        "construal_level": PromptTemplate(
            name="construal_level_assessment",
            system=SYSTEM_PROMPTS["psychological_expert"],
            user_template="""Analyze the following evidence to assess construal level:

User Context:
{user_context}

Evidence:
{evidence}

Conflicts:
{conflicts}

Please assess:
1. Construal level (0=concrete, 1=abstract)
2. Temporal distance (psychological distance in decision)
3. Recommended message abstraction level
4. Confidence in assessment

Respond in JSON format.""",
            output_schema={
                "construal_level": "float 0-1",
                "temporal_distance": "float 0-1",
                "message_abstraction": "string (concrete/mixed/abstract)",
                "confidence": "float 0-1",
                "reasoning": "string",
            },
            temperature=0.5,
        ),
        
        "mechanism_activation": PromptTemplate(
            name="mechanism_activation_assessment",
            system=SYSTEM_PROMPTS["mechanism_expert"],
            user_template="""Analyze which cognitive mechanisms should be activated:

User Profile:
{user_profile}

Current State:
{current_state}

Evidence:
{evidence}

Available Mechanisms:
- automatic_evaluation: Quick, gut-level responses
- wanting_liking_dissociation: Desire vs enjoyment
- evolutionary_motive: Status, safety, belonging
- linguistic_framing: How language shapes perception
- mimetic_desire: Wanting what others want
- embodied_cognition: Physical-mental connections
- attention_dynamics: Focus and salience
- identity_construction: Self-concept alignment
- temporal_construal: Time perspective effects

Please recommend:
1. Top 3 mechanisms to activate
2. Activation strength for each (0-1)
3. Reasoning for each recommendation

Respond in JSON format.""",
            output_schema={
                "mechanisms": [
                    {
                        "mechanism": "string",
                        "activation_strength": "float 0-1",
                        "reasoning": "string",
                    }
                ],
                "overall_confidence": "float 0-1",
            },
            temperature=0.6,
        ),
        
        "evidence_fusion": PromptTemplate(
            name="evidence_fusion",
            system=SYSTEM_PROMPTS["fusion_expert"],
            user_template="""Synthesize the following conflicting evidence:

Intelligence Sources:
{sources}

Conflicts Detected:
{conflicts}

Context:
{context}

For each conflict, please:
1. Analyze the nature of the conflict
2. Assess source reliability
3. Apply psychological theory
4. Provide synthesized values

Respond in JSON format with resolved values.""",
            output_schema={
                "resolved_values": {"key": "value"},
                "conflict_resolutions": [
                    {
                        "conflict": "string",
                        "resolution": "string",
                        "chosen_value": "any",
                        "confidence": "float 0-1",
                    }
                ],
                "overall_confidence": "float 0-1",
            },
            temperature=0.4,
        ),
    }
    
    @classmethod
    def get_template(cls, atom_name: str) -> Optional[PromptTemplate]:
        """Get template for an atom."""
        return cls.ATOM_TEMPLATES.get(atom_name)
    
    @classmethod
    def build_fusion_prompt(
        cls,
        sources: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> tuple:
        """Build a fusion prompt."""
        template = cls.ATOM_TEMPLATES["evidence_fusion"]
        
        prompt = template.render(
            sources=_format_sources(sources),
            conflicts=_format_conflicts(conflicts),
            context=_format_context(context),
        )
        
        return template.system, prompt, template.output_schema
    
    @classmethod
    def build_atom_prompt(
        cls,
        atom_name: str,
        **kwargs,
    ) -> Optional[tuple]:
        """Build prompt for a specific atom."""
        template = cls.get_template(atom_name)
        if not template:
            return None
        
        # Format any dict/list values
        formatted_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                formatted_kwargs[key] = _format_value(value)
            else:
                formatted_kwargs[key] = value
        
        prompt = template.render(**formatted_kwargs)
        
        return template.system, prompt, template.output_schema


def _format_sources(sources: List[Dict[str, Any]]) -> str:
    """Format sources for prompt."""
    lines = []
    for i, source in enumerate(sources, 1):
        lines.append(f"Source {i} ({source.get('name', 'unknown')}):")
        lines.append(f"  Confidence: {source.get('confidence', 0.5)}")
        lines.append(f"  Values: {source.get('values', {})}")
        lines.append("")
    return "\n".join(lines)


def _format_conflicts(conflicts: List[Dict[str, Any]]) -> str:
    """Format conflicts for prompt."""
    if not conflicts:
        return "No conflicts detected."
    
    lines = []
    for i, conflict in enumerate(conflicts, 1):
        lines.append(f"Conflict {i}:")
        lines.append(f"  Field: {conflict.get('field', 'unknown')}")
        lines.append(f"  Source A: {conflict.get('source_a', {})} = {conflict.get('value_a')}")
        lines.append(f"  Source B: {conflict.get('source_b', {})} = {conflict.get('value_b')}")
        lines.append(f"  Difference: {conflict.get('difference', 0)}")
        lines.append("")
    return "\n".join(lines)


def _format_context(context: Dict[str, Any]) -> str:
    """Format context for prompt."""
    lines = []
    for key, value in context.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    """Format a value for inclusion in prompt."""
    import json
    try:
        return json.dumps(value, indent=2, default=str)
    except:
        return str(value)
