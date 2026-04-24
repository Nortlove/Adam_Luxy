-- INFORMATIV Campaign Management Platform — Initial Schema
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ORGANIZATIONS (multi-tenancy root)
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    domain          VARCHAR(255),
    industry        VARCHAR(100),
    tier            VARCHAR(20) DEFAULT 'standard',
    status          VARCHAR(20) DEFAULT 'active',
    settings_json   JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(30) NOT NULL,
    is_active       BOOLEAN DEFAULT true,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================================
-- REFRESH TOKENS
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);

-- ============================================================
-- CAMPAIGNS
-- ============================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',

    brand_name      VARCHAR(255) NOT NULL,
    brand_asin      VARCHAR(50),
    brand_website   VARCHAR(500),
    brand_category  VARCHAR(100),
    brand_logo_url  VARCHAR(500),

    total_budget    DECIMAL(12,2),
    daily_budget    DECIMAL(10,2),
    currency        VARCHAR(3) DEFAULT 'USD',

    start_date      DATE,
    end_date        DATE,
    timezone        VARCHAR(50) DEFAULT 'America/New_York',

    geo_targets     JSONB DEFAULT '[]',
    frequency_cap   JSONB DEFAULT '{}',
    dayparting      JSONB DEFAULT '{}',

    dsp_platform    VARCHAR(50) DEFAULT 'stackadapt',
    dsp_advertiser_id VARCHAR(100),
    dsp_api_key_encrypted VARCHAR(500),

    dcil_enabled         BOOLEAN DEFAULT true,
    dcil_auto_execute    BOOLEAN DEFAULT false,
    dcil_safety_rails    JSONB DEFAULT '{}',

    tier_a_frequency     VARCHAR(30) DEFAULT 'adaptive',

    conversion_pixel_id  VARCHAR(100),
    conversion_type      VARCHAR(50) DEFAULT 'purchase',
    conversion_value     DECIMAL(10,2),
    attribution_window_days INT DEFAULT 30,

    notes           TEXT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_campaigns_org ON campaigns(organization_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_dates ON campaigns(start_date, end_date);

-- ============================================================
-- CAMPAIGN ARCHETYPES
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_archetypes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    archetype_name  VARCHAR(100) NOT NULL,
    is_custom       BOOLEAN DEFAULT false,
    budget_weight   DECIMAL(5,4) DEFAULT 0.0,
    primary_mechanism VARCHAR(100),
    secondary_mechanism VARCHAR(100),
    framing         VARCHAR(20) DEFAULT 'gain',
    notes           TEXT,
    dsp_campaign_id VARCHAR(100),
    dsp_campaign_status VARCHAR(30),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(campaign_id, archetype_name)
);
CREATE INDEX IF NOT EXISTS idx_campaign_archetypes_campaign ON campaign_archetypes(campaign_id);

-- ============================================================
-- CREATIVE VARIANTS
-- ============================================================
CREATE TABLE IF NOT EXISTS creative_variants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_archetype_id UUID NOT NULL REFERENCES campaign_archetypes(id) ON DELETE CASCADE,
    variant_label   VARCHAR(100) NOT NULL,
    mechanism       VARCHAR(100) NOT NULL,
    headline        TEXT NOT NULL,
    body_copy       TEXT,
    cta_text        VARCHAR(200),
    image_url       VARCHAR(500),
    landing_url     VARCHAR(500),
    tone            VARCHAR(50),
    construal_level VARCHAR(20),
    status          VARCHAR(20) DEFAULT 'draft',
    dsp_creative_id VARCHAR(100),
    impressions     BIGINT DEFAULT 0,
    clicks          BIGINT DEFAULT 0,
    conversions     INT DEFAULT 0,
    spend           DECIMAL(10,2) DEFAULT 0,
    ctr             DECIMAL(8,6) DEFAULT 0,
    cvr             DECIMAL(8,6) DEFAULT 0,
    cpa             DECIMAL(10,2) DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_creative_variants_archetype ON creative_variants(campaign_archetype_id);

-- ============================================================
-- DOMAIN LISTS
-- ============================================================
CREATE TABLE IF NOT EXISTS domain_lists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_archetype_id UUID REFERENCES campaign_archetypes(id) ON DELETE CASCADE,
    campaign_id     UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    list_type       VARCHAR(20) NOT NULL,
    domain          VARCHAR(255) NOT NULL,
    audience        VARCHAR(100),
    tier            INT DEFAULT 2,
    source          VARCHAR(50) DEFAULT 'manual',
    added_by        UUID REFERENCES users(id),
    added_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_domain_lists_archetype ON domain_lists(campaign_archetype_id);
CREATE INDEX IF NOT EXISTS idx_domain_lists_campaign ON domain_lists(campaign_id);

-- ============================================================
-- DCIL DIRECTIVES
-- ============================================================
CREATE TABLE IF NOT EXISTS dcil_directives (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    directive_type  VARCHAR(50) NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'proposed',
    campaign_archetype_id UUID REFERENCES campaign_archetypes(id),
    parameter       VARCHAR(100),
    current_value   JSONB,
    proposed_value  JSONB,
    source_finding_id VARCHAR(100),
    rationale       TEXT,
    bilateral_evidence TEXT,
    scope           VARCHAR(30),
    i_squared       DECIMAL(5,2),
    confidence      DECIMAL(5,4),
    expected_impact TEXT,
    expected_lift_pct DECIMAL(8,4),
    rollback_conditions JSONB DEFAULT '[]',
    max_change_pct  DECIMAL(5,2),
    cooldown_hours  INT DEFAULT 48,
    reviewed_by     UUID REFERENCES users(id),
    reviewed_at     TIMESTAMPTZ,
    review_notes    TEXT,
    executed_at     TIMESTAMPTZ,
    pre_change_snapshot JSONB,
    execution_result TEXT,
    rolled_back_at  TIMESTAMPTZ,
    rollback_reason TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dcil_directives_campaign ON dcil_directives(campaign_id);
CREATE INDEX IF NOT EXISTS idx_dcil_directives_status ON dcil_directives(status);

-- ============================================================
-- CONVERSION TRACKERS
-- ============================================================
CREATE TABLE IF NOT EXISTS conversion_trackers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    tracker_type    VARCHAR(30) NOT NULL,
    pixel_id        VARCHAR(100),
    pixel_snippet   TEXT,
    postback_url    VARCHAR(500),
    webhook_secret  VARCHAR(255),
    is_verified     BOOLEAN DEFAULT false,
    verified_at     TIMESTAMPTZ,
    events_received BIGINT DEFAULT 0,
    last_event_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversion_trackers_campaign ON conversion_trackers(campaign_id);

-- ============================================================
-- REPORTS
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    tier            VARCHAR(10) NOT NULL,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    report_data     JSONB NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    generated_by    VARCHAR(50) DEFAULT 'dcil',
    viewed_by_client BOOLEAN DEFAULT false,
    viewed_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_reports_campaign ON reports(campaign_id);
CREATE INDEX IF NOT EXISTS idx_reports_org ON reports(organization_id);
CREATE INDEX IF NOT EXISTS idx_reports_tier ON reports(tier);

-- ============================================================
-- CAMPAIGN PERFORMANCE SNAPSHOTS
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_performance_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    snapshot_date   DATE NOT NULL,
    impressions     BIGINT DEFAULT 0,
    clicks          BIGINT DEFAULT 0,
    conversions     INT DEFAULT 0,
    spend           DECIMAL(12,2) DEFAULT 0,
    revenue         DECIMAL(12,2) DEFAULT 0,
    ctr             DECIMAL(8,6) DEFAULT 0,
    cvr             DECIMAL(8,6) DEFAULT 0,
    cpa             DECIMAL(10,2) DEFAULT 0,
    roas            DECIMAL(8,4) DEFAULT 0,
    archetype_breakdown JSONB DEFAULT '{}',
    domain_breakdown JSONB DEFAULT '{}',
    dcil_directives_active INT DEFAULT 0,
    dcil_last_run_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(campaign_id, snapshot_date)
);
CREATE INDEX IF NOT EXISTS idx_perf_snapshots_campaign ON campaign_performance_snapshots(campaign_id);
CREATE INDEX IF NOT EXISTS idx_perf_snapshots_date ON campaign_performance_snapshots(snapshot_date DESC);

-- ============================================================
-- AUDIT LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       UUID,
    changes         JSONB,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_org ON audit_log(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);
