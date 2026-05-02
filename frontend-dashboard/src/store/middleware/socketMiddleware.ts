/**
 * Redux middleware for Socket.IO: connects once at startup.
 */
import { Middleware } from '@reduxjs/toolkit';

import { connectSocket, getSocket } from '@/services/socket';
import {
  loanUpdated,
  loanCreated,
  statusChanged,
  fetchStatistics,
} from '@/store/slices/loansSlice';
import { addNotification } from '@/store/slices/uiSlice';

let listenersInitialized = false;
let initialConnectDone = false;

const setupSocketListeners = (dispatch: (action: any) => unknown): void => {
  const socket = getSocket();
  if (!socket || listenersInitialized) return;

  socket.on('loan_created', (data: any) => {
    console.log('[Socket.IO] Loan created:', data);
    dispatch(loanCreated(data.data));
    dispatch(fetchStatistics(undefined));
    dispatch(
      addNotification({
        type: 'info',
        message: `Nueva solicitud: ${data.loan_id}`,
        duration: 5000,
      })
    );
  });

  socket.on('loan_updated', (data: any) => {
    console.log('[Socket.IO] Loan updated:', data);
    dispatch(loanUpdated({ id: data.loan_id, ...data.changes }));
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
          data.new_status === 'APPROVED'
            ? 'success'
            : data.new_status === 'REJECTED'
              ? 'error'
              : 'info',
        message: `Solicitud ${data.loan_id.slice(0, 8)}… → ${data.new_status}`,
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
