/**
 * Listado de torneos listwise (ranking_tournaments).
 */
import { useCallback, useEffect, useState } from 'react';
import { Card, Button } from '@/components/ui';
import { fetchRankingTournamentsPage } from '@/services/rankingApi';
import type { RankingTournamentRow } from '@/types/ranking';
import {
  TOURNAMENTS_TITLE,
  TOURNAMENTS_SUBTITLE,
  TOURNAMENTS_COL_CREATED,
  TOURNAMENTS_COL_RUN,
  TOURNAMENTS_COL_TOURNAMENT,
  TOURNAMENTS_COL_K,
  TOURNAMENTS_COL_MODEL,
  TOURNAMENTS_COL_ORDER,
  TOURNAMENTS_COL_TRACE,
  TOURNAMENTS_EMPTY,
  TOURNAMENTS_ERROR,
  TOURNAMENTS_PREV,
  TOURNAMENTS_NEXT,
  TOURNAMENTS_PAGINATION,
} from '@/constants/branding';

const PAGE_SIZE = 20;

const subagentRationaleOnly = (trace: Record<string, unknown>): string => {
  const r = trace.subagent_rationale;
  if (typeof r === 'string' && r.trim()) return r.trim();
  return '—';
};

const TournamentsPage = () => {
  const [rows, setRows] = useState<RankingTournamentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (off: number) => {
    setLoading(true);
    setError(null);
    try {
      const page = await fetchRankingTournamentsPage(off, PAGE_SIZE);
      setRows(page.items);
      setTotal(page.total);
      setOffset(page.offset);
    } catch {
      setError(TOURNAMENTS_ERROR);
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(0);
  }, [load]);

  const canPrev = offset > 0;
  const canNext = offset + rows.length < total;

  if (error && !loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">{TOURNAMENTS_TITLE}</h1>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{TOURNAMENTS_TITLE}</h1>
          <p className="text-gray-600">{TOURNAMENTS_SUBTITLE}</p>
        </div>
        {total > 0 ? (
          <p className="text-sm text-gray-500">
            {TOURNAMENTS_PAGINATION(
              offset + (rows.length ? 1 : 0),
              offset + rows.length,
              total
            )}
          </p>
        ) : null}
      </div>

      <Card>
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
          </div>
        ) : rows.length === 0 ? (
          <p className="text-gray-500 text-center py-8">{TOURNAMENTS_EMPTY}</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase">
                    <th className="py-3 px-3 whitespace-nowrap">{TOURNAMENTS_COL_CREATED}</th>
                    <th className="py-3 px-3 whitespace-nowrap">{TOURNAMENTS_COL_RUN}</th>
                    <th className="py-3 px-3 whitespace-nowrap">{TOURNAMENTS_COL_TOURNAMENT}</th>
                    <th className="py-3 px-3 text-right">{TOURNAMENTS_COL_K}</th>
                    <th className="py-3 px-3">{TOURNAMENTS_COL_MODEL}</th>
                    <th className="py-3 px-3 min-w-[200px]">{TOURNAMENTS_COL_ORDER}</th>
                    <th className="py-3 px-3 min-w-[200px]">{TOURNAMENTS_COL_TRACE}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const trace = (r.llm_trace || {}) as Record<string, unknown>;
                    const rationaleText = subagentRationaleOnly(trace);
                    const orderNames =
                      r.llm_ranking_names?.length === r.llm_ranking.length
                        ? r.llm_ranking_names
                        : r.llm_ranking;
                    const orderTitle =
                      orderNames.length > 0
                        ? orderNames.map((n, i) => `${i + 1}. ${n}`).join('\n')
                        : undefined;
                    return (
                      <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50 align-top">
                        <td className="py-3 px-3 whitespace-nowrap text-gray-700">
                          {new Date(r.created_at).toLocaleString('es-ES', {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })}
                        </td>
                        <td className="py-3 px-3 font-mono text-xs text-primary-700">
                          {r.run_id.slice(0, 8)}…
                        </td>
                        <td className="py-3 px-3 font-mono text-xs">{r.id.slice(0, 8)}…</td>
                        <td className="py-3 px-3 text-right tabular-nums">{r.candidate_ids.length}</td>
                        <td
                          className="py-3 px-3 text-gray-800 max-w-[140px] truncate"
                          title={r.model}
                        >
                          {r.model}
                        </td>
                        <td
                          className="py-3 px-3 text-xs text-gray-800 max-w-[280px] align-top"
                          title={orderTitle}
                        >
                          {orderNames.length === 0 ? (
                            '—'
                          ) : (
                            <ol className="m-0 list-decimal space-y-0.5 pl-4 marker:text-gray-500">
                              {orderNames.map((name, idx) => (
                                <li key={`${r.id}-ord-${idx}`} className="break-words pl-0.5">
                                  {name}
                                </li>
                              ))}
                            </ol>
                          )}
                        </td>
                        <td
                          className="py-3 px-3 text-gray-700 text-xs max-w-md whitespace-pre-wrap break-words"
                          title={rationaleText === '—' ? undefined : rationaleText}
                        >
                          {rationaleText}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-center gap-3 pt-4 border-t border-gray-100">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!canPrev || loading}
                onClick={() => void load(Math.max(0, offset - PAGE_SIZE))}
              >
                {TOURNAMENTS_PREV}
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={!canNext || loading}
                onClick={() => void load(offset + PAGE_SIZE)}
              >
                {TOURNAMENTS_NEXT}
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

export default TournamentsPage;
