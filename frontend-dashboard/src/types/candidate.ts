/**
 * Tipos del funnel de candidatos (screening). Las rutas HTTP siguen usando `/loans` en la API.
 */

/** Alineado con backend `CandidateStatus` (ver `backend/app/models/database.py`). */
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

/** Texto largo para tooltips / ayuda contextual. */
export const CANDIDATE_STATUS_DESCRIPTIONS: Record<CandidateStatus, string> = {
  new:
    'Registro creado en el funnel; el candidato ha iniciado la conversación de screening con la IA.',
  in_progress:
    'Screening conversacional activo: el agente captura requisitos y datos del repartidor.',
  hard_filter:
    'Se evalúan requisitos obligatorios (licencia, ciudad de cobertura, etc.).',
  sentiment_analysis:
    'Se analiza la transcripción del chat (tono, frustración u otras señales) antes de seguir el pipeline.',
  listwise:
    'Mini torneos: el modelo realiza mini torneos de 5 candidatos para obtener un ranking parcial.',
  plackett_luce:
    'Fusiona rankings parciales, estimando utilidades estadísticas latentes que maximizan la posibilidad de obtener un ranking global con mejor accuracy.',
  qualified:
    'Supera los filtros del funnel y puede pasar a reclutamiento / siguiente paso operativo.',
  qualified_flagged:
    'Calificado pero con incertidumbre o riesgo (por ejemplo horario dudoso o señales de frustración).',
  soft_disq:
    'No encaja en este momento por motivos reversibles (horario, fecha de inicio, perfil); puede reevaluarse.',
  hard_disq:
    'No cumple requisitos duros no negociables (por ejemplo sin carnet o fuera de zona de cobertura).',
  waitlist:
    'Fuera de cobertura o timing actual; queda en espera para cuando haya vacantes u oportunidad.',
  abandoned:
    'El candidato dejó de responder tras la secuencia de reenganche; proceso detenido.',
};

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

/** Valores API (`availability_enum`). */
export type ScreeningAvailability = 'full_time' | 'part_time' | 'weekends';

/** Valores API (`preferred_schedule_enum`). */
export type ScreeningPreferredSchedule = 'morning' | 'afternoon' | 'evening' | 'flexible';

export const SCREENING_AVAILABILITY_LABELS: Record<ScreeningAvailability, string> = {
  full_time: 'Tiempo completo',
  part_time: 'Tiempo parcial',
  weekends: 'Fines de semana',
};

export const SCREENING_PREFERRED_SCHEDULE_LABELS: Record<ScreeningPreferredSchedule, string> = {
  morning: 'Mañana',
  afternoon: 'Tarde',
  evening: 'Noche',
  flexible: 'Flexible',
};

export interface BankingInfo {
  provider_name?: string;
  provider?: string;
  credit_score?: number | null;
  loan_score?: number | null;
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
  [key: string]: unknown;
}

export interface Candidate {
  id: string;
  country_code: CountryCode;
  document_type: DocumentType;
  document_number: string;
  full_name: string;
  /** Carnet de conducir capturado en screening (`drivers_license` en DB). */
  drivers_license: boolean | null;
  city_zone: string | null;
  availability: ScreeningAvailability | string | null;
  preferred_schedule: ScreeningPreferredSchedule | string | null;
  experience_years: number | null;
  platforms: string[] | null;
  /** ISO date (`YYYY-MM-DD`). */
  start_date: string | null;
  amount_requested: number;
  currency: string;
  monthly_income: number;
  status: CandidateStatus;
  risk_score: number | null;
  requires_review: boolean;
  banking_info: BankingInfo | null;
  /** `sentiment_results.sentiment` (último por fecha); solo en GET detalle. */
  sentiment?: string | null;
  /** `sentiment_results.confidence`, habitualmente 0–1. */
  sentiment_confidence?: number | null;
  /** `sentiment_results.signals` (último por fecha); solo en GET detalle. */
  sentiment_signals?: Record<string, unknown> | null;
  extra_data?: {
    risk_factors?: Record<string, unknown>;
    validation_warnings?: string[];
    [key: string]: unknown;
  };
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  processed_at?: string | null;
  created_by_id?: string | null;
  reviewed_by_id?: string | null;
}

export interface CandidateCreateRequest {
  country_code: CountryCode;
  document_type: DocumentType;
  document_number: string;
  full_name: string;
  amount_requested: number;
  monthly_income: number;
}

export interface CandidateStatusUpdate {
  status: CandidateStatus;
  reason?: string;
}

/** Respuesta de GET .../history — `loan_id` es el nombre del campo en la API. */
export interface CandidateStatusHistory {
  id: number;
  loan_id: string;
  previous_status: CandidateStatus | null;
  new_status: CandidateStatus;
  reason: string | null;
  changed_by_id: string | null;
  created_at: string;
}

export interface CandidateFilters {
  country_code: CountryCode | null;
  status: CandidateStatus | null;
  requires_review: boolean | null;
  /** Paginación por cursor (API); null = primera página. */
  cursor: string | null;
  page_size: number;
  /** Número de página solo para la UI (1-based). */
  page: number;
}

/** Mensaje del screening (usuario / asistente). */
export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

/** GET /candidates/:id/conversation/messages */
export interface ConversationMessagesResponse {
  items: ConversationMessage[];
  next_cursor: string | null;
  limit: number;
}

/** Respuesta GET /api/v1/candidates (cursor). */
export interface CandidatesCursorResponse {
  items: Candidate[];
  next_cursor: string | null;
  limit: number;
  total: number | null;
}

export interface CandidatePagination {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  next_cursor: string | null;
}

/** Estadísticas — nombres de campos según respuesta de la API (`total_loans`, etc.). */
export interface CandidateStatistics {
  total_loans: number;
  total_count?: number;
  by_status: Record<CandidateStatus, number>;
  by_country: Record<CountryCode, number>;
  total_amount_requested: number;
  average_amount?: number;
  average_risk_score: number | null;
  pending_review_count: number;
}

export interface CandidatesState {
  items: Candidate[];
  /** Vista previa reciente en la home (`GET /candidates` con paginación por cursor). */
  dashboardRecent: Candidate[];
  selectedCandidate: Candidate | null;
  statistics: CandidateStatistics | null;
  statisticsLoading: boolean;
  loading: boolean;
  error: string | null;
  filters: CandidateFilters;
  pagination: CandidatePagination;
  /** Siguiente cursor para «cargar más» recientes sobre la lista principal. */
  recentNextCursor: string | null;
  /** Ya se cargó la primera ventana HTTP de recientes (vacía válida). */
  recentHydrated: boolean;
  recentPageSize: number;
}
