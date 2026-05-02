/**
 * Redux middleware for Socket.IO: connects once at startup, subscribes to candidate feeds.
 */
import { Middleware } from '@reduxjs/toolkit';

import { connectSocket, getSocket } from '@/services/socket';
import {
  candidateUpdated,
  candidateCreated,
  statusChanged,
  fetchStatistics,
  applyWsCandidatesSnapshot,
  applyWsRecentCandidates,
} from '@/store/slices/candidatesSlice';
import {
  CANDIDATE_STATUS_LABELS,
  type Candidate,
  type CandidatesState,
  type CandidateStatus,
} from '@/types/candidate';
import { addNotification } from '@/store/slices/uiSlice';
import { TOAST_NEW_CANDIDATE, TOAST_STATUS_LINE } from '@/constants/branding';

type StoreWithCandidates = { candidates: CandidatesState };

let handlersWired = false;
let initialConnectDone = false;

function emitCandidateSubscriptions(getState: () => StoreWithCandidates): void {
  const socket = getSocket();
  if (!socket?.connected) return;

  const cand = getState().candidates;
  const { filters } = cand;
  const pageSize = (filters.page_size as number) ?? 20;
  const cursor = (filters.cursor as string | null) ?? undefined;
  const recentLimit = cand.recentPageSize ?? 12;

  socket.emit('subscribe_candidates', {
    limit: pageSize,
    status: filters.status ?? undefined,
    country_code: filters.country_code ?? undefined,
    cursor,
    include_total: !cursor,
  });

  socket.emit('subscribe_recent', { limit: recentLimit });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const setupSocketHandlersOnce = (
  dispatch: (action: any) => unknown,
  getState: () => StoreWithCandidates
): void => {
  const socket = getSocket();
  if (!socket || handlersWired) return;

  socket.on('candidates_snapshot', (data: unknown) => {
    dispatch(applyWsCandidatesSnapshot(data as Parameters<typeof applyWsCandidatesSnapshot>[0]));
    dispatch(fetchStatistics(undefined));
  });

  socket.on(
    'recent_candidates_snapshot',
    (payload: {
      items?: unknown[];
      next_cursor?: string | null;
      cursor?: string | null;
    }) => {
      const raw = payload?.items;
      if (!Array.isArray(raw)) return;
      const append = typeof payload.cursor === 'string';
      const next_cursor =
        typeof payload?.next_cursor === 'string'
          ? payload.next_cursor
          : (payload?.next_cursor ?? null);
      dispatch(
        applyWsRecentCandidates({
          items: raw as Candidate[],
          next_cursor,
          append,
        })
      );
    }
  );

  socket.on('loan_created', (data: any) => {
    dispatch(candidateCreated(data.data));
    dispatch(fetchStatistics(undefined));
    dispatch(
      addNotification({
        type: 'info',
        message: TOAST_NEW_CANDIDATE(data.loan_id ?? data.candidate_id ?? ''),
        duration: 5000,
      })
    );
  });

  socket.on('candidate_created', (data: { candidate_id?: string; data?: Candidate }) => {
    if (!data?.data) return;
    const cid = String(data.candidate_id ?? data.data.id);
    const alreadyListed = cid && getState().candidates.items.some((l) => l.id === cid);
    dispatch(candidateCreated(data.data));
    dispatch(fetchStatistics(undefined));
    if (!alreadyListed && cid) {
      dispatch(
        addNotification({
          type: 'info',
          message: TOAST_NEW_CANDIDATE(cid),
          duration: 5000,
        })
      );
    }
  });

  socket.on('loan_updated', (data: any) => {
    dispatch(candidateUpdated({ id: data.loan_id, ...data.changes }));
    dispatch(fetchStatistics(undefined));
  });

  socket.on('candidate_updated', (data: any) => {
    dispatch(candidateUpdated({ id: data.candidate_id, ...data.changes }));
    dispatch(fetchStatistics(undefined));
  });

  socket.on('status_changed', (data: any) => {
    dispatch(
      statusChanged({
        loan_id: data.loan_id,
        candidate_id: data.candidate_id,
        old_status: data.old_status,
        new_status: data.new_status,
      })
    );
    const cid = (data.candidate_id ?? data.loan_id ?? '') as string;
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
          cid.slice(0, 8),
          CANDIDATE_STATUS_LABELS[data.new_status as CandidateStatus] ??
            data.new_status
        ),
        duration: 5000,
      })
    );
    dispatch(fetchStatistics(undefined));
  });

  handlersWired = true;
};

export const socketMiddleware: Middleware = (store) => (next) => (action: any) => {
  const result = next(action);

  if (!initialConnectDone) {
    initialConnectDone = true;
    connectSocket();
    const socket = getSocket();
    const onConnect = () => {
      setupSocketHandlersOnce(store.dispatch, store.getState);
      emitCandidateSubscriptions(store.getState);
    };
    socket?.on('connect', onConnect);
    if (socket?.connected) {
      onConnect();
    }
  }

  if (
    typeof action === 'object' &&
    action &&
    action.type === 'candidates/setFilters'
  ) {
    emitCandidateSubscriptions(store.getState);
  }

  return result;
};

export default socketMiddleware;
