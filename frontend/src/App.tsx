import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AppShell from './components/AppShell';
import Dashboard from './pages/Dashboard';
import Reconciliation from './pages/Reconciliation';
import CaseInvestigation from './pages/CaseInvestigation';
import Exceptions from './pages/Exceptions';
import HumanReview from './pages/HumanReview';
import ReviewDetail from './pages/ReviewDetail';
import FinanceQA from './pages/FinanceQA';
import CashForecast from './pages/CashForecast';
import TaxMatching from './pages/TaxMatching';
import AuditTrail from './pages/AuditTrail';
import Login from './pages/Login';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          {/* Protected Routes inside AppShell */}
          <Route path="/" element={<AppShell />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="reconciliation" element={<Reconciliation />} />
            <Route path="investigation" element={<Navigate to="/reconciliation" replace />} />
            <Route path="investigation/:caseId" element={<CaseInvestigation />} />
            <Route path="exceptions" element={<Exceptions />} />
            <Route path="human-review" element={<HumanReview />} />
            <Route path="human-review/:reviewId" element={<ReviewDetail />} />
            <Route path="finance-qa" element={<FinanceQA />} />
            <Route path="cash-forecast" element={<CashForecast />} />
            <Route path="tax-matching" element={<TaxMatching />} />
            <Route path="audit-trail" element={<AuditTrail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
