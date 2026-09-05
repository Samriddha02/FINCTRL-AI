// src/components/ui/Card.tsx
import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '', ...rest }) => {
  return (
    <div className={`bg-surface rounded-lg shadow-sm p-4 ${className}`} {...rest}>
      {children}
    </div>
  );
};

export default Card;
