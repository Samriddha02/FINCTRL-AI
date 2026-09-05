import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { askQuestion } from '../services/api';

export default function FinanceQA() {
  const [question, setQuestion] = useState('');
  const [answerData, setAnswerData] = useState<any>(null);

  const askMutation = useMutation({
    mutationFn: () => askQuestion(question),
    onSuccess: (data) => {
      setAnswerData(data);
    }
  });

  const handleAsk = () => {
    if (question.trim()) {
      askMutation.mutate();
    }
  };

  const handleSuggest = (q: string) => {
    setQuestion(q);
    askQuestion(q).then(setAnswerData).catch(() => {});
  };

  return (
    <div className="w-full flex flex-col p-page-padding">
      <div className="max-w-4xl mx-auto w-full flex flex-col gap-component-gap">
        {/* Query Header & Input Section */}
        <section className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
          <h2 className="font-section-title text-section-title text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-action-blue-dark">robot_2</span>
            Finance Q&A Assistant
          </h2>
          <div className="flex gap-3 mb-4">
            <div className="relative flex-1">
              <span className="material-symbols-outlined absolute left-3 top-2.5 text-text-muted">search</span>
              <input 
                className="w-full pl-10 pr-4 py-2 border border-border-base rounded-DEFAULT bg-background focus:outline-none focus:border-action-blue-dark focus:ring-1 focus:ring-action-blue-dark font-body-table text-text-primary transition-colors" 
                placeholder="Ask a question about your financial data..." 
                type="text" 
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
              />
            </div>
            <button 
              onClick={handleAsk}
              disabled={askMutation.isPending || !question.trim()}
              className="bg-action-blue-dark hover:bg-secondary text-on-primary font-body-table-bold px-6 py-2 rounded-DEFAULT transition-colors whitespace-nowrap shadow-sm disabled:opacity-50"
            >
              {askMutation.isPending ? 'Analyzing...' : 'Ask'}
            </button>
          </div>
          {askMutation.isError && (
            <div className="text-critical text-sm mb-4">Failed to fetch answer from backend. Ensure valid question.</div>
          )}
          <div className="flex flex-wrap gap-2 items-center">
            <span className="font-label-sm text-text-secondary mr-2">Suggested:</span>
            {['What is the status of PAY-00001?', 'Why is CASE-00001 mismatched?'].map((s) => (
              <button 
                key={s}
                onClick={() => handleSuggest(s)}
                className="px-3 py-1 bg-surface-secondary border border-border-base rounded-full font-label-sm text-text-primary hover:border-action-blue-dark hover:text-action-blue-dark transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </section>

        {/* Main Answer Card */}
        {answerData && (
          <section className="bg-surface border border-border-base rounded-lg shadow-sm overflow-hidden flex flex-col md:flex-row">
            <div className="flex-1 p-6 md:border-r border-border-base">
              <div className="flex items-center gap-2 mb-4 font-label-sm">
                {answerData.status === 'ANSWERED' && <span className="material-symbols-outlined text-[16px] text-success">check_circle</span>}
                {answerData.status === 'NEEDS_CLARIFICATION' && <span className="material-symbols-outlined text-[16px] text-warning">info</span>}
                {answerData.status === 'UNSUPPORTED' && <span className="material-symbols-outlined text-[16px] text-text-muted">block</span>}
                <span className={answerData.status === 'ANSWERED' ? 'text-success' : 'text-warning'}>
                  {answerData.status.replace('_', ' ')}
                </span>
              </div>
              
              <div className="font-body-table text-text-primary leading-relaxed mb-6 whitespace-pre-wrap">
                {answerData.answer}
              </div>
              
              {answerData.facts && answerData.facts.length > 0 && (
                <div className="pt-4 border-t border-border-base">
                  <h3 className="font-label-sm text-text-secondary mb-3 uppercase tracking-wider">Source Facts</h3>
                  <div className="flex flex-wrap gap-3">
                    {answerData.facts.map((fact: any, idx: number) => (
                      <span key={idx} className="flex flex-col gap-1 px-3 py-2 border border-border-base bg-surface-secondary rounded-DEFAULT text-sm">
                        <span className="font-label-xs text-text-secondary">{fact.source} ({fact.key})</span>
                        <span className="font-data-tabular font-bold">{fact.value}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            <div className="w-full md:w-[280px] bg-surface-bright p-6 flex flex-col gap-4">
              <h3 className="font-label-sm text-text-secondary uppercase tracking-wider mb-2">Query Metadata</h3>
              <div className="flex justify-between items-start border-b border-border-base pb-2">
                <span className="font-label-sm text-text-secondary">Query ID</span>
                <span className="font-data-tabular text-text-primary text-right bg-surface-secondary px-2 py-0.5 rounded text-xs">{answerData.query_id || 'Q-TEMP'}</span>
              </div>
              <div className="flex justify-between items-start border-b border-border-base pb-2">
                <span className="font-label-sm text-text-secondary">Type</span>
                <span className="font-data-tabular text-text-primary text-right bg-surface-secondary px-2 py-0.5 rounded text-xs">{answerData.query_type}</span>
              </div>
              {answerData.confidence != null && (
                <div className="mt-auto pt-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-teal-dark text-[18px]">hub</span>
                    <span className="font-label-sm text-primary font-semibold">AI Confidence Level</span>
                  </div>
                  <div className="w-full bg-border-base rounded-full h-1.5 mb-1">
                    <div className="bg-teal-dark h-1.5 rounded-full" style={{width: `${Math.round(answerData.confidence * 100)}%`}}></div>
                  </div>
                  <div className="text-right font-data-tabular text-text-secondary text-xs">{Math.round(answerData.confidence * 100)}%</div>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
