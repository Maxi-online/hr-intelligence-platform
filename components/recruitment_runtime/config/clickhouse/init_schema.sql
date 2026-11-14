-- Clickhouse tables diagrams for Candidate Analysis System
-- Optimized to maximize the productivity of analytical queries

-- Database development
CREATE DATABASE IF NOT EXISTS hrhelp;

-- Use of the database
USE hrhelp;

-- ===============================
-- MAIN TABLES FOR CANDIDATES
-- ===============================

-- Table of candidates (core analytical table)
CREATE TABLE IF NOT EXISTS candidates (
    -- Identifiers
    id String,
    hh_id String,
    
    -- Basic information
    name LowCardinality(String),
    title String,
    age UInt8,
    gender LowCardinality(String),
    
    -- Locacy
    area_id UInt32,
    area_name LowCardinality(String),
    area_country LowCardinality(String),
    
    -- Experience
    experience_total_months UInt16,
    experience_level LowCardinality(String), -- noExperience, between1And3, etc.
    
    -- Expectations for salaries
    salary_from Nullable(UInt32),
    salary_to Nullable(UInt32),
    salary_currency LowCardinality(String),
    
    -- Skills (rapid search)
    skills Array(String),
    verified_skills Array(String),
    
    -- Time
    updated_at DateTime64(3),
    created_at DateTime64(3) DEFAULT now64(),
    last_searched DateTime64(3),
    
    -- Meterics
    search_count UInt32 DEFAULT 0,
    ai_analysis_status LowCardinality(String) DEFAULT 'pending', -- pending, analyzing, completed, failed
    
    -- URL and contacts  
    url String,
    photo_url Nullable(String),
    has_cover_letter Bool DEFAULT false,
    
    -- Rapid search index
    INDEX idx_skills skills TYPE bloom_filter GRANULARITY 1,
    INDEX idx_title title TYPE bloom_filter GRANULARITY 1,
    INDEX idx_area area_name TYPE set(100) GRANULARITY 1
)
ENGINE = MergeTree()
-- Month-by-month party for quick access to up-to-date data
PARTITION BY toYYYYMM(created_at)
-- Sorting for optimal search performance
ORDER BY (area_id, experience_level, created_at, id)
-- TTL for automatic clean-up of old data (optimal))
-- TTL created_at + INTERVAL 2 YEAR DELETE
SETTINGS index_granularity = 8192;

-- ===============================
-- AI ANALYSIS AND RANGERATION
-- ===============================

-- Table AI Skills Analysis
CREATE TABLE IF NOT EXISTS ai_skill_analysis (
    candidate_id String,
    skill_name String,
    relevance_score Float32,
    proficiency_level LowCardinality(String), -- Junior, Middle, Senior, Expert
    years_experience Nullable(Float32),
    ai_confidence Float32,
    search_query String,
    analysis_timestamp DateTime64(3) DEFAULT now64(),
    
    -- Additional metrics for ranking
    keyword_relevance_score Nullable(Float32),
    filter_match_score Nullable(Float32),
    recency_score Nullable(Float32),
    profile_completeness_score Nullable(Float32)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(analysis_timestamp)
ORDER BY (candidate_id, skill_name, analysis_timestamp)
SETTINGS index_granularity = 8192;

-- Table of overall AI evaluations of candidates
CREATE TABLE IF NOT EXISTS ai_candidate_scores (
    candidate_id String,
    search_query String,
    overall_score Float32,
    analysis_summary String,
    reasoning Nullable(String),
    processing_time_ms UInt32,
    
    -- Detailed Streams
    keyword_relevance_score Float32,
    filter_match_score Float32,
    recency_score Float32,
    profile_completeness_score Float32,
    
    -- Weights of ranking
    weight_keyword_relevance Float32 DEFAULT 0.4,
    weight_filter_match Float32 DEFAULT 0.3,
    weight_recency Float32 DEFAULT 0.2,
    weight_profile_completeness Float32 DEFAULT 0.1,
    
    created_at DateTime64(3) DEFAULT now64()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (search_query, candidate_id)
SETTINGS index_granularity = 8192;

-- ===============================
-- PEACEFUL REQUESTS AND STATISTICS
-- ===============================

-- Table of search requests for analysts
CREATE TABLE IF NOT EXISTS search_queries (
    query_id String DEFAULT generateUUIDv4(),
    search_text Nullable(String),
    
    -- Search Filters
    area_ids Array(UInt32),
    salary_from Nullable(UInt32),
    salary_to Nullable(UInt32),
    experience_level Nullable(String),
    employment_types Array(String),
    schedule_types Array(String),
    
    -- Results
    total_results UInt32,
    results_shown UInt32,
    processing_time_ms UInt32,
    
    -- User and Time
    user_id Nullable(String),
    session_id Nullable(String),
    timestamp DateTime64(3) DEFAULT now64(),
    
    -- Source of request
    source LowCardinality(String) DEFAULT 'web' -- web, api, mobile
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, query_id)
SETTINGS index_granularity = 8192;

-- ===============================
-- METRICS OF PRODUCTION
-- ===============================

-- Monitoring system metric table
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_name LowCardinality(String),
    metric_value Float64,
    metric_tags Map(String, String),
    timestamp DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (metric_name, timestamp)
TTL timestamp + INTERVAL 3 MONTH DELETE
SETTINGS index_granularity = 8192;

-- ===============================
-- BACKGROUND DATA (DIMENSIONS)
-- ===============================

-- Region/region directory
CREATE TABLE IF NOT EXISTS dim_areas (
    id UInt32,
    name String,
    country String,
    type LowCardinality(String), -- city, region, country
    parent_id Nullable(UInt32),
    created_at DateTime64(3) DEFAULT now64()
)
ENGINE = MergeTree()
ORDER BY (id)
SETTINGS index_granularity = 8192;

-- Skills guide
CREATE TABLE IF NOT EXISTS dim_skills (
    skill_name String,
    category LowCardinality(String), -- programming, management, design, etc.
    popularity_score Float32 DEFAULT 0.0,
    total_candidates UInt32 DEFAULT 0,
    last_updated DateTime64(3) DEFAULT now64()
)
ENGINE = ReplacingMergeTree(last_updated)
ORDER BY (skill_name)
SETTINGS index_granularity = 8192;

-- ===============================
-- MATERIAL SUBMISSIONS
-- ===============================
-- It's only created after all the tables are created!

-- Rapid statistics on skills
-- CREATE MATERIALIZED VIEW IF NOT EXISTS mv_skill_stats
-- ENGINE = SummingMergeTree()
-- ORDER BY (skill_name, experience_level)
-- AS SELECT
--     skill_name,
--     experience_level,
--     count() as candidate_count,
--     avg(salary_from) as avg_salary_from,
--     avg(salary_to) as avg_salary_to,
--     toYYYYMM(created_at) as month_created
-- FROM candidates
-- ARRAY JOIN skills AS skill_name
-- WHERE skill_name != ''
-- GROUP BY skill_name, experience_level, month_created;

-- Statistics by area
-- CREATE MATERIALIZED VIEW IF NOT EXISTS mv_area_stats
-- ENGINE = SummingMergeTree()
-- ORDER BY (area_name, experience_level)
-- AS SELECT
--     area_name,
--     experience_level,
--     count() as candidate_count,
--     avg(salary_from) as avg_salary_from,
--     avg(salary_to) as avg_salary_to,
--     toYYYYMM(created_at) as month_created
-- FROM candidates
-- WHERE area_name != ''
-- GROUP BY area_name, experience_level, month_created;

-- ===============================
-- INDICES FOR THE OBJECTIVE
-- ===============================

-- Additional indices will be created automatically on the basis of requests

-- ===============================
-- COMMENTS AND DOCUMENTATION
-- ===============================

-- This file creates an optimized scheme for the Candidate Analysis system
-- Basic principles of optimization:
-- 1. Colon storage for rapid analyst
-- 2. Time-lotting for efficient clean-up
-- 3. LowCardinality for strings with limited set of values
-- 4. Bloom filter Indexes for Full Text Search
-- 5. Materialized submissions for preliminary aggregations
-- 6. TTL for automatic cleansing of old data