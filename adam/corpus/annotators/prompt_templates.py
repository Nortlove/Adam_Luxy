"""
Canonical prompt templates for all annotation pipelines.

SINGLE SOURCE OF TRUTH — all annotators and pipeline runners import from here.
Version-controlled so we can track prompt evolution and its impact on annotation quality.
"""

PROMPT_VERSION = "5.0"

# ─────────────────────────────────────────────────────────────────────
# Ad-Side (Product Description) Annotation
# ─────────────────────────────────────────────────────────────────────

AD_SIDE_SYSTEM_PROMPT = (
    "You are ADAM's psychological annotation engine. You score product descriptions "
    "against a comprehensive advertising psychology taxonomy. "
    "Return ONLY valid JSON — no markdown, no explanation, no commentary."
)

AD_SIDE_USER_PROMPT_TEMPLATE = """Score this product description against the advertising psychology taxonomy.

PRODUCT DESCRIPTION:
Title: {title}
Category: {category}
Price: {price}
Brand: {brand}
Description: {description_text}
Features: {features_text}

Score each construct on the indicated scale. Return ONLY the JSON object.
If a construct is not detectable in the text, use the default value (0.0 for intensities, 0.5 for spectrums). Confidence should reflect how clearly the text reveals this construct — 0.0 if guessing, 1.0 if unambiguous.

{{
  "annotation_confidence": <float 0-1>,
  "framing": {{
    "gain": <float 0-1, "achieve/enjoy/improve" language>,
    "loss": <float 0-1, "don't miss/protect/avoid" language>,
    "hedonic": <float 0-1, pleasure/enjoyment/experience focus>,
    "utilitarian": <float 0-1, function/efficiency/value focus>
  }},
  "appeals": {{
    "rational": <float 0-1>,
    "emotional": <float 0-1>,
    "fear": <float 0-1>,
    "narrative": <float 0-1>,
    "comparative": <float 0-1>
  }},
  "processing_targets": {{
    "construal_level": <float 0-1, 0=concrete "how" details, 1=abstract "why" vision>,
    "processing_route": <float 0-1, 0=peripheral cues, 1=central arguments>
  }},
  "persuasion_techniques": {{
    "social_proof": <float 0-1>,
    "scarcity": <float 0-1>,
    "authority": <float 0-1>,
    "reciprocity": <float 0-1>,
    "commitment": <float 0-1>,
    "liking": <float 0-1>,
    "anchoring": <float 0-1>,
    "storytelling": <float 0-1>
  }},
  "value_propositions": {{
    "performance": <float 0-1>,
    "convenience": <float 0-1>,
    "reliability": <float 0-1>,
    "cost": <float 0-1>,
    "pleasure": <float 0-1>,
    "peace_of_mind": <float 0-1>,
    "self_expression": <float 0-1>,
    "transformation": <float 0-1>,
    "status": <float 0-1>,
    "belonging": <float 0-1>,
    "social_responsibility": <float 0-1>,
    "novelty": <float 0-1>,
    "knowledge": <float 0-1>
  }},
  "brand_personality": {{
    "sincerity": <float 0-1>,
    "excitement": <float 0-1>,
    "competence": <float 0-1>,
    "sophistication": <float 0-1>,
    "ruggedness": <float 0-1>,
    "authenticity": <float 0-1>,
    "warmth": <float 0-1>
  }},
  "linguistic_style": {{
    "formality": <float 0-1>,
    "complexity": <float 0-1>,
    "emotional_tone": <float -1 to 1>,
    "directness": <float 0-1>
  }},
  "evolutionary_targets": {{
    "self_protection": <float 0-1>,
    "affiliation": <float 0-1>,
    "status": <float 0-1>,
    "mate_acquisition": <float 0-1>,
    "kin_care": <float 0-1>,
    "disease_avoidance": <float 0-1>
  }},
  "implicit_targets": {{
    "fluency": <float 0-1>,
    "embodied_cognition": <float 0-1>,
    "psychological_ownership": <float 0-1>,
    "nonconscious_goal": <float 0-1>
  }},
  "attachment_positioning": {{
    "warmth": <float 0-1, 0=transactional/distant, 1=intimate/relationship-focused>,
    "reassurance": <float 0-1, 0=confident/minimal guarantees, 1=heavy guarantees/safety nets>
  }},
  "agency_framing": {{
    "locus": <float 0-1, 0="experts recommend for you" authority, 1="you choose/you control" empowerment>
  }},
  "emotional_specificity": <float 0-1, 0=broad emotions like happy/great/amazing, 1=precise emotions like nostalgic pride/serene gratitude/tender relief>,
  "mental_simulation_vividness": <float 0-1, 0=abstract/factual copy, 1=vivid sensory language that helps reader picture themselves using/wearing/holding the product>,
  "social_visibility": <float 0-1, 0=private/personal product (supplements, cleaning), 1=publicly visible/identity-signaling product (fashion, accessories, car)>,
  "brand_trust_signals": {{
    "credibility_cues": <float 0-1, 0=no trust-building evidence, 1=strong credentials/certifications/guarantees>,
    "transparency": <float 0-1, 0=vague/evasive about ingredients/sourcing/process, 1=full disclosure/open about limitations>,
    "familiarity_leverage": <float 0-1, 0=unknown/new brand with no recognition cues, 1=leverages well-known brand heritage/recognition>
  }},
  "reactance_triggers": <float 0-1, 0=soft/informational persuasion, 1=aggressive pressure tactics that may trigger psychological resistance>,
  "anchor_deployment": <float 0-1, 0=no reference pricing/comparison, 1=heavy use of anchoring (was $X now $Y, compare to salon-quality, etc.)>,
  "contamination_risk_framing": <float 0-1, 0=no purity/safety messaging, 1=strong emphasis on purity/natural/clean/safe/non-toxic>
}}"""

# Condensed single-line version for batch API (functionally identical)
AD_SIDE_COMPACT_TEMPLATE = """Score this product description.

Title: {title}
Category: {category}
Price: {price}
Brand: {brand}
Description: {desc}
Features: {feats}

Return JSON:
{{"annotation_confidence":<0-1>,"framing":{{"gain":<0-1>,"loss":<0-1>,"hedonic":<0-1>,"utilitarian":<0-1>}},"appeals":{{"rational":<0-1>,"emotional":<0-1>,"fear":<0-1>,"narrative":<0-1>,"comparative":<0-1>}},"processing_targets":{{"construal_level":<0-1>,"processing_route":<0-1>}},"persuasion_techniques":{{"social_proof":<0-1>,"scarcity":<0-1>,"authority":<0-1>,"reciprocity":<0-1>,"commitment":<0-1>,"liking":<0-1>,"anchoring":<0-1>,"storytelling":<0-1>}},"value_propositions":{{"performance":<0-1>,"convenience":<0-1>,"reliability":<0-1>,"cost":<0-1>,"pleasure":<0-1>,"peace_of_mind":<0-1>,"self_expression":<0-1>,"transformation":<0-1>,"status":<0-1>,"belonging":<0-1>,"social_responsibility":<0-1>,"novelty":<0-1>,"knowledge":<0-1>}},"brand_personality":{{"sincerity":<0-1>,"excitement":<0-1>,"competence":<0-1>,"sophistication":<0-1>,"ruggedness":<0-1>,"authenticity":<0-1>,"warmth":<0-1>}},"linguistic_style":{{"formality":<0-1>,"complexity":<0-1>,"emotional_tone":<-1 to 1>,"directness":<0-1>}},"evolutionary_targets":{{"self_protection":<0-1>,"affiliation":<0-1>,"status":<0-1>,"mate_acquisition":<0-1>,"kin_care":<0-1>,"disease_avoidance":<0-1>}},"implicit_targets":{{"fluency":<0-1>,"embodied_cognition":<0-1>,"psychological_ownership":<0-1>,"nonconscious_goal":<0-1>}},"attachment_positioning":{{"warmth":<0-1>,"reassurance":<0-1>}},"agency_framing":{{"locus":<0-1>}},"emotional_specificity":<0-1>,"mental_simulation_vividness":<0-1>,"social_visibility":<0-1>,"brand_trust_signals":{{"credibility_cues":<0-1>,"transparency":<0-1>,"familiarity_leverage":<0-1>}},"reactance_triggers":<0-1>,"anchor_deployment":<0-1>,"contamination_risk_framing":<0-1>}}"""


# ─────────────────────────────────────────────────────────────────────
# Dual Annotation (Review -> User-Side + Peer-Ad-Side)
# ─────────────────────────────────────────────────────────────────────

DUAL_SYSTEM_PROMPT = (
    "You are ADAM's psychological annotation engine. You analyze Amazon reviews "
    "from TWO simultaneous perspectives and return structured JSON scores. "
    "Return ONLY valid JSON — no markdown, no explanation."
)

DUAL_PROMPT_TEMPLATE = """This Amazon review serves TWO functions and must be scored on BOTH.

REVIEW CONTEXT:
Product: {product_title}
Category: {category}
Star Rating: {star_rating}/5
Helpful Votes: {helpful_votes}
Verified Purchase: Yes

REVIEW TEXT:
{review_text}

FUNCTION 1 — AUTHOR PSYCHOLOGY (what does this reveal about the person who WROTE it?):
Score the reviewer's psychological profile as expressed through their natural language.

FUNCTION 2 — PERSUASION CONTENT (what psychological techniques does this deploy toward FUTURE READERS?):
Score as if this review were an advertisement aimed at the next buyer.

Return ONLY the JSON object with both analyses.

{{
  "user_side": {{
    "annotation_confidence": <float 0-1>,
    "personality": {{
      "openness": <float 0-1>,
      "conscientiousness": <float 0-1>,
      "extraversion": <float 0-1>,
      "agreeableness": <float 0-1>,
      "neuroticism": <float 0-1>,
      "confidence_openness": <float 0-1>,
      "confidence_conscientiousness": <float 0-1>,
      "confidence_extraversion": <float 0-1>,
      "confidence_agreeableness": <float 0-1>,
      "confidence_neuroticism": <float 0-1>
    }},
    "regulatory_focus": {{
      "promotion": <float 0-1>,
      "prevention": <float 0-1>
    }},
    "decision_style": {{
      "maximizer": <float 0-1>,
      "impulse": <float 0-1>,
      "information_search_depth": <float 0-1>
    }},
    "construal_level": <float 0-1>,
    "need_for_cognition": <float 0-1>,
    "evolutionary_motives": {{
      "self_protection": <float 0-1>,
      "affiliation": <float 0-1>,
      "status": <float 0-1>,
      "mate_acquisition": <float 0-1>,
      "kin_care": <float 0-1>,
      "disease_avoidance": <float 0-1>
    }},
    "mechanisms_cited": {{
      "social_proof": <float 0-1>,
      "authority": <float 0-1>,
      "scarcity": <float 0-1>,
      "reciprocity": <float 0-1>,
      "commitment": <float 0-1>,
      "liking": <float 0-1>
    }},
    "emotion": {{
      "pleasure": <float -1 to 1>,
      "arousal": <float 0-1>,
      "dominance": <float 0-1>,
      "primary_emotions": [<up to 3 Plutchik emotions>]
    }},
    "stated_purchase_reason": "<string>",
    "implicit_drivers": {{
      "compensatory": <float 0-1>,
      "identity_signaling": <float 0-1>,
      "wanting_over_liking": <float 0-1>
    }},
    "lay_theories": {{
      "price_quality": <float 0-1>,
      "natural_goodness": <float 0-1>,
      "effort_quality": <float 0-1>,
      "scarcity_value": <float 0-1>
    }},
    "attachment_style": {{
      "anxiety": <float 0-1, need for reassurance/fear of abandonment/brand dependency>,
      "avoidance": <float 0-1, preference for independence/discomfort with brand intimacy>
    }},
    "locus_of_control": <float 0-1, 0=external (fate/luck/experts decide), 1=internal (I control outcomes)>,
    "emotional_granularity": <float 0-1, 0=broad undifferentiated emotions, 1=precise differentiated emotional vocabulary>,
    "linguistic_style": {{
      "formality": <float 0-1, 0=casual/slang, 1=formal/proper>,
      "complexity": <float 0-1, 0=simple short sentences, 1=complex/nested/long>,
      "emotional_expressiveness": <float 0-1, 0=restrained/factual, 1=effusive/emotional>,
      "directness": <float 0-1, 0=hedging/qualified, 1=assertive/definitive>
    }},
    "uniqueness_need": {{
      "creative_choice": <float 0-1, uses products in innovative/unusual ways>,
      "unpopular_choice": <float 0-1, deliberately selects non-mainstream options>,
      "avoidance_of_similarity": <float 0-1, actively avoids what's popular/common>
    }},
    "purchase_involvement": <float 0-1, 0=low-effort/casual purchase, 1=high-deliberation/researched extensively>,
    "anticipated_regret": <float 0-1, 0=no regret concern, 1=strong fear of making wrong choice>,
    "negativity_seeking": <float 0-1, 0=focus on positives, 1=actively sought/weighted negative info>,
    "negativity_bias": <float 0-1, 0=positive info weighted equally, 1=negative info weighted far more heavily in decision>,
    "reactance": <float 0-1, 0=receptive to persuasion/recommendations, 1=resistant to perceived manipulation/strong counter-arguing>,
    "optimal_distinctiveness": <float 0-1, 0=pure conformity/wants what everyone has, 1=strong need to simultaneously belong AND differentiate>,
    "brand_trust": {{
      "known_brand_trust": <float 0-1, 0=skeptical even of known brands, 1=high trust in established brands>,
      "unknown_brand_skepticism": <float 0-1, 0=open to unknown brands, 1=strong avoidance of unfamiliar brands>,
      "review_reliance": <float 0-1, 0=trusts brand claims directly, 1=relies heavily on peer reviews over brand statements>
    }},
    "self_monitoring": <float 0-1, 0=low self-monitoring (acts on internal states), 1=high self-monitoring (adapts to social cues/image-conscious)>,
    "spending_pain_sensitivity": <float 0-1, 0=spendthrift (spending causes no pain), 1=tightwad (strong pain-of-paying)>,
    "disgust_sensitivity": <float 0-1, 0=low contamination concern, 1=high sensitivity to purity/contamination/chemical ingredients>,
    "anchor_susceptibility": <float 0-1, 0=ignores reference prices/comparisons, 1=heavily influenced by initial anchors/reference points>,
    "mental_ownership_strength": <float 0-1, 0=no imagined possession language, 1=strong endowment effect (already talks about product as "mine"/imagines using it)>
  }},
  "peer_ad_side": {{
    "annotation_confidence": <float 0-1>,
    "testimonial_authenticity": <float 0-1>,
    "relatable_vulnerability": <float 0-1>,
    "outcome_specificity": <float 0-1>,
    "outcome_timeline": <float 0-1>,
    "before_after_narrative": <float 0-1>,
    "risk_resolution": {{
      "financial": <float 0-1>,
      "performance": <float 0-1>,
      "social": <float 0-1>,
      "durability": <float 0-1>
    }},
    "use_case_matching": <float 0-1>,
    "social_proof_amplification": <float 0-1>,
    "objection_preemption": <float 0-1>,
    "domain_expertise_signals": <float 0-1>,
    "comparative_depth": <float 0-1>,
    "emotional_contagion_potency": <float 0-1>,
    "narrative_arc_completeness": <float 0-1>,
    "resolved_anxiety_narrative": <float 0-1>,
    "recommendation_strength": <float 0-1>,
    "mental_simulation_enablement": <float 0-1, 0=abstract/generic, 1=vivid details that help reader picture the experience>,
    "negative_diagnosticity": <float 0-1, 0=vague complaint/noise, 1=highly informative specific problem identification>
  }},
  "conversion_outcome": "<one of: satisfied, neutral, regret, evangelized, warned>"
}}"""

# Condensed version for batch API
DUAL_COMPACT_TEMPLATE = """Score this review from TWO perspectives.

Product: {title}  Category: {cat}  Rating: {rating}/5  Helpful: {helpful}  Verified: Yes

REVIEW: {text}

Perspective 1 (AUTHOR): What does this reveal about the reviewer's psychology?
Perspective 2 (PERSUASION): How does this function as persuasion for future readers?

{{"user_side":{{"annotation_confidence":<0-1>,"personality":{{"openness":<0-1>,"conscientiousness":<0-1>,"extraversion":<0-1>,"agreeableness":<0-1>,"neuroticism":<0-1>,"confidence_openness":<0-1>,"confidence_conscientiousness":<0-1>,"confidence_extraversion":<0-1>,"confidence_agreeableness":<0-1>,"confidence_neuroticism":<0-1>}},"regulatory_focus":{{"promotion":<0-1>,"prevention":<0-1>}},"decision_style":{{"maximizer":<0-1>,"impulse":<0-1>,"information_search_depth":<0-1>}},"construal_level":<0-1>,"need_for_cognition":<0-1>,"evolutionary_motives":{{"self_protection":<0-1>,"affiliation":<0-1>,"status":<0-1>,"mate_acquisition":<0-1>,"kin_care":<0-1>,"disease_avoidance":<0-1>}},"mechanisms_cited":{{"social_proof":<0-1>,"authority":<0-1>,"scarcity":<0-1>,"reciprocity":<0-1>,"commitment":<0-1>,"liking":<0-1>}},"emotion":{{"pleasure":<-1 to 1>,"arousal":<0-1>,"dominance":<0-1>,"primary_emotions":["up to 3"]}},"stated_purchase_reason":"<string>","implicit_drivers":{{"compensatory":<0-1>,"identity_signaling":<0-1>,"wanting_over_liking":<0-1>}},"lay_theories":{{"price_quality":<0-1>,"natural_goodness":<0-1>,"effort_quality":<0-1>,"scarcity_value":<0-1>}},"attachment_style":{{"anxiety":<0-1>,"avoidance":<0-1>}},"locus_of_control":<0-1>,"emotional_granularity":<0-1>,"linguistic_style":{{"formality":<0-1>,"complexity":<0-1>,"emotional_expressiveness":<0-1>,"directness":<0-1>}},"uniqueness_need":{{"creative_choice":<0-1>,"unpopular_choice":<0-1>,"avoidance_of_similarity":<0-1>}},"purchase_involvement":<0-1>,"anticipated_regret":<0-1>,"negativity_seeking":<0-1>,"negativity_bias":<0-1>,"reactance":<0-1>,"optimal_distinctiveness":<0-1>,"brand_trust":{{"known_brand_trust":<0-1>,"unknown_brand_skepticism":<0-1>,"review_reliance":<0-1>}},"self_monitoring":<0-1>,"spending_pain_sensitivity":<0-1>,"disgust_sensitivity":<0-1>,"anchor_susceptibility":<0-1>,"mental_ownership_strength":<0-1>}},"peer_ad_side":{{"annotation_confidence":<0-1>,"testimonial_authenticity":<0-1>,"relatable_vulnerability":<0-1>,"outcome_specificity":<0-1>,"outcome_timeline":<0-1>,"before_after_narrative":<0-1>,"risk_resolution":{{"financial":<0-1>,"performance":<0-1>,"social":<0-1>,"durability":<0-1>}},"use_case_matching":<0-1>,"social_proof_amplification":<0-1>,"objection_preemption":<0-1>,"domain_expertise_signals":<0-1>,"comparative_depth":<0-1>,"emotional_contagion_potency":<0-1>,"narrative_arc_completeness":<0-1>,"resolved_anxiety_narrative":<0-1>,"recommendation_strength":<0-1>,"mental_simulation_enablement":<0-1>,"negative_diagnosticity":<0-1>}},"conversion_outcome":"<satisfied|neutral|regret|evangelized|warned>"}}"""


# ─────────────────────────────────────────────────────────────────────
# User-Only Annotation (reviews that don't qualify for peer-ad)
# ─────────────────────────────────────────────────────────────────────

USER_ONLY_PROMPT_TEMPLATE = """Score the reviewer's psychological profile as expressed through their natural language.

REVIEW CONTEXT:
Product: {product_title}
Category: {category}
Star Rating: {star_rating}/5
Helpful Votes: {helpful_votes}
Verified Purchase: Yes

REVIEW TEXT:
{review_text}

Return ONLY the JSON object.

{{
  "annotation_confidence": <float 0-1>,
  "personality": {{
    "openness": <float 0-1>,
    "conscientiousness": <float 0-1>,
    "extraversion": <float 0-1>,
    "agreeableness": <float 0-1>,
    "neuroticism": <float 0-1>,
    "confidence_openness": <float 0-1>,
    "confidence_conscientiousness": <float 0-1>,
    "confidence_extraversion": <float 0-1>,
    "confidence_agreeableness": <float 0-1>,
    "confidence_neuroticism": <float 0-1>
  }},
  "regulatory_focus": {{
    "promotion": <float 0-1>,
    "prevention": <float 0-1>
  }},
  "decision_style": {{
    "maximizer": <float 0-1>,
    "impulse": <float 0-1>,
    "information_search_depth": <float 0-1>
  }},
  "construal_level": <float 0-1>,
  "need_for_cognition": <float 0-1>,
  "evolutionary_motives": {{
    "self_protection": <float 0-1>,
    "affiliation": <float 0-1>,
    "status": <float 0-1>,
    "mate_acquisition": <float 0-1>,
    "kin_care": <float 0-1>,
    "disease_avoidance": <float 0-1>
  }},
  "mechanisms_cited": {{
    "social_proof": <float 0-1>,
    "authority": <float 0-1>,
    "scarcity": <float 0-1>,
    "reciprocity": <float 0-1>,
    "commitment": <float 0-1>,
    "liking": <float 0-1>
  }},
  "emotion": {{
    "pleasure": <float -1 to 1>,
    "arousal": <float 0-1>,
    "dominance": <float 0-1>,
    "primary_emotions": [<up to 3 Plutchik emotions>]
  }},
  "stated_purchase_reason": "<string>",
  "implicit_drivers": {{
    "compensatory": <float 0-1>,
    "identity_signaling": <float 0-1>,
    "wanting_over_liking": <float 0-1>
  }},
  "lay_theories": {{
    "price_quality": <float 0-1>,
    "natural_goodness": <float 0-1>,
    "effort_quality": <float 0-1>,
    "scarcity_value": <float 0-1>
  }},
  "attachment_style": {{
    "anxiety": <float 0-1, need for reassurance/fear of abandonment/brand dependency>,
    "avoidance": <float 0-1, preference for independence/discomfort with brand intimacy>
  }},
  "locus_of_control": <float 0-1, 0=external (fate/luck/experts decide), 1=internal (I control outcomes)>,
  "emotional_granularity": <float 0-1, 0=broad undifferentiated emotions, 1=precise differentiated emotional vocabulary>,
  "linguistic_style": {{
    "formality": <float 0-1, 0=casual/slang, 1=formal/proper>,
    "complexity": <float 0-1, 0=simple short sentences, 1=complex/nested/long>,
    "emotional_expressiveness": <float 0-1, 0=restrained/factual, 1=effusive/emotional>,
    "directness": <float 0-1, 0=hedging/qualified, 1=assertive/definitive>
  }},
  "uniqueness_need": {{
    "creative_choice": <float 0-1, uses products in innovative/unusual ways>,
    "unpopular_choice": <float 0-1, deliberately selects non-mainstream options>,
    "avoidance_of_similarity": <float 0-1, actively avoids what's popular/common>
  }},
  "purchase_involvement": <float 0-1, 0=low-effort/casual purchase, 1=high-deliberation/researched extensively>,
  "anticipated_regret": <float 0-1, 0=no regret concern, 1=strong fear of making wrong choice>,
  "negativity_seeking": <float 0-1, 0=focus on positives, 1=actively sought/weighted negative info>,
  "negativity_bias": <float 0-1, 0=positive info weighted equally, 1=negative info weighted far more heavily in decision>,
  "reactance": <float 0-1, 0=receptive to persuasion/recommendations, 1=resistant to perceived manipulation/strong counter-arguing>,
  "optimal_distinctiveness": <float 0-1, 0=pure conformity/wants what everyone has, 1=strong need to simultaneously belong AND differentiate>,
  "brand_trust": {{
    "known_brand_trust": <float 0-1, 0=skeptical even of known brands, 1=high trust in established brands>,
    "unknown_brand_skepticism": <float 0-1, 0=open to unknown brands, 1=strong avoidance of unfamiliar brands>,
    "review_reliance": <float 0-1, 0=trusts brand claims directly, 1=relies heavily on peer reviews over brand statements>
  }},
  "self_monitoring": <float 0-1, 0=low self-monitoring (acts on internal states), 1=high self-monitoring (adapts to social cues/image-conscious)>,
  "spending_pain_sensitivity": <float 0-1, 0=spendthrift (spending causes no pain), 1=tightwad (strong pain-of-paying)>,
  "disgust_sensitivity": <float 0-1, 0=low contamination concern, 1=high sensitivity to purity/contamination/chemical ingredients>,
  "anchor_susceptibility": <float 0-1, 0=ignores reference prices/comparisons, 1=heavily influenced by initial anchors/reference points>,
  "mental_ownership_strength": <float 0-1, 0=no imagined possession language, 1=strong endowment effect (already talks about product as "mine"/imagines using it)>,
  "conversion_outcome": "<one of: satisfied, neutral, regret, evangelized, warned>"
}}"""

# Condensed version for batch API
USER_ONLY_COMPACT_TEMPLATE = """Score the reviewer's psychological profile.

Product: {title}  Category: {cat}  Rating: {rating}/5  Helpful: {helpful}  Verified: Yes

REVIEW: {text}

{{"annotation_confidence":<0-1>,"personality":{{"openness":<0-1>,"conscientiousness":<0-1>,"extraversion":<0-1>,"agreeableness":<0-1>,"neuroticism":<0-1>,"confidence_openness":<0-1>,"confidence_conscientiousness":<0-1>,"confidence_extraversion":<0-1>,"confidence_agreeableness":<0-1>,"confidence_neuroticism":<0-1>}},"regulatory_focus":{{"promotion":<0-1>,"prevention":<0-1>}},"decision_style":{{"maximizer":<0-1>,"impulse":<0-1>,"information_search_depth":<0-1>}},"construal_level":<0-1>,"need_for_cognition":<0-1>,"evolutionary_motives":{{"self_protection":<0-1>,"affiliation":<0-1>,"status":<0-1>,"mate_acquisition":<0-1>,"kin_care":<0-1>,"disease_avoidance":<0-1>}},"mechanisms_cited":{{"social_proof":<0-1>,"authority":<0-1>,"scarcity":<0-1>,"reciprocity":<0-1>,"commitment":<0-1>,"liking":<0-1>}},"emotion":{{"pleasure":<-1 to 1>,"arousal":<0-1>,"dominance":<0-1>,"primary_emotions":["up to 3"]}},"stated_purchase_reason":"<string>","implicit_drivers":{{"compensatory":<0-1>,"identity_signaling":<0-1>,"wanting_over_liking":<0-1>}},"lay_theories":{{"price_quality":<0-1>,"natural_goodness":<0-1>,"effort_quality":<0-1>,"scarcity_value":<0-1>}},"attachment_style":{{"anxiety":<0-1>,"avoidance":<0-1>}},"locus_of_control":<0-1>,"emotional_granularity":<0-1>,"linguistic_style":{{"formality":<0-1>,"complexity":<0-1>,"emotional_expressiveness":<0-1>,"directness":<0-1>}},"uniqueness_need":{{"creative_choice":<0-1>,"unpopular_choice":<0-1>,"avoidance_of_similarity":<0-1>}},"purchase_involvement":<0-1>,"anticipated_regret":<0-1>,"negativity_seeking":<0-1>,"negativity_bias":<0-1>,"reactance":<0-1>,"optimal_distinctiveness":<0-1>,"brand_trust":{{"known_brand_trust":<0-1>,"unknown_brand_skepticism":<0-1>,"review_reliance":<0-1>}},"self_monitoring":<0-1>,"spending_pain_sensitivity":<0-1>,"disgust_sensitivity":<0-1>,"anchor_susceptibility":<0-1>,"mental_ownership_strength":<0-1>,"conversion_outcome":"<satisfied|neutral|regret|evangelized|warned>"}}"""
