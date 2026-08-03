"""
Test LLM Integration for Session Analyzer
Tests hybrid strategy: LLM + Regex fallback
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp-server"))

import pytest
import asyncio
from src.agents.session_analyzer import SessionAnalyzer
from src.llm.factory import LLMProviderFactory
from src.bus.agent_bus import AgentBus


@pytest.fixture
def agent_bus():
    """Create event bus for testing"""
    return AgentBus()


@pytest.fixture
def llm_config():
    """LLM configuration for DeepSeek"""
    return {
        "llm": {
            "provider": "deepseek",
            "api_key": "sk-1c9d612d9af44212a26f48525e5faf79",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
            "temperature": 0.3
        }
    }


@pytest.fixture
def sample_transcript():
    """Sample conversation transcript"""
    return [
        {
            "role": "user",
            "content": "如何实现异步任务？"
        },
        {
            "role": "assistant",
            "content": "可以使用 asyncio.create_task 创建后台任务。它接受一个协程对象，返回一个 Task 对象，不会阻塞当前协程的执行。"
        },
        {
            "role": "user",
            "content": "什么是 MCP 协议？"
        },
        {
            "role": "assistant",
            "content": "MCP（Model Context Protocol）是一个标准化协议，用于 AI 应用与外部数据源的集成。它定义了资源、工具、提示等核心概念。"
        }
    ]


@pytest.mark.asyncio
async def test_llm_analyze_conversation(llm_config, sample_transcript, agent_bus):
    """测试 LLM 语义分析"""
    analyzer = SessionAnalyzer("test_analyzer_001", agent_bus, llm_config)

    result = await analyzer._analyze_conversation("test_session_001", sample_transcript)

    # 验证返回结构
    assert result["method"] == "llm"
    assert "knowledge_points" in result
    assert "relations" in result
    assert "stats" in result

    # 验证知识点
    knowledge_points = result["knowledge_points"]
    assert len(knowledge_points) > 0

    # 验证字段完整性
    for kp in knowledge_points:
        assert "title" in kp
        assert "content" in kp
        assert "difficulty" in kp
        assert "category" in kp
        assert "importance" in kp
        assert "prerequisites" in kp
        assert "estimated_hours" in kp
        assert "reasoning" in kp

        # 验证难度范围
        assert 0.3 <= kp["difficulty"] <= 0.9

        # 验证重要性范围
        assert 0.0 <= kp["importance"] <= 1.0

    # 验证应该提取到关键概念
    concept_names = [kp["title"] for kp in knowledge_points]
    concept_text = " ".join(concept_names).lower()

    # 应该包含 asyncio 或 MCP 相关概念
    assert "asyncio" in concept_text or "create_task" in concept_text or "mcp" in concept_text

    print(f"LLM 分析成功：提取 {len(knowledge_points)} 个概念")
    for kp in knowledge_points:
        print(f"  - {kp['title']} (难度: {kp['difficulty']}, 类别: {kp['category']})")


@pytest.mark.asyncio
async def test_regex_fallback(sample_transcript, agent_bus):
    """测试正则降级模式"""
    # 不配置 LLM，强制使用正则
    analyzer = SessionAnalyzer("test_analyzer_002", agent_bus, config=None)
    analyzer.use_llm = False

    result = await analyzer._analyze_conversation("test_session_002", sample_transcript)

    # 验证降级到正则
    assert result["method"] == "regex"
    assert "knowledge_points" in result

    knowledge_points = result["knowledge_points"]
    assert len(knowledge_points) > 0

    # 正则模式也应该有基本字段
    for kp in knowledge_points:
        assert "title" in kp
        assert "difficulty" in kp
        assert "reasoning" in kp
        assert kp["reasoning"] == "基于正则匹配" or kp["reasoning"] == "基于内容提取"

    print(f"正则降级成功：提取 {len(knowledge_points)} 个概念")


@pytest.mark.asyncio
async def test_accuracy_comparison(llm_config, sample_transcript, agent_bus):
    """准确率对比测试：LLM vs 正则"""

    # 人工标注的真实概念
    expected_concepts = [
        "asyncio.create_task",
        "协程",
        "MCP",
        "Model Context Protocol"
    ]

    # LLM 分析
    analyzer_llm = SessionAnalyzer("test_analyzer_004", agent_bus, llm_config)
    llm_result = await analyzer_llm._analyze_conversation("test_session_004", sample_transcript)
    llm_concepts = [kp["title"] for kp in llm_result["knowledge_points"]]

    # 正则分析
    analyzer_regex = SessionAnalyzer("test_analyzer_005", agent_bus, config=None)
    analyzer_regex.use_llm = False
    regex_result = await analyzer_regex._analyze_conversation("test_session_005", sample_transcript)
    regex_concepts = [kp["title"] for kp in regex_result["knowledge_points"]]

    # 计算准确率（模糊匹配）
    def calculate_accuracy(extracted, expected):
        correct = 0
        for exp in expected:
            exp_lower = exp.lower()
            if any(exp_lower in ext.lower() or ext.lower() in exp_lower for ext in extracted):
                correct += 1
        return correct / len(expected) if expected else 0

    llm_accuracy = calculate_accuracy(llm_concepts, expected_concepts)
    regex_accuracy = calculate_accuracy(regex_concepts, expected_concepts)

    print(f"\n准确率对比：")
    print(f"  LLM 准确率: {llm_accuracy * 100:.1f}%")
    print(f"  正则准确率: {regex_accuracy * 100:.1f}%")
    print(f"  提升幅度: {(llm_accuracy - regex_accuracy) * 100:.1f}%")

    # LLM 应该更准确
    assert llm_accuracy >= regex_accuracy, "LLM 准确率应该不低于正则"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
