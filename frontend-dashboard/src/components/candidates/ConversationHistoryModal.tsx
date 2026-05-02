/**
 * Modal con transcripción paginada del chat de screening.
 */
import { useCallback, useEffect, useState } from 'react';
import clsx from 'clsx';
import { api } from '@/services/api';
import type { ConversationMessage, ConversationMessagesResponse } from '@/types/candidate';
import { Modal, Button } from '@/components/ui';
import {
  DETAIL_CONVERSATION_TITLE,
  DETAIL_CONVERSATION_EMPTY,
  DETAIL_CONVERSATION_LOAD_MORE,
  DETAIL_CONVERSATION_LOADING,
  DETAIL_CONVERSATION_ROLE_USER,
  DETAIL_CONVERSATION_ROLE_ASSISTANT,
  ERR_CONVERSATION,
} from '@/constants/branding';

const PAGE_SIZE = 40;

function formatMessageTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface ConversationHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateId: string;
}

const ConversationHistoryModal = ({
  isOpen,
  onClose,
  candidateId,
}: ConversationHistoryModalProps) => {
  const [items, setItems] = useState<ConversationMessage[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPage = useCallback(
    async (cursor: string | null, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set('limit', String(PAGE_SIZE));
        if (cursor) params.set('cursor', cursor);
        const { data } = await api.get<ConversationMessagesResponse>(
          `/candidates/${encodeURIComponent(candidateId)}/conversation/messages?${params}`
        );
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
        setNextCursor(data.next_cursor ?? null);
        setError(null);
      } catch {
        setError(ERR_CONVERSATION);
        if (!append) {
          setItems([]);
          setNextCursor(null);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [candidateId]
  );

  useEffect(() => {
    if (!isOpen || !candidateId) return;
    setItems([]);
    setNextCursor(null);
    setError(null);
    void fetchPage(null, false);
  }, [isOpen, candidateId, fetchPage]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={DETAIL_CONVERSATION_TITLE} size="xl">
      <div className="space-y-4">
        {loading && items.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-8">{DETAIL_CONVERSATION_LOADING}</p>
        )}
        {error && items.length === 0 && (
          <p className="text-sm text-red-600 text-center py-6">{error}</p>
        )}
        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-8">{DETAIL_CONVERSATION_EMPTY}</p>
        )}
        {items.length > 0 && (
          <div className="space-y-3 max-h-[65vh] overflow-y-auto pr-1 -mx-2 px-2">
            {items.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={msg.id}
                  className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}
                >
                  <div
                    className={clsx(
                      'max-w-[85%] rounded-lg px-4 py-2 text-sm shadow-sm',
                      isUser
                        ? 'bg-primary-600 text-white rounded-br-none'
                        : 'bg-gray-100 text-gray-900 rounded-bl-none border border-gray-200'
                    )}
                  >
                    <div
                      className={clsx(
                        'text-xs mb-1 opacity-90',
                        isUser ? 'text-primary-100' : 'text-gray-500'
                      )}
                    >
                      {isUser ? DETAIL_CONVERSATION_ROLE_USER : DETAIL_CONVERSATION_ROLE_ASSISTANT}{' '}
                      · {formatMessageTime(msg.created_at)}
                    </div>
                    <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        {error && items.length > 0 && (
          <p className="text-sm text-red-600">{error}</p>
        )}
        {nextCursor && (
          <Button
            variant="secondary"
            fullWidth
            loading={loadingMore}
            onClick={() => void fetchPage(nextCursor, true)}
          >
            {DETAIL_CONVERSATION_LOAD_MORE}
          </Button>
        )}
      </div>
    </Modal>
  );
};

export default ConversationHistoryModal;
