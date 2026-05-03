import api from '@/services/api';
import type { RankingTournamentsPage } from '@/types/ranking';

export async function fetchRankingTournamentsPage(
  offset: number,
  limit: number
): Promise<RankingTournamentsPage> {
  const { data } = await api.get<RankingTournamentsPage>('/ranking/tournaments', {
    params: { offset, limit },
  });
  return data;
}
