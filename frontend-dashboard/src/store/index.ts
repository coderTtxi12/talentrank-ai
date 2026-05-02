/**
 * Redux store configuration.
 */
import { configureStore } from '@reduxjs/toolkit';
import candidatesReducer from './slices/candidatesSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    candidates: candidatesReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
  devTools: import.meta.env.DEV,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
