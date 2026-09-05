import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { getReviews } from '../services/api';

export default function HumanReview() {
  const navigate = useNavigate();
  const { data: reviews, isLoading, refetch } = useQuery({
    queryKey: ['reviews'],
    queryFn: getReviews,
  });

  const allReviews = reviews || [];
  const pendingCount = allReviews.filter((r: any) => r.status === 'PENDING' || r.status === 'ESCALATED').length;
  const completedToday = allReviews.filter((r: any) => r.status === 'APPROVED' || r.status === 'REJECTED').length;

  return (
    <div className="w-full flex flex-col">
      {/* Page Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="font-page-title text-page-title text-text-primary mb-1">Human Review</h2>
          <p className="font-body-table text-body-table text-text-secondary">Review AI-assisted financial decisions before resolution.</p>
        </div>
        <button 
          onClick={() => refetch()}
          className="bg-action-blue-dark text-on-primary px-4 py-2 rounded font-body-table-bold text-body-table-bold hover:bg-secondary transition-colors flex items-center gap-2 shadow-sm"
        >
          <span className="material-symbols-outlined text-[18px]">refresh</span>
          Refresh Queue
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-gutter mb-8">
        <div className="bg-surface border border-border-base rounded-xl p-4 flex flex-col justify-between h-24 shadow-sm">
          <span className="font-label-sm text-label-sm text-text-secondary uppercase tracking-wider">Pending Review</span>
          <span className="font-kpi-primary text-kpi-primary font-data-tabular">{pendingCount}</span>
        </div>
        <div className="bg-surface border border-border-base rounded-xl p-4 flex flex-col justify-between h-24 shadow-sm">
          <span className="font-label-sm text-label-sm text-text-secondary uppercase tracking-wider">Completed Today</span>
          <span className="font-kpi-primary text-kpi-primary font-data-tabular">{completedToday}</span>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="bg-surface border border-border-base rounded-xl overflow-hidden shadow-sm shadow-black/5">
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 text-text-secondary text-center">Loading review queue...</div>
          ) : allReviews.length === 0 ? (
            <div className="p-8 text-text-secondary text-center">No reviews pending.</div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-secondary border-b border-border-base">
                  <th className="py-3 px-4 font-label-sm text-label-sm text-text-secondary uppercase tracking-wider whitespace-nowrap">Review ID</th>
                  <th className="py-3 px-4 font-label-sm text-label-sm text-text-secondary uppercase tracking-wider whitespace-nowrap">Case ID</th>
                  <th className="py-3 px-4 font-label-sm text-label-sm text-text-secondary uppercase tracking-wider whitespace-nowrap">Status</th>
                  <th className="py-3 px-4 font-label-sm text-label-sm text-text-secondary uppercase tracking-wider whitespace-nowrap text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-base">
                {allReviews.map((review: any) => {
                  const isPending = review.status === 'PENDING' || review.status === 'ESCALATED';
                  return (
                    <tr key={review.review_id} className="hover:bg-surface-container-low transition-colors group">
                      <td className="py-3 px-4 whitespace-nowrap font-data-tabular text-text-primary">
                        {review.review_id}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <Link to={`/investigation/${review.case_id}`} className="font-data-tabular text-action-blue-dark font-semibold hover:underline">
                          {review.case_id}
                        </Link>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-label-sm text-label-sm ${
                          isPending ? 'bg-warning/10 text-warning border-warning/20 border' :
                          review.status === 'APPROVED' ? 'bg-success/10 text-success border-success/20 border' :
                          'bg-error-container text-on-error-container border border-error-container'
                        }`}>
                          {review.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <button 
                          onClick={() => navigate(`/human-review/${review.review_id}`)}
                          className="bg-surface border border-action-blue-dark text-action-blue-dark px-3 py-1 rounded font-body-table-bold text-body-table-bold text-sm hover:bg-action-blue-light transition-colors"
                        >
                          {isPending ? 'Review' : 'View'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
