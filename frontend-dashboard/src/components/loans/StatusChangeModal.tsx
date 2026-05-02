/**
 * Modal for changing loan status.
 */
import { useState } from 'react';
import { Modal, Button, Select } from '@/components/ui';
import Input from '@/components/ui/Input';
import type { LoanStatus, CandidateStatus } from '@/types/loan';
import { CANDIDATE_STATUS_LABELS } from '@/types/loan';

interface StatusChangeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (newStatus: LoanStatus, reason: string) => Promise<void>;
  currentStatus: LoanStatus;
  loading?: boolean;
}

const statusLabels = CANDIDATE_STATUS_LABELS;

const allowedTransitions: Record<CandidateStatus, CandidateStatus[]> = {
  new: ['in_progress', 'waitlist', 'abandoned'],
  in_progress: [
    'qualified',
    'qualified_flagged',
    'soft_disq',
    'hard_disq',
    'waitlist',
    'abandoned',
  ],
  qualified: ['qualified_flagged', 'soft_disq', 'waitlist'],
  qualified_flagged: ['qualified', 'soft_disq', 'hard_disq'],
  soft_disq: ['in_progress', 'qualified', 'waitlist'],
  hard_disq: [],
  waitlist: ['in_progress', 'qualified', 'new'],
  abandoned: ['in_progress', 'new'],
};

const StatusChangeModal = ({
  isOpen,
  onClose,
  onConfirm,
  currentStatus,
  loading = false,
}: StatusChangeModalProps) => {
  const [newStatus, setNewStatus] = useState<LoanStatus | ''>('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  const availableStatuses = allowedTransitions[currentStatus] || [];

  const handleConfirm = async () => {
    if (!newStatus) {
      setError('Please select a status');
      return;
    }

    if (
      ['hard_disq', 'soft_disq', 'abandoned'].includes(newStatus) &&
      !reason.trim()
    ) {
      setError('Motivo obligatorio para descalificación o abandono');
      return;
    }

    setError('');
    await onConfirm(newStatus as LoanStatus, reason);
    handleClose();
  };

  const handleClose = () => {
    setNewStatus('');
    setReason('');
    setError('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Change Loan Status" size="md">
      <div className="space-y-4">
        {/* Current status */}
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-sm text-gray-500">Current Status</p>
          <p className="text-lg font-medium text-gray-900">
            {statusLabels[currentStatus]}
          </p>
        </div>

        {/* New status selection */}
        {availableStatuses.length > 0 ? (
          <>
            <Select
              label="New Status"
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value as LoanStatus)}
              options={availableStatuses.map((status) => ({
                value: status,
                label: statusLabels[status],
              }))}
              placeholder="Select new status"
            />

            {/* Reason input */}
            <Input
              label="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter reason for status change"
              helperText={
                newStatus &&
                ['hard_disq', 'soft_disq', 'abandoned'].includes(newStatus)
                  ? 'Obligatorio para descalificación o abandono'
                  : undefined
              }
            />

            {/* Error message */}
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
              <Button variant="ghost" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                variant={
                  newStatus === 'hard_disq' || newStatus === 'soft_disq'
                    ? 'danger'
                    : 'primary'
                }
                onClick={handleConfirm}
                loading={loading}
              >
                Confirm Change
              </Button>
            </div>
          </>
        ) : (
          <div className="text-center py-4">
            <p className="text-gray-500">
              No status transitions available from {statusLabels[currentStatus]}
            </p>
            <Button variant="ghost" onClick={handleClose} className="mt-4">
              Close
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default StatusChangeModal;
