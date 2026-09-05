import os

types_content = """
export interface DashboardMetrics {
  total_payments: number;
  reconciliation_cases: number;
  investigation_queue: number;
  human_review: number;
  cash_forecast: number;
  tax_mismatches: number;
}

export interface Case {
  case_id: string;
  status: string;
  confidence: number;
  risk_level: string;
  created_at: string;
}

export interface InvestigationResult {
  case_id: string;
  status: string;
  confidence_score: number;
  root_cause: string;
  evidence: any[];
  recommendation: string;
}

// Add other types as needed
"""

api_content = """
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
});

// Reconciliation
export const getReconciliationCases = async () => (await api.get('/reconciliation')).data;
export const getReconciliationCase = async (id: string) => (await api.get(`/reconciliation/${id}`)).data;

// Investigations
export const getInvestigation = async (id: string) => (await api.get(`/investigations/${id}`)).data;
export const startInvestigation = async (id: string) => (await api.post(`/investigations/${id}/investigate`)).data;

// Reviews
export const getReviews = async () => (await api.get('/reviews')).data;
export const getReview = async (id: string) => (await api.get(`/reviews/${id}`)).data;
export const approveReview = async (id: string, reason: string) => (await api.post(`/reviews/${id}/approve`, { reason })).data;
export const rejectReview = async (id: string, reason: string) => (await api.post(`/reviews/${id}/reject`, { reason })).data;
export const requestMoreInvestigation = async (id: string, reason: string) => (await api.post(`/reviews/${id}/request-more-investigation`, { reason })).data;

// Finance QA
export const askQuestion = async (query: string) => (await api.post('/finance/qa', { query })).data;
export const getQuestion = async (id: string) => (await api.get(`/finance/qa/${id}`)).data;

// Forecast
export const getCashForecast = async () => (await api.get('/forecast/cash')).data;
export const getForecastById = async (id: string) => (await api.get(`/forecast/cash/${id}`)).data;

// Tax Matching
export const getTaxMatches = async () => (await api.get('/tax-matching')).data;
export const getTaxMatch = async (id: string) => (await api.get(`/tax-matching/${id}`)).data;
export const getTaxMatchResult = async (id: string) => (await api.get(`/tax-matching/results/${id}`)).data;

// Audit
export const getAuditEvents = async () => (await api.get('/audit')).data;
export const getAuditEvent = async (id: string) => (await api.get(`/audit/${id}`)).data;
"""

os.makedirs("src/types", exist_ok=True)
os.makedirs("src/services", exist_ok=True)

with open("src/types/index.ts", "w") as f:
    f.write(types_content)

with open("src/services/api.ts", "w") as f:
    f.write(api_content)

print("Generated API and Types.")
