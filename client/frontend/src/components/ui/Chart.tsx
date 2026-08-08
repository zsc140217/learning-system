import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface ChartProps {
  chartType: 'bar' | 'line' | 'pie';
  title?: string;
  data: {
    labels: string[];
    values: number[];
    colors?: string[];
  };
  config?: {
    height?: number;
    showLegend?: boolean;
  };
}

export const Chart: React.FC<ChartProps> = ({ chartType, title, data, config = {} }) => {
  const chartData = data.labels.map((label, idx) => ({
    name: label,
    value: data.values[idx],
  }));

  const height = config.height || 300;

  return (
    <div className="chart">
      {title && <h3 className="text-lg font-semibold mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        {chartType === 'bar' ? (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            {config.showLegend !== false && <Legend />}
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Chart type "{chartType}" not yet implemented
          </div>
        )}
      </ResponsiveContainer>
    </div>
  );
};
