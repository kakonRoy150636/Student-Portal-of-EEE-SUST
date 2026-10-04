import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getErrorMessage } from '@/lib/errors';
import { aiApi, type AICitation } from '../api/aiApi';

type Message = { role: 'assistant' | 'user'; text: string; citations?: AICitation[] };
export const ChatWindow = () => {
  const [msg, setMsg] = useState('');
  const [course, setCourse] = useState('EEE 311');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [remaining, setRemaining] = useState<number | null>(null);
  const [chat, setChat] = useState<Message[]>([
    { role: 'assistant', text: 'Choose your course and ask a question. Answers cite the available syllabus sources; missing information is not guessed.' },
  ]);

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault();
    const question = msg.trim();
    if (!question || busy) return;
    setBusy(true); setError('');
    setChat((prev) => [...prev, { role: 'user', text: question }]);
    setMsg('');
    try {
      const { data } = await aiApi.query(question, course.trim());
      setChat((prev) => [...prev, { role: 'assistant', text: data.answer, citations: data.citations }]);
      setRemaining(data.quota_remaining);
    } catch (failure) {
      setError(getErrorMessage(failure, 'The academic assistant is unavailable. Try again later.'));
      setMsg(question);
    } finally { setBusy(false); }
  };

  return <div className="surface space-y-4 p-4">
    <label className="block max-w-xs text-sm font-medium">Course code
      <Input value={course} onChange={(event) => setCourse(event.target.value)} maxLength={32} disabled={busy} aria-label="Course code" />
    </label>
    <div className="max-h-[32rem] space-y-3 overflow-y-auto" aria-label="Academic assistant conversation" aria-live="polite">
      {chat.map((message, index) => <article key={index} className={`max-w-xl rounded-xl px-4 py-3 text-sm ${message.role === 'user'
        ? 'ml-auto bg-[var(--primary)] text-[var(--primary-fg)]' : 'mr-auto bg-[var(--surface-muted)] text-[var(--text)]'}`}>
        <p className="whitespace-pre-wrap">{message.text}</p>
        {Boolean(message.citations?.length) && <ul className="mt-3 space-y-1 border-t border-[var(--border)] pt-2" aria-label="Sources">
          {message.citations!.map((citation) => <li key={citation.source_id}>
            [{citation.source_id}] {citation.document_name}
            {citation.page_number !== null && ` · page ${citation.page_number}`}
            {citation.section && ` · ${citation.section}`}
          </li>)}
        </ul>}
      </article>)}
    </div>
    {busy && <p role="status" className="text-sm">Searching syllabus sources…</p>}
    {error && <p role="alert" className="text-sm text-[var(--danger)]">{error}</p>}
    {remaining !== null && <p className="text-xs text-[var(--text-muted)]">{remaining} daily questions remaining · resets at midnight Asia/Dhaka</p>}
    <form className="flex gap-2" onSubmit={(event) => void handleSend(event)}>
      <Input value={msg} onChange={(event) => setMsg(event.target.value)} maxLength={1000}
        placeholder="Ask a syllabus question" aria-label="Ask a syllabus question" disabled={busy} required />
      <Button type="submit" size="sm" disabled={busy || !msg.trim() || !course.trim()}>Send</Button>
    </form>
  </div>;
};
