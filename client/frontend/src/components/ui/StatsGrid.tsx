import React from 'react';

interface StatItem {
  label: string;
  value: string;
  icon?: string;
  color?: string;
}

interface StatsGridProps {
  items: StatItem[];
  columns?: number;
}

export const StatsGrid: React.FC<StatsGridProps> = ({ items, columns = 4 }) => {
  return (
    <div 
      className="stats-grid grid gap-4"
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
    >
      {items.map((item, index) => (
        <StatCard key={index} {...item} />
      ))}
    </div>
  );
};

const StatCard: React.FC<StatItem> = ({ label, value, icon, color = 'blue' }) => {
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-50 border-blue-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    orange: 'bg-orange-50 border-orange-200',
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
  };

  return (
    <div className={`stat-card p-4 rounded-lg border-2 ${colorClasses[color] || colorClasses.blue}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-xl">{getIcon(icon)}</span>}
        <span className="text-sm text-gray-600">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
    </div>
  );
};

function getIcon(name: string): string {
  const icons: Record<string, string> = {
    'clock': '🕐',
    'lightbulb': '💡',
    'trending-up': '📈',
    'check-circle': '✅',
  };
  return icons[name] || '📊';
}
