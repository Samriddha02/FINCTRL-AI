import React from 'react';
import { Bell, Search, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function TopHeader() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('finctrl_auth');
    navigate('/login');
  };

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