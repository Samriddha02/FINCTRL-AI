import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditEvents } from '../services/api';

export default function AuditTrail() {
  const [selectedEvent, setSelectedEvent] = useState<any>(null);

  const { data: events, isLoading, isError, refetch } = useQuery({
    queryKey: ['auditEvents'],
    queryFn: getAuditEvents,
  });

  const auditEvents = events || [];

  const formatDetails = (details: any): string => {
    if (!details) return 'N/A';
    if (typeof details === 'string') return details;
    try {
      return JSON.stringify(details, null, 2);
    } catch {
      return String(details);
    }
  };

  return (
    <div className="w-full flex flex-col p-page-padding">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="font-page-title text-page-title text-primary tracking-tight">Audit Trail</h2>
          <p className="font-body-table text-text-secondary mt-1">APPEND-ONLY immutable ledger of all AI and human financial decisions.</p>
        </div>
        <button onClick={() => refetch()} className="bg-surface border border-border-base text-primary px-4 py-2 rounded text-sm hover:bg-surface-secondary transition-colors">
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-surface border border-border-base rounded-lg overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="p-8 text-center text-text-secondary">Loading audit events...</div>
          ) : isError ? (
            <div className="p-8 text-center text-critical">
              Unable to load audit events. <button onClick={() => refetch()} className="underline hover:text-primary">Retry</button>
            </div>
          ) : auditEvents.length === 0 ? (
            <div className="p-8 text-center text-text-secondary">No audit events recorded yet.</div>
          ) : (
            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
              <table className="w-full text-left font-body-table border-collapse relative">
                <thead className="bg-surface-bright sticky top-0 z-10 shadow-sm shadow-black/5">
                  <tr>
                    <th className="px-4 py-3 border-b border-border-base text-text-muted font-label-sm uppercase tracking-wider">Timestamp</th>
                    <th className="px-4 py-3 border-b border-border-base text-text-muted font-label-sm uppercase tracking-wider">Event Type</th>
                    <th className="px-4 py-3 border-b border-border-base text-text-muted font-label-sm uppercase tracking-wider">Actor</th>
                    <th className="px-4 py-3 border-b border-border-base text-text-muted font-label-sm uppercase tracking-wider">Case / Entity</th>
                    <th className="px-4 py-3 border-b border-border-base text-text-muted font-label-sm uppercase tracking-wider">Result</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-base">
                  {auditEvents.map((evt: any) => (
                    <tr 
                      key={evt.audit_event_id} 
                      onClick={() => setSelectedEvent(evt)}
                      className={`cursor-pointer hover:bg-surface-secondary/50 transition-colors ${selectedEvent?.audit_event_id === evt.audit_event_id ? 'bg-action-blue-light/30' : ''}`}
                    >
                      <td className="px-4 py-4 font-data-tabular text-sm text-text-secondary whitespace-nowrap">
                        {new Date(evt.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <span className="bg-surface-container text-text-primary px-2 py-1 rounded text-xs font-semibold">
                          {evt.event_type}
                        </span>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <span className="flex items-center gap-1 text-sm font-semibold text-action-blue-dark">
                          <span className="material-symbols-outlined text-[16px]">
                            {evt.actor_type === 'AI' || evt.actor_type === 'SYSTEM' ? 'robot_2' : 'person'}
                          </span>
                          {evt.actor_id || evt.actor_type}
                        </span>
                      </td>
                      <td className="px-4 py-4 font-data-tabular text-sm whitespace-nowrap text-text-primary">
                        {evt.case_id || '-'}
                      </td>
                      <td className="px-4 py-4 text-sm whitespace-nowrap">
                        {evt.result && (
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            evt.result === 'SUCCESS' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                          }`}>
                            {evt.result}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail View */}
        <div className="xl:col-span-1">
          {selectedEvent ? (
            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm sticky top-6">
              <h3 className="font-section-title text-lg mb-4 text-primary border-b border-border-base pb-3">Event Details</h3>
              <div className="space-y-4">
                <div>
                  <span className="font-label-sm text-text-secondary block mb-1">Event ID</span>
                  <div className="font-data-tabular text-sm bg-surface-secondary px-2 py-1 rounded border border-border-base inline-block break-all">
                    {selectedEvent.audit_event_id}
                  </div>
                </div>
                <div>
                  <span className="font-label-sm text-text-secondary block mb-1">Timestamp</span>
                  <div className="font-data-tabular text-sm">
                    {new Date(selectedEvent.timestamp).toLocaleString()}
                  </div>
                </div>
                <div>
                  <span className="font-label-sm text-text-secondary block mb-1">Event Type</span>
                  <div className="font-body-table font-bold">
                    {selectedEvent.event_type}
                  </div>
                </div>
                <div>
                  <span className="font-label-sm text-text-secondary block mb-1">Actor</span>
                  <div className="font-body-table flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px] text-text-muted">
                      {selectedEvent.actor_type === 'AI' || selectedEvent.actor_type === 'SYSTEM' ? 'robot_2' : 'person'}
                    </span>
                    {selectedEvent.actor_id || selectedEvent.actor_type} ({selectedEvent.actor_type})
                  </div>
                </div>
                <div>
                  <span className="font-label-sm text-text-secondary block mb-1">Case Reference</span>
                  <div className="font-data-tabular text-action-blue-dark">
                    {selectedEvent.case_id || 'N/A'}
                  </div>
                </div>
                {selectedEvent.review_id && (
                  <div>
                    <span className="font-label-sm text-text-secondary block mb-1">Review ID</span>
                    <div className="font-data-tabular text-sm">{selectedEvent.review_id}</div>
                  </div>
                )}
                {selectedEvent.investigation_id && (
                  <div>
                    <span className="font-label-sm text-text-secondary block mb-1">Investigation ID</span>
                    <div className="font-data-tabular text-sm">{selectedEvent.investigation_id}</div>
                  </div>
                )}
                {(selectedEvent.previous_state || selectedEvent.new_state) && (
                  <div>
                    <span className="font-label-sm text-text-secondary block mb-1">State Transition</span>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="bg-surface-container px-2 py-0.5 rounded font-data-tabular">{selectedEvent.previous_state || '—'}</span>
                      <span className="material-symbols-outlined text-[14px] text-text-muted">arrow_forward</span>
                      <span className="bg-surface-container px-2 py-0.5 rounded font-data-tabular">{selectedEvent.new_state || '—'}</span>
                    </div>
                  </div>
                )}
                {selectedEvent.result && (
                  <div>
                    <span className="font-label-sm text-text-secondary block mb-1">Result</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      selectedEvent.result === 'SUCCESS' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                    }`}>
                      {selectedEvent.result}
                    </span>
                  </div>
                )}
                <div>
                  <span className="font-label-sm text-text-secondary block mb-1">Details</span>
                  <div className="bg-surface-secondary p-3 rounded border border-border-base font-body-table text-sm text-text-primary whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {formatDetails(selectedEvent.details)}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm flex flex-col items-center justify-center h-48 text-text-muted">
              <span className="material-symbols-outlined text-[32px] mb-2">touch_app</span>
              <span>Select an event to view details</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
