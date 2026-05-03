/**
 * Panel principal: estadísticas y candidatos recientes.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchStatistics,
  fetchMoreDashboardRecent,
  bootstrapDashboardRecent,
} from '@/store/slices/candidatesSlice';
import { Card, Button, Modal } from '@/components/ui';
import { StatusBadge } from '@/components/candidates';
import { CandidateStatusTooltip } from '@/components/candidates/CandidateStatusTooltip';
import {
  CANDIDATE_STATUS_ORDER,
  CANDIDATE_STATUS_LABELS,
  CANDIDATE_STATUS_CHART_COLORS,
  type CandidateStatus,
  type CountryCode,
} from '@/types/candidate';
import {
  DASH_TITLE,
  DASH_SUBTITLE,
  DASH_BTN_NEW,
  DASH_BTN_SIMULATION,
  DASH_SIM_MODAL_TITLE,
  DASH_SIM_MODAL_BODY,
  DASH_SIM_MODAL_CANCEL,
  DASH_SIM_MODAL_CONFIRM,
  DASH_SIM_SUBMITTING,
  DASH_SIM_SUCCESS,
  DASH_SIM_ERROR_GENERIC,
  DASH_RANK_MODAL_TITLE,
  DASH_RANK_MODAL_BODY,
  DASH_RANK_MODAL_CANCEL,
  DASH_RANK_MODAL_CONFIRM,
  DASH_RANK_SUBMITTING,
  DASH_RANK_SUCCESS,
  DASH_RANK_ERROR_GENERIC,
  DASH_STAT_TOTAL,
  DASH_STAT_RISK,
  DASH_CHART_STATUS,
  DASH_CHART_COUNTRY,
  DASH_RECENT_TITLE,
  DASH_RECENT_SUBTITLE,
  DASH_EMPTY,
  DASH_VIEW_ALL,
  DASH_RECENT_LOAD_MORE,
  TABLE_COL_COUNTRY,
  TABLE_COL_NAME,
  TABLE_COL_DRIVERS_LICENSE,
  TABLE_COL_STATUS,
} from '@/constants/branding';
import { createListwiseJob } from '@/services/jobsApi';
import { seedScreeningSimulation } from '@/services/simulationApi';

// Country info
const countries: Record<CountryCode, { name: string; flag: string }> = {
  ES: { name: 'España', flag: '🇪🇸' },
  MX: { name: 'México', flag: '🇲🇽' },
};

const statuses: { status: CandidateStatus; label: string; color: string }[] =
  CANDIDATE_STATUS_ORDER.map((status) => ({
    status,
    label: CANDIDATE_STATUS_LABELS[status],
    color: CANDIDATE_STATUS_CHART_COLORS[status],
  }));

const Dashboard = () => {
  const dispatch = useAppDispatch();
  const {
    dashboardRecent,
    statistics,
    statisticsLoading,
    recentHydrated,
    recentNextCursor,
  } = useAppSelector((state) => state.candidates);

  const [simModalOpen, setSimModalOpen] = useState(false);
  const [simSubmitting, setSimSubmitting] = useState(false);
  const [rankModalOpen, setRankModalOpen] = useState(false);
  const [rankSubmitting, setRankSubmitting] = useState(false);
  const [rankBanner, setRankBanner] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  useEffect(() => {
    dispatch(fetchStatistics(undefined));
    dispatch(bootstrapDashboardRecent(undefined));
  }, [dispatch]);

  const formatDriversLicense = (value: boolean | null | undefined) => {
    if (value === true) return 'Sí';
    if (value === false) return 'No';
    return '—';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{DASH_TITLE}</h1>
          <p className="text-gray-600">{DASH_SUBTITLE}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {rankBanner ? (
            <p
              className={`text-sm max-w-md text-right ${rankBanner.type === 'success' ? 'text-green-700' : 'text-red-600'}`}
              role="status"
            >
              {rankBanner.text}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={rankSubmitting || simSubmitting}
              onClick={() => {
                setRankBanner(null);
                setSimModalOpen(true);
              }}
            >
              {DASH_BTN_SIMULATION}
            </Button>
            <button
              type="button"
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-60"
              disabled={rankSubmitting || simSubmitting}
              onClick={() => {
                setRankBanner(null);
                setRankModalOpen(true);
              }}
            >
              {DASH_BTN_NEW}
            </button>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div
        className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4 transition-opacity ${statisticsLoading ? 'opacity-70' : ''}`}
      >
        {/* Total candidatos */}
        <Card className="bg-gradient-to-br from-primary-500 to-primary-600 text-white border-0">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-primary-100 text-sm">{DASH_STAT_TOTAL}</p>
              <p className="text-3xl font-bold mt-1">
                {statistics
                  ? statistics.total_loans ?? statistics.total_count ?? 0
                  : 0}
              </p>
            </div>
            <div className="text-4xl opacity-80">📊</div>
          </div>
        </Card>

        {/* Avg Risk Score */}
        <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white border-0">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">{DASH_STAT_RISK}</p>
              <p className="text-3xl font-bold mt-1">
                {statistics?.average_risk_score != null
                  ? statistics.average_risk_score.toFixed(0)
                  : 'N/A'}
              </p>
            </div>
            <div className="text-4xl opacity-80">📈</div>
          </div>
        </Card>
      </div>

      {/* Status and Country Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Status */}
        <Card title={DASH_CHART_STATUS}>
          <div className="space-y-3">
            {statuses.map(({ status, label, color }) => {
              const count = statistics?.by_status?.[status] ?? 0;
              const total =
                statistics?.total_loans ?? statistics?.total_count ?? 0;
              const percentage = total
                ? Math.round((count / total) * 100)
                : 0;
              return (
                <div key={status} className="flex items-center gap-3">
                  <div className={`w-3 h-3 shrink-0 rounded-full ${color}`} />
                  <CandidateStatusTooltip status={status} className="min-w-0 flex-1">
                    <span className="block cursor-default text-sm text-gray-700">
                      {label}
                    </span>
                  </CandidateStatusTooltip>
                  <span className="text-sm font-medium text-gray-900">{count}</span>
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${color}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-10 text-right">
                    {percentage}%
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* By Country */}
        <Card title={DASH_CHART_COUNTRY}>
          <div className="space-y-3">
            {Object.entries(countries).map(([code, { name, flag }]) => {
              const count = statistics?.by_country?.[code as CountryCode] ?? 0;
              const total =
                statistics?.total_loans ?? statistics?.total_count ?? 0;
              const percentage = total
                ? Math.round((count / total) * 100)
                : 0;
              return (
                <div key={code} className="flex items-center gap-3">
                  <span className="text-xl">{flag}</span>
                  <span className="flex-1 text-sm text-gray-700">{name}</span>
                  <span className="text-sm font-medium text-gray-900">{count}</span>
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-primary-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-10 text-right">
                    {percentage}%
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Candidatos recientes */}
      <Card
        title={DASH_RECENT_TITLE}
        subtitle={
          recentHydrated
            ? `${DASH_RECENT_SUBTITLE} · ${dashboardRecent.length} en esta vista${recentNextCursor ? ' · puedes cargar más' : ''}`
            : DASH_RECENT_SUBTITLE
        }
      >
        {!recentHydrated ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : dashboardRecent.length === 0 ? (
          <p className="text-gray-500 text-center py-8">{DASH_EMPTY}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                    ID
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                    {TABLE_COL_COUNTRY}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                    {TABLE_COL_NAME}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                    {TABLE_COL_DRIVERS_LICENSE}
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                    {TABLE_COL_STATUS}
                  </th>
                </tr>
              </thead>
              <tbody>
                {dashboardRecent.map((candidateRow) => (
                  <tr
                    key={candidateRow.id}
                    className="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="py-3 px-4">
                      <Link
                        to={`/candidates/${candidateRow.id}`}
                        className="text-primary-600 hover:underline font-mono text-sm"
                      >
                        {candidateRow.id.slice(0, 8)}...
                      </Link>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-lg">
                        {countries[candidateRow.country_code]?.flag}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-900">
                      {candidateRow.full_name}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-900">
                      {formatDriversLicense(candidateRow.drivers_license)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={candidateRow.status} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {recentHydrated && recentNextCursor ? (
          <div className="mt-4 flex justify-center border-t border-gray-100 pt-4">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => void dispatch(fetchMoreDashboardRecent())}
            >
              {DASH_RECENT_LOAD_MORE}
            </Button>
          </div>
        ) : null}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <Link
            to="/candidates"
            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            {DASH_VIEW_ALL}
          </Link>
        </div>
      </Card>
      <Modal
        isOpen={simModalOpen}
        onClose={() => !simSubmitting && setSimModalOpen(false)}
        title={DASH_SIM_MODAL_TITLE}
        size="md"
      >
        <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{DASH_SIM_MODAL_BODY}</p>
        <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={simSubmitting}
            onClick={() => setSimModalOpen(false)}
          >
            {DASH_SIM_MODAL_CANCEL}
          </Button>
          <Button
            type="button"
            disabled={simSubmitting}
            onClick={() => {
              void (async () => {
                setSimSubmitting(true);
                setRankBanner(null);
                try {
                  const res = await seedScreeningSimulation();
                  setSimModalOpen(false);
                  setRankBanner({
                    type: 'success',
                    text: DASH_SIM_SUCCESS(res.batch_id, res.inserted_candidates),
                  });
                  dispatch(fetchStatistics(undefined));
                  dispatch(bootstrapDashboardRecent(undefined));
                } catch {
                  setSimModalOpen(false);
                  setRankBanner({ type: 'error', text: DASH_SIM_ERROR_GENERIC });
                } finally {
                  setSimSubmitting(false);
                }
              })();
            }}
          >
            {simSubmitting ? DASH_SIM_SUBMITTING : DASH_SIM_MODAL_CONFIRM}
          </Button>
        </div>
      </Modal>
      <Modal
        isOpen={rankModalOpen}
        onClose={() => !rankSubmitting && setRankModalOpen(false)}
        title={DASH_RANK_MODAL_TITLE}
        size="md"
      >
        <p className="text-sm text-gray-600 leading-relaxed">{DASH_RANK_MODAL_BODY}</p>
        <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={rankSubmitting}
            onClick={() => setRankModalOpen(false)}
          >
            {DASH_RANK_MODAL_CANCEL}
          </Button>
          <Button
            type="button"
            disabled={rankSubmitting}
            onClick={() => {
              void (async () => {
                setRankSubmitting(true);
                setRankBanner(null);
                try {
                  const res = await createListwiseJob({});
                  setRankModalOpen(false);
                  setRankBanner({
                    type: 'success',
                    text: DASH_RANK_SUCCESS(res.job_id),
                  });
                } catch {
                  setRankModalOpen(false);
                  setRankBanner({ type: 'error', text: DASH_RANK_ERROR_GENERIC });
                } finally {
                  setRankSubmitting(false);
                }
              })();
            }}
          >
            {rankSubmitting ? DASH_RANK_SUBMITTING : DASH_RANK_MODAL_CONFIRM}
          </Button>
        </div>
      </Modal>
    </div>
  );
};

export default Dashboard;
