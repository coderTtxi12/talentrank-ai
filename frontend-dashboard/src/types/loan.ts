/**
 * Loan types.
 */

/** Aligned with backend `CandidateStatus` (see `backend/app/models/database.py`). */
export type CandidateStatus =
  | 'new'
  | 'in_progress'
  | 'hard_filter'
  | 'sentiment_analysis'
  | 'listwise'
  | 'plackett_luce'
  | 'qualified'
  | 'qualified_flagged'
  | 'soft_disq'
  | 'hard_disq'
  | 'waitlist'
  | 'abandoned';

/** Legacy name — mismo tipo que estados de candidato. */
export type LoanStatus = CandidateStatus;

export const CANDIDATE_STATUS_ORDER: CandidateStatus[] = [
  'new',
  'in_progress',
  'hard_filter',
  'sentiment_analysis',
  'listwise',
  'plackett_luce',
  'qualified',
  'qualified_flagged',
  'soft_disq',
  'hard_disq',
  'waitlist',
  'abandoned',
];

export const CANDIDATE_STATUS_LABELS: Record<CandidateStatus, string> = {
  new: 'Nuevo',
  in_progress: 'En progreso (screening IA)',
  hard_filter: 'Filtro duro (requisitos)',
  sentiment_analysis: 'Análisis de sentimiento',
  listwise: 'Ranking listwise',
  plackett_luce: 'Plackett–Luce',
  qualified: 'Calificado',
  qualified_flagged: 'Calificado (marcado)',
  soft_disq: 'Descalificación suave',
  hard_disq: 'Descalificación dura',
  waitlist: 'Lista de espera',
  abandoned: 'Abandonado',
};

/** Color de barra / punto en gráficos del dashboard */
export const CANDIDATE_STATUS_CHART_COLORS: Record<CandidateStatus, string> = {
  new: 'bg-yellow-500',
  in_progress: 'bg-blue-400',
  hard_filter: 'bg-indigo-500',
  sentiment_analysis: 'bg-pink-500',
  listwise: 'bg-teal-500',
  plackett_luce: 'bg-amber-500',
  qualified: 'bg-green-500',
  qualified_flagged: 'bg-purple-500',
  soft_disq: 'bg-orange-500',
  hard_disq: 'bg-red-500',
  waitlist: 'bg-cyan-500',
  abandoned: 'bg-gray-400',
};

export type CountryCode = 'ES' | 'MX';

export type DocumentType = 'DNI' | 'CURP' | 'CC' | 'CPF';

export interface BankingInfo {
  provider_name?: string;
  provider?: string; // backward compatibility
  credit_score?: number | null;
  loan_score?: number | null; // backward compatibility
  total_debt?: number | string | null;
  active_loans?: number;
  payment_history?: string | null;
  payment_history_score?: number | null;
  has_defaults?: boolean;
  default_count?: number;
  income_verified?: boolean;
  employment_verified?: boolean;
  available_credit?: number | string | null;
  account_age_months?: number | null;
  monthly_obligations?: number | string | null;
  [key: string]: any; // Allow additional fields
}

export interface Loan {
  id: string;
  country_code: CountryCode;
  document_type: DocumentType;
  document_number: string;
  full_name: string;
  amount_requested: number;
  currency: string;
  monthly_income: number;
  status: LoanStatus;
  risk_score: number | null;
  requires_review: boolean;
  banking_info: BankingInfo | null;
  extra_data?: {
    risk_factors?: Record<string, any>;
    validation_warnings?: string[];
    [key: string]: any;
  };
  metadata?: Record<string, any>; // backward compatibility
  created_at: string;
  updated_at: string;
  processed_at?: string | null;
  created_by_id?: string | null;
  reviewed_by_id?: string | null;
}

export interface LoanCreateRequest {
  country_code: CountryCode;
  document_type: DocumentType;
  document_number: string;
  full_name: string;
  amount_requested: number;
  monthly_income: number;
}

export interface LoanStatusUpdate {
  status: LoanStatus;
  reason?: string;
}

export interface LoanStatusHistory {
  id: number;
  loan_id: string;
  previous_status: LoanStatus | null;
  new_status: LoanStatus;
  reason: string | null;
  changed_by_id: string | null;
  created_at: string;
}

export interface LoanFilters {
  country_code: CountryCode | null;
  status: LoanStatus | null;
  requires_review: boolean | null;
  page: number;
  page_size: number;
}

export interface LoanPagination {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LoanStatistics {
  total_loans: number;
  total_count?: number; // backward compatibility with older API shape
  by_status: Record<LoanStatus, number>;
  by_country: Record<CountryCode, number>;
  total_amount_requested: number;
  average_amount?: number; // currently not used in UI
  average_risk_score: number | null;
  pending_review_count: number;
}

export interface LoansState {
  items: Loan[];
  selectedLoan: Loan | null;
  statistics: LoanStatistics | null;
  loading: boolean;
  error: string | null;
  filters: LoanFilters;
  pagination: LoanPagination;
}
