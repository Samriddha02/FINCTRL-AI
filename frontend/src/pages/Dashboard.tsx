import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getReconciliationCases, getReviews, getTaxMatches, getCashForecast } from '../services/api';
import { Card } from '../components/ui/Card';
import { KPICard } from '../components/ui/KPICard';
import { SectionHeader } from '../components/ui/SectionHeader';
import { DataTable } from '../components/ui/DataTable';
import { ChartContainer } from '../components/ui/ChartContainer';
import { LoadingState } from '../components/ui/LoadingState';

export default function Dashboard() {
  const { data: recData, isLoading: recLoading } = useQuery({ queryKey: ['reconciliation'], queryFn: getReconciliationCases });
  const { data: revData, isLoading: revLoading } = useQuery({ queryKey: ['reviews'], queryFn: getReviews });
  const { data: taxData, isLoading: taxLoading } = useQuery({ queryKey: ['taxMatches'], queryFn: getTaxMatches });
  const { data: forecastData, isLoading: forecastLoading } = useQuery({ queryKey: ['cashForecast'], queryFn: getCashForecast });

  const totalCases = recData?.cases?.length || 0;
  const exactMatches = recData?.cases?.filter((c: any) => c.status === 'EXACT_MATCH').length || 0;
  const requiresInvestigation = totalCases - exactMatches;
  const matchPercentage = totalCases > 0 ? Math.round((exactMatches / totalCases) * 100) : 0;
  const pendingReviews = revData?.filter((r: any) => r.status === 'PENDING' || r.status === 'ESCALATED').length || 0;
  const taxMismatches = taxData?.rate_mismatches || taxData?.amount_mismatches || taxData?.results?.filter((r: any) => r.status !== 'EXACT_MATCH').length || 0;
  const netCash = forecastData?.forecast?.net || 0;

  const forecastConfidence = forecastData?.confidence != null ? Math.round(forecastData.confidence * 100) : null;
  const riskCount = forecastData?.risk_factors?.length || 0;
  const dataQualityScore = forecastData?.data_quality?.score != null ? Math.round(forecastData.data_quality.score * 100) : null;

  const totalTaxResults = taxData?.results?.length || (taxData?.exact_matches ? (taxData.exact_matches + taxMismatches) : 0);
  const exactTaxMatches = taxData?.results?.filter((r: any) => r.status === 'EXACT_MATCH').length || taxData?.exact_matches || 0;
  const rateMismatches = taxData?.rate_mismatches || 0;

  const recentCases = recData?.cases?.slice(0, 5) || [];

  const investigationColumns = [
    {
      header: 'Case ID',
      accessor: (row: any) => (
        <Link to={`/investigation/${row.case_id}`} className="font-semibold text-action-blue-dark hover:underline tracking-tight">
          {row.case_id}
        </Link>
      ),
    },
    {
      header: 'Issue / Reason',
      accessor: (row: any) => (
        <span className="text-text-secondary text-sm font-medium">
          {row.reason_code || row.reason || (row.status === 'EXACT_MATCH' ? 'Match Verified' : 'Discrepancy Detected')}
        </span>
      ),
    },
    {
      header: 'Status',
      accessor: (row: any) => {
        let badgeStyle = 'bg-info/10 text-info border-info/20';
        if (row.status === 'EXACT_MATCH') {
          badgeStyle = 'bg-success/10 text-success border-success/20';
        } else if (row.status === 'REQUIRES_HUMAN_REVIEW' || row.status === 'PENDING' || row.status === 'ESCALATED') {
          badgeStyle = 'bg-critical/10 text-critical border-critical/20';
        } else if (row.status?.includes('INVESTIGATION') || row.status === 'MISMATCH' || row.status === 'REQUIRES_INVESTIGATION') {
          badgeStyle = 'bg-warning/10 text-warning border-warning/20';
        }
        return (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeStyle}`}>
            {row.status}
          </span>
        );
      },
    },
    {
      header: 'Action',
      accessor: (row: any) => (
        <Link to={`/investigation/${row.case_id}`} className="font-semibold text-sm text-action-blue-dark hover:underline flex items-center gap-1">
          Investigate <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
        </Link>
      ),
    },
  ];

  if (recLoading || revLoading || taxLoading || forecastLoading) {
    return <LoadingState />;
  }

  return (
    <div className="w-full flex flex-col p-page-padding min-w-0">
      <div className="mb-8">
        <h2 className="font-page-title text-page-title text-primary tracking-tight">Finance Overview</h2>
        <p className="font-body-table text-text-secondary">Overview of financial health and AI investigations.</p>
      </div>

      <div className="grid grid-cols-12 gap-gutter min-w-0">
        {/* Main Column */}
        <div className="col-span-12 xl:col-span-8 flex flex-col gap-lg min-w-0">
          {/* KPI Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 min-w-0">
            <KPICard label="Total Cases" value={totalCases} icon={<i className="material-symbols-outlined">account_balance</i>} />
            <KPICard label="Exact Matches" value={exactMatches} icon={<i className="material-symbols-outlined">check_circle</i>} />
            <KPICard label="Requires Investigation" value={requiresInvestigation} icon={<i className="material-symbols-outlined">error_outline</i>} />
            <KPICard label="Pending Review" value={pendingReviews} icon={<i className="material-symbols-outlined">hourglass_top</i>} />
          </div>

          {/* Reconciliation Overview */}
          <Card className="p-6 min-w-0">
            <SectionHeader title="Daily Reconciliation" action={<Link to="/reconciliation" className="font-label-sm text-action-blue-dark hover:underline">View All</Link>} />
            <div className="flex flex-col lg:flex-row items-center justify-between gap-8 min-w-0 mt-2">
              <div className="flex flex-col items-center justify-center flex-shrink-0">
                <ChartContainer className="w-56 h-56 flex items-center justify-center flex-shrink-0">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path className="text-surface-container" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3.5" />
                    <path className="text-success" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${matchPercentage}, 100`} strokeWidth="3.5" />
                    <path className="text-warning" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${100 - matchPercentage}, 100`} strokeWidth="3.5" />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-4xl font-extrabold text-text-primary tracking-tight">{matchPercentage}%</span>
                    <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider mt-0.5">Match Rate</span>
                  </div>
                </ChartContainer>
              </div>

              {/* Stats */}
              <div className="flex-1 w-full grid grid-cols-1 sm:grid-cols-2 gap-4 min-w-0">
                <div className="bg-surface-secondary p-4 rounded-lg border border-border-base flex flex-col justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">Total Transactions</span>
                  <div className="text-3xl font-bold text-text-primary">{totalCases.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-success/10 p-4 rounded-lg border border-success/20 flex flex-col justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-success mb-1">Exact Matches</span>
                  <div className="text-3xl font-bold text-success">{exactMatches.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-warning/10 p-4 rounded-lg border border-warning/20 flex flex-col justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-warning mb-1">Requires Investigation</span>
                  <div className="text-3xl font-bold text-warning">{requiresInvestigation.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-critical/10 p-4 rounded-lg border border-critical/20 flex flex-col justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-critical mb-1">Pending Review</span>
                  <div className="text-3xl font-bold text-critical">{pendingReviews.toLocaleString('en-IN')}</div>
                </div>
              </div>
            </div>
          </Card>

          {/* Recent AI Investigations */}
          <Card className="p-6 min-w-0">
            <SectionHeader
              title="Recent AI Investigations"
              action={
                <Link to="/reconciliation" className="font-label-sm text-action-blue-dark hover:underline flex items-center gap-1">
                  View All <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                </Link>
              }
            />
            <DataTable columns={investigationColumns} data={recentCases} loading={recLoading} emptyMessage="No recent investigations found." />
          </Card>
        </div>

        {/* Right Column */}
        <div className="col-span-12 xl:col-span-4 flex flex-col gap-lg min-w-0">
          {/* Quick Actions */}
          <Card className="flex gap-2 p-4 min-w-0">
            <Link to="/human-review" className="flex-1 min-w-0 flex items-center justify-center gap-1.5 bg-action-blue-dark text-white px-3 py-2 rounded font-label-sm hover:bg-secondary transition-colors text-center">
              <span className="material-symbols-outlined text-[18px] shrink-0">fact_check</span>
              <span className="truncate">Human Review</span>
              {pendingReviews > 0 && (<span className="bg-error px-1.5 py-0.5 rounded text-[10px] font-bold shrink-0 ml-0.5">{pendingReviews}</span>)}
            </Link>
            <Link to="/finance-qa" className="flex-1 min-w-0 flex items-center justify-center gap-1.5 bg-surface-secondary text-primary px-3 py-2 rounded font-label-sm hover:bg-border-base transition-colors border border-border-base text-center">
              <span className="material-symbols-outlined text-[18px] shrink-0">forum</span>
              <span className="truncate">Finance Q&amp;A</span>
            </Link>
          </Card>

          {/* Intelligence Cards Container */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-1 gap-lg min-w-0">
            {/* Cash Forecast */}
            <Card className="p-6 min-w-0 flex flex-col justify-between">
              <div>
                <SectionHeader
                  title="Cash Forecast"
                  action={
                    <Link to="/cash-forecast" className="font-label-sm text-action-blue-dark hover:underline flex items-center gap-1">
                      View Forecast <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                    </Link>
                  }
                />
                <div className="mt-3">
                  <div className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">
                    Projected Net Cash (Next 7 Days)
                  </div>
                  <div className="flex items-baseline justify-between gap-2 flex-wrap">
                    <div className="text-3xl font-extrabold text-text-primary tracking-tight">
                      ₹{(netCash || 0).toLocaleString('en-IN')}
                    </div>
                    {forecastConfidence !== null && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-success/10 text-success border border-success/20">
                        {forecastConfidence}% Confidence
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {(dataQualityScore !== null || riskCount > 0) && (
                <div className="mt-4 pt-3 border-t border-border-base flex items-center justify-between text-xs text-text-secondary">
                  {dataQualityScore !== null && (
                    <span>Data Quality: <strong className="text-text-primary">{dataQualityScore}/100</strong></span>
                  )}
                  {riskCount > 0 && (
                    <span className="inline-flex items-center gap-1 text-warning font-medium">
                      <span className="material-symbols-outlined text-[14px]">warning</span>
                      {riskCount} Risk Factor{riskCount > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              )}
            </Card>

            {/* Tax Matching */}
            <Card className="p-6 min-w-0 flex flex-col justify-between">
              <div>
                <SectionHeader
                  title="Tax Matching"
                  action={
                    <Link to="/tax-matching" className="font-label-sm text-action-blue-dark hover:underline flex items-center gap-1">
                      View Tax Matching <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                    </Link>
                  }
                />
                <div className="grid grid-cols-2 gap-3 mt-3">
                  {totalTaxResults > 0 && (
                    <div className="bg-surface-secondary p-3 rounded-lg border border-border-base">
                      <div className="text-2xl font-bold text-text-primary">{totalTaxResults}</div>
                      <div className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Total Reports</div>
                    </div>
                  )}
                  <div className="bg-success/10 p-3 rounded-lg border border-success/20">
                    <div className="text-2xl font-bold text-success">{exactTaxMatches}</div>
                    <div className="text-xs font-semibold text-success uppercase tracking-wider">Exact Matches</div>
                  </div>
                  <div className="bg-warning/10 p-3 rounded-lg border border-warning/20">
                    <div className="text-2xl font-bold text-warning">{taxMismatches}</div>
                    <div className="text-xs font-semibold text-warning uppercase tracking-wider">Mismatches</div>
                  </div>
                  {rateMismatches > 0 && (
                    <div className="bg-critical/10 p-3 rounded-lg border border-critical/20">
                      <div className="text-2xl font-bold text-critical">{rateMismatches}</div>
                      <div className="text-xs font-semibold text-critical uppercase tracking-wider">Rate Mismatches</div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
