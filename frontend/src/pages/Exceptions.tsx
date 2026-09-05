import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getReconciliationCases } from '../services/api';

export default function Exceptions() {
  const { data: recData, isLoading, isError, refetch } = useQuery({
    queryKey: ['reconciliation'],
    queryFn: getReconciliationCases,
  });

  const allCases = recData?.cases || [];
  const exceptions = allCases.filter((c: any) => c.status !== 'EXACT_MATCH');

  return (
    <div className="w-full flex flex-col">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2 className="font-page-title text-page-title text-primary tracking-tight">Exceptions Management</h2>
          <p className="font-body-table text-text-secondary mt-1">Review and manage unresolved financial discrepancies.</p>
        </div>
        <button onClick={() => refetch()} className="bg-surface border border-border-base text-primary px-4 py-2 rounded text-sm hover:bg-surface-secondary transition-colors">
          Refresh List
        </button>
      </div>

      <div className="bg-surface border border-border-base rounded-lg overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-12 text-center text-text-secondary">Loading exceptions data...</div>
        ) : isError ? (
          <div className="p-12 text-center text-critical flex flex-col items-center">
            <span className="material-symbols-outlined text-4xl mb-2">error</span>
            <p>Failed to load exceptions. <button onClick={() => refetch()} className="underline hover:text-primary">Retry</button></p>
          </div>
        ) : exceptions.length === 0 ? (
          <div className="p-12 text-center text-text-secondary flex flex-col items-center">
            <span className="material-symbols-outlined text-4xl mb-2 text-success">task_alt</span>
            <p className="font-semibold text-text-primary">No unresolved exceptions found.</p>
            <p className="text-sm mt-1">All processed records have an exact match.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-body-table">
              <thead className="bg-surface-bright border-b border-border-base">
                <tr>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Case ID</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Mismatch Category</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Reason Code</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Risk</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Confidence</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-base">
                {exceptions.map((c: any) => (
                  <tr key={c.case_id} className="hover:bg-surface-secondary/50 transition-colors">
                    <td className="px-6 py-4 font-body-table-bold whitespace-nowrap">{c.case_id}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-error-container text-on-error-container">
                        {c.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {c.reason_code || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase ${
                        c.status.includes('MISSING') ? 'bg-critical/10 text-critical' : 'bg-warning/10 text-warning'
                      }`}>
                        {c.status.includes('MISSING') ? 'HIGH' : 'MED'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-surface-container rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${c.confidence < 0.8 ? 'bg-warning' : 'bg-success'}`} 
                            style={{ width: `${Math.round(c.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="text-sm text-text-secondary">{Math.round(c.confidence * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <Link to={`/investigation/${c.case_id}`} className="bg-action-blue-light text-action-blue-dark font-semibold px-4 py-1.5 rounded hover:bg-brand-blue hover:text-white transition-colors">
                        Investigate
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
