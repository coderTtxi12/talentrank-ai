/** Ranking API types — listwise tournaments grouped by run. */

export interface RankingTournamentRow {
  id: string;
  run_id: string;
  vacancy_id: string | null;
  rubric_version: string | null;
  candidate_ids: string[];
  llm_ranking: string[];
  llm_ranking_names: string[];
  confidence: number;
  model: string;
  is_active_learning: boolean;
  llm_trace: Record<string, unknown>;
  created_at: string;
}

/** Plackett–Luce fit snippet from orchestrator JSON (when present). */
export interface RankingPlackettFitSummary {
  converged?: boolean | null;
  n_rankings_used?: number | null;
  note?: string | null;
}

/** One row from ``ranking_results`` for this run. */
export interface RankingPlackettResultRow {
  candidate_id: string;
  candidate_name: string;
  rank_position: number;
  utility: number;
  posterior_variance: number;
  tournaments_seen: number;
}

/** One ranking run + its tournaments (GET /ranking/tournaments/by-run). */
export interface RankingRunGroup {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  rubric_version: string;
  vacancy_id: string | null;
  pool_size: number;
  status: string;
  tournaments: RankingTournamentRow[];
  /** Present when API exposes PL rows (older servers may omit). */
  plackett_results?: RankingPlackettResultRow[];
  plackett_fit_summary?: RankingPlackettFitSummary | null;
}

export interface RankingTournamentsByRunPage {
  groups: RankingRunGroup[];
  total_runs: number;
  offset: number;
  limit: number;
}

/** @deprecated Flat page; prefer ``RankingTournamentsByRunPage``. */
export interface RankingTournamentsPage {
  items: RankingTournamentRow[];
  total: number;
  offset: number;
  limit: number;
}
