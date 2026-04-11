#!/usr/bin/env python3
"""
ADAM FINANCIAL TRUST LAYER - Neo4j Schema Creation
===================================================

Creates the complete graph schema for the Financial Trust Layer:
- Bank nodes with psychological profiles
- Financial anxiety state nodes
- Credit journey stage nodes
- Service recovery pattern nodes
- Channel preference nodes
- Mechanism effectiveness edges

This is UNIQUE to bank reviews - no other dataset provides:
- Trust psychology (existential, not preferential)
- Financial anxiety detection patterns
- Credit rebuilding transformation journeys
- Long-term relationship dynamics (years, not transactions)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
BANK_CHECKPOINT = PROJECT_ROOT / "data" / "learning" / "multi_domain" / "checkpoint_bank_reviews.json"


# =============================================================================
# CYPHER SCHEMA DEFINITIONS
# =============================================================================

SCHEMA_CONSTRAINTS = [
    # Bank uniqueness
    "CREATE CONSTRAINT bank_name IF NOT EXISTS FOR (b:Bank) REQUIRE b.name IS UNIQUE",
    
    # Financial state uniqueness
    "CREATE CONSTRAINT financial_anxiety_level IF NOT EXISTS FOR (f:FinancialAnxietyState) REQUIRE f.level IS UNIQUE",
    "CREATE CONSTRAINT credit_journey_stage IF NOT EXISTS FOR (c:CreditJourneyStage) REQUIRE c.stage IS UNIQUE",
    "CREATE CONSTRAINT channel_preference IF NOT EXISTS FOR (ch:ChannelPreference) REQUIRE ch.type IS UNIQUE",
    "CREATE CONSTRAINT service_pattern IF NOT EXISTS FOR (s:ServiceRecoveryPattern) REQUIRE s.pattern_id IS UNIQUE",
    
    # Index for performance
    "CREATE INDEX bank_trust_idx IF NOT EXISTS FOR (b:Bank) ON (b.trust_score)",
    "CREATE INDEX bank_archetype_idx IF NOT EXISTS FOR (b:Bank) ON (b.dominant_archetype)",
]

FINANCIAL_ANXIETY_STATES = [
    {
        "level": "none",
        "description": "No financial anxiety detected",
        "mechanism_adjustments": {
            "authority": 1.3, "commitment": 1.3, "scarcity": 1.0, "fear_appeal": 0.8
        }
    },
    {
        "level": "low",
        "description": "Mild financial awareness, budget-conscious",
        "mechanism_adjustments": {
            "authority": 1.3, "commitment": 1.3, "scarcity": 0.9, "fear_appeal": 0.6
        }
    },
    {
        "level": "medium",
        "description": "Active credit monitoring, concerned about scores",
        "mechanism_adjustments": {
            "authority": 1.4, "commitment": 1.4, "scarcity": 0.5, "fear_appeal": 0.3, "liking": 1.3
        }
    },
    {
        "level": "high",
        "description": "Significant financial stress, seeking solutions",
        "mechanism_adjustments": {
            "authority": 1.4, "commitment": 1.5, "scarcity": 0.3, "fear_appeal": 0.0, "liking": 1.5, "social_proof": 1.3
        }
    },
    {
        "level": "critical",
        "description": "Severe financial distress, requires ethical safeguards",
        "mechanism_adjustments": {
            "authority": 1.3, "commitment": 1.5, "scarcity": 0.0, "fear_appeal": 0.0, "liking": 1.6, "social_proof": 1.4
        },
        "requires_safeguards": True
    },
]

CREDIT_JOURNEY_STAGES = [
    {
        "stage": "shame",
        "description": "Initial awareness and embarrassment about credit situation",
        "optimal_mechanisms": ["liking", "social_proof"],
        "avoid_mechanisms": ["fear_appeal", "scarcity"],
        "messaging_tone": "empathetic, normalizing, non-judgmental"
    },
    {
        "stage": "seeking",
        "description": "Actively looking for solutions and help",
        "optimal_mechanisms": ["authority", "commitment"],
        "avoid_mechanisms": ["fear_appeal"],
        "messaging_tone": "informative, credible, clear path forward"
    },
    {
        "stage": "rebuilding",
        "description": "Actively working on credit improvement",
        "optimal_mechanisms": ["commitment", "reciprocity"],
        "avoid_mechanisms": [],
        "messaging_tone": "encouraging, reward-focused, progress-celebrating"
    },
    {
        "stage": "recovered",
        "description": "Credit restored, enjoying benefits",
        "optimal_mechanisms": ["social_proof", "unity"],
        "avoid_mechanisms": [],
        "messaging_tone": "congratulatory, community-welcoming"
    },
    {
        "stage": "advocate",
        "description": "Helping others on their journey",
        "optimal_mechanisms": ["unity", "social_proof"],
        "avoid_mechanisms": [],
        "messaging_tone": "empowering, story-sharing, community-building"
    },
]

CHANNEL_PREFERENCES = [
    {
        "type": "digital",
        "description": "Strong preference for app, website, mobile",
        "ad_copy_elements": ["instant", "24/7", "app", "online", "convenient", "real-time"],
        "channel_priority": ["mobile_app", "web", "email", "push_notification"]
    },
    {
        "type": "traditional",
        "description": "Prefers branch, phone, personal interaction",
        "ad_copy_elements": ["personal service", "dedicated advisor", "local branch", "speak with"],
        "channel_priority": ["phone", "branch", "direct_mail", "in_person"]
    },
    {
        "type": "hybrid",
        "description": "Uses both digital and traditional channels",
        "ad_copy_elements": ["your choice", "however you prefer", "online or in person"],
        "channel_priority": ["mobile_app", "phone", "web", "branch"]
    },
]

SERVICE_RECOVERY_PATTERNS = [
    {
        "pattern_id": "fraud_resolution",
        "failure_type": "fraud",
        "effective_recovery": ["immediate_action", "proactive_communication", "full_refund"],
        "messaging_priority": ["security", "protection", "swift_response"]
    },
    {
        "pattern_id": "fee_dispute",
        "failure_type": "unexpected_fee",
        "effective_recovery": ["fee_waiver", "clear_explanation", "prevention_education"],
        "messaging_priority": ["transparency", "fairness", "education"]
    },
    {
        "pattern_id": "technical_issue",
        "failure_type": "app_website_failure",
        "effective_recovery": ["quick_fix", "alternative_access", "status_updates"],
        "messaging_priority": ["reliability", "improvement", "apology"]
    },
    {
        "pattern_id": "service_failure",
        "failure_type": "poor_customer_service",
        "effective_recovery": ["escalation_path", "personal_followup", "recognition"],
        "messaging_priority": ["listening", "improvement", "commitment"]
    },
]


# =============================================================================
# NEO4J CLIENT
# =============================================================================

async def get_neo4j_session():
    """Get Neo4j session."""
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if client:
            return await client.session()
    except ImportError:
        pass
    return None


# =============================================================================
# SCHEMA CREATION
# =============================================================================

async def create_schema_constraints(session) -> bool:
    """Create Neo4j constraints and indexes."""
    logger.info("Creating schema constraints...")
    
    for constraint in SCHEMA_CONSTRAINTS:
        try:
            await session.run(constraint)
            logger.debug(f"  Created: {constraint[:50]}...")
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.warning(f"  Failed: {e}")
    
    return True


async def create_financial_anxiety_nodes(session) -> int:
    """Create FinancialAnxietyState nodes."""
    logger.info("Creating FinancialAnxietyState nodes...")
    count = 0
    
    for state in FINANCIAL_ANXIETY_STATES:
        try:
            await session.run("""
                MERGE (f:FinancialAnxietyState {level: $level})
                SET f.description = $description,
                    f.mechanism_adjustments = $mechanism_adjustments,
                    f.requires_safeguards = $requires_safeguards,
                    f.source = 'bank_reviews_psychology'
            """, {
                "level": state["level"],
                "description": state["description"],
                "mechanism_adjustments": json.dumps(state["mechanism_adjustments"]),
                "requires_safeguards": state.get("requires_safeguards", False),
            })
            count += 1
        except Exception as e:
            logger.error(f"  Failed to create {state['level']}: {e}")
    
    logger.info(f"  Created {count} FinancialAnxietyState nodes")
    return count


async def create_credit_journey_nodes(session) -> int:
    """Create CreditJourneyStage nodes."""
    logger.info("Creating CreditJourneyStage nodes...")
    count = 0
    
    for stage in CREDIT_JOURNEY_STAGES:
        try:
            await session.run("""
                MERGE (c:CreditJourneyStage {stage: $stage})
                SET c.description = $description,
                    c.optimal_mechanisms = $optimal_mechanisms,
                    c.avoid_mechanisms = $avoid_mechanisms,
                    c.messaging_tone = $messaging_tone,
                    c.source = 'bank_reviews_psychology'
            """, {
                "stage": stage["stage"],
                "description": stage["description"],
                "optimal_mechanisms": stage["optimal_mechanisms"],
                "avoid_mechanisms": stage["avoid_mechanisms"],
                "messaging_tone": stage["messaging_tone"],
            })
            count += 1
        except Exception as e:
            logger.error(f"  Failed to create {stage['stage']}: {e}")
    
    logger.info(f"  Created {count} CreditJourneyStage nodes")
    return count


async def create_channel_preference_nodes(session) -> int:
    """Create ChannelPreference nodes."""
    logger.info("Creating ChannelPreference nodes...")
    count = 0
    
    for pref in CHANNEL_PREFERENCES:
        try:
            await session.run("""
                MERGE (ch:ChannelPreference {type: $type})
                SET ch.description = $description,
                    ch.ad_copy_elements = $ad_copy_elements,
                    ch.channel_priority = $channel_priority,
                    ch.source = 'bank_reviews_psychology'
            """, {
                "type": pref["type"],
                "description": pref["description"],
                "ad_copy_elements": pref["ad_copy_elements"],
                "channel_priority": pref["channel_priority"],
            })
            count += 1
        except Exception as e:
            logger.error(f"  Failed to create {pref['type']}: {e}")
    
    logger.info(f"  Created {count} ChannelPreference nodes")
    return count


async def create_service_pattern_nodes(session) -> int:
    """Create ServiceRecoveryPattern nodes."""
    logger.info("Creating ServiceRecoveryPattern nodes...")
    count = 0
    
    for pattern in SERVICE_RECOVERY_PATTERNS:
        try:
            await session.run("""
                MERGE (s:ServiceRecoveryPattern {pattern_id: $pattern_id})
                SET s.failure_type = $failure_type,
                    s.effective_recovery = $effective_recovery,
                    s.messaging_priority = $messaging_priority,
                    s.source = 'bank_reviews_psychology'
            """, {
                "pattern_id": pattern["pattern_id"],
                "failure_type": pattern["failure_type"],
                "effective_recovery": pattern["effective_recovery"],
                "messaging_priority": pattern["messaging_priority"],
            })
            count += 1
        except Exception as e:
            logger.error(f"  Failed to create {pattern['pattern_id']}: {e}")
    
    logger.info(f"  Created {count} ServiceRecoveryPattern nodes")
    return count


async def create_bank_nodes(session, bank_data: Dict) -> int:
    """Create Bank nodes with psychological profiles."""
    logger.info("Creating Bank nodes with psychological profiles...")
    count = 0
    
    profiles = bank_data.get("profiles", {})
    
    for bank_name, profile in profiles.items():
        try:
            # Get dominant archetype
            archetypes = profile.get("archetype_distribution", {})
            dominant_archetype = max(archetypes.items(), key=lambda x: x[1])[0] if archetypes else "guardian"
            
            # Get banking psychology scores
            banking_psych = profile.get("banking_psychology", {})
            
            await session.run("""
                MERGE (b:Bank {name: $name})
                SET b.total_reviews = $total_reviews,
                    b.avg_rating = $avg_rating,
                    b.dominant_archetype = $dominant_archetype,
                    b.trust_score = $trust_score,
                    b.anxiety_sensitivity = $anxiety_sensitivity,
                    b.digital_preference = $digital_preference,
                    b.service_experience = $service_experience,
                    b.credit_building_focus = $credit_building_focus,
                    b.relationship_duration = $relationship_duration,
                    b.archetype_distribution = $archetype_distribution,
                    b.source = 'bank_reviews_huggingface',
                    b.category = 'Finance_Banking'
            """, {
                "name": bank_name,
                "total_reviews": profile.get("total_reviews", 0),
                "avg_rating": profile.get("avg_rating", 0),
                "dominant_archetype": dominant_archetype,
                "trust_score": banking_psych.get("trust_security", 0),
                "anxiety_sensitivity": banking_psych.get("financial_anxiety", 0),
                "digital_preference": banking_psych.get("digital_preference", 0),
                "service_experience": banking_psych.get("service_experience", 0),
                "credit_building_focus": banking_psych.get("credit_building", 0),
                "relationship_duration": banking_psych.get("relationship_duration", 0),
                "archetype_distribution": json.dumps(archetypes),
            })
            count += 1
            
        except Exception as e:
            logger.error(f"  Failed to create bank {bank_name}: {e}")
    
    logger.info(f"  Created {count} Bank nodes")
    return count


async def create_mechanism_edges(session, bank_data: Dict) -> int:
    """Create MECHANISM_EFFECTIVENESS edges between Banks and CognitiveMechanisms."""
    logger.info("Creating MECHANISM_EFFECTIVENESS edges...")
    count = 0
    
    profiles = bank_data.get("profiles", {})
    
    for bank_name, profile in profiles.items():
        cialdini = profile.get("cialdini_principles", {})
        
        for mechanism, effectiveness in cialdini.items():
            if effectiveness > 0.01:  # Only create edges for meaningful effectiveness
                try:
                    await session.run("""
                        MERGE (b:Bank {name: $bank_name})
                        MERGE (m:CognitiveMechanism {name: $mechanism})
                        MERGE (b)-[r:MECHANISM_EFFECTIVENESS]->(m)
                        SET r.effectiveness = $effectiveness,
                            r.source = 'bank_reviews_19k',
                            r.domain = 'Finance_Banking'
                    """, {
                        "bank_name": bank_name,
                        "mechanism": mechanism,
                        "effectiveness": effectiveness,
                    })
                    count += 1
                except Exception as e:
                    logger.error(f"  Failed edge {bank_name}->{mechanism}: {e}")
    
    logger.info(f"  Created {count} MECHANISM_EFFECTIVENESS edges")
    return count


async def create_archetype_mappings(session, bank_data: Dict) -> int:
    """Create edges from FinancialAnxietyState and CreditJourneyStage to Archetypes."""
    logger.info("Creating archetype mappings...")
    count = 0
    
    # Financial anxiety states map to certain archetypes
    anxiety_archetype_map = {
        "none": {"pragmatist": 0.4, "achiever": 0.3, "analyst": 0.3},
        "low": {"analyst": 0.4, "pragmatist": 0.3, "guardian": 0.3},
        "medium": {"guardian": 0.5, "analyst": 0.3, "pragmatist": 0.2},
        "high": {"guardian": 0.6, "connector": 0.3, "pragmatist": 0.1},
        "critical": {"guardian": 0.7, "connector": 0.2, "pragmatist": 0.1},
    }
    
    for anxiety_level, archetypes in anxiety_archetype_map.items():
        for archetype, correlation in archetypes.items():
            try:
                await session.run("""
                    MERGE (f:FinancialAnxietyState {level: $level})
                    MERGE (a:Archetype {name: $archetype})
                    MERGE (f)-[r:MAPS_TO_ARCHETYPE]->(a)
                    SET r.correlation = $correlation,
                        r.source = 'bank_reviews_psychology'
                """, {
                    "level": anxiety_level,
                    "archetype": archetype,
                    "correlation": correlation,
                })
                count += 1
            except Exception as e:
                logger.debug(f"  Archetype mapping failed: {e}")
    
    # Credit journey stages map to optimal mechanisms
    for stage in CREDIT_JOURNEY_STAGES:
        for mechanism in stage["optimal_mechanisms"]:
            try:
                await session.run("""
                    MERGE (c:CreditJourneyStage {stage: $stage})
                    MERGE (m:CognitiveMechanism {name: $mechanism})
                    MERGE (c)-[r:OPTIMAL_MECHANISM]->(m)
                    SET r.effectiveness = 1.4,
                        r.source = 'bank_reviews_psychology'
                """, {
                    "stage": stage["stage"],
                    "mechanism": mechanism,
                })
                count += 1
            except Exception as e:
                logger.debug(f"  Mechanism mapping failed: {e}")
        
        for mechanism in stage["avoid_mechanisms"]:
            try:
                await session.run("""
                    MERGE (c:CreditJourneyStage {stage: $stage})
                    MERGE (m:CognitiveMechanism {name: $mechanism})
                    MERGE (c)-[r:AVOID_MECHANISM]->(m)
                    SET r.effectiveness = 0.0,
                        r.source = 'bank_reviews_psychology'
                """, {
                    "stage": stage["stage"],
                    "mechanism": mechanism,
                })
                count += 1
            except Exception as e:
                logger.debug(f"  Avoid mechanism mapping failed: {e}")
    
    logger.info(f"  Created {count} archetype/mechanism mappings")
    return count


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Create the complete Financial Trust Layer in Neo4j."""
    logger.info("=" * 70)
    logger.info("ADAM FINANCIAL TRUST LAYER - Neo4j Schema Creation")
    logger.info("=" * 70)
    
    # Load bank data
    if not BANK_CHECKPOINT.exists():
        logger.error(f"Bank checkpoint not found: {BANK_CHECKPOINT}")
        logger.error("Run scripts/process_bank_reviews.py first")
        return False
    
    with open(BANK_CHECKPOINT) as f:
        bank_data = json.load(f)
    
    logger.info(f"Loaded bank data: {bank_data['total_reviews']:,} reviews, {bank_data['total_banks']} banks")
    
    # Get Neo4j session
    try:
        from adam.infrastructure.neo4j.client import Neo4jClient
        
        # Try to get connection details from environment
        import os
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        client = Neo4jClient(uri, user, password)
        session = client.driver.session()
        
    except Exception as e:
        logger.warning(f"Could not connect to Neo4j: {e}")
        logger.info("")
        logger.info("Neo4j not available - generating Cypher scripts instead")
        logger.info("-" * 50)
        
        # Generate Cypher script for manual execution
        cypher_path = PROJECT_ROOT / "data" / "neo4j_import" / "financial_trust_layer.cypher"
        cypher_path.parent.mkdir(parents=True, exist_ok=True)
        
        generate_cypher_script(bank_data, cypher_path)
        logger.info(f"Generated Cypher script: {cypher_path}")
        logger.info("Import manually with: cat data/neo4j_import/financial_trust_layer.cypher | cypher-shell")
        return True
    
    try:
        # Create schema
        logger.info("")
        logger.info("Creating schema...")
        
        # Constraints
        for constraint in SCHEMA_CONSTRAINTS:
            try:
                session.run(constraint)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.debug(f"Constraint: {e}")
        
        # Financial anxiety nodes
        for state in FINANCIAL_ANXIETY_STATES:
            session.run("""
                MERGE (f:FinancialAnxietyState {level: $level})
                SET f.description = $description,
                    f.mechanism_adjustments = $mechanism_adjustments,
                    f.requires_safeguards = $requires_safeguards
            """, {
                "level": state["level"],
                "description": state["description"],
                "mechanism_adjustments": json.dumps(state["mechanism_adjustments"]),
                "requires_safeguards": state.get("requires_safeguards", False),
            })
        logger.info(f"  Created {len(FINANCIAL_ANXIETY_STATES)} FinancialAnxietyState nodes")
        
        # Credit journey nodes
        for stage in CREDIT_JOURNEY_STAGES:
            session.run("""
                MERGE (c:CreditJourneyStage {stage: $stage})
                SET c.description = $description,
                    c.optimal_mechanisms = $optimal_mechanisms,
                    c.avoid_mechanisms = $avoid_mechanisms,
                    c.messaging_tone = $messaging_tone
            """, {
                "stage": stage["stage"],
                "description": stage["description"],
                "optimal_mechanisms": stage["optimal_mechanisms"],
                "avoid_mechanisms": stage["avoid_mechanisms"],
                "messaging_tone": stage["messaging_tone"],
            })
        logger.info(f"  Created {len(CREDIT_JOURNEY_STAGES)} CreditJourneyStage nodes")
        
        # Channel preference nodes
        for pref in CHANNEL_PREFERENCES:
            session.run("""
                MERGE (ch:ChannelPreference {type: $type})
                SET ch.description = $description,
                    ch.ad_copy_elements = $ad_copy_elements,
                    ch.channel_priority = $channel_priority
            """, {
                "type": pref["type"],
                "description": pref["description"],
                "ad_copy_elements": pref["ad_copy_elements"],
                "channel_priority": pref["channel_priority"],
            })
        logger.info(f"  Created {len(CHANNEL_PREFERENCES)} ChannelPreference nodes")
        
        # Service pattern nodes
        for pattern in SERVICE_RECOVERY_PATTERNS:
            session.run("""
                MERGE (s:ServiceRecoveryPattern {pattern_id: $pattern_id})
                SET s.failure_type = $failure_type,
                    s.effective_recovery = $effective_recovery,
                    s.messaging_priority = $messaging_priority
            """, {
                "pattern_id": pattern["pattern_id"],
                "failure_type": pattern["failure_type"],
                "effective_recovery": pattern["effective_recovery"],
                "messaging_priority": pattern["messaging_priority"],
            })
        logger.info(f"  Created {len(SERVICE_RECOVERY_PATTERNS)} ServiceRecoveryPattern nodes")
        
        # Bank nodes
        bank_count = 0
        for bank_name, profile in bank_data.get("profiles", {}).items():
            archetypes = profile.get("archetype_distribution", {})
            dominant_archetype = max(archetypes.items(), key=lambda x: x[1])[0] if archetypes else "guardian"
            banking_psych = profile.get("banking_psychology", {})
            
            session.run("""
                MERGE (b:Bank {name: $name})
                SET b.total_reviews = $total_reviews,
                    b.avg_rating = $avg_rating,
                    b.dominant_archetype = $dominant_archetype,
                    b.trust_score = $trust_score,
                    b.anxiety_sensitivity = $anxiety_sensitivity,
                    b.digital_preference = $digital_preference,
                    b.service_experience = $service_experience,
                    b.category = 'Finance_Banking',
                    b.source = 'bank_reviews_huggingface'
            """, {
                "name": bank_name,
                "total_reviews": profile.get("total_reviews", 0),
                "avg_rating": profile.get("avg_rating", 0),
                "dominant_archetype": dominant_archetype,
                "trust_score": banking_psych.get("trust_security", 0),
                "anxiety_sensitivity": banking_psych.get("financial_anxiety", 0),
                "digital_preference": banking_psych.get("digital_preference", 0),
                "service_experience": banking_psych.get("service_experience", 0),
            })
            bank_count += 1
        logger.info(f"  Created {bank_count} Bank nodes")
        
        # Mechanism effectiveness edges
        edge_count = 0
        for bank_name, profile in bank_data.get("profiles", {}).items():
            for mechanism, effectiveness in profile.get("cialdini_principles", {}).items():
                if effectiveness > 0.01:
                    session.run("""
                        MERGE (b:Bank {name: $bank_name})
                        MERGE (m:CognitiveMechanism {name: $mechanism})
                        MERGE (b)-[r:MECHANISM_EFFECTIVENESS]->(m)
                        SET r.effectiveness = $effectiveness,
                            r.source = 'bank_reviews_19k'
                    """, {
                        "bank_name": bank_name,
                        "mechanism": mechanism,
                        "effectiveness": effectiveness,
                    })
                    edge_count += 1
        logger.info(f"  Created {edge_count} MECHANISM_EFFECTIVENESS edges")
        
        session.close()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("FINANCIAL TRUST LAYER CREATED SUCCESSFULLY")
        logger.info("=" * 70)
        return True
        
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        return False


def generate_cypher_script(bank_data: Dict, output_path: Path):
    """Generate Cypher script for manual import."""
    lines = [
        "// ADAM Financial Trust Layer - Neo4j Import Script",
        "// Generated from bank review psychological analysis",
        "// Source: 19,271 bank reviews across 47 US banks",
        "",
        "// ============================================================",
        "// CONSTRAINTS AND INDEXES",
        "// ============================================================",
        "",
    ]
    
    for constraint in SCHEMA_CONSTRAINTS:
        lines.append(f"{constraint};")
    
    lines.extend([
        "",
        "// ============================================================",
        "// FINANCIAL ANXIETY STATE NODES",
        "// ============================================================",
        "",
    ])
    
    for state in FINANCIAL_ANXIETY_STATES:
        mechs = json.dumps(state["mechanism_adjustments"]).replace('"', '\\"')
        safeguards = "true" if state.get("requires_safeguards", False) else "false"
        lines.append(f"""MERGE (f:FinancialAnxietyState {{level: "{state['level']}"}})
SET f.description = "{state['description']}",
    f.mechanism_adjustments = "{mechs}",
    f.requires_safeguards = {safeguards},
    f.source = "bank_reviews_psychology";
""")
    
    lines.extend([
        "// ============================================================",
        "// CREDIT JOURNEY STAGE NODES",
        "// ============================================================",
        "",
    ])
    
    for stage in CREDIT_JOURNEY_STAGES:
        optimal = json.dumps(stage["optimal_mechanisms"])
        avoid = json.dumps(stage["avoid_mechanisms"])
        lines.append(f"""MERGE (c:CreditJourneyStage {{stage: "{stage['stage']}"}})
SET c.description = "{stage['description']}",
    c.optimal_mechanisms = {optimal},
    c.avoid_mechanisms = {avoid},
    c.messaging_tone = "{stage['messaging_tone']}",
    c.source = "bank_reviews_psychology";
""")
    
    lines.extend([
        "// ============================================================",
        "// CHANNEL PREFERENCE NODES",
        "// ============================================================",
        "",
    ])
    
    for pref in CHANNEL_PREFERENCES:
        elements = json.dumps(pref["ad_copy_elements"])
        priority = json.dumps(pref["channel_priority"])
        lines.append(f"""MERGE (ch:ChannelPreference {{type: "{pref['type']}"}})
SET ch.description = "{pref['description']}",
    ch.ad_copy_elements = {elements},
    ch.channel_priority = {priority},
    ch.source = "bank_reviews_psychology";
""")
    
    lines.extend([
        "// ============================================================",
        "// BANK NODES (47 banks with psychological profiles)",
        "// ============================================================",
        "",
    ])
    
    for bank_name, profile in bank_data.get("profiles", {}).items():
        archetypes = profile.get("archetype_distribution", {})
        dominant = max(archetypes.items(), key=lambda x: x[1])[0] if archetypes else "guardian"
        psych = profile.get("banking_psychology", {})
        
        lines.append(f"""MERGE (b:Bank {{name: "{bank_name}"}})
SET b.total_reviews = {profile.get('total_reviews', 0)},
    b.avg_rating = {profile.get('avg_rating', 0):.2f},
    b.dominant_archetype = "{dominant}",
    b.trust_score = {psych.get('trust_security', 0):.4f},
    b.anxiety_sensitivity = {psych.get('financial_anxiety', 0):.4f},
    b.digital_preference = {psych.get('digital_preference', 0):.4f},
    b.category = "Finance_Banking",
    b.source = "bank_reviews_huggingface";
""")
    
    lines.extend([
        "// ============================================================",
        "// MECHANISM EFFECTIVENESS EDGES",
        "// ============================================================",
        "",
    ])
    
    for bank_name, profile in bank_data.get("profiles", {}).items():
        for mechanism, effectiveness in profile.get("cialdini_principles", {}).items():
            if effectiveness > 0.01:
                lines.append(f"""MATCH (b:Bank {{name: "{bank_name}"}})
MERGE (m:CognitiveMechanism {{name: "{mechanism}"}})
MERGE (b)-[r:MECHANISM_EFFECTIVENESS]->(m)
SET r.effectiveness = {effectiveness:.4f}, r.source = "bank_reviews_19k";
""")
    
    with open(output_path, 'w') as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
