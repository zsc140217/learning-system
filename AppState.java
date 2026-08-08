 交接文档 - Learning System 前端优化需求

  日期: 2026-08-07
  当前状态: Chat 功能已集成 DeepSeek LLM，但缺少会话管理、知识总结和图谱中文显示

  ---
  📊 当前系统状态

  ✅ 已完成的功能

  1. MCP HTTP Server (端口 8080)
    - DeepSeek LLM 已集成并测试通过
    - 30 个工具已注册，包括 chat、search_knowledge、add_knowledge、ui_knowledge_graph 等
  2. WebSocket Server (端口 8000)
    - 前后端通信正常
    - 客户端连接成功
  3. 前端开发服务器 (端口 3001)
    - Vite + React + TypeScript
    - 基础聊天界面已实现
    - 知识图谱可视化组件已存在
  4. Chat 工具
    - ✅ 调用 DeepSeek LLM 生成回答
    - ✅ 返回完整对话内容
    - ❌ 前端直接显示原始 JSON，未格式化
    - ❌ 无会话管理（每次都是新会话）

  ---
  🎯 需要优化的功能

  1. 前端展示优化 ⭐⭐⭐ (高优先级)

  问题：
  // 当前前端显示的是原始 JSON
  {
    "response": "我来查看这个文件的内容...",
    "session_id": "session_1786097031_ept10r4w",
    "model": "deepseek-chat"
  }

  期望：
  - 只显示 response 字段的内容（AI 回答）
  - 隐藏 session_id 和 model
  - 支持 Markdown 渲染（代码块、列表、加粗等）

  修改位置：
  - 文件：client/frontend/src/components/ChatInterface.tsx
  - 第 67-72 行：handleSend() 函数的响应处理逻辑

  修改方案：
  // 修改前
  addMessage({
    role: 'assistant',
    content: JSON.stringify(parsed.result, null, 2),
  });

  // 修改后
  addMessage({
    role: 'assistant',
    content: parsed.result.response || JSON.stringify(parsed.result, null, 2),
  });

  ---
  2. 会话管理 ⭐⭐⭐ (高优先级)

  问题：
  - 每次发送消息都是新会话，LLM 无法记住上下文
  - session_id 在响应中返回了，但前端没有保存和复用

  期望：
  - 自动保存 session_id
  - 后续消息自动携带 session_id 实现多轮对话
  - 支持"新建会话"按钮清空当前会话

  实现方案：

  // 在 ChatInterface 组件中添加状态
  const [sessionId, setSessionId] = useState<string | null>(null);

  // 修改 handleSend 函数
  const response = await mcpClient.callTool('chat', {
    message: userMessage,
    session_id: sessionId  // 携带会话 ID
  });

  // 保存返回的 session_id
  const parsed = mcpClient.parseResponse(response);
  if (parsed.result.session_id) {
    setSessionId(parsed.result.session_id);
  }

  // 添加"新建会话"按钮
  const handleNewSession = () => {
    setSessionId(null);
    // 清空消息
  };

  ---
  3. 知识总结与图谱生成 ⭐⭐⭐ (高优先级)

  需求：
  - 添加"总结"按钮
  - 点击后，将当前对话内容发送给 LLM 进行知识点提取
  - 提取的知识点自动存储到知识图谱
  - 刷新知识图谱视图

  实现流程：
  用户点击"总结"
    ↓
  调用 chat 工具：
    "请从以下对话中提取关键知识点，格式为：
     - 主题：xxx
     - 内容：xxx
     - 标签：[tag1, tag2]"
    ↓
  解析 LLM 返回的知识点
    ↓
  调用 add_knowledge 工具逐个添加
    ↓
  刷新知识图谱

  新增工具调用：
  const handleSummarize = async () => {
    // 1. 构造对话历史文本
    const conversationText = messages
      .map(m => `${m.role}: ${m.content}`)
      .join('\n');

    // 2. 调用 LLM 提取知识点
    const summaryResponse = await mcpClient.callTool('chat', {
      message: `请从以下对话中提取关键知识点，格式为 JSON 数组：
      [{"title": "知识点标题", "content": "详细内容", "tags": ["标签1", "标签2"]}]

      对话内容：
      ${conversationText}`,
      session_id: null  // 新会话
    });

    // 3. 解析并存储知识点
    const knowledgePoints = JSON.parse(summaryResponse.result.response);
    for (const point of knowledgePoints) {
      await mcpClient.callTool('add_knowledge', point);
    }

    // 4. 刷新图谱
    handleLoadGraph();
  };

  ---
  4. 知识图谱中文显示 ⭐⭐ (中优先级)

  问题：
  - 知识图谱节点标签可能显示为英文或 ID
  - 需要确保节点和边的标签是中文

  检查位置：
  1. 后端数据源：
    - 文件：mcp-server/src/tools/ui_knowledge_graph.py
    - 检查节点的 label 字段是否使用了中文标题
  2. 前端渲染：
    - 文件：client/frontend/src/components/KnowledgeGraph.tsx
    - 确认显示的是 node.label 而不是 node.id

  修改方案（如果后端返回英文）：
  # mcp-server/src/tools/ui_knowledge_graph.py
  nodes.append({
      "id": node["id"],
      "label": node.get("title", node["id"]),  # 优先使用 title
      "type": node.get("type", "concept")
  })

  ---
  🔧 技术细节

  Chat 工具返回格式

  {
    "response": "LLM 生成的回答文本",
    "session_id": "session_1786097031_ept10r4w",
    "model": "deepseek-chat"
  }

  Add Knowledge 工具参数

  {
    "title": "知识点标题",
    "content": "详细内容",
    "tags": ["标签1", "标签2"],
    "type": "concept"  // 可选：concept, technology, method, etc.
  }

  UI Knowledge Graph 工具返回格式

  {
    "nodes": [
      {"id": "1", "label": "React", "type": "technology"},
      {"id": "2", "label": "Vue", "type": "technology"}
    ],
    "edges": [
      {"source": "1", "target": "2", "label": "类似于", "type": "similar"}
    ]
  }

  ---
  📁 关键文件清单

  前端文件

  client/frontend/src/
  ├── components/
  │   ├── ChatInterface.tsx           # ⭐ 主要修改：会话管理、总结按钮
  │   ├── KnowledgeGraph.tsx          # 检查中文显示
  │   └── ui/
  │       └── UIRenderer.tsx
  ├── services/
  │   ├── websocket.ts
  │   └── mcpClient.ts
  └── store/
      └── appStore.ts                 # 可能需要添加 sessionId 状态

  后端文件

  mcp-server/
  ├── server.py                       # Chat 工具定义（第 2070-2136 行）
  ├── src/
  │   ├── tools/
  │   │   ├── ui_knowledge_graph.py   # ⭐ 检查中文 label
  │   │   └── __init__.py
  │   └── llm/
  │       ├── factory.py              # LLM Provider Factory
  │       └── deepseek_client.py      # DeepSeek 客户端
  └── .env                            # DeepSeek API Key

  ---
  🎨 UI 设计建议

  聊天界面布局

  ┌─────────────────────────────────────────────────┐
  │ Learning System          [总结] [新会话] [图谱] │  ← Header
  ├─────────────────────────────────────────────────┤
  │                                                 │
  │  👤 用户: 什么是 FastAPI？                      │
  │                                                 │
  │  🤖 助手: FastAPI 是一个现代 Python 框架...     │
  │                                                 │
  │  👤 用户: 它有什么优点？                        │
  │                                                 │
  │  🤖 助手: 主要优点包括：                        │
  │     1. 高性能                                   │
  │     2. 自动文档生成                             │
  │     3. 类型提示支持                             │
  │                                                 │
  ├─────────────────────────────────────────────────┤
  │ [输入框                              ] [发送]   │  ← Input
  └─────────────────────────────────────────────────┘

  按钮功能

  - 总结：提取当前对话的知识点并存入图谱
  - 新会话：清空对话历史，开始新的会话
  - 图谱：显示知识图谱可视化

  ---
  🧪 测试场景

  场景 1：多轮对话测试

  用户: 什么是 React？
  助手: React 是一个用于构建用户界面的 JavaScript 库...

  用户: 它的核心概念是什么？  ← 应该能理解"它"指 React
  助手: React 的核心概念包括...

  场景 2：知识总结测试

  1. 进行一段关于 FastAPI 的对话（3-5 轮）
  2. 点击"总结"按钮
  3. 系统自动提取知识点（如：FastAPI 定义、优点、用途）
  4. 点击"图谱"按钮，应该看到新增的 FastAPI 节点

  场景 3：图谱中文显示测试

  1. 添加中文知识点："React Hooks"、"Vue 组件"
  2. 关联它们："React Hooks" → "类似于" → "Vue Composition API"
  3. 查看图谱，所有节点和边都应显示中文

  ---
  📚 相关学习概念

  1. 会话管理（Session Management）

  - 概念：在多轮对话中保持上下文，让 AI 记住之前说过的内容
  - 实现：通过 session_id 标识不同会话，服务端缓存历史消息
  - 应用：聊天机器人、客服系统、智能助手

  2. 知识图谱（Knowledge Graph）

  - 概念：用图结构表示知识，节点是实体，边是关系
  - 优势：可视化、关联查询、推理能力
  - 应用：推荐系统、问答系统、语义搜索

  3. RAG（Retrieval-Augmented Generation）

  - 概念：检索增强生成，先检索相关知识，再让 LLM 生成回答
  - 流程：用户提问 → 检索知识库 → 将知识作为上下文 → LLM 生成
  - 优势：减少幻觉、提供引用来源、知识可更新

  4. Prompt Engineering

  - 概念：设计有效的提示词，引导 LLM 生成期望的输出
  - 技巧：
    - 明确输出格式（如 JSON）
    - 提供示例（Few-shot Learning）
    - 分步骤引导（Chain-of-Thought）

  ---
  🚀 下一步行动

  1. 前端优化（预计 2-3 小时）
    - [ ] 修改 ChatInterface 显示格式（只显示 response）
    - [ ] 实现会话管理（保存和复用 session_id）
    - [ ] 添加"总结"按钮和逻辑
    - [ ] 添加"新会话"按钮
  2. 后端检查（预计 1 小时）
    - [ ] 确认 ui_knowledge_graph 返回中文 label
    - [ ] 测试 add_knowledge 工具是否正常工作
  3. 集成测试（预计 1 小时）
    - [ ] 多轮对话测试
    - [ ] 知识总结测试
    - [ ] 图谱中文显示测试

  ---
  💡 设计建议

  Markdown 渲染

  建议使用 react-markdown 库来渲染 LLM 的回答：
  npm install react-markdown

  状态管理优化

  如果会话状态复杂，建议在 appStore.ts 中集中管理：
  interface AppState {
    messages: Message[];
    sessionId: string | null;
    connected: boolean;
    // ...
  }

  知识提取提示词模板

  请从以下对话中提取关键知识点，以 JSON 数组格式返回。

  要求：
  1. 每个知识点包含 title（简短标题）、content（详细内容）、tags（标签数组）
  2. 标题和内容使用中文
  3. 只提取实质性的技术知识，不包括问候语
  4. 至少提取 3 个知识点

  格式示例：
  [
    {
      "title": "FastAPI 定义",
      "content": "FastAPI 是一个现代、快速的 Python Web 框架...",
      "tags": ["Python", "Web框架", "API"]
    }
  ]

  对话内容：
  {conversation_text}
