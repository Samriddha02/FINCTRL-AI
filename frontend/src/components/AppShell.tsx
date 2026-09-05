import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopHeader from './TopHeader';

export default function AppShell() {
  const isAuthenticated = localStorage.getItem('finctrl_auth') === 'true';

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

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
}