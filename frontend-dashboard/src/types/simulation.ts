export interface ScreeningSimulationSeedResponse {
  batch_id: string;
  inserted_candidates: number;
  candidate_ids: string[];
  breakdown: Record<string, unknown>;
}
