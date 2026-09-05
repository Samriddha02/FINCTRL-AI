import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { getInvestigation, startInvestigation, createReview } from '../services/api';

export default function CaseInvestigation() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: invData, isLoading } = useQuery({
    queryKey: ['investigation', caseId],
    queryFn: () => getInvestigation(caseId as string),
    retry: false
  });

  const startInvMutation = useMutation({
    mutationFn: () => startInvestigation(caseId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigation', caseId] });
    },
  });

  const sendToReviewMutation = useMutation({
    mutationFn: () => createReview(caseId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      navigate('/human-review');
    },
  });

  if (isLoading && !invData) {
    return (
      <div className="w-full flex flex-col p-page-padding">
        <div className="p-12 text-center text-text-secondary">Loading investigation...</div>
      </div>
    );
  }

  const investigation = invData || null;
  const status = investigation?.investigation_status || 'NOT_STARTED';
  const isComplete = status === 'COMPLETED' || status === 'ESCALATED';
  const isNotStarted = status === 'NOT_STARTED' || status === 'NOT_FOUND';

  const steps = investigation?.investigation_steps || [];
  const rootCause = investigation?.root_cause;
  const summary = investigation?.summary;
  const confidence = investigation?.root_cause_confidence || 0;
  const facts = investigation?.facts || [];
  const recommendedActions = investigation?.recommended_actions || [];
  const toolCalls = investigation?.tool_calls || [];

  return (
    <div className="w-full flex flex-col p-page-padding">
      <div className="mb-6 flex justify-between items-start">
        <div>
          <button onClick={() => navigate(-1)} className="text-text-secondary hover:text-primary mb-2 flex items-center gap-1 text-sm font-semibold transition-colors">
            <span className="material-symbols-outlined text-[16px]">arrow_back</span> Back
          </button>
          <h2 className="font-page-title text-page-title text-primary tracking-tight flex items-center gap-3">
            Investigation: {caseId}
            <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
              isComplete ? 'bg-success/10 text-success' : 'bg-surface-secondary text-text-muted'
            }`}>
              {status}
            </span>
          </h2>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-component-gap">
          {/* Main Investigation Content */}
          {isComplete ? (
            <>
              {/* Root Cause Card */}
              <section className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-section-title text-section-title text-primary flex items-center gap-2">
                    <span className="material-symbols-outlined text-action-blue-dark">search_insights</span> Root Cause Analysis
                  </h3>
                  <div className="flex items-center gap-2 bg-surface-container px-3 py-1 rounded-full border border-border-base">
                    <span className="text-xs text-text-secondary font-semibold uppercase">Confidence</span>
                    <span className={`text-sm font-bold ${confidence > 0.8 ? 'text-success' : 'text-warning'}`}>
                      {Math.round(confidence * 100)}%
                    </span>
                  </div>
                </div>
                <div className="bg-surface-secondary rounded p-4 border border-border-base mb-4">
                  <p className="font-body-table-bold text-primary">{rootCause || 'Root cause not determined.'}</p>
                </div>
              </section>

              {/* Evidence & Facts Card */}
              <section className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
                <h3 className="font-section-title text-section-title text-primary mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-action-blue-dark">fact_check</span> Evidence & Facts
                </h3>
                {facts.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-body-table text-sm">
                      <thead className="bg-surface-bright">
                        <tr>
                          <th className="py-2 px-3 border-b text-text-muted font-label-sm uppercase whitespace-nowrap">Source</th>
                          <th className="py-2 px-3 border-b text-text-muted font-label-sm uppercase whitespace-nowrap">Fact Key</th>
                          <th className="py-2 px-3 border-b text-text-muted font-label-sm uppercase whitespace-nowrap">Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-base">
                        {facts.map((fact: any, idx: number) => (
                          <tr key={idx} className="hover:bg-surface-secondary/50">
                            <td className="py-3 px-3">
                              <span className="px-2 py-0.5 bg-surface-container text-text-secondary rounded text-xs">{fact.source}</span>
                            </td>
                            <td className="py-3 px-3 font-semibold text-primary">{fact.key}</td>
                            <td className="py-3 px-3 font-data-tabular">
                              {typeof fact.value === 'object' ? JSON.stringify(fact.value) : String(fact.value)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary py-4 text-center">No evidence facts available.</p>
                )}
              </section>

              {/* Tool Calls */}
              {toolCalls.length > 0 && (
                <section className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
                  <h3 className="font-section-title text-section-title text-primary mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-action-blue-dark">build</span> Tools Executed
                  </h3>
                  <div className="space-y-3">
                    {toolCalls.map((tc: any, idx: number) => (
                      <div key={idx} className="p-3 border border-border-base rounded bg-surface-secondary text-sm">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-bold font-mono text-primary">{tc.tool_name}</span>
                          <span className={`text-xs font-semibold ${tc.success ? 'text-success' : 'text-critical'}`}>
                            {tc.success ? 'SUCCESS' : 'FAILED'}
                          </span>
                        </div>
                        <p className="font-mono text-xs text-text-secondary bg-surface p-2 rounded">
                          {JSON.stringify(tc.arguments)}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          ) : (
            <section className="bg-surface border border-border-base rounded-lg p-12 text-center shadow-sm">
              <span className="material-symbols-outlined text-[48px] text-border-base mb-4 block">query_stats</span>
              <h3 className="font-section-title text-lg text-primary mb-2">No active investigation</h3>
              <p className="text-text-secondary mb-6 max-w-md mx-auto">
                An investigation has not been run for this case yet. Click 'Start Investigation' to deploy the autonomous agent to gather facts and identify the root cause.
              </p>
              <button
                onClick={() => startInvMutation.mutate()}
                disabled={startInvMutation.isPending}
                className="px-6 py-2.5 bg-action-blue-dark hover:bg-secondary text-surface font-label-sm rounded transition-colors shadow-sm disabled:opacity-50"
              >
                {startInvMutation.isPending ? 'Starting...' : 'Start Investigation'}
              </button>
              {startInvMutation.isError && (
                <p className="text-critical text-sm mt-3">Failed to start investigation. Please try again.</p>
              )}
            </section>
          )}
        </div>

        {/* RIGHT COLUMN: Status & Recommendation */}
        <div className="col-span-12 lg:col-span-4 space-y-component-gap">
          {/* Investigation Status Panel */}
          {investigation && steps.length > 0 && (
            <section className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
              <h3 className="font-section-title text-section-title text-primary mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-action-blue-dark">radar</span> Investigation Progress
              </h3>
              <div className="space-y-3">
                {steps.map((stepName: string, idx: number) => (
                  <div key={idx} className="relative flex items-center gap-3 bg-surface z-10">
                    <div className="h-6 w-6 rounded-full flex items-center justify-center shrink-0 border-2 border-surface bg-success text-surface">
                      <span className="material-symbols-outlined text-[14px] font-bold">check</span>
                    </div>
                    <span className="text-sm font-body-table-bold text-primary">{stepName}</span>
                  </div>
                ))}
              </div>
              {isComplete && (
                <div className="mt-6 bg-success/10 border border-success/20 rounded p-3 text-center flex items-center justify-center gap-2 text-success">
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                  <span className="font-body-table-bold text-sm">Investigation Complete</span>
                </div>
              )}
            </section>
          )}

          {/* AI Analysis Summary */}
          {summary && (
            <section className="bg-action-blue-light/50 border border-action-blue-light rounded-lg p-5 shadow-sm">
              <h4 className="font-section-title text-sm text-primary mb-2 flex items-center gap-2">
                <span className="material-symbols-outlined text-action-blue-dark text-[18px]">psychology</span> AI Investigation Summary
              </h4>
              <p className="text-sm text-text-secondary leading-relaxed font-body-table">{summary}</p>
            </section>
          )}

          {/* Safety Panel */}
          <section className="bg-surface border border-border-base rounded-lg p-5 shadow-sm">
            <h4 className="font-section-title text-sm text-primary mb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-text-muted text-[18px]">gpp_maybe</span> Security Constraints
            </h4>
            <ul className="space-y-2">
              <li className="flex justify-between items-center text-sm border-b border-border-base pb-2">
                <span className="text-text-secondary">System Access</span>
                <span className="bg-info/10 text-info px-2 py-0.5 rounded text-xs font-semibold">READ-ONLY</span>
              </li>
              <li className="flex justify-between items-center text-sm border-b border-border-base pb-2">
                <span className="text-text-secondary">Financial Mutation</span>
                <span className="bg-surface-container text-text-muted px-2 py-0.5 rounded text-xs font-semibold">DISABLED</span>
              </li>
              <li className="flex justify-between items-center text-sm">
                <span className="text-text-secondary">Oversight Status</span>
                <span className="text-primary font-semibold flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px] text-warning">warning</span> REQUIRED
                </span>
              </li>
            </ul>
          </section>

          {/* Recommendation Card */}
          {isComplete && recommendedActions.length > 0 && (
            <section className="bg-surface border border-warning/30 shadow-[0_0_15px_rgba(245,158,11,0.05)] rounded-lg p-6 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-warning"></div>
              <h3 className="font-section-title text-section-title text-primary mb-2">Recommended Action</h3>
              <p className="text-sm text-text-secondary mb-6 font-body-table font-semibold">
                {recommendedActions[0].action}
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => sendToReviewMutation.mutate()}
                  disabled={sendToReviewMutation.isPending}
                  className="w-full bg-action-blue-dark hover:bg-secondary text-surface font-label-sm text-label-sm py-2.5 rounded transition-colors shadow-sm flex justify-center items-center gap-2 disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[18px]">send</span>
                  {sendToReviewMutation.isPending ? 'Sending...' : 'Send to Human Review'}
                </button>
              </div>
            </section>
          )}

          {isNotStarted && (
            <section className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
              <h3 className="font-section-title text-section-title text-primary mb-2">Start Analysis</h3>
              <p className="text-sm text-text-secondary mb-4 font-body-table">
                Run the AI investigation agent to analyze this case.
              </p>
              <button
                onClick={() => startInvMutation.mutate()}
                disabled={startInvMutation.isPending}
                className="w-full bg-action-blue-dark hover:bg-secondary text-surface font-label-sm text-label-sm py-2.5 rounded transition-colors shadow-sm flex justify-center items-center gap-2 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">play_arrow</span>
                {startInvMutation.isPending ? 'Starting...' : 'Run AI Check'}
              </button>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
