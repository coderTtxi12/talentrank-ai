import api from '@/services/api';
import type { ScreeningSimulationSeedResponse } from '@/types/simulation';

/** POST /simulation/seed-screening-cohort — inserts synthetic candidates + chats (+ optional sentiment). */
export async function seedScreeningSimulation(
  count = 10
): Promise<ScreeningSimulationSeedResponse> {
  const { data } = await api.post<ScreeningSimulationSeedResponse>(
    '/simulation/seed-screening-cohort',
    {},
    { params: { count }, timeout: 120_000 }
  );
  return data;
}
