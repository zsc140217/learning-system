-- Migration: 初始化知识图谱数据库架构
-- Date: 2026-08-08
-- Description: 创建基础表（entities, relations, entity_embeddings）

-- 1. 启用 pgvector 扩展（如果未安装，需要先安装 pgvector）
-- 注意：pgvector 扩展需要单独安装，如果未安装则跳过向量搜索功能
-- 安装方法：https://github.com/pgvector/pgvector
-- CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 创建实体表
CREATE TABLE IF NOT EXISTS entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,           -- 实体名称（唯一标识）
    entity_type VARCHAR(50) NOT NULL,            -- 实体类型（concept/technology/method/tool）
    observations TEXT[] NOT NULL DEFAULT '{}',   -- 观察列表
    metadata JSONB DEFAULT '{}',                 -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_updated ON entities(updated_at DESC);

-- 3. 创建关系表
CREATE TABLE IF NOT EXISTS relations (
    id SERIAL PRIMARY KEY,
    from_entity VARCHAR(255) NOT NULL,           -- 源实体名称
    to_entity VARCHAR(255) NOT NULL,             -- 目标实体名称
    relation_type VARCHAR(50) NOT NULL,          -- 关系类型（uses/requires/related_to/belongs_to）
    metadata JSONB DEFAULT '{}',                 -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(from_entity, to_entity, relation_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity);
CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);

-- 4. 创建实体向量嵌入表（用于语义搜索）
-- 注意：需要 pgvector 扩展支持，暂时跳过
-- CREATE TABLE IF NOT EXISTS entity_embeddings (
--     id SERIAL PRIMARY KEY,
--     entity_id INTEGER UNIQUE NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
--     embedding vector(1536),                      -- DeepSeek embedding 维度
--     created_at TIMESTAMP DEFAULT NOW()
-- );

-- 向量索引（HNSW 算法，用于快速相似度搜索）
-- CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON entity_embeddings
-- USING hnsw (embedding vector_cosine_ops);

-- 5. 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 6. 为 entities 表添加更新时间触发器
DROP TRIGGER IF EXISTS update_entities_updated_at ON entities;
CREATE TRIGGER update_entities_updated_at
BEFORE UPDATE ON entities
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 7. 添加表注释
COMMENT ON TABLE entities IS '知识图谱实体表，存储知识点、技术、概念等';
COMMENT ON TABLE relations IS '知识图谱关系表，存储实体之间的关系';
COMMENT ON TABLE entity_embeddings IS '实体向量嵌入表，用于语义搜索';
COMMENT ON COLUMN entities.observations IS '观察列表，存储关于该实体的多个事实描述';
COMMENT ON COLUMN entity_embeddings.embedding IS 'DeepSeek embedding 向量（1536维）';
