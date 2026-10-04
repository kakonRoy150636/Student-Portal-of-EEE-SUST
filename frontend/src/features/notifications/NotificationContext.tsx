import React, { createContext, useContext, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/axios';
import { listenToPush } from '@/lib/pushSession';

export type NotificationRow = { id: number; title: string; body: string; is_read: boolean; created_at: string; data_payload: { url?: string } };
type Snapshot = { items: NotificationRow[]; unread_count: number };
type NotificationState = Snapshot & { loading: boolean; error: boolean; marking: boolean; markError: boolean; markRead: (id?: number) => void };
const NotificationContext = createContext<NotificationState | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const client = useQueryClient();
  const key = ['notifications', user?.id];
  const query = useQuery({ queryKey: key, enabled: Boolean(user),
    queryFn: async () => (await api.get<Snapshot>('/notifications/summary')).data,
    refetchInterval: 30000, retry: false });
  const mark = useMutation({ mutationFn: async (id?: number) => {
    await api.patch(id === undefined ? '/notifications/read-all' : `/notifications/${id}/read`);
  }, onSuccess: () => client.invalidateQueries({ queryKey: key }) });

  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    const userKey = ['notifications', user.id];
    const update = () => { void client.invalidateQueries({ queryKey: userKey }); };
    let unsubscribe = () => {};
    void listenToPush(update).then((stop) => { if (controller.signal.aborted) stop(); else unsubscribe = stop; }).catch(() => {});
    const message = (event: MessageEvent) => { if (event.data?.type === 'PORTAL_NOTIFICATION') update(); };
    navigator.serviceWorker?.addEventListener('message', message);
    const run = async () => {
      while (!controller.signal.aborted) {
        try {
          // Axios fetch adapter streams with Authorization and normal refresh
          // interception; EventSource would force a bearer token into the URL.
          const response = await api.get<ReadableStream<Uint8Array>>('/notifications/stream', {
            adapter: 'fetch', responseType: 'stream', signal: controller.signal, timeout: 0,
          });
          const reader = response.data.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          try {
            while (!controller.signal.aborted) {
              const chunk = await reader.read();
              if (chunk.done) break;
              buffer += decoder.decode(chunk.value, { stream: true });
              let end;
              while ((end = buffer.indexOf('\n\n')) !== -1) {
                const event = buffer.slice(0, end); buffer = buffer.slice(end + 2);
                const data = event.split('\n').find((line) => line.startsWith('data: '));
                if (data && !controller.signal.aborted) client.setQueryData(userKey, JSON.parse(data.slice(6)) as Snapshot);
              }
            }
          } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
        } catch { /* Fallback polling remains live while SSE reconnects. */ }
        if (!controller.signal.aborted) await new Promise<void>((resolve) => {
          const done = () => { clearTimeout(timer); controller.signal.removeEventListener('abort', done); resolve(); };
          const timer = window.setTimeout(done, 3000);
          controller.signal.addEventListener('abort', done, { once: true });
        });
      }
    };
    void run();
    return () => { controller.abort(); unsubscribe(); navigator.serviceWorker?.removeEventListener('message', message); };
  }, [user, client]);

  const snapshot = user ? query.data : undefined;
  return <NotificationContext.Provider value={{ items: snapshot?.items ?? [], unread_count: snapshot?.unread_count ?? 0,
    loading: query.isPending, error: query.isError, marking: mark.isPending, markError: mark.isError,
    markRead: (id) => mark.mutate(id) }}>{children}</NotificationContext.Provider>;
}
export function useNotifications() {
  const value = useContext(NotificationContext);
  if (!value) throw new Error('NotificationProvider required');
  return value;
}
