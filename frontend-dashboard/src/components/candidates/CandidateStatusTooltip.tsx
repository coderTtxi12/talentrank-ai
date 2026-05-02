/**
 * Hover tooltip with full status explanation (fixed position avoids clipping in scroll/overflow areas).
 */
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import clsx from 'clsx';
import {
  CANDIDATE_STATUS_DESCRIPTIONS,
  type CandidateStatus,
} from '@/types/candidate';

interface CandidateStatusTooltipProps {
  status: CandidateStatus;
  children: ReactNode;
  /** Wrapper layout — default keeps badges inline */
  className?: string;
}

export function CandidateStatusTooltip({
  status,
  children,
  className,
}: CandidateStatusTooltipProps) {
  const triggerRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [tipStyle, setTipStyle] = useState<CSSProperties>({});
  const tipId = useId();

  const description = CANDIDATE_STATUS_DESCRIPTIONS[status];

  const updatePosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const gap = 8;
    const estimatedHeight = 140;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const placeAbove =
      spaceBelow < estimatedHeight && rect.top > estimatedHeight + gap;

    const left = rect.left + rect.width / 2;
    if (placeAbove) {
      setTipStyle({
        position: 'fixed',
        left,
        top: rect.top - gap,
        transform: 'translate(-50%, -100%)',
      });
    } else {
      setTipStyle({
        position: 'fixed',
        left,
        top: rect.bottom + gap,
        transform: 'translate(-50%, 0)',
      });
    }
  }, []);

  const show = () => {
    updatePosition();
    setVisible(true);
  };

  const hide = () => setVisible(false);

  useEffect(() => {
    if (!visible) return;
    const dismiss = () => setVisible(false);
    window.addEventListener('scroll', dismiss, true);
    window.addEventListener('resize', dismiss);
    return () => {
      window.removeEventListener('scroll', dismiss, true);
      window.removeEventListener('resize', dismiss);
    };
  }, [visible]);

  return (
    <>
      <div
        ref={triggerRef}
        className={clsx('inline-flex max-w-full', className)}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        tabIndex={0}
        aria-describedby={visible ? tipId : undefined}
      >
        {children}
      </div>
      {visible &&
        createPortal(
          <div
            id={tipId}
            role="tooltip"
            className="pointer-events-none fixed z-[200] max-w-xs rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-left text-xs leading-snug text-white shadow-xl"
            style={tipStyle}
          >
            {description}
          </div>,
          document.body
        )}
    </>
  );
}
