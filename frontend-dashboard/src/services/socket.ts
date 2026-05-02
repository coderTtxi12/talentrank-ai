/**
 * Cliente Socket.IO — conexión al namespace por defecto (/) vía /socket.io.
 * La URL base es solo origen + puerto del API (sin /candidates en la ruta).
 */
import { io, Socket } from 'socket.io-client';

let socket: Socket | null = null;
let isConnected = false;
let lastConnectionTime: Date | null = null;

export const getSocket = (): Socket | null => socket;

export const isSocketConnected = (): boolean =>
  isConnected && socket?.connected === true;

export const getLastConnectionTime = (): Date | null => lastConnectionTime;

/** Origen del API (Engine.IO). En dev: VITE_SOCKET_URL o http://<host>:<VITE_SOCKET_PORT|8000>. */
function getApiOriginForSocket(): string {
  const env = (import.meta.env.VITE_SOCKET_URL as string | undefined)?.trim();
  if (env) return env.replace(/\/$/, '');

  if (import.meta.env.DEV) {
    const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    const port = (import.meta.env.VITE_SOCKET_PORT as string | undefined)?.trim() || '8000';
    return `http://${host}:${port}`;
  }

  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.host}`.replace(/\/$/, '');
  }
  return '';
}

export const connectSocket = (): Socket => {
  if (socket?.connected) {
    return socket;
  }
  if (socket) {
    socket.removeAllListeners();
    socket.disconnect();
    socket = null;
  }

  const fromConfig = getApiOriginForSocket();
  const originResolved = fromConfig || 'http://localhost:8000';
  if (!fromConfig) {
    console.warn(
      '[Socket.IO] Origen deducido vacío → usando fallback',
      originResolved,
      '(ajusta VITE_SOCKET_URL si el API no está ahí)'
    );
  }

  const path = (import.meta.env.VITE_SOCKET_PATH as string | undefined)?.trim() || '/socket.io';

  console.info('[Socket.IO] Conectando', {
    origin: originResolved,
    path,
    pageOrigin: typeof window !== 'undefined' ? window.location.origin : '',
  });

  socket = io(originResolved, {
    path,
    transports: ['polling', 'websocket'],
    reconnection: true,
    reconnectionAttempts: 20,
    reconnectionDelay: 800,
    reconnectionDelayMax: 8000,
    autoConnect: true,
  });

  socket.on('connect', () => {
    isConnected = true;
    lastConnectionTime = new Date();
    console.info('[Socket.IO] Conectado', socket?.id, socket?.io.engine?.transport?.name);
  });

  socket.on('disconnect', (reason) => {
    isConnected = false;
    console.info('[Socket.IO] Desconectado', reason);
  });

  socket.on('connect_error', (err) => {
    isConnected = false;
    console.error('[Socket.IO] connect_error', err?.message || err);
  });

  return socket;
};

export const disconnectSocket = (): void => {
  if (socket) {
    socket.removeAllListeners();
    socket.disconnect();
    socket = null;
  }
  isConnected = false;
};

export const subscribeToCountry = (countryCode: string): void => {
  socket?.emit('subscribe_country', { country_code: countryCode });
};

export const unsubscribeFromCountry = (countryCode: string): void => {
  socket?.emit('unsubscribe_country', { country_code: countryCode });
};

export const subscribeToLoan = (recordId: string): void => {
  socket?.emit('subscribe_loan', { loan_id: recordId });
};

export const unsubscribeFromLoan = (recordId: string): void => {
  socket?.emit('unsubscribe_loan', { loan_id: recordId });
};

export const subscribeToCandidateRoom = subscribeToLoan;
export const unsubscribeFromCandidateRoom = unsubscribeFromLoan;

export default {
  getSocket,
  connectSocket,
  disconnectSocket,
  isSocketConnected,
  getLastConnectionTime,
  subscribeToCountry,
  unsubscribeFromCountry,
  subscribeToLoan,
  unsubscribeFromLoan,
  subscribeToCandidateRoom,
  unsubscribeFromCandidateRoom,
};
