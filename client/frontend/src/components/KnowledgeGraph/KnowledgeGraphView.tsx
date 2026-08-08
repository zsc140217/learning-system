import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface Node {
  id: string;
  label: string;
  type: string;
  size: number;
  color?: string;
  description?: string;
  observations?: string[];  // 新增：观察记录（中文内容）
  highlighted?: boolean;     // 新增：搜索高亮标记
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface Edge {
  source: string | Node;
  target: string | Node;
  type: string;
  label?: string;  // 新增：边标签（中文）
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

interface KnowledgeGraphViewProps {
  data: GraphData;
  width?: number;
  height?: number;
  onNodeClick?: (node: Node) => void;
  onNodeDoubleClick?: (node: Node) => void;
  onSearchNodes?: (query: string) => Promise<Node[]>;  // 新增：搜索回调
  onOpenNodeDetails?: (nodeId: string) => Promise<Node>;  // 新增：获取详情回调
}

// 类型中文标签映射（固定术语的中文显示）
const TYPE_LABELS: Record<string, string> = {
  'concept': '概念',
  'technology': '技术',
  'method': '方法',
  'tool': '工具',
  'skill': '技能',
  'project': '项目',
};

// 类型颜色映射
const TYPE_COLORS: Record<string, string> = {
  'concept': '#60A5FA',      // 蓝色
  'technology': '#34D399',   // 绿色
  'method': '#FBBF24',       // 黄色
  'tool': '#F87171',         // 红色
  'skill': '#A78BFA',        // 紫色
  'project': '#FB923C',      // 橙色
};

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({
  data,
  width = 800,
  height = 600,
  onNodeClick,
  onNodeDoubleClick,
  onSearchNodes,
  onOpenNodeDetails,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // 处理类型筛选
  const handleTypeFilter = (type: string) => {
    const newTypes = new Set(selectedTypes);
    if (newTypes.has(type)) {
      newTypes.delete(type);
    } else {
      newTypes.add(type);
    }
    setSelectedTypes(newTypes);
  };

  // 处理搜索
  const handleSearch = async () => {
    if (!searchQuery.trim() || !onSearchNodes) {
      return;
    }

    setIsSearching(true);
    try {
      const results = await onSearchNodes(searchQuery);
      const resultIds = new Set(results.map((r) => r.id));

      // 标记高亮节点
      data.nodes.forEach((node) => {
        node.highlighted = resultIds.has(node.id);
      });
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  // 处理节点点击（增强版 - 获取详情）
  const handleNodeClickInternal = async (node: Node) => {
    if (onOpenNodeDetails) {
      try {
        const details = await onOpenNodeDetails(node.id);
        setSelectedNode({ ...node, ...details });
      } catch (error) {
        console.error('Failed to load node details:', error);
        setSelectedNode(node);
      }
    } else {
      setSelectedNode(node);
    }

    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  // 应用类型筛选
  const visibleNodes = selectedTypes.size === 0
    ? data.nodes
    : data.nodes.filter((n) => selectedTypes.has(n.type));

  const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = data.edges.filter((e) => {
    const sourceId = typeof e.source === 'string' ? e.source : e.source.id;
    const targetId = typeof e.target === 'string' ? e.target : e.target.id;
    return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
  });

  useEffect(() => {
    if (!svgRef.current || visibleNodes.length === 0) return;

    // Clear previous content
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);

    // Create main group for zooming/panning
    const g = svg.append('g');

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Create force simulation (优化参数)
    const simulation = d3.forceSimulation<Node>(visibleNodes)
      .force('link', d3.forceLink<Node, Edge>(visibleEdges)
        .id((d) => d.id)
        .distance(100)
        .strength(0.5))
      .force('charge', d3.forceManyBody()
        .strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide()
        .radius((d: any) => d.size + 10));

    // Create arrow markers for directed edges
    const defs = svg.append('defs');
    defs.append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Create edges
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(visibleEdges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2)
      .attr('marker-end', 'url(#arrowhead)');

    // Create edge labels (显示中文标签)
    const edgeLabels = g.append('g')
      .attr('class', 'edge-labels')
      .selectAll('text')
      .data(visibleEdges)
      .enter()
      .append('text')
      .attr('font-size', 10)
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .text((d) => d.label || d.type.replace(/_/g, ' '));

    // Create node groups
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(visibleNodes)
      .enter()
      .append('g')
      .call(d3.drag<SVGGElement, Node>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended) as any);

    // Add circles for nodes (支持高亮)
    node.append('circle')
      .attr('r', (d) => d.size)
      .attr('fill', (d) => d.color || TYPE_COLORS[d.type] || '#9CA3AF')
      .attr('stroke', (d) => d.highlighted ? '#000' : '#fff')
      .attr('stroke-width', (d) => d.highlighted ? 3 : 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        handleNodeClickInternal(d);
      })
      .on('dblclick', (event, d) => {
        event.stopPropagation();
        if (onNodeDoubleClick) onNodeDoubleClick(d);
      })
      .on('mouseover', function(_event, d) {
        setHoveredNode(d.id);
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', (d as Node).size * 1.2)
          .attr('stroke-width', 3);
      })
      .on('mouseout', function(_event, d) {
        setHoveredNode(null);
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', (d as Node).size)
          .attr('stroke-width', (d as Node).highlighted ? 3 : 2);
      });

    // Add labels for nodes (显示中文标签)
    node.append('text')
      .attr('dx', 0)
      .attr('dy', (d) => d.size + 15)
      .attr('text-anchor', 'middle')
      .attr('font-size', 12)
      .attr('fill', '#333')
      .attr('font-weight', (d) => d.highlighted ? 'bold' : 'normal')
      .text((d) => d.label);

    // Update positions on each tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      edgeLabels
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: Node) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [visibleNodes, visibleEdges, width, height, hoveredNode]);

  return (
    <div className="knowledge-graph-container" style={{ position: 'relative' }}>
      {/* 搜索框 */}
      <div style={{
        position: 'absolute',
        top: 16,
        left: 16,
        display: 'flex',
        gap: 8,
        zIndex: 10,
      }}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="搜索知识点..."
          style={{
            width: 250,
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: 4,
            fontSize: 14,
          }}
          disabled={isSearching}
        />
        <button
          onClick={handleSearch}
          disabled={isSearching || !onSearchNodes}
          style={{
            padding: '8px 16px',
            background: isSearching ? '#ccc' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            cursor: isSearching ? 'not-allowed' : 'pointer',
            fontSize: 14,
          }}
        >
          {isSearching ? '搜索中...' : '搜索'}
        </button>
      </div>

      {/* 类型筛选按钮 */}
      <div style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        display: 'flex',
        gap: 8,
        zIndex: 10,
      }}>
        {Object.entries(TYPE_LABELS).map(([type, label]) => (
          <button
            key={type}
            onClick={() => handleTypeFilter(type)}
            style={{
              padding: '6px 12px',
              background: selectedTypes.has(type) ? TYPE_COLORS[type] : '#f5f5f5',
              color: selectedTypes.has(type) ? 'white' : '#333',
              border: `2px solid ${TYPE_COLORS[type]}`,
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: selectedTypes.has(type) ? 'bold' : 'normal',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* SVG 画布 */}
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{ background: '#fafafa', border: '1px solid #ddd' }}
      />

      {/* 增强的节点详情面板 */}
      {selectedNode && (
        <div style={{
          position: 'absolute',
          right: 20,
          top: 20,
          width: 320,
          maxHeight: 400,
          padding: 16,
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          overflow: 'auto',
          zIndex: 10,
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'start',
            marginBottom: 12,
          }}>
            <h3 style={{
              margin: 0,
              fontSize: 18,
              fontWeight: 'bold',
              color: '#333',
            }}>
              {selectedNode.label}
            </h3>
            <button
              onClick={() => setSelectedNode(null)}
              style={{
                background: 'none',
                border: 'none',
                fontSize: 20,
                cursor: 'pointer',
                color: '#999',
                padding: 0,
                lineHeight: 1,
              }}
            >
              ×
            </button>
          </div>

          {/* 类型标签（中文显示） */}
          <div style={{ marginBottom: 12 }}>
            <span style={{
              display: 'inline-block',
              padding: '4px 8px',
              background: TYPE_COLORS[selectedNode.type] || '#9CA3AF',
              color: 'white',
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 'bold',
            }}>
              {TYPE_LABELS[selectedNode.type] || selectedNode.type}
            </span>
          </div>

          {/* 描述 */}
          {selectedNode.description && (
            <div style={{ marginBottom: 12 }}>
              <p style={{
                margin: 0,
                fontSize: 13,
                color: '#666',
                lineHeight: 1.5,
              }}>
                {selectedNode.description}
              </p>
            </div>
          )}

          {/* 观察记录（中文内容） */}
          {selectedNode.observations && selectedNode.observations.length > 0 && (
            <div>
              <h4 style={{
                margin: '0 0 8px 0',
                fontSize: 14,
                fontWeight: 'bold',
                color: '#555',
              }}>
                观察记录：
              </h4>
              <ul style={{
                margin: 0,
                paddingLeft: 20,
                fontSize: 13,
                color: '#666',
                lineHeight: 1.6,
              }}>
                {selectedNode.observations.map((obs, i) => (
                  <li key={i}>{obs}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 统计信息 */}
      <div style={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        padding: '8px 12px',
        background: 'rgba(255, 255, 255, 0.9)',
        border: '1px solid #ddd',
        borderRadius: 4,
        fontSize: 12,
        color: '#666',
        zIndex: 10,
      }}>
        节点: {visibleNodes.length} / {data.nodes.length} | 边: {visibleEdges.length} / {data.edges.length}
      </div>
    </div>
  );
};
