/**
 * Torneos listwise agrupados por corrida (ranking run).
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, Button } from '@/components/ui';
import { fetchRankingTournamentsByRunPage } from '@/services/rankingApi';
import type { RankingRunGroup, RankingTournamentRow } from '@/types/ranking';
import {
  TOURNAMENTS_TITLE,
  TOURNAMENTS_SUBTITLE,
  TOURNAMENTS_COL_CREATED,
  TOURNAMENTS_COL_TOURNAMENT,
  TOURNAMENTS_COL_K,
  TOURNAMENTS_COL_MODEL,
  TOURNAMENTS_COL_ORDER,
  TOURNAMENTS_COL_TRACE,
  TOURNAMENTS_EMPTY,
  TOURNAMENTS_ERROR,
  TOURNAMENTS_PREV,
  TOURNAMENTS_NEXT,
  TOURNAMENTS_PAGINATION_RUNS,
  TOURNAMENTS_RUN_META,
  TOURNAMENTS_PL_TITLE,
  TOURNAMENTS_PL_EMPTY,
  TOURNAMENTS_PL_COL_RANK,
  TOURNAMENTS_PL_COL_CANDIDATE,
  TOURNAMENTS_PL_COL_UTILITY,
  TOURNAMENTS_PL_COL_SEEN,
} from '@/constants/branding';

const RUN_PAGE_SIZE = 10;

const subagentRationaleOnly = (trace: Record<string, unknown>): string => {
  const r = trace.subagent_rationale;
  if (typeof r === 'string' && r.trim()) return r.trim();
  return '—';
};

function TournamentRows({ rows }: { rows: RankingTournamentRow[] }) {
  if (rows.length === 0) {
    return (
      <tr>
        <td colSpan={6} className="py-6 px-3 text-center text-gray-500 text-sm">
          Sin mini-torneos en esta corrida.
        </td>
      </tr>
    );
  }
  return (
    <>
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
    </>
  );
}

function PlackettSection({ group }: { group: RankingRunGroup }) {
  const rows = group.plackett_results ?? [];

  return (
    <div className="border-t border-gray-200 bg-slate-50/90">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">{TOURNAMENTS_PL_TITLE}</h3>
        {rows.length === 0 ? (
          <p className="text-xs text-gray-600 mt-1">{TOURNAMENTS_PL_EMPTY}</p>
        ) : null}
      </div>
      {rows.length === 0 ? null : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase">
                <th className="py-2.5 px-3 w-10">{TOURNAMENTS_PL_COL_RANK}</th>
                <th className="py-2.5 px-3">{TOURNAMENTS_PL_COL_CANDIDATE}</th>
                <th className="py-2.5 px-3 text-right whitespace-nowrap">
                  {TOURNAMENTS_PL_COL_UTILITY}
                </th>
                <th className="py-2.5 px-3 text-right whitespace-nowrap">{TOURNAMENTS_PL_COL_SEEN}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.candidate_id}
                  className="border-b border-gray-100/90 hover:bg-white align-middle"
                >
                  <td className="py-2 px-3 tabular-nums text-gray-700">{r.rank_position}</td>
                  <td className="py-2 px-3">
                    <Link
                      to={`/candidates/${r.candidate_id}`}
                      className="text-primary-700 hover:underline font-medium text-gray-900"
                    >
                      {r.candidate_name}
                    </Link>
                  </td>
                  <td className="py-2 px-3 text-right tabular-nums text-gray-800">
                    {r.utility.toLocaleString('es-ES', {
                      minimumFractionDigits: 4,
                      maximumFractionDigits: 4,
                    })}
                  </td>
                  <td className="py-2 px-3 text-right tabular-nums text-gray-700">
                    {r.tournaments_seen}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RunSection({ group }: { group: RankingRunGroup }) {
  const shortRun = group.run_id.slice(0, 8);
  const started = new Date(group.started_at).toLocaleString('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
          <h2 className="text-base font-semibold text-gray-900">
            Corrida <span className="font-mono text-primary-700">{shortRun}…</span>
            <span className="font-normal text-gray-600 text-sm font-sans ml-2">· {started}</span>
          </h2>
          <span className="text-xs text-gray-500 font-mono" title={group.run_id}>
            {group.run_id}
          </span>
        </div>
        <p className="text-xs text-gray-600 mt-1.5">
          {TOURNAMENTS_RUN_META(
            group.rubric_version,
            group.pool_size,
            group.status,
            group.tournaments.length
          )}
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase">
              <th className="py-3 px-3 whitespace-nowrap">{TOURNAMENTS_COL_CREATED}</th>
              <th className="py-3 px-3 whitespace-nowrap">{TOURNAMENTS_COL_TOURNAMENT}</th>
              <th className="py-3 px-3 text-right">{TOURNAMENTS_COL_K}</th>
              <th className="py-3 px-3">{TOURNAMENTS_COL_MODEL}</th>
              <th className="py-3 px-3 min-w-[200px]">{TOURNAMENTS_COL_ORDER}</th>
              <th className="py-3 px-3 min-w-[200px]">{TOURNAMENTS_COL_TRACE}</th>
            </tr>
          </thead>
          <tbody>
            <TournamentRows rows={group.tournaments} />
          </tbody>
        </table>
      </div>
      <PlackettSection group={group} />
    </Card>
  );
}

const TournamentsPage = () => {
  const [groups, setGroups] = useState<RankingRunGroup[]>([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (off: number) => {
    setLoading(true);
    setError(null);
    try {
      const page = await fetchRankingTournamentsByRunPage(off, RUN_PAGE_SIZE);
      setGroups(page.groups);
      setTotalRuns(page.total_runs);
      setOffset(page.offset);
    } catch {
      setError(TOURNAMENTS_ERROR);
      setGroups([]);
      setTotalRuns(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(0);
  }, [load]);

  const canPrev = offset > 0;
  const canNext = offset + groups.length < totalRuns;

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
        {totalRuns > 0 ? (
          <p className="text-sm text-gray-500">
            {TOURNAMENTS_PAGINATION_RUNS(
              offset + (groups.length ? 1 : 0),
              offset + groups.length,
              totalRuns
            )}
          </p>
        ) : null}
      </div>

      {loading ? (
        <Card>
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
          </div>
        </Card>
      ) : groups.length === 0 ? (
        <Card>
          <p className="text-gray-500 text-center py-8">{TOURNAMENTS_EMPTY}</p>
        </Card>
      ) : (
        <>
          <div className="space-y-6">
            {groups.map((g) => (
              <RunSection key={g.run_id} group={g} />
            ))}
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={!canPrev || loading}
              onClick={() => void load(Math.max(0, offset - RUN_PAGE_SIZE))}
            >
              {TOURNAMENTS_PREV}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={!canNext || loading}
              onClick={() => void load(offset + RUN_PAGE_SIZE)}
            >
              {TOURNAMENTS_NEXT}
            </Button>
          </div>
        </>
      )}
    </div>
  );
};

export default TournamentsPage;
