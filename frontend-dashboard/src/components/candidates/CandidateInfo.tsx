/**
 * Ficha de detalle de un candidato.
 */
import {
  SCREENING_AVAILABILITY_LABELS,
  SCREENING_PREFERRED_SCHEDULE_LABELS,
  type Candidate,
  type CountryCode,
  type ScreeningAvailability,
  type ScreeningPreferredSchedule,
} from '@/types/candidate';
import {
  INFO_STATUS_LABEL,
  INFO_RISK_LABEL,
  INFO_REVIEW_BANNER,
  INFO_SECTION_APPLICANT,
  INFO_SECTION_POST_CONVERSATION_SUMMARY,
  INFO_FULL_NAME,
  INFO_SECTION_TIMELINE,
  INFO_SECTION_BANKING,
  INFO_SECTION_RISK,
  TABLE_COL_COUNTRY,
  TABLE_COL_DRIVERS_LICENSE,
  TABLE_COL_CITY_ZONE,
  TABLE_COL_AVAILABILITY,
  TABLE_COL_PREFERRED_SCHEDULE,
  TABLE_COL_EXPERIENCE_YEARS,
  TABLE_COL_PLATFORMS,
  TABLE_COL_START_DATE,
} from '@/constants/branding';
import { StatusBadge } from '@/components/candidates';
import SentimentSignalsSection, {
  shouldShowSentimentAnalysis,
} from '@/components/candidates/SentimentSignalsSection';

const EM_DASH = '—';

function formatAvailability(value: string | null | undefined): string {
  if (value == null || value === '') return EM_DASH;
  return SCREENING_AVAILABILITY_LABELS[value as ScreeningAvailability] ?? value;
}

function formatPreferredSchedule(value: string | null | undefined): string {
  if (value == null || value === '') return EM_DASH;
  return SCREENING_PREFERRED_SCHEDULE_LABELS[value as ScreeningPreferredSchedule] ?? value;
}

function formatExperienceYears(n: number | null | undefined): string {
  if (n == null) return EM_DASH;
  return n === 1 ? '1 año' : `${n} años`;
}

function formatStartDate(iso: string | null | undefined): string {
  if (iso == null || iso === '') return EM_DASH;
  const d = new Date(iso.includes('T') ? iso : `${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function formatDriversLicense(value: boolean | null | undefined): string {
  if (value === true) return 'Sí';
  if (value === false) return 'No';
  return EM_DASH;
}

interface CandidateInfoProps {
  candidate: Candidate;
}

const countries: Record<CountryCode, { name: string; flag: string }> = {
  ES: { name: 'España', flag: '🇪🇸' },
  MX: { name: 'México', flag: '🇲🇽' },
};

const CandidateInfo = ({ candidate }: CandidateInfoProps) => {
  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const InfoRow = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4 py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500 shrink-0">{label}</span>
      <span className="text-sm font-medium text-gray-900 text-left sm:text-right min-w-0 sm:max-w-[65%] break-words">
        {children}
      </span>
    </div>
  );

  const sig = candidate.sentiment_signals;
  const postConversationSummaryRaw =
    sig && typeof sig === 'object'
      ? (sig as Record<string, unknown>).post_conversation_summary
      : undefined;
  const postConversationSummary =
    typeof postConversationSummaryRaw === 'string' ? postConversationSummaryRaw.trim() : '';

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
          <InfoRow label={TABLE_COL_COUNTRY}>
            <span className="inline-flex items-center justify-end gap-2">
              <span className="text-lg">{countries[candidate.country_code]?.flag}</span>
              {countries[candidate.country_code]?.name ?? candidate.country_code}
            </span>
          </InfoRow>
          <InfoRow label={INFO_FULL_NAME}>{candidate.full_name || EM_DASH}</InfoRow>
          <InfoRow label={TABLE_COL_DRIVERS_LICENSE}>
            {formatDriversLicense(candidate.drivers_license)}
          </InfoRow>
          <InfoRow label={TABLE_COL_CITY_ZONE}>
            {candidate.city_zone?.trim() ? candidate.city_zone.trim() : EM_DASH}
          </InfoRow>
          <InfoRow label={TABLE_COL_AVAILABILITY}>
            {formatAvailability(candidate.availability)}
          </InfoRow>
          <InfoRow label={TABLE_COL_PREFERRED_SCHEDULE}>
            {formatPreferredSchedule(candidate.preferred_schedule)}
          </InfoRow>
          <InfoRow label={TABLE_COL_EXPERIENCE_YEARS}>
            {formatExperienceYears(candidate.experience_years)}
          </InfoRow>
          <InfoRow label={TABLE_COL_PLATFORMS}>
            {candidate.platforms?.length ? candidate.platforms.join(', ') : EM_DASH}
          </InfoRow>
          <InfoRow label={TABLE_COL_START_DATE}>{formatStartDate(candidate.start_date)}</InfoRow>
        </div>
      </div>

      {/* Resumen tras screening (sentiment worker, si existe) */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
          {INFO_SECTION_POST_CONVERSATION_SUMMARY}
        </h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-normal text-gray-900 whitespace-pre-wrap break-words leading-relaxed">
            {postConversationSummary || EM_DASH}
          </p>
        </div>
      </div>

      {shouldShowSentimentAnalysis(candidate) && (
        <SentimentSignalsSection
          sentiment={candidate.sentiment}
          sentimentConfidence={candidate.sentiment_confidence}
          signals={candidate.sentiment_signals}
        />
      )}

      {/* Banking Information */}
      {candidate.banking_info && (
        <div>
          <h3 className="text-sm font-semibold text-gray-900 uppercase mb-3">
            {INFO_SECTION_BANKING}
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
            {INFO_SECTION_RISK}
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
          {INFO_SECTION_TIMELINE}
        </h3>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <InfoRow label="Alta">{formatDate(candidate.created_at)}</InfoRow>
          <InfoRow label="Última actualización">{formatDate(candidate.updated_at)}</InfoRow>
          {candidate.processed_at && (
            <InfoRow label="Procesado">{formatDate(candidate.processed_at)}</InfoRow>
          )}
        </div>
      </div>
    </div>
  );
};

export default CandidateInfo;
