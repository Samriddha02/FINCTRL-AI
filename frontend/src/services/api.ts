import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
});

// Reconciliation
export const getReconciliationCases = async () => (await api.get('/reconciliation')).data;
export const getReconciliationCase = async (id: string) => (await api.get(`/reconciliation/${id}`)).data;

// Investigations
export const getInvestigation = async (id: string) => (await api.get(`/investigations/${id}`)).data;
export const startInvestigation = async (id: string) => (await api.post(`/investigations/${id}`)).data;

// Reviews
export const getReviews = async () => (await api.get('/reviews')).data;
export const getReview = async (id: string) => (await api.get(`/reviews/${id}`)).data;
export const createReview = async (caseId: string) => (await api.post(`/reviews/${caseId}`)).data;
export const approveReview = async (id: string, reason: string) => (await api.post(`/reviews/${id}/approve`, { reviewer_id: 'DEMO-USER', reason })).data;
export const rejectReview = async (id: string, reason: string) => (await api.post(`/reviews/${id}/reject`, { reviewer_id: 'DEMO-USER', reason })).data;
export const requestMoreInvestigation = async (id: string, reason: string) => (await api.post(`/reviews/${id}/request-more-investigation`, { reviewer_id: 'DEMO-USER', reason })).data;

// Finance QA
export const askQuestion = async (question: string) => (await api.post('/finance/qa', { question })).data;
export const getQuestion = async (query_id: string) => (await api.get(`/finance/qa/${query_id}`)).data;

// Forecast
export const getCashForecast = async () => (await api.get('/forecast/cash')).data;
export const getForecastById = async (id: string) => (await api.get(`/forecast/cash/${id}`)).data;

// Tax Matching
export const getTaxMatches = async () => (await api.get('/tax-matching')).data;
export const getTaxMatch = async (invoice_id: string) => (await api.get(`/tax-matching/${invoice_id}`)).data;
export const getTaxMatchResult = async (match_id: string) => (await api.get(`/tax-matching/results/${match_id}`)).data;

// Audit
export const getAuditEvents = async () => (await api.get('/audit')).data;
export const getAuditEvent = async (case_id: string) => (await api.get(`/audit/${case_id}`)).data;
