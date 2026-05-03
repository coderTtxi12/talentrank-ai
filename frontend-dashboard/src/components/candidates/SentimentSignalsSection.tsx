/**
 * Muestra el último `sentiment_results` (clasificación, signals).
 * Estilo alineado con el funnel de screening Orbio (primary, tarjetas tipo ficha).
 */
import type { ReactNode } from 'react';
import type { Candidate } from '@/types/candidate';
import {
  INFO_SECTION_SENTIMENT,
  INFO_SECTION_SENTIMENT_HINT,
  INFO_SENTIMENT_CLASSIFICATION,
} from '@/constants/branding';

export function hasSentimentSignals(s: unknown): s is Record<string, unknown> {
  return typeof s === 'object' && s !== null && Object.keys(s as object).length > 0;
}

/** Hay contenido útil en `signals` aparte de evidencias de chat (no mostradas). */
function signalsHasVisibleContent(signals: Record<string, unknown>): boolean {
  const nonEmptyStr = (v: unknown) => typeof v === 'string' && v.trim().length > 0;
  if (
    nonEmptyStr(signals.tone) ||
    nonEmptyStr(signals.engagement) ||
    nonEmptyStr(signals.notes) ||
    nonEmptyStr(signals.reasoning)
  ) {
    return true;
  }
  if ('concerns' in signals && Array.isArray(signals.concerns)) return true;

  const known = new Set([
    'tone',
    'engagement',
    'notes',
    'reasoning',
    'concerns',
    'evidence',
    'post_conversation_summary',
    'key_data_points',
  ]);
  for (const k of Object.keys(signals)) {
    if (known.has(k)) continue;
    const val = signals[k];
    if (val == null || val === '') continue;
    if (Array.isArray(val) && val.length === 0) continue;
    if (
      typeof val === 'object' &&
      !Array.isArray(val) &&
      Object.keys(val as object).length === 0
    ) {
      continue;
    }
    return true;
  }
  return false;
}

export function shouldShowSentimentAnalysis(
  c: Pick<Candidate, 'sentiment' | 'sentiment_signals'>
): boolean {
  if (c.sentiment != null && String(c.sentiment).trim() !== '') return true;
  const sig = c.sentiment_signals;
  if (hasSentimentSignals(sig) && signalsHasVisibleContent(sig)) return true;
  return false;
}

const TONE_LABELS: Record<string, string> = {
  cooperative: 'Cooperativo',
  neutral: 'Neutral',
  frustrated: 'Frustrado',
  hostile: 'Tenso / hostil',
  positive: 'Positivo',
  negative: 'Negativo',
};

const ENGAGEMENT_LABELS: Record<string, string> = {
  high: 'Alto',
  medium: 'Medio',
  low: 'Bajo',
};

/** Valores de `sentiment_results.sentiment` (enum backend). */
const SENTIMENT_ENUM_LABELS: Record<string, string> = {
  positive: 'Positivo',
  neutral: 'Neutral',
  confused: 'Confuso',
  frustrated: 'Frustrado',
};

function formatTone(raw: unknown): string {
  if (typeof raw !== 'string' || !raw.trim()) return '';
  const k = raw.trim().toLowerCase().replace(/\s+/g, '_');
  if (TONE_LABELS[k]) return TONE_LABELS[k];
  return raw.trim().charAt(0).toUpperCase() + raw.trim().slice(1).toLowerCase();
}

function formatEngagement(raw: unknown): string {
  if (typeof raw !== 'string' || !raw.trim()) return '';
  const k = raw.trim().toLowerCase();
  return ENGAGEMENT_LABELS[k] ?? raw.trim();
}

function formatSentimentEnum(raw: string): string {
  const k = raw.trim().toLowerCase();
  return SENTIMENT_ENUM_LABELS[k] ?? raw.trim();
}

function sentimentBadgeClass(raw: string): string {
  const k = raw.trim().toLowerCase();
  const base =
    'inline-flex items-center rounded-md px-2.5 py-1 text-sm font-semibold ring-1 ring-inset';
  switch (k) {
    case 'positive':
      return `${base} bg-green-50 text-green-800 ring-green-600/25`;
    case 'neutral':
      return `${base} bg-slate-100 text-slate-800 ring-slate-500/20`;
    case 'confused':
      return `${base} bg-amber-50 text-amber-900 ring-amber-600/25`;
    case 'frustrated':
      return `${base} bg-red-50 text-red-800 ring-red-600/25`;
    default:
      return `${base} bg-gray-50 text-gray-800 ring-gray-500/15`;
  }
}

/** Filas del bloque de métricas (separadores vía `divide-y` del contenedor). */
function MetricRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4 py-2.5">
      <span className="text-sm text-gray-500 shrink-0">{label}</span>
      <span className="text-sm font-medium text-gray-900 text-left sm:text-right min-w-0 sm:max-w-[70%] break-words">
        {children}
      </span>
    </div>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">{children}</p>
  );
}

// Claves tratadas aquí explícitamente o ignoradas (`key_data_points` sigue en API).
const KNOWN_KEYS = [
  'tone',
  'engagement',
  'notes',
  'reasoning',
  'concerns',
  'evidence',
  'post_conversation_summary',
  'key_data_points',
] as const;

interface SentimentSignalsSectionProps {
  sentiment?: string | null;
  signals?: Record<string, unknown> | null;
}

const SentimentSignalsSection = ({
  sentiment,
  signals: signalsProp,
}: SentimentSignalsSectionProps) => {
  const signals: Record<string, unknown> =
    signalsProp && typeof signalsProp === 'object' ? signalsProp : {};

  if (
    !shouldShowSentimentAnalysis({
      sentiment,
      sentiment_signals: signalsProp,
    })
  ) {
    return null;
  }

  const hasTone = signals.tone != null && signals.tone !== '';
  const hasEngagement = signals.engagement != null && signals.engagement !== '';
  const toneStr = hasTone ? formatTone(signals.tone) : '';
  const engagementStr = hasEngagement ? formatEngagement(signals.engagement) : '';
  const hasSentimentEnum = sentiment != null && String(sentiment).trim() !== '';

  const showMetrics =
    hasSentimentEnum ||
    (hasTone && toneStr) ||
    (hasEngagement && engagementStr);

  const renderConcerns = () => {
    const v = signals.concerns;
    if (!Array.isArray(v)) return null;
    const strings = v.filter((x): x is string => typeof x === 'string' && x.trim().length > 0);
    return (
      <div>
        <SectionLabel>Puntos de atención</SectionLabel>
        {strings.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm text-gray-700">
            Sin incidencias destacadas.
          </div>
        ) : (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50/80 px-3 py-3 text-sm text-yellow-950">
            <ul className="space-y-2">
              {strings.map((c, i) => (
                <li key={i} className="flex gap-2">
                  <span
                    className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-yellow-600/70"
                    aria-hidden
                  />
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const extras = Object.keys(signals)
    .filter((k) => !KNOWN_KEYS.includes(k as (typeof KNOWN_KEYS)[number]))
    .sort();

  const showSignalsBody = signalsHasVisibleContent(signals);

  return (
    <div>
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
          {INFO_SECTION_SENTIMENT}
        </h3>
        <p className="text-xs text-gray-500 mt-1 leading-snug">{INFO_SECTION_SENTIMENT_HINT}</p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 space-y-5">
        {showMetrics && (
          <div className="rounded-lg border border-gray-200 bg-gray-50/80 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
              Resultado del análisis
            </p>
            <div className="rounded-md border border-gray-100 bg-white px-3 divide-y divide-gray-100">
              {hasSentimentEnum && (
                <MetricRow label={INFO_SENTIMENT_CLASSIFICATION}>
                  <span className={sentimentBadgeClass(String(sentiment))}>
                    {formatSentimentEnum(String(sentiment))}
                  </span>
                </MetricRow>
              )}
              {hasTone && toneStr && (
                <MetricRow label="Tono percibido">{toneStr}</MetricRow>
              )}
              {hasEngagement && engagementStr && (
                <MetricRow label="Nivel de implicación">{engagementStr}</MetricRow>
              )}
            </div>
          </div>
        )}

        {showSignalsBody && (
          <>
            {typeof signals.notes === 'string' && signals.notes.trim() && (
              <div>
                <SectionLabel>Notas del modelo</SectionLabel>
                <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap break-words">
                  {signals.notes.trim()}
                </p>
              </div>
            )}

            {typeof signals.reasoning === 'string' && signals.reasoning.trim() && (
              <div>
                <SectionLabel>Razonamiento del modelo</SectionLabel>
                <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap break-words">
                  {signals.reasoning.trim()}
                </p>
              </div>
            )}

            {'concerns' in signals && renderConcerns()}

            {extras.map((key) => {
              const val = signals[key];
              if (val === null || val === undefined || val === '') return null;
              if (typeof val === 'object' && !Array.isArray(val) && Object.keys(val as object).length === 0) {
                return null;
              }
              const label = key.replace(/_/g, ' ');
              const title = label.charAt(0).toUpperCase() + label.slice(1);
              return (
                <div key={key}>
                  <SectionLabel>{title}</SectionLabel>
                  {Array.isArray(val) ? (
                    <ul className="list-disc list-outside pl-4 space-y-1.5 text-sm text-gray-900 marker:text-gray-400">
                      {val.map((item, i) => (
                        <li key={i} className="pl-1">
                          {typeof item === 'string' ? item : JSON.stringify(item)}
                        </li>
                      ))}
                    </ul>
                  ) : typeof val === 'object' ? (
                    <pre className="text-xs leading-relaxed whitespace-pre-wrap break-words rounded-lg bg-gray-50 border border-gray-100 p-3 overflow-x-auto text-gray-800 font-mono">
                      {JSON.stringify(val, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{String(val)}</p>
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
};

export default SentimentSignalsSection;
