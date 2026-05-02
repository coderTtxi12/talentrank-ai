/**
 * Estado Redux del listado y detalle de candidatos (API `/loans`).
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import axios from 'axios';
import type {
  Candidate,
  CandidateCreateRequest,
  CandidatesState,
  CandidateFilters,
  CandidateStatistics,
  CandidateStatus,
  CandidatesCursorResponse,
} from '@/types/candidate';
import { api } from '@/services/api';
import { getSocket } from '@/services/socket';
import {
  ERR_FETCH_LIST,
  ERR_FETCH_ONE,
  ERR_CREATE,
  ERR_UPDATE_STATUS,
  ERR_HISTORY,
  ERR_STATS,
} from '@/constants/branding';

const DASHBOARD_RECENT_WS_LIMIT = 12;

/** Petición cancelada o deduplicada (StrictMode, dispatch repetido). */
const THUNK_SUPERSEDED = '__thunkSuperseded__';

let bootstrapRecentInFlightKey: string | null = null;
let bootstrapRecentAbortController: AbortController | null = null;

let statisticsInFlightKey: string | null = null;
let statisticsAbortController: AbortController | null = null;

const BOOTSTRAP_RECENT_QUERY_KEY = `recent|${DASHBOARD_RECENT_WS_LIMIT}`;
const STATISTICS_FETCH_KEY = 'statistics';

let listFetchInFlightKey: string | null = null;
let listFetchAbortController: AbortController | null = null;

function listFetchKey(f: CandidateFilters): string {
  return [
    f.country_code ?? '',
    f.status ?? '',
    f.requires_review === null ? '' : String(f.requires_review),
    f.cursor ?? '',
    String(f.page_size),
  ].join('|');
}

const initialState: CandidatesState = {
  items: [],
  dashboardRecent: [],
  selectedCandidate: null,
  statistics: null,
  statisticsLoading: false,
  loading: false,
  error: null,
  filters: {
    country_code: null,
    status: null,
    requires_review: null,
    cursor: null,
    page: 1,
    page_size: 20,
  },
  pagination: {
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0,
    next_cursor: null,
  },
  recentNextCursor: null,
  recentHydrated: false,
  recentPageSize: DASHBOARD_RECENT_WS_LIMIT,
};

/** Si WebSocket no llega a tiempo, primera página vía HTTP (misma forma que el snapshot WS). */
export const bootstrapDashboardRecent = createAsyncThunk(
  'candidates/bootstrapRecent',
  async (_, { rejectWithValue }) => {
    const myKey = BOOTSTRAP_RECENT_QUERY_KEY;
    const signal = bootstrapRecentAbortController!.signal;
    try {
      const params = new URLSearchParams();
      params.append('limit', String(DASHBOARD_RECENT_WS_LIMIT));
      const response = await api.get<CandidatesCursorResponse>(
        `/candidates?${params.toString()}`,
        { signal }
      );
      return response.data;
    } catch (error: unknown) {
      if (axios.isCancel(error)) {
        return rejectWithValue(THUNK_SUPERSEDED);
      }
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_FETCH_LIST;
      return rejectWithValue(message);
    } finally {
      if (bootstrapRecentInFlightKey === myKey) {
        bootstrapRecentInFlightKey = null;
      }
    }
  },
  {
    condition: () => {
      if (bootstrapRecentInFlightKey === BOOTSTRAP_RECENT_QUERY_KEY) {
        return false;
      }
      bootstrapRecentAbortController?.abort();
      bootstrapRecentAbortController = new AbortController();
      bootstrapRecentInFlightKey = BOOTSTRAP_RECENT_QUERY_KEY;
      return true;
    },
  }
);

export const fetchCandidates = createAsyncThunk(
  'candidates/fetchList',
  async (filters: Partial<CandidateFilters> | undefined, { getState, rejectWithValue }) => {
    const state = getState() as { candidates: CandidatesState };
    const currentFilters = { ...state.candidates.filters, ...filters };
    const myKey = listFetchKey(currentFilters);
    const signal = listFetchAbortController!.signal;

    try {
      const params = new URLSearchParams();
      if (currentFilters.country_code) params.append('country_code', currentFilters.country_code);
      if (currentFilters.status) params.append('status', currentFilters.status);
      if (currentFilters.requires_review !== null) {
        params.append('requires_review', String(currentFilters.requires_review));
      }
      if (currentFilters.cursor) params.append('cursor', currentFilters.cursor);
      params.append('limit', String(currentFilters.page_size));
      if (!currentFilters.cursor) params.append('include_total', 'true');

      const response = await api.get<CandidatesCursorResponse>(
        `/candidates?${params.toString()}`,
        { signal }
      );
      return response.data;
    } catch (error: unknown) {
      if (axios.isCancel(error)) {
        return rejectWithValue(THUNK_SUPERSEDED);
      }
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_FETCH_LIST;
      return rejectWithValue(message);
    } finally {
      if (listFetchInFlightKey === myKey) {
        listFetchInFlightKey = null;
      }
    }
  },
  {
    condition: (filters, { getState }) => {
      const state = (getState() as { candidates: CandidatesState }).candidates;
      const key = listFetchKey({ ...state.filters, ...filters });
      if (listFetchInFlightKey === key) {
        return false;
      }
      listFetchAbortController?.abort();
      listFetchAbortController = new AbortController();
      listFetchInFlightKey = key;
      return true;
    },
  }
);

export const fetchCandidateById = createAsyncThunk(
  'candidates/fetchOne',
  async (candidateId: string, { rejectWithValue }) => {
    try {
      const response = await api.get(`/candidates/${candidateId}`);
      return response.data as Candidate;
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_FETCH_ONE;
      return rejectWithValue(message);
    }
  }
);

export const createCandidate = createAsyncThunk(
  'candidates/create',
  async (payload: CandidateCreateRequest, { rejectWithValue }) => {
    try {
      const response = await api.post('/candidates', payload);
      return response.data as Candidate;
    } catch (error: unknown) {
      console.error('Create candidate error:', {
        status: (error as { response?: { status?: number } })?.response?.status,
        data: (error as { response?: { data?: unknown } })?.response?.data,
        request: payload,
      });

      const errorData = (error as { response?: { data?: Record<string, unknown> } })?.response
        ?.data;
      let message = ERR_CREATE;
      let errors: string[] = [];

      if (errorData?.detail) {
        const detail = errorData.detail;
        if (Array.isArray(detail)) {
          errors = detail.map(
            (err: { loc?: string[]; msg?: string }) =>
              `${err.loc?.join('.')}: ${err.msg}`
          );
          message = `Error de validación: ${errors.join(', ')}`;
        } else if (typeof detail === 'object' && detail !== null) {
          const d = detail as { message?: string; errors?: string[] };
          message = d.message || message;
          errors = d.errors || [];
        } else if (typeof detail === 'string') {
          message = detail;
        }
      } else if (typeof errorData?.message === 'string') {
        message = errorData.message;
      }

      return rejectWithValue({ message, errors });
    }
  }
);

export const updateCandidateStatus = createAsyncThunk(
  'candidates/updateStatus',
  async (
    {
      candidateId,
      status,
      reason,
    }: { candidateId: string; status: string; reason?: string },
    { rejectWithValue }
  ) => {
    try {
      const response = await api.patch(`/candidates/${candidateId}/status`, { status, reason });
      return response.data as Candidate;
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_UPDATE_STATUS;
      return rejectWithValue(message);
    }
  }
);

export const fetchCandidateHistory = createAsyncThunk(
  'candidates/fetchHistory',
  async (candidateId: string, { rejectWithValue }) => {
    try {
      const response = await api.get(`/candidates/${candidateId}/history`);
      return { candidateId, history: response.data };
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_HISTORY;
      return rejectWithValue(message);
    }
  }
);

/** Siguiente ventana de "recientes" vía Socket (`subscribe_recent` con cursor). */
export const fetchMoreDashboardRecentWs = createAsyncThunk(
  'candidates/fetchMoreRecentWs',
  async (_, { getState }) => {
    const state = getState() as { candidates: CandidatesState };
    const { recentNextCursor, recentPageSize } = state.candidates;
    const socket = getSocket();
    if (!recentNextCursor || !socket?.connected) {
      return;
    }
    socket.emit('subscribe_recent', {
      limit: recentPageSize,
      cursor: recentNextCursor,
    });
  }
);

export const fetchStatistics = createAsyncThunk(
  'candidates/fetchStatistics',
  async (_countryCode: string | undefined, { rejectWithValue }) => {
    const myKey = STATISTICS_FETCH_KEY;
    const signal = statisticsAbortController!.signal;
    try {
      const response = await api.get<CandidateStatistics>('/candidates/statistics', { signal });
      return response.data;
    } catch (error: unknown) {
      if (axios.isCancel(error)) {
        return rejectWithValue(THUNK_SUPERSEDED);
      }
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_STATS;
      return rejectWithValue(message);
    } finally {
      if (statisticsInFlightKey === myKey) {
        statisticsInFlightKey = null;
      }
    }
  },
  {
    condition: () => {
      if (statisticsInFlightKey === STATISTICS_FETCH_KEY) {
        return false;
      }
      statisticsAbortController?.abort();
      statisticsAbortController = new AbortController();
      statisticsInFlightKey = STATISTICS_FETCH_KEY;
      return true;
    },
  }
);

const candidatesSlice = createSlice({
  name: 'candidates',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<Partial<CandidateFilters>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = { ...initialState.filters };
    },
    clearSelectedCandidate: (state) => {
      state.selectedCandidate = null;
    },
    clearError: (state) => {
      state.error = null;
    },
    candidateUpdated: (state, action: PayloadAction<Partial<Candidate> & { id: string }>) => {
      const index = state.items.findIndex((l) => l.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = { ...state.items[index], ...action.payload };
      }
      if (state.selectedCandidate?.id === action.payload.id) {
        state.selectedCandidate = { ...state.selectedCandidate, ...action.payload };
      }
    },
    candidateCreated: (state, action: PayloadAction<Candidate>) => {
      const incoming = action.payload;
      const exists = state.items.some((l) => l.id === incoming.id);
      if (!exists) {
        state.items.unshift(incoming);
        state.pagination.total += 1;
      }
      state.dashboardRecent = [
        incoming,
        ...state.dashboardRecent.filter((c) => c.id !== incoming.id),
      ];
    },
    statusChanged: (
      state,
      action: PayloadAction<{
        loan_id?: string;
        candidate_id?: string;
        old_status: string;
        new_status: string;
      }>
    ) => {
      const id = action.payload.candidate_id ?? action.payload.loan_id;
      if (!id) return;
      const { new_status } = action.payload;
      const index = state.items.findIndex((l) => l.id === id);
      if (index !== -1) {
        state.items[index].status = new_status as CandidateStatus;
      }
      if (state.selectedCandidate?.id === id) {
        state.selectedCandidate.status = new_status as CandidateStatus;
      }
      const ridx = state.dashboardRecent.findIndex((l) => l.id === id);
      if (ridx !== -1) {
        state.dashboardRecent[ridx].status = new_status as CandidateStatus;
      }
    },
    applyWsCandidatesSnapshot: (
      state,
      action: PayloadAction<CandidatesCursorResponse>
    ) => {
      const p = action.payload;
      state.items = p.items;
      const total = p.total ?? state.pagination.total;
      const limit = p.limit;
      state.pagination = {
        total,
        page: state.filters.page,
        page_size: limit,
        total_pages:
          total > 0 && limit > 0 ? Math.max(1, Math.ceil(total / limit)) : 1,
        next_cursor: p.next_cursor ?? null,
      };
    },
    applyWsRecentCandidates: (
      state,
      action: PayloadAction<{
        items: Candidate[];
        next_cursor: string | null;
        append: boolean;
      }>
    ) => {
      const { items, next_cursor, append } = action.payload;
      if (append && state.dashboardRecent.length > 0) {
        const seen = new Set(state.dashboardRecent.map((c) => c.id));
        for (const c of items) {
          if (!seen.has(c.id)) {
            seen.add(c.id);
            state.dashboardRecent.push(c);
          }
        }
      } else {
        state.dashboardRecent = items;
      }
      state.recentNextCursor = next_cursor ?? null;
      state.recentHydrated = true;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(bootstrapDashboardRecent.fulfilled, (state, action) => {
        if (state.recentHydrated) return;
        const p = action.payload;
        state.dashboardRecent = p.items;
        state.recentNextCursor = p.next_cursor ?? null;
        state.recentHydrated = true;
      })
      .addCase(bootstrapDashboardRecent.rejected, (state, action) => {
        if (action.payload === THUNK_SUPERSEDED) {
          return;
        }
        if (!state.recentHydrated) {
          state.recentHydrated = true;
          state.dashboardRecent = [];
          state.recentNextCursor = null;
        }
      })

      .addCase(fetchCandidates.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCandidates.fulfilled, (state, action) => {
        state.loading = false;
        const p = action.payload;
        state.items = p.items;
        const total = p.total ?? state.pagination.total;
        const limit = p.limit;
        state.pagination = {
          total,
          page: state.filters.page,
          page_size: limit,
          total_pages:
            total > 0 && limit > 0 ? Math.max(1, Math.ceil(total / limit)) : 1,
          next_cursor: p.next_cursor ?? null,
        };
      })
      .addCase(fetchCandidates.rejected, (state, action) => {
        if (action.payload === THUNK_SUPERSEDED) {
          return;
        }
        state.loading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(fetchCandidateById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCandidateById.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedCandidate = action.payload;
      })
      .addCase(fetchCandidateById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(createCandidate.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createCandidate.fulfilled, (state, action) => {
        state.loading = false;
        const incoming = action.payload;
        if (!state.items.some((l) => l.id === incoming.id)) {
          state.items.unshift(incoming);
          state.pagination.total += 1;
        }
        state.dashboardRecent = [
          incoming,
          ...state.dashboardRecent.filter((c) => c.id !== incoming.id),
        ];
      })
      .addCase(createCandidate.rejected, (state, action) => {
        state.loading = false;
        const payload = action.payload as { message?: string } | string | undefined;
        state.error =
          typeof payload === 'string' ? payload : payload?.message || ERR_CREATE;
      });

    builder
      .addCase(updateCandidateStatus.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateCandidateStatus.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.items.findIndex((l) => l.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
        if (state.selectedCandidate?.id === action.payload.id) {
          state.selectedCandidate = action.payload;
        }
      })
      .addCase(updateCandidateStatus.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(fetchStatistics.pending, (state) => {
        state.statisticsLoading = true;
      })
      .addCase(fetchStatistics.fulfilled, (state, action) => {
        state.statisticsLoading = false;
        state.statistics = action.payload;
      })
      .addCase(fetchStatistics.rejected, (state, action) => {
        if (action.payload === THUNK_SUPERSEDED) {
          return;
        }
        state.statisticsLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const {
  setFilters,
  clearFilters,
  clearSelectedCandidate,
  clearError,
  candidateUpdated,
  candidateCreated,
  statusChanged,
  applyWsCandidatesSnapshot,
  applyWsRecentCandidates,
} = candidatesSlice.actions;

export default candidatesSlice.reducer;
