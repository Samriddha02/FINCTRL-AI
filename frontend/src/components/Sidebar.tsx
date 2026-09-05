import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileSearch, AlertCircle, UserCheck, MessageSquare, TrendingUp, Receipt, ShieldCheck } from 'lucide-react';

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

  return (
    <aside className="w-sidebar-width bg-primary-container text-white flex flex-col hidden md:flex">
      <div className="p-6 flex items-center gap-3 border-b border-white/10">
        <div className="w-8 h-8 rounded bg-brand-blue flex items-center justify-center font-bold">F</div>
        <span className="font-semibold text-lg tracking-wide">FINCTRL-AI</span>
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
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}