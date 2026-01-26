# CLAUDE.md - iHeartMedia Psycholinguistic Advertising Graph Database

> This file provides context for Claude Code and other AI coding assistants working on this project.

## Project Overview

This is a **Neo4j graph database** designed for **psycholinguistic advertising optimization** for iHeartMedia's radio stations and podcasts. The system enables matching advertisements to content channels based on psychological, emotional, and behavioral listener profiles.

### Core Concept: State-Behavior-Traits (SBT) Framework

The database models three psychological dimensions:
- **STATE**: Emotional states (excitement, nostalgia, fear) + Mindsets (learning, entertainment)
- **BEHAVIOR**: Behavioral tendencies (impulsive, brand_loyalty) + Urges (purchase_intent, share)
- **TRAITS**: Personality traits (Big Five) + Cognitive styles (analytical, intuitive)

Plus: **Persuasion techniques** (Cialdini principles) and **Temporal optimization** (time slots)

---

## File Structure

```
.
├── iheart_neo4j_psycholinguistics.py   # Main loader script
├── iheart_complete_catalog.json         # iHeart station/podcast data
├── IHEART_NEO4J_SCHEMA_DOCUMENTATION.md # Detailed schema docs
└── CLAUDE.md                            # This file (AI assistant context)
```

---

## Key Technologies

- **Database**: Neo4j (Graph Database)
- **Language**: Python 3.x
- **Driver**: `neo4j` Python package
- **Query Language**: Cypher

---

## How to Run

```bash
# Install dependency
pip install neo4j

# Load data into Neo4j (requires running Neo4j instance)
python iheart_neo4j_psycholinguistics.py \
    --uri bolt://localhost:7687 \
    --username neo4j \
    --password YOUR_PASSWORD \
    --catalog iheart_complete_catalog.json \
    --clear  # Optional: wipe existing data first

# View example Cypher queries without connecting to database
python iheart_neo4j_psycholinguistics.py --queries-only
```

---

## Graph Schema Summary

### Content Nodes (from iHeart catalog)
| Node Label | Description | Key Properties |
|------------|-------------|----------------|
| `Network` | iHeartMedia parent | name, total_stations, revenue |
| `Station` | Radio station | call_sign, brand_name, market, format, description |
| `Show` | Radio show | id, name, air_time, syndicated, description |
| `Podcast` | Podcast show | id, name, network, category, description |
| `Host` | Show/podcast host | id, name |
| `Segment` | Show segment | id, name, description |
| `Topic` | Content topic | name, display_name |
| `Market` | Geographic market | name |
| `Format` | Station format | name (e.g., "Top 40/CHR", "Country") |
| `TimeSlot` | Broadcast time | name, hours, attention_level, typical_mood |
| `Event` | Annual event | name, location, month |
| `PodcastNetwork` | Podcast network | name |

### Psycholinguistic Taxonomy Nodes
| Node Label | Count | Key Properties |
|------------|-------|----------------|
| `EmotionalState` | 20 | name, valence (-1 to 1), arousal (0-1), category |
| `Mindset` | 12 | name, openness, focus, receptivity (all 0-1) |
| `BehavioralTendency` | 14 | name, various behavioral scores |
| `Urge` | 14 | name, conversion_potential |
| `PersonalityTrait` | 16 | name, dimension, level, description |
| `CognitiveStyle` | 11 | name, processing style attributes |
| `PersuasionTechnique` | 15 | name, principle, effectiveness_context |

### Key Relationships
| Relationship | From | To | Properties |
|--------------|------|-----|------------|
| `EVOKES_STATE` | Show/Podcast/Station | EmotionalState | intensity (0-1), source |
| `CREATES_MINDSET` | Show/Podcast/Station | Mindset | strength (0-1), source |
| `TRIGGERS_BEHAVIOR` | Show/Podcast/Station | BehavioralTendency | likelihood (0-1), source |
| `ATTRACTS_TRAIT` | Show/Podcast/Station | PersonalityTrait | correlation (0-1), source |
| `RECEPTIVE_TO` | Show/Podcast/Station | PersuasionTechnique | effectiveness (0-1), source |
| `AIRS_DURING` | Show | TimeSlot | - |
| `COVERS_TOPIC` | Show/Podcast | Topic | - |
| `HOSTED_BY` | Show/Podcast | Host | - |
| `BROADCASTS` | Station | Show | - |
| `HAS_FORMAT` | Station | Format | - |
| `IN_MARKET` | Station | Market | - |

---

## Common Development Tasks

### Task: Add a new emotional state
```python
# In EMOTIONAL_STATES dict (line ~35)
EMOTIONAL_STATES = {
    # ... existing states ...
    "new_emotion": {"valence": 0.5, "arousal": 0.5, "category": "mixed"},
}
```

### Task: Add a new persuasion technique
```python
# In PERSUASION_TECHNIQUES dict (line ~150)
PERSUASION_TECHNIQUES = {
    # ... existing techniques ...
    "new_technique": {"principle": "description", "effectiveness_context": "use_case"},
}
```

### Task: Add format-to-psycholinguistic mappings
```python
# In CONTENT_PSYCHOLINGUISTIC_MAPPINGS["formats"] (line ~175)
"New Format Name": {
    "emotions": [("excitement", 0.8), ("joy", 0.7)],
    "mindsets": [("entertainment", 0.8)],
    "behaviors": [("social_sharing", 0.7)],
    "traits": [("extraversion_high", 0.7)],
    "persuasion": [("social_proof", 0.8)],
},
```

### Task: Query shows for a specific ad campaign
```cypher
// Find shows evoking excitement for extraversion-high audiences
MATCH (s:Show)-[ev:EVOKES_STATE]->(e:EmotionalState {name: 'excitement'})
MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait {name: 'extraversion_high'})
WHERE ev.intensity > 0.7 AND at.correlation > 0.6
RETURN s.name, ev.intensity, at.correlation
ORDER BY ev.intensity * at.correlation DESC;
```

### Task: Get full psycholinguistic profile for a show
```cypher
MATCH (s:Show {name: 'The Bobby Bones Show'})
OPTIONAL MATCH (s)-[ev:EVOKES_STATE]->(e:EmotionalState)
OPTIONAL MATCH (s)-[cm:CREATES_MINDSET]->(m:Mindset)
OPTIONAL MATCH (s)-[tb:TRIGGERS_BEHAVIOR]->(b:BehavioralTendency)
OPTIONAL MATCH (s)-[at:ATTRACTS_TRAIT]->(p:PersonalityTrait)
OPTIONAL MATCH (s)-[rt:RECEPTIVE_TO]->(pt:PersuasionTechnique)
RETURN s.name,
       COLLECT(DISTINCT {state: e.name, intensity: ev.intensity}) AS emotions,
       COLLECT(DISTINCT {mindset: m.name, strength: cm.strength}) AS mindsets,
       COLLECT(DISTINCT {behavior: b.name, likelihood: tb.likelihood}) AS behaviors,
       COLLECT(DISTINCT {trait: p.name, correlation: at.correlation}) AS traits,
       COLLECT(DISTINCT {technique: pt.name, effectiveness: rt.effectiveness}) AS persuasion;
```

---

## Code Architecture

### Main Classes

**`IHeartPsycholinguisticGraph`** (line ~250)
- Primary class managing Neo4j connection and data loading
- Key methods:
  - `create_schema()` - Creates constraints and indexes
  - `load_psycholinguistic_taxonomy()` - Loads all SBT nodes
  - `load_iheart_catalog(catalog_data)` - Loads stations, shows, podcasts
  - `_create_*_psycholinguistic_links()` - Infers and creates relationships

### Data Flow
```
JSON Catalog → Parse → Create Content Nodes → Infer Psycholinguistics → Create Relationships
```

### Psycholinguistic Inference Logic

1. **Format-based**: Station format (e.g., "Country") maps to predefined emotional/trait profiles
2. **Keyword extraction**: Description text scanned for emotion-triggering keywords
3. **Show type detection**: Morning show, countdown, true crime, etc. → mindset mappings
4. **Inheritance**: Shows inherit from station format with slightly reduced intensity (0.9x)

---

## Extension Points

### Adding Vector Embeddings
The schema stores full `description` text on nodes specifically for embedding:
```python
# After loading, you can add embeddings:
# 1. Extract descriptions
# 2. Generate embeddings (OpenAI, Sentence Transformers, etc.)
# 3. Store on nodes:
MATCH (s:Show {id: $id})
SET s.embedding = $vector_array
```

### Adding Brand/Product Nodes
```cypher
CREATE (b:Brand {name: 'Nike'})
SET b.target_emotions = ['excitement', 'inspiration']
SET b.target_traits = ['sensation_seeking', 'extraversion_high']
SET b.preferred_persuasion = ['aspiration', 'social_proof']
```

### Real-time Ad Scoring API
Build a FastAPI/Flask endpoint that:
1. Accepts brand psycholinguistic profile
2. Queries Neo4j for matching shows
3. Returns scored recommendations

---

## Testing Notes

- Script validates JSON syntax but doesn't validate Neo4j connection until runtime
- Use `--queries-only` flag to test query generation without database
- Full load creates ~2000+ nodes and ~3000+ relationships
- Idempotent: Uses MERGE statements, safe to re-run

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: neo4j` | `pip install neo4j` |
| Connection refused | Ensure Neo4j is running on specified URI |
| Constraint already exists | Safe to ignore (handled in code) |
| Slow loading | Normal for first run; subsequent runs faster due to MERGE |

---

## Related Documentation

- `IHEART_NEO4J_SCHEMA_DOCUMENTATION.md` - Full schema details, all queries, extension guides
- Neo4j Cypher Manual: https://neo4j.com/docs/cypher-manual/
- Neo4j Python Driver: https://neo4j.com/docs/python-manual/

---

## Quick Reference: Emotional States

| State | Valence | Arousal | Best For |
|-------|---------|---------|----------|
| excitement | +0.8 | 0.9 | Product launches, events |
| joy | +0.9 | 0.7 | Celebrations, lifestyle |
| nostalgia | +0.5 | 0.4 | Heritage brands, reunions |
| fear | -0.7 | 0.8 | Insurance, security |
| trust | +0.6 | 0.3 | Financial, healthcare |
| curiosity | +0.6 | 0.6 | Tech, education |

## Quick Reference: Persuasion Techniques

| Technique | Principle | Best Content |
|-----------|-----------|--------------|
| social_proof | Others do it | High-listener shows |
| scarcity | Limited availability | Morning drive (urgency) |
| authority | Expert endorsement | News/talk, educational |
| unity | Shared identity | Country, urban formats |
| storytelling | Narrative transport | True crime, Lore-style |
| humor | Entertainment | Comedy podcasts |

---

## Contact / Ownership

This database serves iHeartMedia's psycholinguistic advertising optimization system.
Schema designed for State-Behavior-Traits framework with nonconscious analytics support.
