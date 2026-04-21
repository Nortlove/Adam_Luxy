// =============================================================================
// ADAM Migration 022: Multi-tenant shell (Partner / Advertiser / Workspace)
//
// Per HMT Foundation §11 and the Phase C roadmap: the schema for the
// DV360-style three-tier hierarchy (Partner = agency/holdco,
// Advertiser = brand, Workspace = campaign scope). Existing
// endpoints stay single-tenant in v1; this migration establishes
// the nodes so the Settings admin surface can render the hierarchy
// and future endpoints can filter by tenant without a schema
// break.
//
// Role hierarchy:
//   superadmin      — INFORMATIV staff, access to everything
//   partner_admin   — agency admins, scoped to their Partner
//   advertiser_admin — brand admins, scoped to their Advertiser
//   viewer          — read-only, any scope
// =============================================================================


// =============================================================================
// CONSTRAINTS
// =============================================================================

CREATE CONSTRAINT tenant_partner_pk IF NOT EXISTS
FOR (p:TenantPartner) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT tenant_advertiser_pk IF NOT EXISTS
FOR (a:TenantAdvertiser) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT tenant_workspace_pk IF NOT EXISTS
FOR (w:TenantWorkspace) REQUIRE w.id IS UNIQUE;


// =============================================================================
// INDEXES
// =============================================================================

CREATE INDEX tenant_partner_name_idx IF NOT EXISTS
FOR (p:TenantPartner) ON (p.name);

CREATE INDEX tenant_advertiser_partner_idx IF NOT EXISTS
FOR (a:TenantAdvertiser) ON (a.partner_id);

CREATE INDEX tenant_workspace_advertiser_idx IF NOT EXISTS
FOR (w:TenantWorkspace) ON (w.advertiser_id);


// =============================================================================
// NODE DEFINITIONS (documented shape)
// =============================================================================

// TenantPartner node shape:
//   id: string (e.g. "partner:informativ", "partner:mindshare")
//   name: string (agency / holdco name)
//   kind: "superadmin" | "agency" | "independent" | "direct_brand"
//   white_label_name: string | null (agency brand of the dashboard)
//   billing_email: string | null
//   status: "active" | "suspended" | "archived"
//   created_at: datetime

// TenantAdvertiser node shape:
//   id: string (e.g. "advertiser:luxy_ride")
//   partner_id: string (FK TenantPartner.id)
//   name: string (brand name)
//   category: string | null (e.g. "luxury_transport")
//   stackadapt_advertiser_id: string | null (links to external DSP)
//   status: "active" | "paused" | "archived"
//   created_at: datetime

// TenantWorkspace node shape:
//   id: string (e.g. "workspace:luxy-2026-q2")
//   advertiser_id: string (FK TenantAdvertiser.id)
//   name: string (campaign / flight / region grouping)
//   purpose: string | null (one-line description)
//   status: "active" | "paused" | "archived"
//   created_at: datetime


// =============================================================================
// EXTEND DialogueUser WITH TENANT MEMBERSHIP
// =============================================================================

// DialogueUser now has:
//   role: "superadmin" | "partner_admin" | "advertiser_admin" | "viewer"
//   partner_id: string | null (null for superadmin)
//   advertiser_id: string | null (null for partner_admin and above)

// Relationships:
//   (DialogueUser)-[:BELONGS_TO_PARTNER]->(TenantPartner)
//   (DialogueUser)-[:ADMIN_OF_ADVERTISER]->(TenantAdvertiser)
//   (TenantPartner)-[:HAS_ADVERTISER]->(TenantAdvertiser)
//   (TenantAdvertiser)-[:HAS_WORKSPACE]->(TenantWorkspace)


// =============================================================================
// SEED — INFORMATIV as the superadmin Partner + Chris's membership
// =============================================================================

MERGE (p:TenantPartner {id: "partner:informativ"})
  ON CREATE SET p.name = "INFORMATIV",
                p.kind = "superadmin",
                p.white_label_name = null,
                p.billing_email = null,
                p.status = "active",
                p.created_at = datetime();

MERGE (a:TenantAdvertiser {id: "advertiser:luxy_ride"})
  ON CREATE SET a.partner_id = "partner:informativ",
                a.name = "LUXY Ride",
                a.category = "luxury_transport",
                a.stackadapt_advertiser_id = null,
                a.status = "active",
                a.created_at = datetime();

MERGE (w:TenantWorkspace {id: "workspace:luxy-pilot"})
  ON CREATE SET w.advertiser_id = "advertiser:luxy_ride",
                w.name = "LUXY Pilot",
                w.purpose = "Live pilot campaign — bilateral cascade + retargeting",
                w.status = "active",
                w.created_at = datetime();

MATCH (p:TenantPartner {id: "partner:informativ"})
MATCH (a:TenantAdvertiser {id: "advertiser:luxy_ride"})
MERGE (p)-[:HAS_ADVERTISER]->(a);

MATCH (a:TenantAdvertiser {id: "advertiser:luxy_ride"})
MATCH (w:TenantWorkspace {id: "workspace:luxy-pilot"})
MERGE (a)-[:HAS_WORKSPACE]->(w);

// Extend Chris's membership — superadmin, belongs to INFORMATIV Partner.
MATCH (u:DialogueUser {id: "user:chris"})
SET u.role = coalesce(u.role, "superadmin"),
    u.partner_id = "partner:informativ",
    u.advertiser_id = null;

MATCH (u:DialogueUser {id: "user:chris"})
MATCH (p:TenantPartner {id: "partner:informativ"})
MERGE (u)-[:BELONGS_TO_PARTNER]->(p);
