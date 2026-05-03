import api from '@/services/api';
import type { RankingTournamentsByRunPage } from '@/types/ranking';

export async function fetchRankingTournamentsByRunPage(
  offset: number,
  limit: number
): Promise<RankingTournamentsByRunPage> {
  const { data } = await api.get<RankingTournamentsByRunPage>('/ranking/tournaments/by-run', {
    params: { offset, limit },
  });
  return data;
}
