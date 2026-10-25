-- 매일 동기부여 DB 스키마 (PostgreSQL)
-- 사용: psql -U youheaukjun -f db/schema.sql

CREATE DATABASE quotes_db;
\c quotes_db;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 마스터 테이블
CREATE TABLE IF NOT EXISTS fields (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS professions (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    group_name VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS keywords (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    group_name VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS situations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    group_name VARCHAR(100)
);

-- 수집 이력
CREATE TABLE IF NOT EXISTS collection_logs (
    id VARCHAR(36) PRIMARY KEY,
    category VARCHAR(100),
    requested_count INT,
    saved_count INT,
    duplicate_count INT,
    error_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 저자
CREATE TABLE IF NOT EXISTS authors (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    nationality CHAR(2) NOT NULL,
    birth_year INT NOT NULL,
    profession_id VARCHAR(36) REFERENCES professions(id),
    field_id VARCHAR(36) REFERENCES fields(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 저자 관계
CREATE TABLE IF NOT EXISTS author_relations (
    id VARCHAR(36) PRIMARY KEY,
    from_author_id VARCHAR(36) NOT NULL REFERENCES authors(id),
    to_author_id VARCHAR(36) NOT NULL REFERENCES authors(id),
    relation_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(from_author_id, to_author_id, relation_type)
);

-- 명언
CREATE TABLE IF NOT EXISTS quotes (
    id VARCHAR(36) PRIMARY KEY,
    text TEXT NOT NULL,
    text_original TEXT,
    original_language VARCHAR(10),
    author_id VARCHAR(36) NOT NULL REFERENCES authors(id),
    source VARCHAR(500),
    year INT,
    keywords JSONB NOT NULL,
    situation JSONB NOT NULL,
    keyword_ids VARCHAR(36)[],
    situation_ids VARCHAR(36)[],
    need_types VARCHAR(20)[],                            -- motivation / comfort / reflection / insight / relationship / humor
    status VARCHAR(20) NOT NULL DEFAULT 'draft',         -- draft / reviewed / published / rejected
    source_reliability VARCHAR(20) DEFAULT 'unknown',    -- verified / attributed / disputed / unknown
    collection_log_id VARCHAR(36) REFERENCES collection_logs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 행동 로그 (암묵적 개인화용)
CREATE TABLE IF NOT EXISTS user_interactions (
    id VARCHAR(36) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    quote_id VARCHAR(36) NOT NULL REFERENCES quotes(id),
    interaction_type VARCHAR(20) NOT NULL,  -- like, unlike, share, view_detail, dwell
    dwell_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_interactions_device ON user_interactions(device_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON user_interactions(created_at);
CREATE INDEX IF NOT EXISTS idx_interactions_device_type ON user_interactions(device_id, interaction_type);

-- 유사도 검색용 trigram 인덱스
CREATE INDEX IF NOT EXISTS idx_quotes_text_trgm ON quotes USING gin (text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_quotes_text_original_trgm ON quotes USING gin (text_original gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_quotes_need_types ON quotes USING gin (need_types);
