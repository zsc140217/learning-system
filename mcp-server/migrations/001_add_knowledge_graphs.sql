-- Migration: 添加知识图谱管理功能
-- Date: 2026-08-08
-- Description: 支持每次对话创建独立图谱，用户可删除、合并图谱

-- 1. 创建知识图谱表
CREATE TABLE IF NOT EXISTS knowledge_graphs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,              -- 图谱名称，如"FastAPI学习对话-20260808"
    description TEXT DEFAULT '',              -- 可选描述
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    node_count INTEGER DEFAULT 0             -- 节点数量（冗余字段，便于列表显示）
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_kg_created ON knowledge_graphs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kg_name ON knowledge_graphs(name);

-- 2. 修改 entities 表，添加 graph_id 外键
ALTER TABLE entities
ADD COLUMN IF NOT EXISTS graph_id INTEGER REFERENCES knowledge_graphs(id) ON DELETE CASCADE;

-- 索引
CREATE INDEX IF NOT EXISTS idx_entities_graph ON entities(graph_id);

-- 3. 为 knowledge_graphs 表创建更新时间触发器
CREATE TRIGGER update_knowledge_graphs_updated_at
BEFORE UPDATE ON knowledge_graphs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 4. 创建默认图谱（用于迁移现有数据）
INSERT INTO knowledge_graphs (name, description, node_count)
VALUES ('默认图谱', '系统自动创建的默认图谱，包含迁移前的所有知识点', 0)
ON CONFLICT DO NOTHING;

-- 5. 将现有的 entities 分配到默认图谱
UPDATE entities
SET graph_id = (SELECT id FROM knowledge_graphs WHERE name = '默认图谱')
WHERE graph_id IS NULL;

-- 6. 更新默认图谱的节点计数
UPDATE knowledge_graphs
SET node_count = (SELECT COUNT(*) FROM entities WHERE graph_id = knowledge_graphs.id)
WHERE name = '默认图谱';

-- 7. 添加表注释
COMMENT ON TABLE knowledge_graphs IS '知识图谱管理表，每个图谱包含一组相关的知识节点';
COMMENT ON COLUMN knowledge_graphs.name IS '图谱名称，如"FastAPI学习-20260808"';
COMMENT ON COLUMN knowledge_graphs.node_count IS '冗余字段，加速列表查询';
COMMENT ON COLUMN entities.graph_id IS '所属图谱ID，用于隔离不同对话的知识点';
