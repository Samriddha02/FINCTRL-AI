import os

files = {
    "src/components/AppShell.tsx": """import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopHeader from './TopHeader';

export default function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto p-page-padding">
          <Outlet />
        </main>
      </div>
    </div>
  );
}""",
    "src/components/Sidebar.tsx": """import React from 'react';
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
}""",
    "src/components/TopHeader.tsx": """import React from 'react';
import { Bell, Search, User } from 'lucide-react';

export default function TopHeader() {
  return (
    <header className="h-16 bg-surface border-b border-border-base flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center text-text-secondary">
        <Search size={20} className="mr-2" />
        <input 
          type="text" 
          placeholder="Search cases, invoices..." 
          className="bg-transparent border-none focus:outline-none text-sm w-64"
        />
      </div>
      <div className="flex items-center gap-4 text-text-secondary">
        <button className="relative p-2 hover:bg-surface-secondary rounded-full transition-colors">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-critical rounded-full"></span>
        </button>
        <div className="w-8 h-8 rounded-full bg-action-blue-light text-brand-blue flex items-center justify-center font-semibold">
          JD
        </div>
      </div>
    </header>
  );
}""",
    "src/pages/Dashboard.tsx": "export default function Dashboard() { return <div>Dashboard</div>; }",
    "src/pages/Reconciliation.tsx": "export default function Reconciliation() { return <div>Reconciliation</div>; }",
    "src/pages/CaseInvestigation.tsx": "export default function CaseInvestigation() { return <div>CaseInvestigation</div>; }",
    "src/pages/Exceptions.tsx": "export default function Exceptions() { return <div>Exceptions</div>; }",
    "src/pages/HumanReview.tsx": "export default function HumanReview() { return <div>HumanReview</div>; }",
    "src/pages/ReviewDetail.tsx": "export default function ReviewDetail() { return <div>ReviewDetail</div>; }",
    "src/pages/FinanceQA.tsx": "export default function FinanceQA() { return <div>FinanceQA</div>; }",
    "src/pages/CashForecast.tsx": "export default function CashForecast() { return <div>CashForecast</div>; }",
    "src/pages/TaxMatching.tsx": "export default function TaxMatching() { return <div>TaxMatching</div>; }",
    "src/pages/AuditTrail.tsx": "export default function AuditTrail() { return <div>AuditTrail</div>; }",
    "src/pages/Login.tsx": "export default function Login() { return <div>Login</div>; }",
}

for filepath, content in files.items():
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Scaffolded components.")
