import React from 'react';

interface KnowledgeItem {
  id: string;
  title: string;
  difficulty?: number;
  mastery?: number;
  tags?: string[];
  action?: {
    label: string;
    toolName: string;
    params: Record<string, any>;
  };
}

interface KnowledgeListProps {
  title?: string;
  items: KnowledgeItem[];
}

export const KnowledgeList: React.FC<KnowledgeListProps> = ({ title, items }) => {
  return (
    <div className="knowledge-list">
      {title && <h3 className="text-lg font-semibold mb-3">{title}</h3>}
      <div className="space-y-2">
        {items.map((item) => (
          <KnowledgeCard key={item.id} {...item} />
        ))}
      </div>
    </div>
  );
};

const KnowledgeCard: React.FC<KnowledgeItem> = ({
  title,
  difficulty,
  mastery,
  tags,
  action,
}) => {
  return (
    <div className="knowledge-card p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h4 className="font-medium text-gray-800">{title}</h4>
          {tags && tags.length > 0 && (
            <div className="flex gap-2 mt-2">
              {tags.map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4 ml-4">
          {difficulty !== undefined && (
            <div className="text-center">
              <div className="text-xs text-gray-500">难度</div>
              <div className="text-sm font-medium">{(difficulty * 10).toFixed(1)}</div>
            </div>
          )}
          {mastery !== undefined && (
            <div className="text-center">
              <div className="text-xs text-gray-500">掌握</div>
              <div className="text-sm font-medium text-green-600">
                {(mastery * 100).toFixed(0)}%
              </div>
            </div>
          )}
          {action && (
            <button
              className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => console.log('Action:', action)}
            >
              {action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
