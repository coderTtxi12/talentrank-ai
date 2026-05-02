/**
 * Detalle de candidato e historial de estado.
 */
import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchCandidateById,
  updateCandidateStatus,
  fetchCandidateHistory,
  clearSelectedCandidate,
} from '@/store/slices/candidatesSlice';
import { Card, Button } from '@/components/ui';
import {
  CandidateInfo,
  StatusTimeline,
  StatusChangeModal,
  ConversationHistoryModal,
} from '@/components/candidates';
import type { CandidateStatus, CandidateStatusHistory } from '@/types/candidate';
import {
  DETAIL_TITLE,
  DETAIL_BACK,
  DETAIL_ERROR_LOAD,
  DETAIL_NOT_FOUND,
  DETAIL_NOT_FOUND_DESC,
  DETAIL_CARD_INFO,
  DETAIL_CARD_HISTORY,
  DETAIL_BTN_CHANGE_STATUS,
  DETAIL_BTN_CONVERSATION,
  DETAIL_NAV_SHORT,
} from '@/constants/branding';

const CandidateDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { selectedCandidate, loading, error } = useAppSelector((state) => state.candidates);

  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showConversationModal, setShowConversationModal] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [history, setHistory] = useState<CandidateStatusHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (id) {
      dispatch(fetchCandidateById(id));
    }

    return () => {
      dispatch(clearSelectedCandidate());
    };
  }, [dispatch, id]);

  useEffect(() => {
    const loadHistory = async () => {
      if (id) {
        setHistoryLoading(true);
        try {
          const result = await dispatch(fetchCandidateHistory(id)).unwrap();
          setHistory(result.history || []);
        } catch {
          setHistory([]);
        } finally {
          setHistoryLoading(false);
        }
      }
    };
    loadHistory();
  }, [dispatch, id, selectedCandidate?.status]);

  const handleStatusChange = async (newStatus: CandidateStatus, reason: string) => {
    if (!id) return;

    setStatusLoading(true);
    try {
      await dispatch(updateCandidateStatus({ candidateId: id, status: newStatus, reason })).unwrap();
      setShowStatusModal(false);
      const result = await dispatch(fetchCandidateHistory(id)).unwrap();
      setHistory(result.history || []);
    } finally {
      setStatusLoading(false);
    }
  };

  if (loading && !selectedCandidate) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">❌</div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{DETAIL_ERROR_LOAD}</h2>
        <p className="text-gray-600 mb-4">{error}</p>
        <Button onClick={() => navigate('/candidates')}>{DETAIL_NAV_SHORT}</Button>
      </div>
    );
  }

  if (!selectedCandidate) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">🔍</div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">{DETAIL_NOT_FOUND}</h2>
        <p className="text-gray-600 mb-4">{DETAIL_NOT_FOUND_DESC}</p>
        <Button onClick={() => navigate('/candidates')}>{DETAIL_NAV_SHORT}</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link
              to="/candidates"
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              {DETAIL_BACK}
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{DETAIL_TITLE}</h1>
          <p className="text-gray-600 font-mono text-sm">{selectedCandidate.id}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <Button variant="secondary" onClick={() => setShowConversationModal(true)}>
            {DETAIL_BTN_CONVERSATION}
          </Button>
          <Button onClick={() => setShowStatusModal(true)}>
            {DETAIL_BTN_CHANGE_STATUS}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card title={DETAIL_CARD_INFO}>
            <CandidateInfo candidate={selectedCandidate} />
          </Card>
        </div>

        <div>
          <Card title={DETAIL_CARD_HISTORY}>
            <StatusTimeline history={history} loading={historyLoading} />
          </Card>
        </div>
      </div>

      <StatusChangeModal
        isOpen={showStatusModal}
        onClose={() => setShowStatusModal(false)}
        onConfirm={handleStatusChange}
        currentStatus={selectedCandidate.status}
        loading={statusLoading}
      />

      <ConversationHistoryModal
        isOpen={showConversationModal}
        onClose={() => setShowConversationModal(false)}
        candidateId={selectedCandidate.id}
      />
    </div>
  );
};

export default CandidateDetail;
