import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getReconciliationCases, getReviews, getTaxMatches, getCashForecast } from '../services/api';

export default function Dashboard() {
  const { data: recData, isLoading: recLoading } = useQuery({ queryKey: ['reconciliation'], queryFn: getReconciliationCases });
  const { data: revData, isLoading: revLoading } = useQuery({ queryKey: ['reviews'], queryFn: getReviews });
  const { data: taxData, isLoading: taxLoading } = useQuery({ queryKey: ['taxMatches'], queryFn: getTaxMatches });
  const { data: forecastData, isLoading: forecastLoading } = useQuery({ queryKey: ['cashForecast'], queryFn: getCashForecast });

  const totalCases = recData?.cases?.length || 0;
  const exactMatches = recData?.cases?.filter((c: any) => c.status === 'EXACT_MATCH').length || 0;
  const requiresInvestigation = totalCases - exactMatches;
  const matchPercentage = totalCases > 0 ? Math.round((exactMatches / totalCases) * 100) : 0;
  const investigatePercentage = 100 - matchPercentage;

  const pendingReviews = revData?.filter((r: any) => r.status === 'PENDING' || r.status === 'IN_REVIEW').length || 0;
  
  const taxMismatches = taxData?.rate_mismatches || taxData?.amount_mismatches || taxData?.results?.filter((r: any) => r.status !== 'EXACT_MATCH').length || 0;
  
  const netCash = forecastData?.forecast?.net || 0;

  return (
    <div className="w-full flex flex-col p-page-padding">
      <div className="mb-8">
        <h2 className="font-page-title text-page-title text-primary tracking-tight">Finance Overview</h2>
        <p className="font-body-table text-text-secondary">Overview of financial health and AI investigations.</p>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        {/* Main Column */}
        <div className="col-span-12 xl:col-span-8 flex flex-col gap-lg">
          
          {/* Reconciliation Overview Card */}
          <div className="bg-surface border border-border-base rounded-lg p-lg shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-section-title text-section-title text-primary flex items-center gap-2">
                <span className="material-symbols-outlined text-action-blue-dark">account_balance</span>
                Daily Reconciliation
              </h3>
              <Link to="/reconciliation" className="font-label-sm text-action-blue-dark hover:underline">View All</Link>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
              {/* Donut Chart (simplified visual) */}
              <div className="relative w-32 h-32 mx-auto">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  {/* Background */}
                  <path className="text-surface-container" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3"></path>
                  {/* Exact Match */}
                  <path className="text-success transition-all duration-1000" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${matchPercentage}, 100`} strokeWidth="3"></path>
                  {/* Requires Investigation */}
                  <path className="text-warning transition-all duration-1000" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${investigatePercentage}, 100`} strokeDashoffset={`-${matchPercentage}`} strokeWidth="3"></path>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="font-display-sm text-primary font-bold">{matchPercentage}%</span>
                  <span className="font-caption text-text-muted text-[10px] uppercase">Matched</span>
                </div>
              </div>
              
              {/* Stats */}
              <div className="md:col-span-2 grid grid-cols-2 gap-4">
                <div className="bg-surface-secondary p-4 rounded border border-border-base">
                  <div className="font-display-lg text-primary mb-1">{totalCases}</div>
                  <div className="font-label-xs text-text-secondary">Total Transactions</div>
                </div>
                <div className="bg-success/10 p-4 rounded border border-success/20">
                  <div className="font-display-lg text-success mb-1">{exactMatches}</div>
                  <div className="font-label-xs text-success">Exact Matches</div>
                </div>
                <div className="bg-warning/10 p-4 rounded border border-warning/20">
                  <div className="font-display-lg text-warning mb-1">{requiresInvestigation}</div>
                  <div className="font-label-xs text-warning">Requires Investigation</div>
                </div>
                <div className="bg-critical/10 p-4 rounded border border-critical/20">
                  <div className="font-display-lg text-critical mb-1">{pendingReviews}</div>
                  <div className="font-label-xs text-critical">Pending Review</div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Recent AI Investigations */}
          <div className="bg-surface border border-border-base rounded-lg p-lg shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-section-title text-section-title text-primary flex items-center gap-2">
                <span className="material-symbols-outlined text-action-blue-dark">robot_2</span>
                Recent AI Investigations
              </h3>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left font-body-table">
                <thead className="bg-surface-bright">
                  <tr>
                    <th className="px-4 py-3 border-b text-text-muted font-label-sm uppercase">Case ID</th>
                    <th className="px-4 py-3 border-b text-text-muted font-label-sm uppercase">Risk</th>
                    <th className="px-4 py-3 border-b text-text-muted font-label-sm uppercase text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-base">
                  {recData?.cases?.slice(0, 5).map((c: any) => (
                    <tr key={c.case_id} className="hover:bg-surface-secondary/50">
                      <td className="px-4 py-3 font-body-table-bold">{c.case_id}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          c.status === 'EXACT_MATCH' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link to={`/investigation/${c.case_id}`} className="text-action-blue-dark font-semibold hover:underline">
                          Investigate
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {(!recData?.cases || recData.cases.length === 0) && (
                    <tr><td colSpan={3} className="px-4 py-4 text-center text-text-muted">No recent investigations found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="col-span-12 xl:col-span-4 flex flex-col gap-lg">
          
          {/* Quick Actions */}
          <div className="bg-surface border border-border-base rounded-lg p-4 shadow-sm flex gap-2 overflow-x-auto">
            <Link to="/human-review" className="flex-shrink-0 flex items-center gap-2 bg-action-blue-dark text-white px-4 py-2 rounded font-label-sm hover:bg-secondary transition-colors">
              <span className="material-symbols-outlined text-[18px]">fact_check</span>
              Human Review {pendingReviews > 0 && <span className="bg-error px-1.5 py-0.5 rounded text-[10px] font-bold">{pendingReviews}</span>}
            </Link>
            <Link to="/finance-qa" className="flex-shrink-0 flex items-center gap-2 bg-surface-secondary text-primary px-4 py-2 rounded font-label-sm hover:bg-border-base transition-colors border border-border-base">
              <span className="material-symbols-outlined text-[18px]">forum</span>
              Finance Q&A
            </Link>
          </div>

          {/* Cash Forecast Snippet */}
          <div className="bg-surface border border-border-base rounded-lg p-lg shadow-sm">
            <h3 className="font-section-title text-section-title text-primary mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-action-blue-dark">trending_up</span>
              Cash Forecast
            </h3>
            <div className="flex justify-between items-center mb-4">
              <div className="font-display-lg text-primary">₹{(netCash || 0).toLocaleString('en-IN')}</div>
              <div className="text-success flex items-center bg-success/10 px-2 py-1 rounded text-xs font-semibold">
                <span className="material-symbols-outlined text-[14px]">arrow_upward</span> Net Cash
              </div>
            </div>
            <Link to="/cash-forecast" className="text-action-blue-dark font-label-sm hover:underline flex items-center gap-1">
              View Detailed Forecast <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </Link>
          </div>

          {/* Tax Matching Snippet */}
          <div className="bg-surface border border-border-base rounded-lg p-lg shadow-sm">
            <h3 className="font-section-title text-section-title text-primary mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-action-blue-dark">receipt_long</span>
              Tax Matching
            </h3>
            <div className="flex justify-between items-center mb-4">
              <div>
                <div className="font-display-lg text-warning mb-1">{taxMismatches}</div>
                <div className="font-label-xs text-text-secondary">Rate Mismatches</div>
              </div>
            </div>
            <Link to="/tax-matching" className="text-action-blue-dark font-label-sm hover:underline flex items-center gap-1">
              Review Tax Rules <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </Link>
          </div>

        </div>
      </div>
    </div>
  );
}
