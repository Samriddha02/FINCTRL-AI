import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getTaxMatches, getTaxMatch } from '../services/api';

export default function TaxMatching() {
  const [selectedInvoice, setSelectedInvoice] = useState<string | null>(null);

  const { data: taxData, isLoading, isError } = useQuery({
    queryKey: ['taxMatches'],
    queryFn: getTaxMatches,
  });

  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ['taxMatchDetail', selectedInvoice],
    queryFn: () => getTaxMatch(selectedInvoice!),
    enabled: !!selectedInvoice,
  });

  const discrepancies = taxData?.results || [];

  if (selectedInvoice) {
    return (
      <div className="w-full flex flex-col">
        <div className="mb-6 flex items-center gap-4">
          <button onClick={() => setSelectedInvoice(null)} className="text-text-secondary hover:text-primary transition-colors">
            <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          </button>
          <h2 className="font-page-title text-page-title text-primary tracking-tight">Invoice: {selectedInvoice}</h2>
        </div>

        {detailLoading ? (
          <div className="p-8 text-text-secondary">Loading tax match details...</div>
        ) : detailData ? (
          <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="font-section-title text-lg font-bold">{detailData.match_id}</h3>
                <p className="text-text-secondary font-body-table">{detailData.explanation}</p>
              </div>
              <span className={`px-3 py-1 rounded text-sm font-bold ${
                detailData.status === 'EXACT_MATCH' ? 'bg-success/10 text-success' : 'bg-error-container text-on-error-container'
              }`}>
                {detailData.status}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8 border-t border-border-base pt-6">
              <div>
                <div className="font-label-sm text-text-secondary uppercase mb-1">Invoice Taxable</div>
                <div className="font-data-tabular">₹{detailData.invoice_taxable_amount?.toLocaleString() || '-'}</div>
              </div>
              <div>
                <div className="font-label-sm text-text-secondary uppercase mb-1">Invoice Tax Rate</div>
                <div className="font-data-tabular">{(detailData.invoice_tax_rate * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div className="font-label-sm text-text-secondary uppercase mb-1">Ledger Tax Rate</div>
                <div className="font-data-tabular text-warning">{(detailData.ledger_tax_rate * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div className="font-label-sm text-text-secondary uppercase mb-1">Difference</div>
                <div className="font-data-tabular text-critical font-bold">₹{detailData.difference?.toLocaleString() || '0'}</div>
              </div>
            </div>

            {detailData.evidence && detailData.evidence.length > 0 && (
              <div className="mb-6">
                <h4 className="font-label-sm text-text-secondary uppercase tracking-wider mb-3">Evidence</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-body-table text-sm">
                    <thead className="bg-surface-bright">
                      <tr>
                        <th className="py-2 px-3 border-b text-text-muted">Source</th>
                        <th className="py-2 px-3 border-b text-text-muted">Entity ID</th>
                        <th className="py-2 px-3 border-b text-text-muted">Field</th>
                        <th className="py-2 px-3 border-b text-text-muted">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-base">
                      {detailData.evidence.map((ev: any, idx: number) => (
                        <tr key={idx}>
                          <td className="py-2 px-3">{ev.source}</td>
                          <td className="py-2 px-3 font-data-tabular">{ev.entity_id}</td>
                          <td className="py-2 px-3">{ev.field}</td>
                          <td className="py-2 px-3 font-data-tabular">{ev.value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            {detailData.needs_review && (
              <div className="bg-warning/10 border border-warning/20 p-4 rounded text-warning text-sm font-semibold flex items-center gap-2">
                <span className="material-symbols-outlined">warning</span> This discrepancy requires human review.
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-critical">Failed to load details.</div>
        )}
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col">
      <div className="mb-8">
        <h2 className="font-page-title text-page-title text-primary tracking-tight">Tax Matching Control</h2>
        <p className="font-body-table text-text-secondary mt-1">Identify tax rate mismatches between invoices, payments, and ledger.</p>
      </div>

      <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-text-secondary">Loading tax match reports...</div>
        ) : isError ? (
          <div className="py-12 text-center text-critical">Failed to load tax matching data. Retry later.</div>
        ) : discrepancies.length === 0 ? (
          <div className="py-12 text-center text-text-secondary flex flex-col items-center">
            <span className="material-symbols-outlined text-[48px] text-success mb-4">verified</span>
            <p>No tax mismatches found. All rates align.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-bright border-b border-border-base">
                  <th className="py-3 px-4 font-label-sm text-text-secondary uppercase">Invoice ID</th>
                  <th className="py-3 px-4 font-label-sm text-text-secondary uppercase">Invoice Rate</th>
                  <th className="py-3 px-4 font-label-sm text-text-secondary uppercase">Ledger Rate</th>
                  <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-right">Tax Diff</th>
                  <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-center">Status</th>
                  <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-base">
                {discrepancies.map((d: any, idx: number) => (
                  <tr key={idx} className="hover:bg-surface-secondary/50">
                    <td className="py-4 px-4 font-data-tabular">{d.invoice_id}</td>
                    <td className="py-4 px-4 font-data-tabular">{(d.invoice_tax_rate * 100).toFixed(1)}%</td>
                    <td className="py-4 px-4 font-data-tabular text-warning">{(d.ledger_tax_rate * 100).toFixed(1)}%</td>
                    <td className="py-4 px-4 text-right font-data-tabular font-bold text-critical">
                      ₹{d.difference?.toLocaleString() || '0'}
                    </td>
                    <td className="py-4 px-4 text-center">
                      <span className={`inline-flex px-2 py-1 rounded text-xs font-semibold ${
                        d.status === 'EXACT_MATCH' ? 'bg-success/10 text-success' : 'bg-error-container text-on-error-container'
                      }`}>
                        {d.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <button 
                        onClick={() => setSelectedInvoice(d.invoice_id)}
                        className="bg-surface border border-border-base text-action-blue-dark px-3 py-1 rounded font-body-table-bold text-sm hover:bg-surface-container"
                      >
                        View Details
                      </button>
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
