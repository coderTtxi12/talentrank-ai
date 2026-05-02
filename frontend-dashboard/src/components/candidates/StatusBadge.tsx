/**
 * Status badge component with color coding.
 */
import clsx from 'clsx';
import {
  CANDIDATE_STATUS_LABELS,
  type CandidateStatus,
} from '@/types/candidate';

interface StatusBadgeProps {
  status: CandidateStatus;
  size?: 'sm' | 'md' | 'lg';
}

const statusConfig: Record<
  CandidateStatus,
  { label: string; className: string }
> = {
  new: {
    label: CANDIDATE_STATUS_LABELS.new,
    className: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  },
  in_progress: {
    label: CANDIDATE_STATUS_LABELS.in_progress,
    className: 'bg-blue-100 text-blue-800 border-blue-200',
  },
  hard_filter: {
    label: CANDIDATE_STATUS_LABELS.hard_filter,
    className: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  },
  sentiment_analysis: {
    label: CANDIDATE_STATUS_LABELS.sentiment_analysis,
    className: 'bg-pink-100 text-pink-800 border-pink-200',
  },
  listwise: {
    label: CANDIDATE_STATUS_LABELS.listwise,
    className: 'bg-teal-100 text-teal-800 border-teal-200',
  },
  plackett_luce: {
    label: CANDIDATE_STATUS_LABELS.plackett_luce,
    className: 'bg-amber-100 text-amber-800 border-amber-200',
  },
  qualified: {
    label: CANDIDATE_STATUS_LABELS.qualified,
    className: 'bg-green-100 text-green-800 border-green-200',
  },
  qualified_flagged: {
    label: CANDIDATE_STATUS_LABELS.qualified_flagged,
    className: 'bg-purple-100 text-purple-800 border-purple-200',
  },
  soft_disq: {
    label: CANDIDATE_STATUS_LABELS.soft_disq,
    className: 'bg-orange-100 text-orange-800 border-orange-200',
  },
  hard_disq: {
    label: CANDIDATE_STATUS_LABELS.hard_disq,
    className: 'bg-red-100 text-red-800 border-red-200',
  },
  waitlist: {
    label: CANDIDATE_STATUS_LABELS.waitlist,
    className: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  },
  abandoned: {
    label: CANDIDATE_STATUS_LABELS.abandoned,
    className: 'bg-gray-100 text-gray-800 border-gray-200',
  },
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-sm',
};

const StatusBadge = ({ status, size = 'md' }: StatusBadgeProps) => {
  const config = statusConfig[status as CandidateStatus] || statusConfig.new;

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full border',
        config.className,
        sizeStyles[size]
      )}
    >
      {config.label}
    </span>
  );
};

export default StatusBadge;
