# iHeartMedia Psycholinguistic Advertising Graph Database

## Overview

This Neo4j graph database is designed for psycholinguistic advertising optimization. It models the **State-Behavior-Traits (SBT)** framework plus **nonconscious analytics** to enable:

1. **Emotional State Matching**: Align ad emotional tone with show-induced listener states
2. **Behavioral Tendency Targeting**: Match products to listener action propensities  
3. **Personality Trait Alignment**: Target audiences based on Big Five and advertising-relevant traits
4. **Persuasion Technique Optimization**: Select the most effective persuasion approach per channel
5. **Temporal Optimization**: Time ads for maximum receptivity based on time slot psychology

---

## Graph Schema Architecture

### Node Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CORE CONTENT NODES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Network ──owns──> Station ──broadcasts──> Show ──has_segment──> Segment   │
│                       │                      │                              │
│                       │                      └──hosted_by──> Host           │
│                       │                      └──covers_topic──> Topic       │
│                       │                      └──airs_during──> TimeSlot     │
│                       │                                                     │
│                       ├──has_format──> Format                               │
│                       └──in_market──> Market                                │
│                                                                             │
│  PodcastNetwork ──contains──> Podcast ──hosted_by──> Host                  │
│                                  └──covers_topic──> Topic                   │
│                                                                             │
│  Event (Annual events like Jingle Ball, iHeartRadio Music Festival)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      PSYCHOLINGUISTIC TAXONOMY NODES                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ EmotionalState  │    │    Mindset      │    │ BehavioralTend. │         │
│  │ (STATE dim.)    │    │  (STATE dim.)   │    │ (BEHAVIOR dim.) │         │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤         │
│  │ • excitement    │    │ • learning      │    │ • impulsive     │         │
│  │ • joy           │    │ • entertainment │    │ • deliberate    │         │
│  │ • nostalgia     │    │ • escapism      │    │ • social_sharing│         │
│  │ • fear          │    │ • info_seeking  │    │ • brand_loyalty │         │
│  │ • trust         │    │ • relaxation    │    │ • early_adoption│         │
│  │ • (20 total)    │    │ • (12 total)    │    │ • (14 total)    │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │     Urge        │    │PersonalityTrait │    │ CognitiveStyle  │         │
│  │ (BEHAVIOR dim.) │    │ (TRAITS dim.)   │    │ (TRAITS dim.)   │         │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤         │
│  │ • purchase      │    │ • openness_high │    │ • analytical    │         │
│  │ • share_content │    │ • extraversion  │    │ • intuitive     │         │
│  │ • learn_more    │    │ • agreeableness │    │ • visual        │         │
│  │ • connect       │    │ • need_for_cog  │    │ • sequential    │         │
│  │ • escape        │    │ • sensation_sk  │    │ • reflective    │         │
│  │ • (14 total)    │    │ • (16 total)    │    │ • (11 total)    │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                                │
│  │PersuasionTech.  │    │   TimeSlot      │                                │
│  │ (AD STRATEGY)   │    │ (TEMPORAL)      │                                │
│  ├─────────────────┤    ├─────────────────┤                                │
│  │ • reciprocity   │    │ • early_morning │                                │
│  │ • social_proof  │    │ • morning_drive │                                │
│  │ • authority     │    │ • late_morning  │                                │
│  │ • scarcity      │    │ • evening_drive │                                │
│  │ • storytelling  │    │ • late_night    │                                │
│  │ • (15 total)    │    │ • (12 total)    │                                │
│  └─────────────────┘    └─────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Relationship Types with Properties

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PSYCHOLINGUISTIC RELATIONSHIPS                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Show/Podcast/Station ──[EVOKES_STATE]──> EmotionalState                   │
│                         {intensity: 0.0-1.0, source: string}               │
│                                                                             │
│  Show/Podcast/Station ──[CREATES_MINDSET]──> Mindset                       │
│                         {strength: 0.0-1.0, source: string}                │
│                                                                             │
│  Show/Podcast/Station ──[TRIGGERS_BEHAVIOR]──> BehavioralTendency          │
│                         {likelihood: 0.0-1.0, source: string}              │
│                                                                             │
│  Show/Podcast/Station ──[INDUCES_URGE]──> Urge                             │
│                         {potency: 0.0-1.0, source: string}                 │
│                                                                             │
│  Show/Podcast/Station ──[ATTRACTS_TRAIT]──> PersonalityTrait               │
│                         {correlation: 0.0-1.0, source: string}             │
│                                                                             │
│  Show/Podcast/Station ──[ENGAGES_COGNITIVE]──> CognitiveStyle              │
│                         {alignment: 0.0-1.0, source: string}               │
│                                                                             │
│  Show/Podcast/Station ──[RECEPTIVE_TO]──> PersuasionTechnique              │
│                         {effectiveness: 0.0-1.0, source: string}           │
│                                                                             │
│  Show ──[AIRS_DURING]──> TimeSlot                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Psycholinguistic Dimensions Explained

### STATE Dimension

**Emotional States** (Valence-Arousal Model)
| State | Valence | Arousal | Category | Ad Applications |
|-------|---------|---------|----------|-----------------|
| excitement | +0.8 | 0.9 | positive_high | Entertainment, events, launches |
| joy | +0.9 | 0.7 | positive_high | Celebrations, gifts, lifestyle |
| contentment | +0.7 | 0.3 | positive_low | Comfort products, home goods |
| nostalgia | +0.5 | 0.4 | mixed | Heritage brands, reunions |
| fear | -0.7 | 0.8 | negative_high | Insurance, security, health |
| trust | +0.6 | 0.3 | social | Financial services, healthcare |

**Mindsets** (Cognitive State During Consumption)
| Mindset | Openness | Focus | Receptivity | Best For |
|---------|----------|-------|-------------|----------|
| learning | 0.9 | 0.8 | 0.9 | Educational products, courses |
| entertainment | 0.7 | 0.4 | 0.6 | Consumer goods, entertainment |
| information_seeking | 0.8 | 0.9 | 0.8 | High-consideration purchases |
| commute_routine | 0.5 | 0.3 | 0.6 | Convenience, fast food |

### BEHAVIOR Dimension

**Behavioral Tendencies**
| Tendency | Description | Product Fit |
|----------|-------------|-------------|
| impulsive_action | Act quickly without deliberation | Limited offers, flash sales |
| deliberate_consideration | Research before purchasing | High-ticket items, B2B |
| social_sharing | Share discoveries with others | Viral products, experiences |
| brand_loyalty | Stick with known brands | Established brands, subscriptions |
| early_adoption | Try new things first | Tech, innovation, beta products |
| variety_seeking | Constantly try new things | New flavors, line extensions |

**Urges** (Action Impulses)
| Urge | Conversion Potential | Trigger Strategy |
|------|---------------------|------------------|
| purchase_intent | 0.9 | Direct response ads |
| brand_discovery | 0.4 | Awareness campaigns |
| share_content | 0.8 (viral) | Shareable content |
| learn_more | 0.7 | Content marketing |
| self_improvement | 0.8 | Aspirational messaging |

### TRAITS Dimension

**Personality Traits** (Big Five Extended)
| Trait | Level | Ad Response Pattern |
|-------|-------|---------------------|
| openness_high | High | Responds to novel, creative ads |
| openness_low | Low | Prefers familiar, proven products |
| extraversion_high | High | Social proof, testimonials effective |
| extraversion_low | Low | Quiet, personal appeals work better |
| need_for_cognition | High | Detailed, rational arguments |
| sensation_seeking | High | Exciting, intense imagery |
| materialism | High | Status symbols, luxury positioning |

**Cognitive Styles**
| Style | Processing | Best Ad Format |
|-------|------------|----------------|
| analytical | Systematic, deep | Data-driven, comparison |
| intuitive | Holistic, fast | Emotional, imagery-driven |
| visual | Image-preference | Rich media, video |
| verbal | Word-preference | Copywriting, podcasts |

---

## Persuasion Technique Mapping

| Technique | Principle | Best Content Match |
|-----------|-----------|-------------------|
| **reciprocity** | Give to receive | Shows with community focus |
| **commitment_consistency** | Small-to-large asks | Loyalty program content |
| **social_proof** | Others are doing it | High-listener shows, pop formats |
| **authority** | Expert endorsement | News, educational content |
| **liking** | Similar/attractive source | Celebrity hosts, AC format |
| **scarcity** | Limited availability | Morning shows (commute urgency) |
| **unity** | Shared identity | Country, Urban formats |
| **storytelling** | Narrative transport | True crime, Lore-style pods |
| **humor** | Entertainment | Comedy podcasts, morning shows |
| **fear_appeal** | Threat + solution | News/talk, true crime |
| **aspiration** | Ideal self | Celebrity content, lifestyle |
| **nostalgia** | Past connection | Classic rock, country |

---

## Usage Examples

### Installation

```bash
# Install dependencies
pip install neo4j

# Run the loader
python iheart_neo4j_psycholinguistics.py \
    --uri bolt://localhost:7687 \
    --username neo4j \
    --password your_password \
    --catalog iheart_complete_catalog.json \
    --clear  # Optional: clear existing data first
```

### Example Ad Targeting Scenarios

#### Scenario 1: Energy Drink Launch
**Goal**: Reach young, high-energy audiences receptive to excitement messaging

```cypher
MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState {name: 'excitement'})
MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait {name: 'sensation_seeking'})
MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique {name: 'scarcity'})
WHERE ev.intensity > 0.7 AND at.correlation > 0.6
RETURN s.name, labels(s)[0] AS type,
       ev.intensity AS excitement,
       at.correlation AS sensation_seeking,
       rt.effectiveness AS scarcity_receptivity
ORDER BY ev.intensity * at.correlation DESC
LIMIT 10;
```

#### Scenario 2: Financial Services (High-Consideration)
**Goal**: Reach analytical thinkers in information-seeking mindset

```cypher
MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait {name: 'need_for_cognition'})
MATCH (s)-[cm:CREATES_MINDSET]->(m:Mindset {name: 'information_seeking'})
MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique {name: 'authority'})
WHERE at.correlation > 0.7 AND cm.strength > 0.7
RETURN s.name, labels(s)[0] AS type,
       at.correlation AS cognition_match,
       cm.strength AS info_seeking,
       rt.effectiveness AS authority_receptivity
ORDER BY at.correlation + cm.strength DESC;
```

#### Scenario 3: Heritage Brand Nostalgia Campaign
**Goal**: Evoke nostalgia in loyal, tradition-valuing audiences

```cypher
MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState {name: 'nostalgia'})
MATCH (s)-[tb:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency {name: 'brand_loyalty'})
MATCH (s)-[:AIRS_DURING]->(t:TimeSlot)
WHERE ev.intensity > 0.6 AND tb.likelihood > 0.6
RETURN s.name, t.name AS time_slot, t.hours,
       ev.intensity AS nostalgia_intensity,
       tb.likelihood AS loyalty_likelihood
ORDER BY ev.intensity * tb.likelihood DESC;
```

#### Scenario 4: Viral Product Launch
**Goal**: Reach social sharers with high early-adoption tendency

```cypher
MATCH (s)-[tb1:TRIGGERS_BEHAVIOR]->(b1:BehavioralTendency {name: 'social_sharing'})
MATCH (s)-[tb2:TRIGGERS_BEHAVIOR]->(b2:BehavioralTendency {name: 'early_adoption'})
MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait {name: 'extraversion_high'})
WHERE tb1.likelihood > 0.6 AND tb2.likelihood > 0.6
RETURN s.name, labels(s)[0] AS type,
       tb1.likelihood AS sharing,
       tb2.likelihood AS early_adoption,
       at.correlation AS extraversion
ORDER BY tb1.likelihood + tb2.likelihood DESC;
```

#### Scenario 5: Complete Psycholinguistic Profile Query
**Goal**: Get full SBT profile for a specific show for ad planning

```cypher
MATCH (s:Show {name: 'The Breakfast Club'})
OPTIONAL MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState)
OPTIONAL MATCH (s)-[cm:CREATES_MINDSET]->(m:Mindset)
OPTIONAL MATCH (s)-[tb:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency)
OPTIONAL MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
OPTIONAL MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique)
OPTIONAL MATCH (s)-[:AIRS_DURING]->(t:TimeSlot)
RETURN s.name,
       COLLECT(DISTINCT {state: e.name, intensity: ev.intensity}) AS emotions,
       COLLECT(DISTINCT {mindset: m.name, strength: cm.strength}) AS mindsets,
       COLLECT(DISTINCT {behavior: b.name, likelihood: tb.likelihood}) AS behaviors,
       COLLECT(DISTINCT {trait: p.name, correlation: at.correlation}) AS traits,
       COLLECT(DISTINCT {technique: pt.name, effectiveness: rt.effectiveness}) AS persuasion,
       COLLECT(DISTINCT t.name) AS time_slots;
```

---

## Extending the Model

### Adding Vector Embeddings
The schema stores full descriptions on nodes specifically to enable vector embedding:

```python
# Extract descriptions for embedding
MATCH (s:Show)
RETURN s.id, s.name, s.description

# After embedding, add to nodes
MATCH (s:Show {id: $id})
SET s.embedding = $vector_array
```

### Adding Brand/Product Nodes
Extend the schema with Brand and Product nodes:

```cypher
CREATE (b:Brand {name: 'Nike', industry: 'Sportswear'})
SET b.target_emotions = ['excitement', 'inspiration', 'empowerment']
SET b.target_traits = ['sensation_seeking', 'extraversion_high']
SET b.preferred_persuasion = ['aspiration', 'social_proof']

// Then query for matches
MATCH (b:Brand {name: 'Nike'})
MATCH (s:Show)-[ev:EVOKES_STATE]->(e:EmotionalState)
WHERE e.name IN b.target_emotions AND ev.intensity > 0.7
RETURN s.name, COLLECT(e.name) AS matching_emotions
```

### Real-Time Scoring
Create a scoring function for ad-show matching:

```cypher
// Ad-Show compatibility score
MATCH (s:Show {name: $show_name})
OPTIONAL MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState)
WHERE e.name IN $target_emotions
WITH s, AVG(ev.intensity) AS emotion_score
OPTIONAL MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
WHERE p.name IN $target_traits
WITH s, emotion_score, AVG(at.correlation) AS trait_score
OPTIONAL MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique)
WHERE pt.name IN $planned_techniques
WITH s, emotion_score, trait_score, AVG(rt.effectiveness) AS persuasion_score
RETURN s.name,
       emotion_score * 0.4 + trait_score * 0.35 + persuasion_score * 0.25 AS total_score;
```

---

## Database Statistics (Expected)

After loading the complete iHeart catalog:

| Node Type | Count |
|-----------|-------|
| Station | ~15-20 |
| Show | ~40-50 |
| Podcast | ~45-55 |
| Host | ~80-100 |
| Segment | ~50-70 |
| Topic | ~150-200 |
| EmotionalState | 20 |
| Mindset | 12 |
| BehavioralTendency | 14 |
| Urge | 14 |
| PersonalityTrait | 16 |
| CognitiveStyle | 11 |
| PersuasionTechnique | 15 |
| TimeSlot | 12 |
| Market | ~15-20 |
| Format | ~10-15 |
| Event | 6 |
| PodcastNetwork | ~15-20 |

| Relationship Type | Count |
|-------------------|-------|
| EVOKES_STATE | ~500-700 |
| CREATES_MINDSET | ~300-400 |
| TRIGGERS_BEHAVIOR | ~400-500 |
| ATTRACTS_TRAIT | ~400-500 |
| RECEPTIVE_TO | ~400-500 |
| COVERS_TOPIC | ~400-500 |
| HOSTED_BY | ~100-150 |
| BROADCASTS | ~40-50 |
| AIRS_DURING | ~40-50 |

---

## Notes on Nonconscious Analytics

The graph structure supports nonconscious influence modeling through:

1. **Priming Pathways**: Track which emotional states prime listeners for specific urges
   ```cypher
   MATCH path = (e:EmotionalState)<-[:EVOKES_STATE]-(s:Show)-[:INDUCES_URGE]->(u:Urge)
   RETURN path
   ```

2. **Implicit Association**: Personality traits correlate with unspoken preferences
   ```cypher
   MATCH (t:PersonalityTrait)<-[:ATTRACTS_TRAIT]-(s)-[:COVERS_TOPIC]->(topic)
   RETURN t.name, COLLECT(DISTINCT topic.name) AS associated_topics
   ```

3. **Temporal Susceptibility**: Time slots have inherent psychological characteristics
   ```cypher
   MATCH (t:TimeSlot)
   RETURN t.name, t.attention_level, t.typical_mood
   // Use attention_level for susceptibility to different message types
   ```

4. **Cognitive Load Matching**: Match ad complexity to mindset focus level
   ```cypher
   MATCH (m:Mindset)
   WHERE m.focus < 0.5  // Low cognitive load context
   RETURN m.name  // Best for simple, repetitive messaging
   ```

---

## License

This schema and code are provided for use with iHeartMedia advertising optimization systems.
