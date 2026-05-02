/**
 * Estado Redux del listado y detalle de candidatos (API `/loans`).
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type {
  Candidate,
  CandidateCreateRequest,
  CandidatesState,
  CandidateFilters,
  CandidateStatistics,
  CandidateStatus,
} from '@/types/candidate';
import { api } from '@/services/api';
import {
  ERR_FETCH_LIST,
  ERR_FETCH_ONE,
  ERR_CREATE,
  ERR_UPDATE_STATUS,
  ERR_HISTORY,
  ERR_STATS,
} from '@/constants/branding';

const initialState: CandidatesState = {
  items: [],
  selectedCandidate: null,
  statistics: null,
  loading: false,
  error: null,
  filters: {
    country_code: null,
    status: null,
    requires_review: null,
    page: 1,
    page_size: 20,
  },
  pagination: {
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0,
  },
};

export const fetchCandidates = createAsyncThunk(
  'candidates/fetchList',
  async (filters: Partial<CandidateFilters> | undefined, { getState, rejectWithValue }) => {
    try {
      const state = getState() as { candidates: CandidatesState };
      const currentFilters = { ...state.candidates.filters, ...filters };

      const params = new URLSearchParams();
      if (currentFilters.country_code) params.append('country_code', currentFilters.country_code);
      if (currentFilters.status) params.append('status', currentFilters.status);
      if (currentFilters.requires_review !== null) {
        params.append('requires_review', String(currentFilters.requires_review));
      }
      params.append('page', String(currentFilters.page));
      params.append('page_size', String(currentFilters.page_size));

      const response = await api.get(`/loans?${params.toString()}`);
      return response.data;
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_FETCH_LIST;
      return rejectWithValue(message);
    }
  }
);

export const fetchCandidateById = createAsyncThunk(
  'candidates/fetchOne',
  async (candidateId: string, { rejectWithValue }) => {
    try {
      const response = await api.get(`/loans/${candidateId}`);
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
      const response = await api.post('/loans', payload);
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
      const response = await api.patch(`/loans/${candidateId}/status`, { status, reason });
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
      const response = await api.get(`/loans/${candidateId}/history`);
      return { candidateId, history: response.data };
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_HISTORY;
      return rejectWithValue(message);
    }
  }
);

export const fetchStatistics = createAsyncThunk(
  'candidates/fetchStatistics',
  async (countryCode: string | undefined, { rejectWithValue }) => {
    try {
      const url = countryCode
        ? `/loans/statistics?country_code=${countryCode}`
        : '/loans/statistics';
      const response = await api.get(url);
      return response.data as CandidateStatistics;
    } catch (error: unknown) {
      const message =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        ERR_STATS;
      return rejectWithValue(message);
    }
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
      state.filters = initialState.filters;
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
      state.items.unshift(action.payload);
      state.pagination.total += 1;
    },
    statusChanged: (
      state,
      action: PayloadAction<{ loan_id: string; old_status: string; new_status: string }>
    ) => {
      const { loan_id, new_status } = action.payload;
      const index = state.items.findIndex((l) => l.id === loan_id);
      if (index !== -1) {
        state.items[index].status = new_status as CandidateStatus;
      }
      if (state.selectedCandidate?.id === loan_id) {
        state.selectedCandidate.status = new_status as CandidateStatus;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCandidates.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCandidates.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.pagination = {
          total: action.payload.total,
          page: action.payload.page,
          page_size: action.payload.page_size,
          total_pages: action.payload.total_pages,
        };
      })
      .addCase(fetchCandidates.rejected, (state, action) => {
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
        state.items.unshift(action.payload);
        state.pagination.total += 1;
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
        state.loading = true;
      })
      .addCase(fetchStatistics.fulfilled, (state, action) => {
        state.loading = false;
        state.statistics = action.payload;
      })
      .addCase(fetchStatistics.rejected, (state, action) => {
        state.loading = false;
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
} = candidatesSlice.actions;

export default candidatesSlice.reducer;
