// src/components/ui/SectionHeader.tsx
import React from 'react';

interface SectionHeaderProps {
  title: string;
  /** Optional element (e.g., link or button) displayed on the right side */
  action?: React.ReactNode;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ title, action }) => (
  <div className="flex items-center justify-between mb-4">
    <h3 className="font-section-title text-section-title text-primary flex items-center gap-2">
      {title}
    </h3>
    {action && <div>{action}</div>}
  </div>
);

export default SectionHeader;
