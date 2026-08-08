import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { mcpClient } from '@/services/mcpClient';
import { skillLoader } from '@/services/skillLoader';
import { UIRenderer } from './ui/UIRenderer';
import { TaskProgress } from './TaskProgress';
import { ConfirmDialog } from './ConfirmDialog';
import { KnowledgeGraphView } from './KnowledgeGraph';
import { KnowledgeConfirmDialog } from './KnowledgeConfirmDialog';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface KnowledgePoint {
  title: string;
  content: string;
  tags: string[];
  type: string;
}

interface GraphOption {
  id: number;
  name: string;
  node_count: number;
}

export const ChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [graphData, setGraphData] = useState<any>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingKnowledge, setPendingKnowledge] = useState<KnowledgePoint[]>([]);
  const [summaryProgress, setSummaryProgress] = useState<string>('');
  const [existingGraphs, setExistingGraphs] = useState<GraphOption[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    addMessage,
    connected,
    activeUI,
    setActiveUI,
    activeTasks,
    pendingConfirmation,
    sessionId,
    setSessionId,
    clearMessages,
  } = useAppStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 加载知识图谱列表
  useEffect(() => {
    loadGraphs();
  }, []);

  const loadGraphs = async () => {
    try {
      const response = await mcpClient.callTool('list_knowledge_graphs', {});
      const parsed = mcpClient.parseResponse(response);

      if (parsed.success && parsed.graphs) {
        setExistingGraphs(parsed.graphs);
      }
    } catch (error) {
      console.error('Failed to load graphs:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading || !connected) return;

    const userMessage = input.trim();
    setInput('');

    // 检测并加载 Skill
    const skillName = skillLoader.detectSkillTrigger(userMessage);
    let skillContext: string | null = null;

    if (skillName) {
      try {
        const skill = await skillLoader.loadSkill(skillName);
        if (skill) {
          // 提取 Skill 文档内容（不附加到用户消息中，而是作为独立参数）
          skillContext = `# ${skill.metadata.name}\n\n${skill.content}`;
          console.log(`[Skill] Loaded skill: ${skillName}`);

          // 显示系统提示
          addMessage({
            role: 'system',
            content: `已加载 Skill: ${skill.metadata.description}`,
          });
        }
      } catch (error) {
        console.error('[Skill] Failed to load:', error);
      }
    }

    addMessage({
      role: 'user',
      content: userMessage,
    });

    setLoading(true);

    try {
      // Call chat tool with session_id and optional skill_context
      const params: any = {
        message: userMessage,
        session_id: sessionId
      };

      // 如果有 Skill 上下文，传递给后端
      if (skillContext) {
        params.skill_context = skillContext;
      }

      const response = await mcpClient.callTool('chat', params);

      const parsed = mcpClient.parseResponse(response);

      // Handle UI template
      if (parsed.uiTemplate) {
        setActiveUI(parsed.uiTemplate);
        addMessage({
          role: 'assistant',
          content: 'Here is the result:',
          uiTemplate: parsed.uiTemplate,
        });
      }
      // Handle task
      else if (parsed.taskHandle) {
        addMessage({
          role: 'system',
          content: `Task started: ${parsed.taskHandle.task_id}`,
        });
      }
      // Handle regular response
      else {
        // Extract only the response field, not the entire JSON
        const assistantMessage = parsed.result?.response ||
                                JSON.stringify(parsed.result, null, 2);

        addMessage({
          role: 'assistant',
          content: assistantMessage,
        });

        // Save session_id for next turn
        if (parsed.result?.session_id) {
          setSessionId(parsed.result.session_id);
        }
      }
    } catch (error) {
      addMessage({
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    // Clear session_id to start a new conversation
    setSessionId(null);

    // Clear message history
    clearMessages();

    // Optional: show system message
    addMessage({
      role: 'system',
      content: '已开始新会话',
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLoadGraph = async () => {
    setLoadingGraph(true);
    try {
      // Call ui_knowledge_graph tool to get graph data
      console.log('[KnowledgeGraph] Calling ui_knowledge_graph tool...');
      const response = await mcpClient.callTool('ui_knowledge_graph', {});
      console.log('[KnowledgeGraph] Response received:', response);

      // Parse response to extract graph data
      const parsed = mcpClient.parseResponse(response);
      console.log('[KnowledgeGraph] Parsed:', parsed);

      if (parsed.uiTemplate?.data) {
        console.log('[KnowledgeGraph] Graph data:', parsed.uiTemplate.data);
        setGraphData(parsed.uiTemplate.data);
        setShowGraph(true);
        addMessage({
          role: 'system',
          content: 'Knowledge graph loaded successfully',
        });
      } else {
        console.error('[KnowledgeGraph] No graph data found in response');
        addMessage({
          role: 'system',
          content: 'No graph data available',
        });
      }
    } catch (error) {
      console.error('[KnowledgeGraph] Error:', error);
      addMessage({
        role: 'system',
        content: `Failed to load graph: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
    } finally {
      setLoadingGraph(false);
    }
  };

  // 搜索节点（新增）
  const handleSearchNodes = async (query: string) => {
    try {
      console.log('[KnowledgeGraph] Searching nodes:', query);
      const response = await mcpClient.callTool('search_nodes', { query });
      const parsed = mcpClient.parseResponse(response);
      return parsed.result || [];
    } catch (error) {
      console.error('[KnowledgeGraph] Search failed:', error);
      return [];
    }
  };

  // 获取节点详情（新增）
  const handleOpenNodeDetails = async (nodeId: string) => {
    try {
      console.log('[KnowledgeGraph] Opening node details:', nodeId);
      const response = await mcpClient.callTool('open_nodes', { names: [nodeId] });
      const parsed = mcpClient.parseResponse(response);
      const nodes = parsed.result || [];
      return nodes.length > 0 ? nodes[0] : null;
    } catch (error) {
      console.error('[KnowledgeGraph] Failed to load node details:', error);
      return null;
    }
  };

  const handleSummarize = async () => {
    if (messages.length === 0) {
      addMessage({
        role: 'system',
        content: '当前对话为空，无法总结',
      });
      return;
    }

    setLoading(true);
    setSummaryProgress('正在分析对话内容...');

    try {
      // 构造对话历史文本
      const conversationText = messages
        .filter((m) => m.role !== 'system')
        .map((m) => `${m.role === 'user' ? '用户' : '助手'}: ${m.content}`)
        .join('\n\n');

      // 调用 summarize_conversation 工具
      const response = await mcpClient.callTool('summarize_conversation', {
        conversation_text: conversationText,
      });

      setSummaryProgress('正在提取知识点...');
      const parsed = mcpClient.parseResponse(response);

      // 检查是否有错误
      if (parsed.result?.error) {
        throw new Error(parsed.result.error);
      }

      const knowledgePoints = parsed.result?.knowledge_points;

      if (!knowledgePoints || knowledgePoints.length === 0) {
        addMessage({
          role: 'system',
          content: '未能提取到有效的知识点，请尝试更详细的对话',
        });
        return;
      }

      // 显示确认对话框
      setPendingKnowledge(knowledgePoints);
      setShowConfirmDialog(true);
      setSummaryProgress('');
    } catch (error) {
      console.error('Summarize failed:', error);
      addMessage({
        role: 'system',
        content: `总结失败: ${error instanceof Error ? error.message : 'Unknown error'}`,
      });
      setSummaryProgress('');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmKnowledge = async (
    selectedPoints: KnowledgePoint[],
    graphOption: { mode: 'new' | 'merge'; graphId?: number; graphName?: string }
  ) => {
    setShowConfirmDialog(false);
    setLoading(true);

    try {
      let targetGraphId = graphOption.graphId;

      // 如果是新建模式，先创建图谱
      if (graphOption.mode === 'new') {
        const createResponse = await mcpClient.callTool('create_knowledge_graph', {
          name: graphOption.graphName || `对话总结-${new Date().toLocaleDateString('zh-CN')}`,
          description: '',
        });
        const parsed = mcpClient.parseResponse(createResponse);

        if (parsed.result?.success && parsed.result?.graph) {
          targetGraphId = parsed.result.graph.id;
        } else {
          throw new Error('创建图谱失败');
        }
      }

      // 逐个添加知识点到图谱
      let successCount = 0;
      for (const point of selectedPoints) {
        try {
          await mcpClient.callTool('save_knowledge', {
            knowledge_points: [
              {
                title: point.title,
                content: point.content,
                tags: point.tags,
                type: point.type,
              },
            ],
            session_id: sessionId || 'default',
            graph_id: targetGraphId,
          });
          successCount++;
        } catch (error) {
          console.error(`Failed to add knowledge point: ${point.title}`, error);
        }
      }

      // 刷新图谱列表
      await loadGraphs();

      // 显示成功提示
      addMessage({
        role: 'system',
        content: `成功添加 ${successCount}/${selectedPoints.length} 个知识点到知识图谱`,
      });
    } catch (error) {
      console.error('Add knowledge failed:', error);
      addMessage({
        role: 'system',
        content: `添加知识点失败: ${error instanceof Error ? error.message : '未知错误'}`,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelConfirm = () => {
    setShowConfirmDialog(false);
    setPendingKnowledge([]);
  };

  return (
    <div className="chat-interface flex flex-col h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/30 relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
      }} />

      {/* Header with Glassmorphism */}
      <div className="header relative backdrop-blur-xl bg-white/80 shadow-lg px-6 py-4 flex items-center justify-between border-b border-white/20">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 via-indigo-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/30 transform hover:scale-105 transition-transform">
            <span className="text-white font-bold text-xl">LS</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Learning System
            </h1>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-gray-500">AI 驱动的智能学习助手</span>
              <span className="px-2 py-0.5 bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 text-xs rounded-full font-medium">
                Beta
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={handleNewSession}
            disabled={!connected}
            className="group px-4 py-2 bg-white/60 backdrop-blur-sm border border-gray-200/50 text-gray-700 rounded-xl hover:bg-white hover:border-blue-300 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-all"
          >
            <span className="group-hover:rotate-180 inline-block transition-transform duration-500">🔄</span> 新会话
          </button>
          <button
            onClick={handleLoadGraph}
            disabled={!connected || loadingGraph}
            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl hover:from-purple-600 hover:to-pink-600 hover:shadow-lg hover:shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-all transform hover:scale-105"
          >
            {loadingGraph ? '⏳ 加载中...' : '🕸️ 知识图谱'}
          </button>
          <div className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${
            connected
              ? 'bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200/50'
              : 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-200/50'
          }`}>
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500 animate-pulse shadow-lg shadow-emerald-500/50' : 'bg-red-500'}`} />
            <span className={`text-xs font-semibold ${connected ? 'text-emerald-700' : 'text-red-700'}`}>
              {connected ? '已连接' : '未连接'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="messages flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fadeIn">
            <div className="relative mb-8">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-400 to-purple-500 rounded-3xl blur-2xl opacity-20 animate-pulse"></div>
              <div className="relative w-28 h-28 bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 rounded-3xl flex items-center justify-center shadow-2xl shadow-blue-500/30 transform hover:scale-110 transition-transform duration-300">
                <span className="text-6xl">🎓</span>
              </div>
            </div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-gray-800 via-gray-700 to-gray-800 bg-clip-text text-transparent mb-3">
              欢迎使用 Learning System
            </h2>
            <p className="text-gray-600 mb-8 max-w-lg text-lg leading-relaxed">
              我是你的 AI 学习助手，可以帮助你学习技术知识、准备面试、总结知识点
            </p>
            <div className="grid grid-cols-3 gap-4 text-sm max-w-2xl">
              <div className="group px-5 py-4 bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-2xl text-blue-700 border border-blue-200/50 hover:shadow-lg hover:shadow-blue-500/10 transition-all cursor-default">
                <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">💬</div>
                <div className="font-semibold">多轮对话</div>
                <div className="text-xs text-blue-600/70 mt-1">上下文记忆</div>
              </div>
              <div className="group px-5 py-4 bg-gradient-to-br from-emerald-50 to-green-100/50 rounded-2xl text-emerald-700 border border-emerald-200/50 hover:shadow-lg hover:shadow-emerald-500/10 transition-all cursor-default">
                <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">📝</div>
                <div className="font-semibold">知识总结</div>
                <div className="text-xs text-emerald-600/70 mt-1">自动提取要点</div>
              </div>
              <div className="group px-5 py-4 bg-gradient-to-br from-purple-50 to-pink-100/50 rounded-2xl text-purple-700 border border-purple-200/50 hover:shadow-lg hover:shadow-purple-500/10 transition-all cursor-default">
                <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">🕸️</div>
                <div className="font-semibold">知识图谱</div>
                <div className="text-xs text-purple-600/70 mt-1">可视化关联</div>
              </div>
            </div>
          </div>
        )}
        {messages.map((msg, index) => (
          <MessageBubble key={msg.id} message={msg} index={index} />
        ))}
        {loading && (
          <div className="flex justify-start mb-4 animate-fadeIn">
            <div className="backdrop-blur-xl bg-white/80 border border-gray-200/50 rounded-2xl px-6 py-4 shadow-lg">
              <div className="flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full animate-bounce shadow-lg shadow-blue-500/30" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2.5 h-2.5 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full animate-bounce shadow-lg shadow-indigo-500/30" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2.5 h-2.5 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full animate-bounce shadow-lg shadow-purple-500/30" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-gray-700 text-sm font-medium">AI 正在思考...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Active Tasks */}
      {activeTasks.size > 0 && (
        <div className="tasks bg-white border-t px-6 py-4">
          {Array.from(activeTasks.values()).map((task) => (
            <TaskProgress key={task.task_id} task={task} />
          ))}
        </div>
      )}

      {/* Active UI */}
      {activeUI && (
        <div className="active-ui bg-white border-t p-6 max-h-96 overflow-y-auto">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold">UI Preview</h3>
            <button
              onClick={() => setActiveUI(null)}
              className="text-gray-500 hover:text-gray-700"
            >
              Close
            </button>
          </div>
          <UIRenderer template={activeUI} />
        </div>
      )}

      {/* Confirmation Dialog */}
      {pendingConfirmation && <ConfirmDialog />}

      {/* Knowledge Confirm Dialog */}
      {showConfirmDialog && (
        <KnowledgeConfirmDialog
          knowledgePoints={pendingKnowledge}
          existingGraphs={existingGraphs}
          onConfirm={handleConfirmKnowledge}
          onCancel={handleCancelConfirm}
        />
      )}

      {/* Summary Progress */}
      {summaryProgress && (
        <div className="fixed bottom-8 right-8 bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 animate-pulse">
          <div className="w-5 h-5 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
          <span className="font-medium">{summaryProgress}</span>
        </div>
      )}

      {/* Knowledge Graph Modal */}
      {showGraph && graphData && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl max-w-6xl w-full m-8 max-h-[90vh] overflow-hidden">
            <div className="flex justify-between items-center px-8 py-6 border-b-2 border-gray-100 bg-gradient-to-r from-purple-50 to-pink-50">
              <div>
                <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                  🕸️ 知识图谱
                </h2>
                <p className="text-sm text-gray-600 mt-1">可视化你的知识网络</p>
              </div>
              <button
                onClick={() => setShowGraph(false)}
                className="w-10 h-10 flex items-center justify-center text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-all text-2xl"
              >
                ✕
              </button>
            </div>
            <div className="p-8 overflow-auto bg-gray-50">
              <KnowledgeGraphView
                data={graphData}
                width={1000}
                height={600}
                onNodeClick={(node) => {
                  console.log('Node clicked:', node);
                  addMessage({
                    role: 'system',
                    content: `已选择节点: ${node.label} (${node.type})`,
                  });
                }}
                onNodeDoubleClick={(node) => {
                  console.log('Node double-clicked:', node);
                  setShowGraph(false);
                  setInput(`告诉我更多关于 ${node.label} 的知识`);
                }}
                onSearchNodes={handleSearchNodes}
                onOpenNodeDetails={handleOpenNodeDetails}
              />
            </div>
          </div>
        </div>
      )}

      {/* Input Area with Tool Buttons */}
      <div className="input-area relative backdrop-blur-xl bg-white/80 border-t border-white/20 px-6 py-5 shadow-2xl">
        {/* Tool Buttons - Card Style */}
        <div className="tool-buttons mb-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1 h-4 bg-gradient-to-b from-blue-500 to-indigo-500 rounded-full"></div>
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">快速操作</span>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <button
              onClick={handleSummarize}
              disabled={!connected || loading || messages.length === 0}
              className="group relative overflow-hidden px-4 py-3.5 bg-gradient-to-br from-emerald-500 to-green-600 text-white rounded-xl hover:from-emerald-600 hover:to-green-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-sm font-medium transition-all shadow-lg hover:shadow-emerald-500/40 hover:scale-105 disabled:hover:scale-100"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              <div className="relative flex items-center justify-center gap-2">
                <span className="text-lg">📝</span>
                <span>总结知识点</span>
              </div>
            </button>
            <button
              onClick={() => setInput('/summarize ')}
              disabled={!connected || loading}
              className="group relative overflow-hidden px-4 py-3.5 bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-sm font-medium transition-all shadow-lg hover:shadow-blue-500/40 hover:scale-105 disabled:hover:scale-100"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              <div className="relative flex items-center justify-center gap-2">
                <span className="text-lg">🎯</span>
                <span>Skill: 总结</span>
              </div>
            </button>
            <button
              onClick={() => setInput('/interview-prep ')}
              disabled={!connected || loading}
              className="group relative overflow-hidden px-4 py-3.5 bg-gradient-to-br from-orange-500 to-red-600 text-white rounded-xl hover:from-orange-600 hover:to-red-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-sm font-medium transition-all shadow-lg hover:shadow-orange-500/40 hover:scale-105 disabled:hover:scale-100"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              <div className="relative flex items-center justify-center gap-2">
                <span className="text-lg">💼</span>
                <span>面试准备</span>
              </div>
            </button>
            <button
              onClick={() => setInput('/tech-deep-dive ')}
              disabled={!connected || loading}
              className="group relative overflow-hidden px-4 py-3.5 bg-gradient-to-br from-purple-500 to-pink-600 text-white rounded-xl hover:from-purple-600 hover:to-pink-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-sm font-medium transition-all shadow-lg hover:shadow-purple-500/40 hover:scale-105 disabled:hover:scale-100"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
              <div className="relative flex items-center justify-center gap-2">
                <span className="text-lg">🔬</span>
                <span>深度研究</span>
              </div>
            </button>
          </div>
        </div>

        {/* Input Box */}
        <div className="flex gap-3">
          <div className="flex-1 relative group">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={connected ? "输入消息或使用 /skill-name 触发 Skill..." : "连接中..."}
              disabled={!connected || loading}
              className="w-full px-5 py-3.5 pr-12 bg-white/60 backdrop-blur-sm border-2 border-gray-200/50 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white disabled:bg-gray-100/50 text-base shadow-lg transition-all group-hover:border-blue-300 group-hover:shadow-xl"
            />
            {input && (
              <button
                onClick={() => setInput('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 w-6 h-6 rounded-full flex items-center justify-center transition-all"
              >
                ✕
              </button>
            )}
          </div>
          <button
            onClick={handleSend}
            disabled={!connected || loading || !input.trim()}
            className="relative overflow-hidden px-8 py-3.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-blue-600 text-white rounded-2xl hover:from-blue-600 hover:via-indigo-600 hover:to-blue-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed font-semibold transition-all shadow-lg hover:shadow-blue-500/40 hover:scale-105 disabled:hover:scale-100 group"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-700"></div>
            <span className="relative">{loading ? '⏳ 思考中...' : '发送 →'}</span>
          </button>
        </div>

        {/* Helper Text */}
        {!loading && messages.length === 0 && (
          <div className="mt-4 text-xs text-gray-500 text-center backdrop-blur-sm bg-white/40 py-2 rounded-xl border border-gray-200/30">
            💡 <span className="font-medium">提示</span>：点击上方按钮快速使用功能，或输入 <code className="px-2 py-0.5 bg-blue-100/80 text-blue-700 rounded font-mono">/skill-name</code> 触发 Skill
          </div>
        )}
      </div>
    </div>
  );
};

const MessageBubble: React.FC<{ message: any; index: number }> = ({ message, index }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isAssistant = message.role === 'assistant';

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 animate-fadeIn`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div
        className={`max-w-3xl rounded-2xl shadow-lg transition-all hover:shadow-xl ${
          isUser
            ? 'bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 text-white px-6 py-4'
            : isSystem
            ? 'backdrop-blur-xl bg-gradient-to-br from-amber-50/90 to-yellow-50/90 text-amber-900 border-2 border-amber-300/50 px-6 py-4'
            : 'backdrop-blur-xl bg-white/90 border border-gray-200/50 px-6 py-4'
        }`}
      >
        {/* Role Label with Icon */}
        {!isUser && (
          <div className={`flex items-center gap-2 mb-3 pb-2 ${
            isSystem ? 'border-b border-amber-200' : 'border-b border-gray-200/50'
          }`}>
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
              isSystem
                ? 'bg-gradient-to-br from-amber-400 to-orange-500 shadow-md'
                : 'bg-gradient-to-br from-blue-500 to-indigo-600 shadow-md'
            }`}>
              <span className="text-white text-sm">{isSystem ? '🔔' : '🤖'}</span>
            </div>
            <span className={`text-sm font-bold ${isSystem ? 'text-amber-800' : 'text-gray-700'}`}>
              {isSystem ? '系统通知' : 'AI 助手'}
            </span>
          </div>
        )}

        {isAssistant ? (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, className, children, ...props }: any) {
                  const isInline = !className || !className.includes('language-');
                  return isInline ? (
                    <code className="bg-blue-100 text-blue-800 px-2 py-1 rounded-lg text-sm font-mono border border-blue-200" {...props}>
                      {children}
                    </code>
                  ) : (
                    <code className="block bg-gradient-to-br from-gray-900 to-gray-800 text-emerald-400 p-4 rounded-xl overflow-x-auto font-mono text-sm my-3 shadow-xl border border-gray-700" {...props}>
                      {children}
                    </code>
                  );
                },
                p({ children }) {
                  return <p className="my-2 text-gray-800 leading-relaxed">{children}</p>;
                },
                ul({ children }) {
                  return <ul className="list-disc list-inside my-2 space-y-1.5 text-gray-800">{children}</ul>;
                },
                ol({ children }) {
                  return <ol className="list-decimal list-inside my-2 space-y-1.5 text-gray-800">{children}</ol>;
                },
                li({ children }) {
                  return <li className="ml-2">{children}</li>;
                },
                a({ href, children }) {
                  return (
                    <a href={href} className="text-blue-600 hover:text-blue-800 underline decoration-2 underline-offset-2 font-medium transition-colors" target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  );
                },
                strong({ children }) {
                  return <strong className="font-bold text-gray-900 bg-yellow-100/50 px-1 rounded">{children}</strong>;
                },
                h1({ children }) {
                  return <h1 className="text-2xl font-bold text-gray-900 mt-4 mb-3 pb-2 border-b-2 border-blue-200">{children}</h1>;
                },
                h2({ children }) {
                  return <h2 className="text-xl font-bold text-gray-900 mt-3 mb-2">{children}</h2>;
                },
                h3({ children }) {
                  return <h3 className="text-lg font-semibold text-gray-800 mt-2 mb-2">{children}</h3>;
                },
                blockquote({ children }) {
                  return <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-3 bg-blue-50/50 rounded-r-lg italic text-gray-700">{children}</blockquote>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        ) : (
          <div className={`whitespace-pre-wrap leading-relaxed ${
            isUser ? 'text-white' : isSystem ? 'text-amber-900' : 'text-gray-800'
          }`}>
            {message.content}
          </div>
        )}
        {message.uiTemplate && (
          <div className="mt-3 pt-3 border-t border-white/20 text-xs opacity-75 flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></span>
            <span>UI: {message.uiTemplate.templateId}</span>
          </div>
        )}
      </div>
    </div>
  );
};
