import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCashForecast } from '../services/api';

export default function CashForecast() {
  const { data: forecastData, isLoading, isError, refetch } = useQuery({
    queryKey: ['cashForecast'],
    queryFn: getCashForecast,
  });

  const daily = forecastData?.daily_forecasts || [];

  return (
    <div className="w-full flex flex-col p-page-padding">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2 className="font-page-title text-page-title text-primary tracking-tight mb-1">Cash Forecast</h2>
          <p className="font-body-table text-text-secondary">AI-driven liquidity projections based on historical patterns.</p>
        </div>
        <button onClick={() => refetch()} className="bg-surface border border-border-base text-primary px-4 py-2 rounded text-sm hover:bg-surface-secondary transition-colors">
          Refresh Forecast
        </button>
      </div>

      {isLoading ? (
        <div className="bg-surface border border-border-base rounded-lg p-12 text-center text-text-secondary shadow-sm">
          <span className="material-symbols-outlined text-4xl animate-spin mb-2">sync</span>
          <p>Generating cash forecast model...</p>
        </div>
      ) : isError ? (
        <div className="bg-surface border border-border-base rounded-lg p-12 text-center text-critical shadow-sm flex flex-col items-center">
          <span className="material-symbols-outlined text-4xl mb-2">error</span>
          <p>Failed to load forecast data. <button onClick={() => refetch()} className="underline hover:text-primary">Retry</button></p>
        </div>
      ) : !forecastData ? (
        <div className="bg-surface border border-border-base rounded-lg p-12 text-center text-text-secondary shadow-sm">
          <p>No forecast data available for the selected period.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Metrics Dashboard */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
              <h3 className="font-section-title text-lg mb-4 text-text-secondary border-b border-border-base pb-2">Historical (Past 30 Days)</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <span className="font-label-sm text-text-muted uppercase">Inflow</span>
                  <div className="font-data-tabular font-bold text-success text-lg mt-1">₹{forecastData.historical.inflow.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
                </div>
                <div>
                  <span className="font-label-sm text-text-muted uppercase">Outflow</span>
                  <div className="font-data-tabular font-bold text-critical text-lg mt-1">₹{forecastData.historical.outflow.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
                </div>
                <div>
                  <span className="font-label-sm text-text-muted uppercase">Net Cash</span>
                  <div className="font-data-tabular font-bold text-primary text-lg mt-1">₹{forecastData.historical.net.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
                </div>
              </div>
            </div>

            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
              <h3 className="font-section-title text-lg mb-4 text-text-secondary border-b border-border-base pb-2">Projected (Next 7 Days)</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <span className="font-label-sm text-text-muted uppercase">Inflow</span>
                  <div className="font-data-tabular font-bold text-success text-lg mt-1">₹{forecastData.forecast.inflow.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
                </div>
                <div>
                  <span className="font-label-sm text-text-muted uppercase">Outflow</span>
                  <div className="font-data-tabular font-bold text-critical text-lg mt-1">₹{forecastData.forecast.outflow.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
                </div>
                <div>
                  <span className="font-label-sm text-text-muted uppercase">Net Cash</span>
                  <div className="font-data-tabular font-bold text-primary text-lg mt-1">₹{forecastData.forecast.net.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm flex flex-col items-center justify-center">
              <span className="font-label-sm text-text-secondary uppercase mb-2">Confidence Level</span>
              <div className="text-3xl font-data-tabular font-bold text-action-blue-dark">
                {Math.round(forecastData.confidence * 100)}%
              </div>
            </div>
            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
              <span className="font-label-sm text-text-secondary uppercase mb-2 block">Uncertainty</span>
              <div className="font-body-table text-sm">
                <p><span className="text-text-muted">Margin of Error:</span> <span className="font-data-tabular">±₹{forecastData.uncertainty.margin_of_error.toLocaleString('en-IN', {maximumFractionDigits:0})}</span></p>
                <p><span className="text-text-muted">Standard Dev:</span> <span className="font-data-tabular">₹{forecastData.uncertainty.std_dev.toLocaleString('en-IN', {maximumFractionDigits:0})}</span></p>
              </div>
            </div>
            <div className="bg-surface border border-border-base rounded-lg p-6 shadow-sm">
              <span className="font-label-sm text-text-secondary uppercase mb-2 block">Data Quality</span>
              <div className="font-body-table text-sm">
                <p><span className="text-text-muted">Score:</span> <span className="font-data-tabular">{Math.round(forecastData.data_quality.score * 100)}/100</span></p>
                <p><span className="text-text-muted">Issues:</span> {forecastData.data_quality.unresolved_reconciliation_count} unresolved cases</p>
              </div>
            </div>
          </div>

          {forecastData.risk_factors && forecastData.risk_factors.length > 0 && (
            <div className="bg-warning/10 border border-warning/20 rounded-lg p-4">
              <h4 className="font-label-sm text-warning uppercase mb-2 flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">warning</span> Risk Factors
              </h4>
              <ul className="list-disc pl-5 text-sm text-warning font-body-table">
                {forecastData.risk_factors.map((risk: string, i: number) => (
                  <li key={i}>{risk}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="bg-surface border border-border-base rounded-lg shadow-sm overflow-hidden mt-2">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse font-body-table">
                <thead>
                  <tr className="bg-surface-bright border-b border-border-base">
                    <th className="py-3 px-4 font-label-sm text-text-secondary uppercase whitespace-nowrap">Date</th>
                    <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-right whitespace-nowrap">Expected Inflow</th>
                    <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-right whitespace-nowrap">Expected Outflow</th>
                    <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-right whitespace-nowrap">Net Cash</th>
                    <th className="py-3 px-4 font-label-sm text-text-secondary uppercase text-center whitespace-nowrap">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-base">
                  {daily.map((f: any, idx: number) => (
                    <tr key={idx} className="hover:bg-surface-secondary/50 transition-colors">
                      <td className="py-4 px-4 font-data-tabular whitespace-nowrap">{f.date}</td>
                      <td className="py-4 px-4 text-right font-data-tabular text-success whitespace-nowrap">
                        +₹{Number(f.expected_inflow).toLocaleString('en-IN', {maximumFractionDigits:0})}
                      </td>
                      <td className="py-4 px-4 text-right font-data-tabular text-critical whitespace-nowrap">
                        -₹{Number(f.expected_outflow).toLocaleString('en-IN', {maximumFractionDigits:0})}
                      </td>
                      <td className="py-4 px-4 text-right font-data-tabular font-bold text-primary whitespace-nowrap">
                        ₹{Number(f.expected_net).toLocaleString('en-IN', {maximumFractionDigits:0})}
                      </td>
                      <td className="py-4 px-4 text-center whitespace-nowrap">
                        <span className={`inline-flex px-2.5 py-1 rounded text-xs font-semibold ${
                          f.confidence > 0.8 ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                        }`}>
                          {Math.round(f.confidence * 100)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                  {daily.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-text-secondary">
                        No daily forecast data available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
