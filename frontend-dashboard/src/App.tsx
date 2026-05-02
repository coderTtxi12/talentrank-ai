import { Routes, Route, Navigate, useParams } from 'react-router-dom';
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const CandidatesList = lazy(() => import('./pages/CandidatesList'));
const CandidateDetail = lazy(() => import('./pages/CandidateDetail'));
const CreateCandidate = lazy(() => import('./pages/CreateCandidate'));

import Layout from './components/layout/Layout';

/** Redirección desde rutas antiguas `/loans/:id`. */
const LegacyLoanDetailRedirect = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/candidates/${id ?? ''}`} replace />;
};

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
          <Route path="candidates" element={<CandidatesList />} />
          <Route path="candidates/new" element={<CreateCandidate />} />
          <Route path="candidates/:id" element={<CandidateDetail />} />
          <Route path="loans" element={<Navigate to="/candidates" replace />} />
          <Route path="loans/new" element={<Navigate to="/candidates/new" replace />} />
          <Route path="loans/:id" element={<LegacyLoanDetailRedirect />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;
