import React, { useState } from 'react';

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

interface Props {
  knowledgePoints: KnowledgePoint[];
  existingGraphs: GraphOption[];
  onConfirm: (
    selectedPoints: KnowledgePoint[],
    graphOption: { mode: 'new' | 'merge'; graphId?: number; graphName?: string }
  ) => void;
  onCancel: () => void;
}

export const KnowledgeConfirmDialog: React.FC<Props> = ({
  knowledgePoints,
  existingGraphs,
  onConfirm,
  onCancel,
}) => {
  const [selected, setSelected] = useState<Set<number>>(
    new Set(knowledgePoints.map((_, i) => i)) // 默认全选
  );
  const [editedPoints, setEditedPoints] = useState(knowledgePoints);

  // 图谱选择状态
  const [graphMode, setGraphMode] = useState<'new' | 'merge'>('new');
  const [selectedGraphId, setSelectedGraphId] = useState<number | undefined>();
  const [newGraphName, setNewGraphName] = useState(
    `学习记录-${new Date().toLocaleDateString('zh-CN')}`
  );

  const handleToggle = (index: number) => {
    const newSelected = new Set(selected);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelected(newSelected);
  };

  const handleEdit = (index: number, field: string, value: any) => {
    const newPoints = [...editedPoints];
    newPoints[index] = { ...newPoints[index], [field]: value };
    setEditedPoints(newPoints);
  };

  const handleConfirm = () => {
    const selectedPoints = Array.from(selected).map((i) => editedPoints[i]);

    const graphOption = {
      mode: graphMode,
      graphId: graphMode === 'merge' ? selectedGraphId : undefined,
      graphName: graphMode === 'new' ? newGraphName : undefined,
    };

    onConfirm(selectedPoints, graphOption);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full m-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">确认知识点</h2>
          <p className="text-sm text-gray-600 mt-1">
            请检查提取的知识点，可以编辑或取消不需要的项
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {editedPoints.map((point, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 ${
                !selected.has(index) ? 'opacity-50 bg-gray-50' : 'bg-white'
              }`}
            >
              {/* Title Row */}
              <div className="flex items-center gap-2 mb-3">
                <input
                  type="checkbox"
                  checked={selected.has(index)}
                  onChange={() => handleToggle(index)}
                  className="w-4 h-4"
                />
                <input
                  type="text"
                  value={point.title}
                  onChange={(e) => handleEdit(index, 'title', e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="知识点标题"
                />
              </div>

              {/* Content */}
              <textarea
                value={point.content}
                onChange={(e) => handleEdit(index, 'content', e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
                placeholder="详细内容"
              />

              {/* Tags and Type */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={point.tags.join(', ')}
                  onChange={(e) =>
                    handleEdit(
                      index,
                      'tags',
                      e.target.value.split(',').map((t) => t.trim())
                    )
                  }
                  placeholder="标签（逗号分隔）"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={point.type}
                  onChange={(e) => handleEdit(index, 'type', e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="concept">概念</option>
                  <option value="technology">技术</option>
                  <option value="method">方法</option>
                  <option value="tool">工具</option>
                </select>
              </div>
            </div>
          ))}
        </div>

        {/* 图谱选择区域 */}
        <div className="px-6 py-4 border-t">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            保存到知识图谱
          </label>

          <div className="space-y-3">
            {/* 选项1：创建新图谱 */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={graphMode === 'new'}
                onChange={() => setGraphMode('new')}
                className="w-4 h-4"
              />
              <span className="text-sm">创建新图谱</span>
            </label>

            {graphMode === 'new' && (
              <input
                type="text"
                value={newGraphName}
                onChange={(e) => setNewGraphName(e.target.value)}
                placeholder="图谱名称（如：FastAPI学习-2026-08-08）"
                className="ml-6 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}

            {/* 选项2：合并到已有图谱 */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={graphMode === 'merge'}
                onChange={() => setGraphMode('merge')}
                disabled={existingGraphs.length === 0}
                className="w-4 h-4 disabled:opacity-50"
              />
              <span className="text-sm">合并到已有图谱</span>
              {existingGraphs.length === 0 && (
                <span className="text-xs text-gray-500">（暂无图谱）</span>
              )}
            </label>

            {graphMode === 'merge' && existingGraphs.length > 0 && (
              <select
                value={selectedGraphId || ''}
                onChange={(e) => setSelectedGraphId(Number(e.target.value))}
                className="ml-6 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">请选择图谱</option>
                {existingGraphs.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name} ({g.node_count} 个节点)
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={
              selected.size === 0 ||
              (graphMode === 'new' && !newGraphName.trim()) ||
              (graphMode === 'merge' && !selectedGraphId)
            }
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            确认添加 ({selected.size} 个)
          </button>
        </div>
      </div>
    </div>
  );
};
