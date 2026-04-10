"""
Deep Bilateral Annotation Engine
==================================

Produces Amazon-quality dual-sided psychological annotations using
Claude, designed backwards from what the cascade ACTUALLY consumes.

Key design principles (from cross-disciplinary analysis):

1. GENOMICS (dual-read): Annotate buyer-side AND product-side
   independently, then compute alignment from both reads.

2. RADIOLOGY (BI-RADS): Output in the EXACT dimensional space
   the cascade consumes. Zero translation layer.

3. CLINICAL TRIALS (pre-registered): The dimensions extracted are
   defined by the cascade's consumption, not by the data.

4. PROTEIN FOLDING (multi-scale): Annotate at micro (word-level),
   meso (narrative arc), and macro (category-level) simultaneously.

5. CONTRASTIVE FRAMING: Ask what distinguishes this buyer from
   neutral, not just absolute scores. Prevents 0.5 clustering.

6. ANCHORED SCORING: Provide reference examples for each score
   level to reduce drift and improve calibration.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# The EXACT 20 edge property names the cascade consumes
# Each with its definition and scoring anchors
ANNOTATION_DIMENSIONS = {
    "regulatory_fit_score": {
        "name": "Regulatory Fit",
        "definition": "Was the buyer in promotion focus (seeking gains, aspirational) or prevention focus (avoiding losses, protective)?",
        "anchor_low": "0.1 = pure prevention ('I needed to make sure nothing went wrong', 'I was worried about safety')",
        "anchor_mid": "0.5 = balanced or unclear focus",
        "anchor_high": "0.9 = pure promotion ('I wanted to treat myself', 'looking for the best experience')",
    },
    "construal_fit_score": {
        "name": "Construal Level",
        "definition": "Was the buyer thinking abstractly (values, identity, big picture) or concretely (features, specs, price)?",
        "anchor_low": "0.1 = very concrete ('the car was a 2024 Suburban, pickup was at 3:15 PM')",
        "anchor_mid": "0.5 = mixed abstract and concrete",
        "anchor_high": "0.9 = very abstract ('it elevated the entire experience', 'this is what luxury should be')",
    },
    "personality_brand_alignment": {
        "name": "Personality-Brand Match",
        "definition": "Did the buyer feel the service's personality matched their own? Social orientation, warmth, formality.",
        "anchor_low": "0.1 = personality mismatch ('felt corporate and cold', 'not my vibe')",
        "anchor_mid": "0.5 = neutral or no personality signal",
        "anchor_high": "0.9 = strong match ('felt like they understood me', 'exactly my style')",
    },
    "emotional_resonance": {
        "name": "Emotional Depth",
        "definition": "How emotionally charged was this experience? Deep emotional engagement vs purely transactional.",
        "anchor_low": "0.1 = purely transactional ('car showed up, got to airport')",
        "anchor_mid": "0.5 = moderate emotional engagement",
        "anchor_high": "0.9 = deeply emotional ('brought tears to my eyes', 'made our wedding day perfect', 'devastating failure')",
    },
    "value_alignment": {
        "name": "Shared Values",
        "definition": "Did the buyer feel the service shared their values (quality, honesty, reliability, sustainability)?",
        "anchor_low": "0.1 = values conflict ('they clearly only care about money')",
        "anchor_mid": "0.5 = values not mentioned or neutral",
        "anchor_high": "0.9 = strong values match ('they genuinely care about their customers')",
    },
    "evolutionary_motive_match": {
        "name": "Primal Need Activation",
        "definition": "Which primal need was activated? Safety/survival, status/dominance, belonging/tribe, attraction/mating.",
        "anchor_low": "0.1 = minimal primal activation (routine, unemotional transaction)",
        "anchor_mid": "0.5 = moderate (some status or safety concern)",
        "anchor_high": "0.9 = strong primal activation ('I needed to protect my family', 'arrived like a VIP', 'wedding day arrival')",
    },
    "linguistic_style_matching": {
        "name": "Language Register Match",
        "definition": "Does the reviewer's language match formal/professional communication or casual/personal?",
        "anchor_low": "0.1 = very casual ('dude was awesome, totally recommend')",
        "anchor_mid": "0.5 = standard mixed register",
        "anchor_high": "0.9 = very formal ('impeccable service, exemplary professionalism')",
    },
    "spending_pain_match": {
        "name": "Loss Aversion / Price Sensitivity",
        "definition": "How much did price/cost/value factor into the experience? Did they feel pain or relief about spending?",
        "anchor_low": "0.1 = price irrelevant ('worth every penny, didnt even check the price')",
        "anchor_mid": "0.5 = price mentioned but not dominant",
        "anchor_high": "0.9 = price dominant ('overcharged', 'hidden fees', 'not worth the money', OR 'great value', 'transparent pricing')",
    },
    "reactance_fit": {
        "name": "Autonomy / Reactance",
        "definition": "Did the buyer feel in control of the experience or pressured/manipulated?",
        "anchor_low": "0.1 = felt fully in control, no pressure, empowered",
        "anchor_mid": "0.5 = neutral control dynamic",
        "anchor_high": "0.9 = felt pressured, manipulated, or autonomy violated ('forced to pay', 'no choice')",
    },
    "self_monitoring_fit": {
        "name": "Information Seeking",
        "definition": "Was the buyer in active research/evaluation mode or passive consumption?",
        "anchor_low": "0.1 = not researching (impulse booking, referred by friend)",
        "anchor_mid": "0.5 = moderate research",
        "anchor_high": "0.9 = heavy research ('compared 5 services', 'read every review', 'tested multiple options')",
    },
    "processing_route_match": {
        "name": "Cognitive Load Tolerance",
        "definition": "How much cognitive effort did the buyer invest? Detailed analysis vs quick decision?",
        "anchor_low": "0.1 = quick intuitive decision, minimal cognitive effort",
        "anchor_mid": "0.5 = moderate deliberation",
        "anchor_high": "0.9 = deep analysis ('evaluated every option', 'created a spreadsheet', 'spent hours researching')",
    },
    "mental_simulation_resonance": {
        "name": "Narrative Transport",
        "definition": "Does the review tell a STORY or just list facts? Was the buyer emotionally transported?",
        "anchor_low": "0.1 = pure facts ('driver was on time. car was clean.')",
        "anchor_mid": "0.5 = some narrative elements",
        "anchor_high": "0.9 = vivid story ('Picture this: its 4 AM, pouring rain, and our flight was canceled...')",
    },
    "optimal_distinctiveness_fit": {
        "name": "Social Proof Sensitivity",
        "definition": "How much did others' opinions matter to this buyer? Were they influenced by reviews, recommendations, popularity?",
        "anchor_low": "0.1 = made independent decision, didnt mention others",
        "anchor_mid": "0.5 = some social influence",
        "anchor_high": "0.9 = heavily socially influenced ('everyone recommended them', 'top rated', 'my friend uses them')",
    },
    "involvement_weight_modifier": {
        "name": "Temporal Urgency",
        "definition": "How urgent was the decision? Immediate need vs planned well in advance?",
        "anchor_low": "0.1 = planned months ahead ('booked for our June wedding in February')",
        "anchor_mid": "0.5 = moderate planning horizon",
        "anchor_high": "0.9 = immediate urgency ('needed a car in 30 minutes', 'last-minute flight change')",
    },
    "brand_trust_fit": {
        "name": "Brand Relationship Depth",
        "definition": "Is this a first-time user, repeat customer, or loyal advocate?",
        "anchor_low": "0.1 = first time, no prior relationship",
        "anchor_mid": "0.5 = used a few times",
        "anchor_high": "0.9 = deep loyalty ('been using them for years', 'only company I trust', 'cant imagine using anyone else')",
    },
    "identity_signaling_match": {
        "name": "Mimetic Desire / Aspiration",
        "definition": "Was the buyer motivated by wanting what others have? Status imitation? Keeping up?",
        "anchor_low": "0.1 = purely functional ('just needed a ride')",
        "anchor_mid": "0.5 = some aspirational element",
        "anchor_high": "0.9 = strongly aspirational ('wanted to arrive like a CEO', 'our wedding deserved the best')",
    },
    "anchor_susceptibility_match": {
        "name": "Sensory / Embodied Experience",
        "definition": "How much did physical/sensory details matter? Comfort, cleanliness, smell, temperature.",
        "anchor_low": "0.1 = sensory details not mentioned",
        "anchor_mid": "0.5 = some sensory mentions",
        "anchor_high": "0.9 = highly sensory ('leather seats were so comfortable', 'car smelled amazing', 'ice cold water waiting')",
    },
    "lay_theory_alignment": {
        "name": "Fairness / Reciprocity Orientation",
        "definition": "Did the buyer frame the experience in terms of fairness, value exchange, being treated right?",
        "anchor_low": "0.1 = fairness not relevant",
        "anchor_mid": "0.5 = some fairness framing",
        "anchor_high": "0.9 = strongly fairness-oriented ('got exactly what I paid for', 'felt ripped off', 'they went above and beyond')",
    },
    "negativity_bias_match": {
        "name": "Decision Difficulty / Entropy",
        "definition": "How hard was the decision? Were they torn between options? Confused by choices?",
        "anchor_low": "0.1 = easy, obvious decision ('no-brainer', 'immediately knew')",
        "anchor_mid": "0.5 = moderate difficulty",
        "anchor_high": "0.9 = very difficult ('agonized over the decision', 'went back and forth', 'almost didnt book')",
    },
    "persuasion_confidence_multiplier": {
        "name": "Persuadability / Openness to Influence",
        "definition": "How receptive was this buyer to being persuaded? Open to suggestion vs skeptical?",
        "anchor_low": "0.1 = highly skeptical, resistant to influence ('I dont trust ads', 'marketing doesnt work on me')",
        "anchor_mid": "0.5 = moderately open",
        "anchor_high": "0.9 = very persuadable ('the reviews convinced me', 'the guarantee sealed the deal')",
    },
}


def build_annotation_prompt(review_text: str, rating: int, company: str) -> str:
    """Build the comprehensive annotation prompt.

    Designed backwards from what the cascade consumes,
    using anchored scoring and contrastive framing.
    """
    # Build dimension definitions with anchors
    dim_definitions = []
    for prop_name, dim_info in ANNOTATION_DIMENSIONS.items():
        dim_definitions.append(
            f"  {prop_name} ({dim_info['name']}):\n"
            f"    {dim_info['definition']}\n"
            f"    {dim_info['anchor_low']}\n"
            f"    {dim_info['anchor_high']}"
        )
    dims_text = "\n".join(dim_definitions)

    prompt = f"""You are a psycholinguistic analyst annotating customer reviews for a bilateral graph database that predicts purchase behavior. Your annotations directly feed a mechanism-selection cascade used in real-time advertising.

REVIEW TO ANALYZE:
"{review_text}"
Rating: {rating}/5
Company: {company}

ANNOTATION TASK: Score this review on 20 psychological dimensions. Each score must be 0.0-1.0.

CRITICAL INSTRUCTIONS:
- Use CONTRASTIVE scoring: identify what makes this buyer DIFFERENT from a neutral 0.5 baseline. If the review gives no signal on a dimension, score exactly 0.5.
- Use the ANCHORED definitions below to calibrate your scores.
- Score from the BUYER'S perspective (what does this reveal about the buyer's psychology?), not the product's quality.
- Negative reviews are especially valuable — they reveal which psychological thresholds FAILED.

DIMENSIONS TO SCORE:
{dims_text}

ALSO EXTRACT:
- primary_mechanism: Which of these was the DOMINANT persuasion mechanism that drove (or would have driven) conversion? Choose ONE: authority, social_proof, loss_aversion, commitment, liking, cognitive_ease, reciprocity, scarcity, curiosity
- secondary_mechanism: Second most relevant mechanism
- buyer_archetype: corporate_executive, airport_anxiety, special_occasion, first_timer, repeat_loyal
- purchase_dance_stage: shopping (comparing), just_bought (justifying), repeat (loyal), churned (betrayed)
- regulatory_focus: prevention (avoiding bad outcomes) or promotion (seeking good outcomes)
- triggering_moment: The SINGLE thing that tipped the decision (string)
- anti_trigger: What almost stopped them or what broke the experience (string)
- ad_recommendation: If advertising to someone in this exact psychological state, what should the ad say? (string)

Return ONLY valid JSON with these exact keys:
{{
  "regulatory_fit_score": 0.0-1.0,
  "construal_fit_score": 0.0-1.0,
  "personality_brand_alignment": 0.0-1.0,
  "emotional_resonance": 0.0-1.0,
  "value_alignment": 0.0-1.0,
  "evolutionary_motive_match": 0.0-1.0,
  "linguistic_style_matching": 0.0-1.0,
  "spending_pain_match": 0.0-1.0,
  "reactance_fit": 0.0-1.0,
  "self_monitoring_fit": 0.0-1.0,
  "processing_route_match": 0.0-1.0,
  "mental_simulation_resonance": 0.0-1.0,
  "optimal_distinctiveness_fit": 0.0-1.0,
  "involvement_weight_modifier": 0.0-1.0,
  "brand_trust_fit": 0.0-1.0,
  "identity_signaling_match": 0.0-1.0,
  "anchor_susceptibility_match": 0.0-1.0,
  "lay_theory_alignment": 0.0-1.0,
  "negativity_bias_match": 0.0-1.0,
  "persuasion_confidence_multiplier": 0.0-1.0,
  "primary_mechanism": "string",
  "secondary_mechanism": "string",
  "buyer_archetype": "string",
  "purchase_dance_stage": "string",
  "regulatory_focus": "string",
  "triggering_moment": "string",
  "anti_trigger": "string",
  "ad_recommendation": "string"
}}"""

    return prompt


async def annotate_review(
    client,
    review_text: str,
    rating: int,
    company: str,
    model: str = "claude-haiku-4-5-20251001",
) -> Optional[Dict[str, Any]]:
    """Annotate a single review with the deep bilateral prompt."""
    prompt = build_annotation_prompt(review_text, rating, company)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        resp_text = response.content[0].text.strip()
        if resp_text.startswith("```"):
            resp_text = resp_text.split("\n", 1)[1].rsplit("```", 1)[0]

        result = json.loads(resp_text)

        # Validate: all 20 dimension scores should be present and 0-1
        for prop_name in ANNOTATION_DIMENSIONS:
            val = result.get(prop_name)
            if val is None:
                result[prop_name] = 0.5
            elif not isinstance(val, (int, float)):
                result[prop_name] = 0.5
            else:
                result[prop_name] = max(0.0, min(1.0, float(val)))

        return result

    except json.JSONDecodeError:
        logger.debug(f"JSON parse error for review")
        return None
    except Exception as e:
        logger.debug(f"Annotation error: {e}")
        return None


def compute_composite_alignment(annotation: Dict[str, Any]) -> float:
    """Compute composite alignment from the 20 dimension scores.

    Uses the same weighting as the cascade's composite_alignment
    computation for consistency.
    """
    core_dims = [
        "regulatory_fit_score", "construal_fit_score",
        "personality_brand_alignment", "emotional_resonance",
        "value_alignment", "evolutionary_motive_match",
        "linguistic_style_matching",
    ]

    total = 0.0
    count = 0
    for dim in core_dims:
        val = annotation.get(dim, 0.5)
        total += val
        count += 1

    return round(total / count, 4) if count > 0 else 0.5
