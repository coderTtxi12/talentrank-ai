/**
 * Filtros de listado de candidatos.
 */
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setFilters, clearFilters, fetchCandidates } from '@/store/slices/candidatesSlice';
import { Button } from '@/components/ui';
import type { CountryCode, CandidateStatus } from '@/types/candidate';
import { CANDIDATE_STATUS_ORDER, CANDIDATE_STATUS_LABELS } from '@/types/candidate';
import {
  FILTERS_LABEL_COUNTRY,
  FILTERS_ALL_COUNTRIES,
  FILTERS_LABEL_STATUS,
  FILTERS_ALL_STATUSES,
  FILTERS_CLEAR,
} from '@/constants/branding';

const countries: { code: CountryCode; name: string; flag: string }[] = [
  { code: 'ES', name: 'España', flag: '🇪🇸' },
  { code: 'MX', name: 'México', flag: '🇲🇽' },
];

const statuses: { value: CandidateStatus; label: string }[] =
  CANDIDATE_STATUS_ORDER.map((value) => ({
    value,
    label: CANDIDATE_STATUS_LABELS[value],
  }));

const CandidateFilters = () => {
  const dispatch = useAppDispatch();
  const { filters } = useAppSelector((state) => state.candidates);

  const handleCountryChange = (value: string) => {
    const countryCode = value === '' ? null : (value as CountryCode);
    dispatch(setFilters({ country_code: countryCode, page: 1 }));
    dispatch(fetchCandidates({ country_code: countryCode, page: 1 }));
  };

  const handleStatusChange = (value: string) => {
    const status = value === '' ? null : (value as CandidateStatus);
    dispatch(setFilters({ status, page: 1 }));
    dispatch(fetchCandidates({ status, page: 1 }));
  };

  const handleClearFilters = () => {
    dispatch(clearFilters());
    dispatch(fetchCandidates({ page: 1 }));
  };

  const hasActiveFilters =
    filters.country_code !== null ||
    filters.status !== null ||
    filters.requires_review !== null;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Country filter */}
        <div className="flex-1 min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
            {FILTERS_LABEL_COUNTRY}
          </label>
          <select
            value={filters.country_code || ''}
            onChange={(e) => handleCountryChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">{FILTERS_ALL_COUNTRIES}</option>
            {countries.map((country) => (
              <option key={country.code} value={country.code}>
                {country.flag} {country.name}
              </option>
            ))}
          </select>
        </div>

        {/* Status filter */}
        <div className="flex-1 min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
            {FILTERS_LABEL_STATUS}
          </label>
          <select
            value={filters.status || ''}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">{FILTERS_ALL_STATUSES}</option>
            {statuses.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </div>

        {/* Review filter */}
        {/* <div className="flex-1 min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
            Review Status
          </label>
          <select
            value={filters.requires_review === null ? '' : String(filters.requires_review)}
            onChange={(e) => handleReviewChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="">All</option>
            <option value="true">Requires Review</option>
            <option value="false">No Review Needed</option>
          </select>
        </div> */}

        {/* Clear filters button */}
        {hasActiveFilters && (
          <div className="flex items-end">
            <Button variant="ghost" size="sm" onClick={handleClearFilters}>
              {FILTERS_CLEAR}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CandidateFilters;
