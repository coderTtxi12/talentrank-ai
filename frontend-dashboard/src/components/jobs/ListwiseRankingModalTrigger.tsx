/**
 * Primary action to enqueue Listwise + Plackett–Luce (confirmation modal + API).
 */
import { useState } from 'react';
import { Button, Modal } from '@/components/ui';
import {
  DASH_BTN_NEW,
  DASH_RANK_MODAL_TITLE,
  DASH_RANK_MODAL_BODY,
  DASH_RANK_MODAL_CANCEL,
  DASH_RANK_MODAL_CONFIRM,
  DASH_RANK_SUBMITTING,
  DASH_RANK_SUCCESS,
  DASH_RANK_ERROR_GENERIC,
} from '@/constants/branding';
import { createListwiseJob } from '@/services/jobsApi';

export interface ListwiseRankingModalTriggerProps {
  /** Disable button (e.g. while another dashboard action runs). */
  disabled?: boolean;
  /** Extra Tailwind classes for the trigger button. */
  buttonClassName?: string;
  /** Clear parent-held banners when opening or confirming (e.g. dashboard). */
  onClearFeedback?: () => void;
  /**
   * When set, success/error feedback is delegated to the parent (e.g. dashboard banner above multiple buttons).
   * Otherwise an inline status line is shown above the button.
   */
  onQueued?: (jobId: string) => void;
  onQueueFailed?: () => void;
}

export function ListwiseRankingModalTrigger({
  disabled = false,
  buttonClassName = 'px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-60',
  onClearFeedback,
  onQueued,
  onQueueFailed,
}: ListwiseRankingModalTriggerProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [inlineBanner, setInlineBanner] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const delegated = Boolean(onQueued);

  return (
    <>
      {!delegated && inlineBanner ? (
        <p
          className={`text-sm max-w-md text-right ${
            inlineBanner.type === 'success' ? 'text-green-700' : 'text-red-600'
          }`}
          role="status"
        >
          {inlineBanner.text}
        </p>
      ) : null}
      <button
        type="button"
        className={buttonClassName}
        disabled={disabled || submitting}
        onClick={() => {
          onClearFeedback?.();
          if (!delegated) setInlineBanner(null);
          setModalOpen(true);
        }}
      >
        {DASH_BTN_NEW}
      </button>
      <Modal
        isOpen={modalOpen}
        onClose={() => !submitting && setModalOpen(false)}
        title={DASH_RANK_MODAL_TITLE}
        size="md"
      >
        <p className="text-sm text-gray-600 leading-relaxed">{DASH_RANK_MODAL_BODY}</p>
        <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={submitting}
            onClick={() => setModalOpen(false)}
          >
            {DASH_RANK_MODAL_CANCEL}
          </Button>
          <Button
            type="button"
            disabled={submitting}
            onClick={() => {
              void (async () => {
                setSubmitting(true);
                onClearFeedback?.();
                if (!delegated) setInlineBanner(null);
                try {
                  const res = await createListwiseJob({});
                  setModalOpen(false);
                  if (onQueued) {
                    onQueued(res.job_id);
                  } else {
                    setInlineBanner({
                      type: 'success',
                      text: DASH_RANK_SUCCESS(res.job_id),
                    });
                  }
                } catch {
                  setModalOpen(false);
                  if (onQueueFailed) {
                    onQueueFailed();
                  } else {
                    setInlineBanner({ type: 'error', text: DASH_RANK_ERROR_GENERIC });
                  }
                } finally {
                  setSubmitting(false);
                }
              })();
            }}
          >
            {submitting ? DASH_RANK_SUBMITTING : DASH_RANK_MODAL_CONFIRM}
          </Button>
        </div>
      </Modal>
    </>
  );
}
