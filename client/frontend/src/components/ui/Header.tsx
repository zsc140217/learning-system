import React from 'react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  icon?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle, icon }) => {
  return (
    <div className="header mb-4">
      <div className="flex items-center gap-3">
        {icon && <span className="text-2xl">{getIcon(icon)}</span>}
        <div>
          <h2 className="text-2xl font-bold text-gray-800">{title}</h2>
          {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
};

function getIcon(name: string): string {
  const icons: Record<string, string> = {
    'book-open': '📖',
    'clock': '🕐',
    'lightbulb': '💡',
    'trending-up': '📈',
    'check-circle': '✅',
  };
  return icons[name] || '📄';
}
