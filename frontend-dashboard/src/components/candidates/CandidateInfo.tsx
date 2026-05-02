/**
 * Ficha de detalle de un candidato.
 */
import type { Candidate, CountryCode } from '@/types/candidate';
import {
  INFO_STATUS_LABEL,
  INFO_RISK_LABEL,
  INFO_REVIEW_BANNER,
  INFO_SECTION_APPLICANT,
  INFO_SECTION_AMOUNTS,
} from '@/constants/branding';
import { StatusBadge } from '@/components/candidates';

interface CandidateInfoProps {
  candidate: Candidate;
}

const countries: Record<CountryCode, { name: string; flag: string }> = {
  ES: { name: 'España', flag: '🇪🇸' },
  MX: { name: 'México', flag: '🇲🇽' },
};

const CandidateInfo = ({ candidate }: CandidateInfoProps) => {
  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const InfoRow = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="flex justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{children}</span>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Status Section */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">{INFO_STATUS_LABEL}</p>
            <div className="mt-1">
              <StatusBadge status={candidate.status} size="lg" />
            </div>
          </div>
          {candidate.risk_score !== null && (
            <div className="text-right">
              <p className="text-sm text-gray-500">{INFO_RISK_LABEL}</p>
              <p className="text-2xl font-bold text-gray-900">{candidate.risk_score}</p>
            </div>
          )}
        </div>
        {candidate.requires_review && (
          <div className="mt-3 p-2 bg-yellow-100 rounded text-sm text-yellow-800">
            ⚠️ {INFO_REVIEW_BANNER}
          </div>
        )}
      </div>

      {/* Applicant Information */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
          {INFO_SECTION_APPLICANT}
        </h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <InfoRow label="Full Name">{candidate.full_name}</InfoRow>
          <InfoRow label="Document Type">{candidate.document_type}</InfoRow>
          <InfoRow label="Document Number">
            <span className="font-mono">{candidate.document_number}</span>
          </InfoRow>
        </div>
      </div>

      {/* Importes / país */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
          {INFO_SECTION_AMOUNTS}
        </h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <InfoRow label="Country">
            <span className="flex items-center gap-2">
              <span className="text-lg">{countries[candidate.country_code]?.flag}</span>
              {countries[candidate.country_code]?.name}
            </span>
          </InfoRow>
          <InfoRow label="Amount Requested">
            {formatCurrency(candidate.amount_requested, candidate.currency)}
          </InfoRow>
          <InfoRow label="Currency">{candidate.currency}</InfoRow>
          <InfoRow label="Monthly Income">
            {formatCurrency(candidate.monthly_income, candidate.currency)}
          </InfoRow>
        </div>
      </div>

      {/* Banking Information */}
      {candidate.banking_info && (
        <div>
          <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
            Banking Information
          </h3>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            {(candidate.banking_info.provider_name || candidate.banking_info.provider) && (
              <InfoRow label="Provider">
                {candidate.banking_info.provider_name || candidate.banking_info.provider}
              </InfoRow>
            )}
            {(candidate.banking_info.credit_score !== null && candidate.banking_info.credit_score !== undefined) && (
              <InfoRow label="Credit Score">{candidate.banking_info.credit_score}</InfoRow>
            )}
            {(candidate.banking_info.loan_score !== null && candidate.banking_info.loan_score !== undefined && !candidate.banking_info.credit_score) && (
              <InfoRow label="Credit Score">{candidate.banking_info.loan_score}</InfoRow>
            )}
            {candidate.banking_info.total_debt !== null && candidate.banking_info.total_debt !== undefined && (
              <InfoRow label="Total Debt">
                {formatCurrency(
                  typeof candidate.banking_info.total_debt === 'string' 
                    ? parseFloat(candidate.banking_info.total_debt) 
                    : candidate.banking_info.total_debt,
                  candidate.currency
                )}
              </InfoRow>
            )}
            {candidate.banking_info.monthly_obligations !== null && candidate.banking_info.monthly_obligations !== undefined && (
              <InfoRow label="Monthly Obligations">
                {formatCurrency(
                  typeof candidate.banking_info.monthly_obligations === 'string'
                    ? parseFloat(candidate.banking_info.monthly_obligations)
                    : candidate.banking_info.monthly_obligations,
                  candidate.currency
                )}
              </InfoRow>
            )}
            {candidate.banking_info.available_credit !== null && candidate.banking_info.available_credit !== undefined && (
              <InfoRow label="Available Credit">
                {formatCurrency(
                  typeof candidate.banking_info.available_credit === 'string'
                    ? parseFloat(candidate.banking_info.available_credit)
                    : candidate.banking_info.available_credit,
                  candidate.currency
                )}
              </InfoRow>
            )}
            {candidate.banking_info.account_age_months !== null && candidate.banking_info.account_age_months !== undefined && (
              <InfoRow label="Account Age">
                {candidate.banking_info.account_age_months} months
              </InfoRow>
            )}
            {candidate.banking_info.payment_history_score !== null && candidate.banking_info.payment_history_score !== undefined && (
              <InfoRow label="Payment History Score">
                {candidate.banking_info.payment_history_score}/100
              </InfoRow>
            )}
            {candidate.banking_info.payment_history && (
              <InfoRow label="Payment History">{candidate.banking_info.payment_history}</InfoRow>
            )}
            {candidate.banking_info.has_defaults !== undefined && (
              <InfoRow label="Has Defaults">
                <span className={candidate.banking_info.has_defaults ? 'text-red-600 font-semibold' : 'text-green-600'}>
                  {candidate.banking_info.has_defaults ? 'Yes' : 'No'}
                </span>
              </InfoRow>
            )}
            {candidate.banking_info.default_count !== undefined && candidate.banking_info.default_count > 0 && (
              <InfoRow label="Default Count">
                <span className="text-red-600 font-semibold">{candidate.banking_info.default_count}</span>
              </InfoRow>
            )}
            {candidate.banking_info.income_verified !== undefined && (
              <InfoRow label="Income Verified">
                <span className={candidate.banking_info.income_verified ? 'text-green-600' : 'text-gray-500'}>
                  {candidate.banking_info.income_verified ? '✓ Verified' : '✗ Not Verified'}
                </span>
              </InfoRow>
            )}
            {candidate.banking_info.employment_verified !== undefined && (
              <InfoRow label="Employment Verified">
                <span className={candidate.banking_info.employment_verified ? 'text-green-600' : 'text-gray-500'}>
                  {candidate.banking_info.employment_verified ? '✓ Verified' : '✗ Not Verified'}
                </span>
              </InfoRow>
            )}
            {candidate.banking_info.active_loans !== undefined && (
              <InfoRow label="Active Loans">{candidate.banking_info.active_loans}</InfoRow>
            )}
          </div>
        </div>
      )}

      {/* Risk Factors & Warnings */}
      {candidate.extra_data && (
        <div>
          <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
            Risk Analysis
          </h3>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            {candidate.extra_data.risk_factors && Object.keys(candidate.extra_data.risk_factors).length > 0 && (
              <div className="mb-4">
                <p className="text-sm font-medium text-gray-700 mb-2">Risk Factors:</p>
                <div className="space-y-1">
                  {Object.entries(candidate.extra_data.risk_factors).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-gray-600 capitalize">
                        {key.replace(/_/g, ' ')}:
                      </span>
                      <span className="text-gray-900 font-medium">
                        {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : 
                         typeof value === 'number' && value < 1 ? `${(value * 100).toFixed(1)}%` :
                         String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {candidate.extra_data.validation_warnings && candidate.extra_data.validation_warnings.length > 0 && (
              <div>
                <p className="text-sm font-medium text-yellow-700 mb-2">Validation Warnings:</p>
                <ul className="list-disc list-inside space-y-1">
                  {candidate.extra_data.validation_warnings.map((warning, index) => (
                    <li key={index} className="text-sm text-yellow-600">
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
          Timeline
        </h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <InfoRow label="Created">{formatDate(candidate.created_at)}</InfoRow>
          <InfoRow label="Last Updated">{formatDate(candidate.updated_at)}</InfoRow>
          {candidate.processed_at && (
            <InfoRow label="Processed">{formatDate(candidate.processed_at)}</InfoRow>
          )}
        </div>
      </div>
    </div>
  );
};

export default CandidateInfo;
