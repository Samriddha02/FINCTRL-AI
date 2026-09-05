// src/components/ui/KPICard.tsx
import React from 'react';
import { Card } from './Card';

interface KPICardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: 'up' | 'down';
  trendValue?: string | number;
}

export const KPICard: React.FC<KPICardProps> = ({ label, value, icon, trend, trendValue }) => {
  const trendColor = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-critical' : '';
  const trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : null;
  return (
    <Card className="flex items-center space-x-4 p-4 border border-border-base hover:shadow-md">
      {icon && <div className="text-4xl text-primary">{icon}</div>}
      <div className="flex-1">
        <div className="text-sm font-medium text-text-secondary">{label}</div>
        <div className="text-4xl font-semibold text-text-primary">{value}</div>
      </div>
      {trend && (
        <div className={`text-sm font-medium ${trendColor}`}>
          {trendIcon} {trendValue}
        </div>
      )}
    </Card>
  );
};

export default KPICard;
