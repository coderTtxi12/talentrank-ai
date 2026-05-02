/**
 * Listado de candidatos con filtros y paginación por cursor.
 */
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchCandidates, setFilters } from '@/store/slices/candidatesSlice';
import { Card, Button } from '@/components/ui';
import { CandidateTable, CandidateFilters, RealTimeIndicator } from '@/components/candidates';
import {
  LIST_TITLE,
  LIST_SUBTITLE,
  LIST_BTN_NEW,
  LIST_SHOWING,
  LIST_FILTERS_ACTIVE,
} from '@/constants/branding';

const CandidatesList = () => {
  const dispatch = useAppDispatch();
  const { items, loading, pagination, filters } = useAppSelector((state) => state.candidates);

  useEffect(() => {
    dispatch(setFilters({ page_size: 20, cursor: null, page: 1 }));
  }, [dispatch]);

  useEffect(() => {
    dispatch(fetchCandidates(undefined));
  }, [dispatch, filters.country_code, filters.status, filters.requires_review, filters.page_size]);

  const goFirstPage = () => {
    dispatch(setFilters({ cursor: null, page: 1 }));
    dispatch(fetchCandidates({ cursor: null, page: 1 }));
  };

  const goNextPage = () => {
    if (!pagination.next_cursor) return;
    dispatch(
      setFilters({ cursor: pagination.next_cursor, page: filters.page + 1 })
    );
    dispatch(fetchCandidates({ cursor: pagination.next_cursor, page: filters.page + 1 }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{LIST_TITLE}</h1>
          <p className="text-gray-600">{LIST_SUBTITLE}</p>
        </div>
        <div className="flex items-center gap-4">
          <RealTimeIndicator />
          <Link
            to="/candidates/new"
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            {LIST_BTN_NEW}
          </Link>
        </div>
      </div>

      <CandidateFilters />

      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>
          {LIST_SHOWING(items.length, pagination.total)}
        </span>
        {(filters.country_code || filters.status || filters.requires_review !== null) && (
          <span className="text-primary-600">{LIST_FILTERS_ACTIVE}</span>
        )}
      </div>

      <Card padding="none">
        <CandidateTable candidates={items} loading={loading} />
      </Card>

      {(pagination.next_cursor || filters.cursor) && (
        <div className="flex flex-wrap items-center justify-center gap-3 text-sm text-gray-600">
          <span>
            Página {pagination.page}
            {pagination.total > 0 && (
              <span className="text-gray-400"> · {pagination.total} candidatos (filtro actual)</span>
            )}
          </span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={!filters.cursor}
              onClick={goFirstPage}
            >
              Inicio
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={!pagination.next_cursor}
              onClick={goNextPage}
            >
              Siguiente →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CandidatesList;
