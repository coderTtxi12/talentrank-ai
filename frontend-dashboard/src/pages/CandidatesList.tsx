/**
 * Listado de candidatos con filtros y paginación.
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
    dispatch(fetchCandidates(undefined));
  }, [dispatch, filters.country_code, filters.status, filters.requires_review, filters.page]);

  const handlePageChange = (newPage: number) => {
    dispatch(setFilters({ page: newPage }));
    dispatch(fetchCandidates({ page: newPage }));
  };

  const pages = Array.from({ length: pagination.total_pages }, (_, i) => i + 1);

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

      {pagination.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={pagination.page <= 1}
            onClick={() => handlePageChange(pagination.page - 1)}
          >
            ← Previous
          </Button>

          <div className="flex items-center gap-1">
            {pages.map((page) => {
              const showPage =
                page === 1 ||
                page === pagination.total_pages ||
                Math.abs(page - pagination.page) <= 1;

              const showEllipsis =
                page === 2 && pagination.page > 3 ||
                page === pagination.total_pages - 1 && pagination.page < pagination.total_pages - 2;

              if (!showPage && !showEllipsis) return null;

              if (showEllipsis && !showPage) {
                return (
                  <span key={page} className="px-2 text-gray-400">
                    ...
                  </span>
                );
              }

              return (
                <Button
                  key={page}
                  variant={page === pagination.page ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => handlePageChange(page)}
                >
                  {page}
                </Button>
              );
            })}
          </div>

          <Button
            variant="ghost"
            size="sm"
            disabled={pagination.page >= pagination.total_pages}
            onClick={() => handlePageChange(pagination.page + 1)}
          >
            Next →
          </Button>
        </div>
      )}
    </div>
  );
};

export default CandidatesList;
