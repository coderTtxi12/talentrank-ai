import api from '@/services/api';

export interface CreateListwiseJobResponse {
  job_id: string;
  status: string;
  listen_channel: string;
}

/** POST /jobs/listwise — encola pipeline listwise (worker por NOTIFY). */
export async function createListwiseJob(
  body: { vacancy_id?: string } = {}
): Promise<CreateListwiseJobResponse> {
  const { data } = await api.post<CreateListwiseJobResponse>(
    '/jobs/listwise',
    body
  );
  return data;
}
