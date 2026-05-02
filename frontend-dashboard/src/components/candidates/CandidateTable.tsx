/**
 * Tabla de candidatos.
 */
import { Link } from 'react-router-dom';
import {
  SCREENING_AVAILABILITY_LABELS,
  SCREENING_PREFERRED_SCHEDULE_LABELS,
  type Candidate,
  type CountryCode,
  type ScreeningAvailability,
  type ScreeningPreferredSchedule,
} from '@/types/candidate';
import {
  TABLE_EMPTY,
  TABLE_EMPTY_HINT,
  TABLE_COL_COUNTRY,
  TABLE_COL_NAME,
  TABLE_COL_DRIVERS_LICENSE,
  TABLE_COL_CITY_ZONE,
  TABLE_COL_AVAILABILITY,
  TABLE_COL_PREFERRED_SCHEDULE,
  TABLE_COL_EXPERIENCE_YEARS,
  TABLE_COL_PLATFORMS,
  TABLE_COL_START_DATE,
  TABLE_COL_STATUS,
  TABLE_COL_DATE,
  TABLE_TITLE_REVIEW,
} from '@/constants/branding';
import { StatusBadge } from '@/components/candidates';
import clsx from 'clsx';

interface CandidateTableProps {
  candidates: Candidate[];
  loading?: boolean;
}

const countries: Record<CountryCode, { name: string; flag: string }> = {
  ES: { name: 'España', flag: '🇪🇸' },
  MX: { name: 'México', flag: '🇲🇽' },
};

function formatAvailability(value: string | null | undefined): string {
  if (value == null || value === '') return '—';
  return SCREENING_AVAILABILITY_LABELS[value as ScreeningAvailability] ?? value;
}

function formatPreferredSchedule(value: string | null | undefined): string {
  if (value == null || value === '') return '—';
  return SCREENING_PREFERRED_SCHEDULE_LABELS[value as ScreeningPreferredSchedule] ?? value;
}

function formatExperienceYears(n: number | null | undefined): string {
  if (n == null) return '—';
  return n === 1 ? '1 año' : `${n} años`;
}

function formatStartDate(iso: string | null | undefined): string {
  if (iso == null || iso === '') return '—';
  const d = new Date(iso.includes('T') ? iso : `${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

const CandidateTable = ({ candidates, loading = false }: CandidateTableProps) => {
  const formatDriversLicense = (value: boolean | null | undefined) => {
    if (value === true) return 'Sí';
    if (value === false) return 'No';
    return '—';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3">📋</div>
        <p className="text-gray-500">{TABLE_EMPTY}</p>
        <p className="text-sm text-gray-400 mt-1">{TABLE_EMPTY_HINT}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              ID
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_COUNTRY}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_NAME}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_DRIVERS_LICENSE}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_CITY_ZONE}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_AVAILABILITY}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_PREFERRED_SCHEDULE}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_EXPERIENCE_YEARS}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_PLATFORMS}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_START_DATE}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_STATUS}
            </th>
            <th className="text-left py-3 px-3 text-xs font-medium text-gray-500 uppercase whitespace-nowrap">
              {TABLE_COL_DATE}
            </th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((row) => (
            <tr
              key={row.id}
              className={clsx(
                'border-b border-gray-100 hover:bg-gray-50 transition-colors',
                row.requires_review && 'bg-yellow-50 hover:bg-yellow-100'
              )}
            >
              <td className="py-3 px-3 align-top whitespace-nowrap">
                <Link
                  to={`/candidates/${row.id}`}
                  className="text-primary-600 hover:underline font-mono text-sm"
                >
                  {row.id.slice(0, 8)}...
                </Link>
                {row.requires_review && (
                  <span className="ml-2 text-yellow-600" title={TABLE_TITLE_REVIEW}>
                    ⚠️
                  </span>
                )}
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{countries[row.country_code]?.flag}</span>
                  <span className="text-gray-500">{row.country_code}</span>
                </div>
              </td>
              <td className="py-3 px-3 align-top min-w-[8rem]">
                <p className="font-medium text-gray-900">{row.full_name}</p>
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap text-gray-900">
                {formatDriversLicense(row.drivers_license)}
              </td>
              <td className="py-3 px-3 align-top min-w-[7rem] max-w-[10rem] text-gray-900">
                <span className="line-clamp-2">{row.city_zone?.trim() || '—'}</span>
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap text-gray-900">
                {formatAvailability(row.availability)}
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap text-gray-900">
                {formatPreferredSchedule(row.preferred_schedule)}
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap text-gray-900">
                {formatExperienceYears(row.experience_years)}
              </td>
              <td className="py-3 px-3 align-top min-w-[6rem] max-w-[12rem] text-gray-900">
                <span className="line-clamp-2 break-words">
                  {row.platforms?.length ? row.platforms.join(', ') : '—'}
                </span>
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap text-gray-900">
                {formatStartDate(row.start_date)}
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap">
                <StatusBadge status={row.status} size="sm" />
              </td>
              <td className="py-3 px-3 align-top whitespace-nowrap text-gray-500">
                {formatDate(row.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default CandidateTable;
