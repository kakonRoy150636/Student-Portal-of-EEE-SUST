import React, { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { aiApi, type AICitation } from '../api/aiApi';

interface Turn {
  role: 'student' | 'assistant';
  content: string;
  citations?: AICitation[];
  grounded?: boolean;
  mode?: string;
}

const INTRO =
  'Ask a syllabus, circuit or lab question. I answer from material indexed for the ' +
  'department and show which documents I used.';

export const ChatWindow = () => {
  const qc = useQueryClient();
  const [msg, setMsg] = useState('');
  const [turns, setTurns] = useState<Turn[]>([{ role: 'assistant', content: INTRO }]);
  const endRef = useRef<HTMLDivElement>(null);

  // The exchange is persisted server-side, so a reload keeps the thread.
  const history = useQuery({
    queryKey: ['ai', 'history'],
    queryFn: async () => (await aiApi.history()).data,
    retry: false,
  });

  useEffect(() => {
    if (!history.data?.length) return;
    setTurns([
      { role: 'assistant', content: INTRO },
      ...history.data.map((row) => ({
        role: row.role === 'student' ? ('student' as const) : ('assistant' as const),
        content: row.content,
      })),
    ]);
  }, [history.data]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [turns]);

  const ask = useMutation({
    mutationFn: (prompt: string) => aiApi.query(prompt),
    onSuccess: async ({ data }) => {
      setTurns((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
          grounded: data.grounded,
          mode: data.mode,
        },
      ]);
      await qc.invalidateQueries({ queryKey: ['ai', 'history'] });
    },
    onError: () => {
      setTurns((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'The assistant could not be reached. Your question was not answered — please try again.',
        },
      ]);
    },
  });

  const handleSend = () => {
    const prompt = msg.trim();
    if (!prompt || ask.isPending) return;
    setTurns((prev) => [...prev, { role: 'student', content: prompt }]);
    setMsg('');
    ask.mutate(prompt);
  };

  return (
    <div className="surface space-y-3 p-4">
      <div className="max-h-96 space-y-3 overflow-y-auto" aria-live="polite">
        {turns.map((turn, index) => (
          <div
            key={index}
            className={`max-w-prose rounded-xl px-3 py-2 text-sm ${
              turn.role === 'student'
                ? 'ml-auto bg-[var(--primary)] text-[var(--primary-fg)]'
                : 'mr-auto bg-[var(--surface-muted)] text-[var(--text)]'
            }`}
          >
            <p className="whitespace-pre-wrap">{turn.content}</p>
            {turn.citations && turn.citations.length > 0 && (
              <ul className="mt-2 space-y-1 border-t border-[var(--border)] pt-2 text-xs text-[var(--text-muted)]">
                {turn.citations.map((citation) => (
                  <li key={`${citation.document_title}-${citation.snippet.slice(0, 16)}`} className="flex items-start gap-1">
                    <BookOpen className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
                    <span>
                      <span className="font-medium">{citation.document_title}</span>
                      {citation.course_code ? ` · ${citation.course_code}` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {turn.role === 'assistant' && turn.grounded === false && turn.mode === 'extractive' && (
              <Badge variant="outline" className="mt-2">From the course library</Badge>
            )}
          </div>
        ))}
        {ask.isPending && (
          <p className="mr-auto text-xs text-[var(--text-muted)]">Searching the course library…</p>
        )}
        <div ref={endRef} />
      </div>
      <div className="flex gap-2">
        <Input
          value={msg}
          onChange={(event) => setMsg(event.target.value)}
          placeholder="Ask a syllabus question"
          aria-label="Ask a syllabus question"
          maxLength={1000}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              handleSend();
            }
          }}
        />
        <Button size="sm" onClick={handleSend} disabled={ask.isPending || !msg.trim()}>
          <Send className="mr-1 h-3.5 w-3.5" aria-hidden="true" /> Send
        </Button>
      </div>
    </div>
  );
};
