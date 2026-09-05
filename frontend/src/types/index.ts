
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
