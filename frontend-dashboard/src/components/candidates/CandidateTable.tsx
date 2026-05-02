/**
 * Tabla de candidatos.
 */
import { Link } from 'react-router-dom';
import type { Candidate, CountryCode } from '@/types/candidate';
import {
  TABLE_EMPTY,
  TABLE_EMPTY_HINT,
  TABLE_COL_COUNTRY,
  TABLE_COL_NAME,
  TABLE_COL_DOC,
  TABLE_COL_AMOUNT,
  TABLE_COL_STATUS,
  TABLE_COL_RISK,
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

const CandidateTable = ({ candidates, loading = false }: CandidateTableProps) => {
  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
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
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
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
              {TABLE_COL_DOC}
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
              {TABLE_COL_AMOUNT}
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
              {TABLE_COL_STATUS}
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
              {TABLE_COL_RISK}
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
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
              <td className="py-3 px-4">
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
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{countries[row.country_code]?.flag}</span>
                  <span className="text-sm text-gray-500">{row.country_code}</span>
                </div>
              </td>
              <td className="py-3 px-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">{row.full_name}</p>
                </div>
              </td>
              <td className="py-3 px-4">
                <div>
                  <span className="text-xs text-gray-500">{row.document_type}</span>
                  <p className="text-sm font-mono text-gray-900">{row.document_number}</p>
                </div>
              </td>
              <td className="py-3 px-4">
                <p className="text-sm font-medium text-gray-900">
                  {formatCurrency(row.amount_requested, row.currency)}
                </p>
                <p className="text-xs text-gray-500">{row.currency}</p>
              </td>
              <td className="py-3 px-4">
                <StatusBadge status={row.status} size="sm" />
              </td>
              <td className="py-3 px-4">
                {row.risk_score !== null ? (
                  <span
                    className={clsx(
                      'text-sm font-medium',
                      row.risk_score <= 300 && 'text-green-600',
                      row.risk_score > 300 && row.risk_score < 700 && 'text-yellow-600',
                      row.risk_score >= 700 && 'text-red-600'
                    )}
                  >
                    {row.risk_score}
                  </span>
                ) : (
                  <span className="text-sm text-gray-400">—</span>
                )}
              </td>
              <td className="py-3 px-4 text-sm text-gray-500">
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
