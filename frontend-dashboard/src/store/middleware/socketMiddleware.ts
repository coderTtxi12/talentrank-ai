/**
 * Redux middleware for Socket.IO: connects once at startup.
 */
import { Middleware } from '@reduxjs/toolkit';

import { connectSocket, getSocket } from '@/services/socket';
import {
  candidateUpdated,
  candidateCreated,
  statusChanged,
  fetchStatistics,
} from '@/store/slices/candidatesSlice';
import { CANDIDATE_STATUS_LABELS, type CandidateStatus } from '@/types/candidate';
import { addNotification } from '@/store/slices/uiSlice';
import { TOAST_NEW_CANDIDATE, TOAST_STATUS_LINE } from '@/constants/branding';

let listenersInitialized = false;
let initialConnectDone = false;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const setupSocketListeners = (dispatch: (action: any) => unknown): void => {
  const socket = getSocket();
  if (!socket || listenersInitialized) return;

  socket.on('loan_created', (data: any) => {
    console.log('[Socket.IO] Candidate created:', data);
    dispatch(candidateCreated(data.data));
    dispatch(fetchStatistics(undefined));
    dispatch(
      addNotification({
        type: 'info',
        message: TOAST_NEW_CANDIDATE(data.loan_id),
        duration: 5000,
      })
    );
  });

  socket.on('loan_updated', (data: any) => {
    console.log('[Socket.IO] Candidate updated:', data);
    dispatch(candidateUpdated({ id: data.loan_id, ...data.changes }));
    dispatch(fetchStatistics(undefined));
  });

  socket.on('status_changed', (data: any) => {
    console.log('[Socket.IO] Status changed:', data);
    dispatch(
      statusChanged({
        loan_id: data.loan_id,
        old_status: data.old_status,
        new_status: data.new_status,
      })
    );
    dispatch(
      addNotification({
        type:
          data.new_status === 'qualified' ||
          data.new_status === 'qualified_flagged'
            ? 'success'
            : data.new_status === 'hard_disq' ||
                data.new_status === 'soft_disq'
              ? 'error'
              : 'info',
        message: TOAST_STATUS_LINE(
          data.loan_id.slice(0, 8),
          CANDIDATE_STATUS_LABELS[data.new_status as CandidateStatus] ??
            data.new_status
        ),
        duration: 5000,
      })
    );
    dispatch(fetchStatistics(undefined));
  });

  listenersInitialized = true;
};

export const socketMiddleware: Middleware = (store) => (next) => (action: any) => {
  const result = next(action);

  if (!initialConnectDone) {
    initialConnectDone = true;
    const socket = getSocket();
    if (!socket?.connected) {
      connectSocket();
      setupSocketListeners(store.dispatch);
    }
  }

  return result;
};

export default socketMiddleware;
