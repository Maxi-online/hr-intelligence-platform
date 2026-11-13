-- Схемы таблиц ClickHouse для Candidate Analysis системы
-- Оптимизировано для максимальной производительности аналитических запросов

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS hrhelp;

-- Использование базы данных
USE hrhelp;

-- ===============================
-- ОСНОВНЫЕ ТАБЛИЦЫ ДЛЯ КАНДИДАТОВ
-- ===============================

-- Таблица кандидатов (основная аналитическая таблица)
CREATE TABLE IF NOT EXISTS candidates (
    -- Идентификаторы
    id String,
    hh_id String,
    
    -- Основная информация
    name LowCardinality(String),
    title String,
    age UInt8,
    gender LowCardinality(String),
    
    -- Локация
    area_id UInt32,
    area_name LowCardinality(String),
    area_country LowCardinality(String),
    
    -- Опыт работы
    experience_total_months UInt16,
    experience_level LowCardinality(String), -- noExperience, between1And3, etc.
    
    -- Зарплатные ожидания
    salary_from Nullable(UInt32),
    salary_to Nullable(UInt32),
    salary_currency LowCardinality(String),
    
    -- Навыки (для быстрого поиска)
    skills Array(String),
    verified_skills Array(String),
    
    -- Время
    updated_at DateTime64(3),
    created_at DateTime64(3) DEFAULT now64(),
    last_searched DateTime64(3),
    
    -- Метрики
    search_count UInt32 DEFAULT 0,
    ai_analysis_status LowCardinality(String) DEFAULT 'pending', -- pending, analyzing, completed, failed
    
    -- URL и контакты  
    url String,
    photo_url Nullable(String),
    has_cover_letter Bool DEFAULT false,
    
    -- Индекс для быстрого поиска
    INDEX idx_skills skills TYPE bloom_filter GRANULARITY 1,
    INDEX idx_title title TYPE bloom_filter GRANULARITY 1,
    INDEX idx_area area_name TYPE set(100) GRANULARITY 1
)
ENGINE = MergeTree()
-- Партиционирование по месяцам для быстрого доступа к свежим данным
PARTITION BY toYYYYMM(created_at)
-- Сортировка для оптимальной производительности поиска
ORDER BY (area_id, experience_level, created_at, id)
-- TTL для автоматической очистки старых данных (опционально)
-- TTL created_at + INTERVAL 2 YEAR DELETE
SETTINGS index_granularity = 8192;

-- ===============================
-- AI АНАЛИЗ И РАНЖИРОВАНИЕ
-- ===============================

-- Таблица AI анализа навыков
CREATE TABLE IF NOT EXISTS ai_skill_analysis (
    candidate_id String,
    skill_name String,
    relevance_score Float32,
    proficiency_level LowCardinality(String), -- Junior, Middle, Senior, Expert
    years_experience Nullable(Float32),
    ai_confidence Float32,
    search_query String,
    analysis_timestamp DateTime64(3) DEFAULT now64(),
    
    -- Дополнительные метрики для ранжирования
    keyword_relevance_score Nullable(Float32),
    filter_match_score Nullable(Float32),
    recency_score Nullable(Float32),
    profile_completeness_score Nullable(Float32)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(analysis_timestamp)
ORDER BY (candidate_id, skill_name, analysis_timestamp)
SETTINGS index_granularity = 8192;

-- Таблица общих AI оценок кандидатов
CREATE TABLE IF NOT EXISTS ai_candidate_scores (
    candidate_id String,
    search_query String,
    overall_score Float32,
    analysis_summary String,
    reasoning Nullable(String),
    processing_time_ms UInt32,
    
    -- Детализированные скоры
    keyword_relevance_score Float32,
    filter_match_score Float32,
    recency_score Float32,
    profile_completeness_score Float32,
    
    -- Веса ранжирования
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
-- ПОИСКОВЫЕ ЗАПРОСЫ И СТАТИСТИКА
-- ===============================

-- Таблица поисковых запросов для аналитики
CREATE TABLE IF NOT EXISTS search_queries (
    query_id String DEFAULT generateUUIDv4(),
    search_text Nullable(String),
    
    -- Фильтры поиска
    area_ids Array(UInt32),
    salary_from Nullable(UInt32),
    salary_to Nullable(UInt32),
    experience_level Nullable(String),
    employment_types Array(String),
    schedule_types Array(String),
    
    -- Результаты
    total_results UInt32,
    results_shown UInt32,
    processing_time_ms UInt32,
    
    -- Пользователь и время
    user_id Nullable(String),
    session_id Nullable(String),
    timestamp DateTime64(3) DEFAULT now64(),
    
    -- Источник запроса
    source LowCardinality(String) DEFAULT 'web' -- web, api, mobile
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, query_id)
SETTINGS index_granularity = 8192;

-- ===============================
-- МЕТРИКИ ПРОИЗВОДИТЕЛЬНОСТИ
-- ===============================

-- Таблица метрик системы для мониторинга
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
-- СПРАВОЧНЫЕ ДАННЫЕ (DIMENSIONS)
-- ===============================

-- Справочник областей/регионов
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

-- Справочник навыков
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
-- МАТЕРИАЛИЗОВАННЫЕ ПРЕДСТАВЛЕНИЯ
-- ===============================
-- ВАЖНО: Создаем только ПОСЛЕ создания всех таблиц!

-- Быстрая статистика по навыкам
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

-- Статистика по областям
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
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ
-- ===============================

-- Дополнительные индексы будут созданы автоматически на основе запросов

-- ===============================
-- КОММЕНТАРИИ И ДОКУМЕНТАЦИЯ
-- ===============================

-- Этот файл создает оптимизированную схему для Candidate Analysis системы
-- Основные принципы оптимизации:
-- 1. Колоночное хранение для быстрой аналитики
-- 2. Партиционирование по времени для эффективной очистки
-- 3. LowCardinality для строк с ограниченным набором значений
-- 4. Bloom filter индексы для полнотекстового поиска
-- 5. Материализованные представления для предварительных агрегаций
-- 6. TTL для автоматической очистки старых данных