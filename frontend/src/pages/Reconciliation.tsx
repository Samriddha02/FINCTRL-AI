import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getReconciliationCases } from '../services/api';

export default function Reconciliation() {
  const { data: recData, isLoading } = useQuery({
    queryKey: ['reconciliation'],
    queryFn: getReconciliationCases,
  });

  const cases = recData?.cases || [];

  return (
    <div className="w-full flex flex-col">
      <div className="mb-6">
        <h2 className="font-page-title text-page-title text-primary tracking-tight">Reconciliation</h2>
      </div>

      <div className="bg-surface border border-border-base rounded-lg overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-8 text-text-secondary">Loading reconciliation data...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-body-table">
              <thead className="bg-surface-bright border-b border-border-base">
                <tr>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Case ID</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Status</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Reason</th>
                  <th className="px-6 py-3 text-text-muted font-label-sm uppercase whitespace-nowrap">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-base">
                {cases.map((c: any) => (
                  <tr key={c.case_id} className="hover:bg-surface-secondary/50 transition-colors">
                    <td className="px-6 py-4 font-body-table-bold whitespace-nowrap">{c.case_id}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                        c.status === 'EXACT_MATCH' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{c.reason_code || '-'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link to={`/investigation/${c.case_id}`} className="text-brand-blue font-semibold hover:underline">
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
