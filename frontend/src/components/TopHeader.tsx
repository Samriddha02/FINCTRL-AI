import React from 'react';
import { Bell, Search } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function TopHeader() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem('finctrl_auth');
    navigate('/login');
  };

  // Derive breadcrumb parts from path, ignoring leading slash
  const pathParts = location.pathname.split('/').filter(Boolean);
  const breadcrumb = pathParts.map((part, idx) => {
    const isLast = idx === pathParts.length - 1;
    const name = part.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    return isLast ? (
      <span key={idx} className="text-text-primary font-medium">{name}</span>
    ) : (
      <span key={idx} className="text-text-secondary">
        {name} <span className="mx-1">/</span>
      </span>
    );
  });

  return (
    <header className="h-16 bg-surface border-b border-border-base flex items-center justify-between px-6 shrink-0">
      {/* Breadcrumb */}
      <div className="flex items-center space-x-2 text-sm">
        {breadcrumb.length > 0 ? breadcrumb : <span className="text-text-secondary">Dashboard</span>}
      </div>
      {/* Global search (UI‑only) */}
      <div className="flex items-center text-text-secondary">
        <Search size={20} className="mr-2" />
        <input
          type="text"
          placeholder="Search cases, invoices..."
          className="bg-transparent border-none focus:outline-none text-sm w-64"
          // No backend call – UI‑only placeholder
        />
      </div>
      <div className="flex items-center gap-4 text-text-secondary">
        <button className="relative p-2 hover:bg-surface-secondary rounded-full transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-critical rounded-full" />
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-action-blue-light text-brand-blue font-semibold hover:bg-action-blue-dark hover:text-white transition-colors"
          title="Log Out"
        >
          JD
        </button>
      </div>
    </header>
  );
}