import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileSearch, AlertCircle, UserCheck, MessageSquare, TrendingUp, Receipt, ShieldCheck } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getReviews } from '../services/api';

export default function Sidebar() {
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'Reconciliation', path: '/reconciliation', icon: <FileSearch size={20} /> },
    { name: 'Exceptions', path: '/exceptions', icon: <AlertCircle size={20} /> },
    { name: 'Human Review', path: '/human-review', icon: <UserCheck size={20} /> },
    { name: 'Finance Q&A', path: '/finance-qa', icon: <MessageSquare size={20} /> },
    { name: 'Cash Forecast', path: '/cash-forecast', icon: <TrendingUp size={20} /> },
    { name: 'Tax Matching', path: '/tax-matching', icon: <Receipt size={20} /> },
    { name: 'Audit Trail', path: '/audit-trail', icon: <ShieldCheck size={20} /> },
  ];

  // Fetch reviews to compute pending count (PENDING + ESCALATED)
  const { data: reviews = [] } = useQuery({ queryKey: ['reviews'], queryFn: getReviews });
  const pendingCount = reviews.filter((r: any) => r.status === 'PENDING' || r.status === 'ESCALATED').length;

  return (
    <aside className="w-sidebar-width bg-primary-container text-white flex flex-col hidden md:flex">
      <div className="px-2 py-4 flex items-center justify-center w-full border-b border-white/10">
        <img
          src="/assets/finctrl-ai-logo-high-quality.svg"
          alt="FINCTRL-AI"
          className="w-[220px] h-auto object-contain"
        />
      </div>
      <nav className="flex-1 py-6 px-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                isActive ? 'bg-brand-blue text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`
            }
          >
            {item.icon}
            <span className="font-medium text-sm">{item.name}</span>
            {item.name === 'Human Review' && pendingCount > 0 && (
              <span className="ml-auto inline-flex items-center justify-center h-5 min-w-[1.25rem] px-1 text-xs font-medium bg-warning/20 text-warning rounded-full">
                {pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}