/** Ranking tournament row from GET /api/v1/ranking/tournaments */

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

export interface RankingTournamentsPage {
  items: RankingTournamentRow[];
  total: number;
  offset: number;
  limit: number;
}
