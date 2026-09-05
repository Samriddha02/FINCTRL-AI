import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getReview, approveReview, rejectReview, requestMoreInvestigation } from '../services/api';

export default function ReviewDetail() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const { data: review, isLoading } = useQuery({
    queryKey: ['review', reviewId],
    queryFn: () => getReview(reviewId!),
    enabled: !!reviewId,
  });

  const onSuccessAction = () => {
    queryClient.invalidateQueries({ queryKey: ['review', reviewId] });
    queryClient.invalidateQueries({ queryKey: ['reviews'] });
    navigate('/human-review');
  };

  const approveMutation = useMutation({
    mutationFn: () => approveReview(reviewId!, reason),
    onSuccess: onSuccessAction,
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectReview(reviewId!, reason),
    onSuccess: onSuccessAction,
  });

  const investigateMutation = useMutation({
    mutationFn: () => requestMoreInvestigation(reviewId!, reason),
    onSuccess: onSuccessAction,
  });

  const handleAction = (action: 'approve' | 'reject' | 'investigate') => {
    if (!reason.trim()) {
      setErrorMsg('Decision reason is required.');
      return;
    }
    setErrorMsg('');
    if (action === 'approve') approveMutation.mutate();
    if (action === 'reject') rejectMutation.mutate();
    if (action === 'investigate') investigateMutation.mutate();
  };

  if (isLoading) return <div className="p-8 text-text-secondary">Loading review details...</div>;
  if (!review) return <div className="p-8 text-critical">Review not found</div>;

  const isPending = !['APPROVED', 'REJECTED'].includes(review.status);

  return (
    <div className="w-full flex flex-col p-page-padding">
      <div className="mb-6 flex items-center gap-4">
        <button onClick={() => navigate('/human-review')} className="text-text-secondary hover:text-primary transition-colors">
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
        </button>
        <div>
          <h2 className="font-page-title text-page-title text-text-primary">Review: {reviewId}</h2>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-gutter items-start">
        {/* Case Details */}
        <div className="xl:col-span-8 flex flex-col gap-gutter">
          <div className="bg-surface border border-border-base rounded-xl p-6 shadow-sm shadow-black/5">
            <div className="flex justify-between items-start border-b border-border-base pb-4 mb-6">
              <div>
                <h3 className="font-section-title text-section-title text-text-primary flex items-center gap-2 mb-2">
                  <span>Case: <Link to={`/investigation/${review.case_id}`} className="text-action-blue-dark hover:underline font-data-tabular">{review.case_id}</Link></span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-label-sm text-label-sm ${
                    review.status === 'PENDING' || review.status === 'ESCALATED' ? 'bg-warning/10 text-warning border-warning/20 border' :
                    review.status === 'APPROVED' ? 'bg-success/10 text-success border-success/20 border' :
                    'bg-error-container text-on-error-container border border-error-container'
                  }`}>
                    {review.status}
                  </span>
                </h3>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-surface border border-border-base rounded p-4">
                <span className="font-label-sm text-text-secondary uppercase mb-1 block">Risk Level</span>
                <span className={`font-semibold ${review.risk_level === 'CRITICAL' || review.risk_level === 'HIGH' ? 'text-critical' : 'text-warning'}`}>
                  {review.risk_level || '-'}
                </span>
              </div>
              <div className="bg-surface border border-border-base rounded p-4">
                <span className="font-label-sm text-text-secondary uppercase mb-1 block">Confidence</span>
                <span className="font-data-tabular font-bold text-primary">
                  {review.confidence != null ? `${Math.round(review.confidence * 100)}%` : '-'}
                </span>
              </div>
            </div>

            <div className="mb-6">
              <span className="font-label-sm text-label-sm text-text-secondary uppercase tracking-wider block mb-2">Investigation Summary</span>
              <div className="bg-surface-secondary p-4 rounded-lg border border-border-base flex items-start gap-3">
                <span className="material-symbols-outlined text-info mt-0.5">smart_toy</span>
                <p className="font-body-table text-text-primary leading-relaxed">
                  {review.review_reason || "No detailed summary provided."}
                </p>
              </div>
            </div>

            <div className="mb-6">
              <span className="font-label-sm text-label-sm text-text-secondary uppercase tracking-wider block mb-2">Recommended Action</span>
              <div className="bg-surface-bright p-4 rounded-lg border border-border-base">
                <p className="font-body-table-bold text-primary">
                  {review.recommended_action || "None"}
                </p>
              </div>
            </div>
            
            {review.decision_reason && (
              <div className="mb-6">
                <span className="font-label-sm text-label-sm text-text-secondary uppercase tracking-wider block mb-2">Reviewer Decision ({review.decision})</span>
                <div className="bg-surface-secondary p-4 rounded-lg border border-border-base flex items-start gap-3">
                  <span className="material-symbols-outlined text-text-secondary mt-0.5">person</span>
                  <p className="font-body-table text-text-primary leading-relaxed">
                    {review.decision_reason}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Decision Panel */}
        {isPending && (
          <div className="xl:col-span-4 bg-surface border border-border-base rounded-xl p-6 shadow-sm shadow-black/5 sticky top-6">
            <h4 className="font-section-title text-section-title text-text-primary mb-4">Do you approve the AI recommendation?</h4>
            
            <div className="flex flex-col gap-4">
              <div className="flex gap-3">
                <button 
                  onClick={() => handleAction('approve')}
                  disabled={approveMutation.isPending}
                  className="flex-1 bg-action-blue-dark text-on-primary py-2.5 px-4 rounded-lg font-body-table-bold text-body-table-bold hover:bg-secondary transition-colors text-center shadow-sm disabled:opacity-50"
                >
                  Approve
                </button>
                <button 
                  onClick={() => handleAction('reject')}
                  disabled={rejectMutation.isPending}
                  className="flex-1 bg-surface text-text-primary border border-border-base py-2.5 px-4 rounded-lg font-body-table-bold text-body-table-bold hover:bg-surface-container-low transition-colors text-center shadow-sm disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
              
              <button 
                onClick={() => handleAction('investigate')}
                disabled={investigateMutation.isPending}
                className="w-full bg-surface text-text-primary border border-border-base py-2.5 px-4 rounded-lg font-body-table-bold text-body-table-bold hover:bg-surface-container-low transition-colors text-center shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">search</span>
                Request More Investigation
              </button>

              <div className="mt-2">
                <label className="font-label-sm text-label-sm text-text-primary block mb-1" htmlFor="decision-reason">Decision Reason <span className="text-critical">*</span></label>
                <textarea 
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full bg-surface border border-border-base rounded-lg p-3 font-body-table text-body-table text-text-primary focus:border-action-blue-dark focus:ring-1 focus:ring-action-blue-dark outline-none transition-all" 
                  id="decision-reason" 
                  placeholder="Enter justification for audit logs..." 
                  rows={3}
                ></textarea>
                {errorMsg && <p className="text-critical text-xs mt-1">{errorMsg}</p>}
                <p className="font-caption text-caption text-text-secondary mt-1 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">info</span>
                  Decision reason is required for all actions.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}