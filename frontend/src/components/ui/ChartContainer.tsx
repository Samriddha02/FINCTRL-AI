// src/components/ui/ChartContainer.tsx
import React from 'react';

interface ChartContainerProps {
  className?: string;
  title?: string;
  children: React.ReactNode;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({ className = '', title, children }) => (
  <div className={`bg-surface rounded-lg shadow-sm p-4 ${className}`}>
    {title && <h3 className="font-label-sm text-primary mb-2">{title}</h3>}
    <div className="relative">{children}</div>
  </div>
);

export default ChartContainer;
