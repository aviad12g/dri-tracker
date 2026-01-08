-- DRI Tracker Initial Schema
-- Version: 001
-- Date: 2025-12-22

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ======================
-- TABLE 1: actors_config
-- ======================
-- Stores curated list of tracked actors with platform identifiers
CREATE TABLE actors_config (
    actor_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('mega', 'core', 'prop', 'control')),
    x_handle VARCHAR(64),
    tiktok_handle VARCHAR(64),
    youtube_channel_id VARCHAR(64),
    instagram_handle VARCHAR(64),
    rumble_channel_id VARCHAR(64),
    telegram_channel_username VARCHAR(64),
    cozy_slug VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_actors_tier ON actors_config(tier);

-- ======================
-- TABLE 2: actor_daily_platform_metrics
-- ======================
-- One row per actor per platform per day
CREATE TABLE actor_daily_platform_metrics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE NOT NULL,
    actor_id VARCHAR(64) NOT NULL REFERENCES actors_config(actor_id),
    platform VARCHAR(32) NOT NULL CHECK (platform IN ('x', 'tiktok', 'youtube', 'youtube_short', 'instagram', 'reels', 'rumble', 'telegram', 'cozy')),
    followers BIGINT,
    views_total BIGINT,
    shares_total BIGINT,
    likes_total BIGINT,
    comments_total BIGINT,
    raw_source JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date, actor_id, platform)
);

CREATE INDEX idx_adpm_date ON actor_daily_platform_metrics(date);
CREATE INDEX idx_adpm_actor ON actor_daily_platform_metrics(actor_id);
CREATE INDEX idx_adpm_platform ON actor_daily_platform_metrics(platform);
CREATE INDEX idx_adpm_date_actor ON actor_daily_platform_metrics(date, actor_id);

-- ======================
-- TABLE 3: bottom_funnel_daily
-- ======================
-- One row per day for bottom funnel metrics
CREATE TABLE bottom_funnel_daily (
    date DATE PRIMARY KEY,
    telegram_views_total BIGINT DEFAULT 0,
    rumble_live_concurrents_peak BIGINT DEFAULT 0,
    x_impressions_feeder BIGINT DEFAULT 0,
    raw_source JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ======================
-- TABLE 4: search_interest_daily
-- ======================
-- One row per keyword per day per region
CREATE TABLE search_interest_daily (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE NOT NULL,
    keyword VARCHAR(128) NOT NULL,
    region VARCHAR(16) NOT NULL CHECK (region IN ('US', 'GLOBAL')),
    volume_index INTEGER NOT NULL CHECK (volume_index >= 0 AND volume_index <= 100),
    raw_source JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date, keyword, region)
);

CREATE INDEX idx_sid_date ON search_interest_daily(date);
CREATE INDEX idx_sid_keyword ON search_interest_daily(keyword);
CREATE INDEX idx_sid_region ON search_interest_daily(region);
CREATE INDEX idx_sid_date_keyword ON search_interest_daily(date, keyword);

-- ======================
-- TABLE 5: political_events
-- ======================
-- One row per political event
CREATE TABLE political_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE NOT NULL,
    actor_id VARCHAR(64) REFERENCES actors_config(actor_id),
    description TEXT NOT NULL,
    score_delta DECIMAL(3,2) NOT NULL CHECK (score_delta >= 0 AND score_delta <= 5),
    evidence_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pe_date ON political_events(date);
CREATE INDEX idx_pe_actor ON political_events(actor_id);

-- ======================
-- TABLE 6: dri_daily (Derived)
-- ======================
-- One row per day with computed DRI and subscores
CREATE TABLE dri_daily (
    date DATE PRIMARY KEY,
    -- Raw computed values
    v_vir DECIMAL(20,4),
    r_rad DECIMAL(20,4),
    delta_s DECIMAL(10,4),
    pol DECIMAL(5,2),
    -- Normalized scores (0-100)
    v_score DECIMAL(5,2) CHECK (v_score >= 0 AND v_score <= 100),
    r_score DECIMAL(5,2) CHECK (r_score >= 0 AND r_score <= 100),
    s_score DECIMAL(5,2) CHECK (s_score >= 0 AND s_score <= 100),
    p_score DECIMAL(5,2) CHECK (p_score >= 0 AND p_score <= 100),
    -- Master index
    dri DECIMAL(5,2) CHECK (dri >= 0 AND dri <= 100),
    -- Data quality
    data_quality_summary JSONB NOT NULL DEFAULT '{}',
    -- Alerts
    is_spike BOOLEAN DEFAULT FALSE,
    spike_details JSONB,
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_dri_date ON dri_daily(date);

-- ======================
-- HELPER TABLES
-- ======================

-- Keywords configuration
CREATE TABLE keywords_config (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    keyword VARCHAR(128) NOT NULL UNIQUE,
    category VARCHAR(20) NOT NULL CHECK (category IN ('soft', 'hard')),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_kw_category ON keywords_config(category);

-- Rolling statistics cache for normalization
CREATE TABLE rolling_stats (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    metric_name VARCHAR(32) NOT NULL,
    as_of_date DATE NOT NULL,
    window_days INTEGER NOT NULL,
    mean_value DECIMAL(20,6),
    std_value DECIMAL(20,6),
    sample_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(metric_name, as_of_date, window_days)
);

CREATE INDEX idx_rs_metric ON rolling_stats(metric_name);
CREATE INDEX idx_rs_date ON rolling_stats(as_of_date);

-- ======================
-- TRIGGERS
-- ======================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_actors_config_updated_at
    BEFORE UPDATE ON actors_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bottom_funnel_daily_updated_at
    BEFORE UPDATE ON bottom_funnel_daily
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_political_events_updated_at
    BEFORE UPDATE ON political_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dri_daily_updated_at
    BEFORE UPDATE ON dri_daily
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ======================
-- VIEWS
-- ======================

-- Latest DRI with changes
CREATE VIEW dri_with_changes AS
SELECT 
    d.*,
    LAG(d.dri) OVER (ORDER BY d.date) as prev_dri,
    d.dri - LAG(d.dri) OVER (ORDER BY d.date) as dri_change,
    CASE 
        WHEN LAG(d.dri) OVER (ORDER BY d.date) > 0 
        THEN ((d.dri - LAG(d.dri) OVER (ORDER BY d.date)) / LAG(d.dri) OVER (ORDER BY d.date)) * 100
        ELSE 0 
    END as dri_pct_change
FROM dri_daily d;

-- Actor engagement summary
CREATE VIEW actor_engagement_summary AS
SELECT 
    a.actor_id,
    a.name,
    a.tier,
    m.date,
    SUM(m.views_total) as total_views,
    SUM(m.shares_total) as total_shares,
    SUM(m.likes_total) as total_likes,
    MAX(m.followers) as max_followers
FROM actors_config a
JOIN actor_daily_platform_metrics m ON a.actor_id = m.actor_id
GROUP BY a.actor_id, a.name, a.tier, m.date;


