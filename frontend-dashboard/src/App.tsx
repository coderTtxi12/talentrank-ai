import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const LoansList = lazy(() => import('./pages/LoansList'));
const LoanDetail = lazy(() => import('./pages/LoanDetail'));
const CreateLoan = lazy(() => import('./pages/CreateLoan'));

import Layout from './components/layout/Layout';

const PageLoader = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
  </div>
);

function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Navigate to="/" replace />} />
          <Route path="loans" element={<LoansList />} />
          <Route path="loans/new" element={<CreateLoan />} />
          <Route path="loans/:id" element={<LoanDetail />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
