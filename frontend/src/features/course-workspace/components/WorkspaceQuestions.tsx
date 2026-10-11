import React, { useState } from 'react';
import { MessageCircleQuestion } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import { useCourseAnnouncementMutations, useCourseQuestions } from '../hooks/useCourseWorkspace';

const controlClassName = 'h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]';

export function WorkspaceQuestions({ offeringId, manager }: { offeringId: string; manager: boolean }) {
  const query = useCourseQuestions(offeringId);
  const mutations = useCourseAnnouncementMutations(offeringId);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [answering, setAnswering] = useState<string | null>(null);
  const [answer, setAnswer] = useState('');

  const ask = (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim() || !body.trim()) return;
    mutations.createQuestion.mutate({ title: title.trim(), body: body.trim(), visibility: 'course' }, { onSuccess: () => { setTitle(''); setBody(''); } });
  };

  const submitAnswer = (questionId: string) => {
    if (!answer.trim()) return;
    mutations.answerQuestion.mutate({ questionId, payload: { answer_body: answer.trim(), status: 'answered' } }, { onSuccess: () => { setAnswer(''); setAnswering(null); } });
  };

  return (
    <section id="workspace-panel-questions" role="tabpanel" aria-labelledby="workspace-tab-questions" className="space-y-4">
      <div><p className="kicker">Course help</p><h2 className="mt-1 font-display text-lg font-semibold">Questions</h2><p className="mt-1 text-sm text-[var(--text-muted)]">Ask the teaching team and keep answers in the course workspace.</p></div>
      {!manager && <Card><CardHeader><CardTitle>Ask a question</CardTitle></CardHeader><CardContent><form className="space-y-3" onSubmit={ask}><input className={controlClassName} aria-label="Question title" placeholder="Short question title" value={title} onChange={(event) => setTitle(event.target.value)} required /><textarea className="min-h-28 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-3 text-sm" aria-label="Question body" placeholder="Describe what you need help with" value={body} onChange={(event) => setBody(event.target.value)} required />{mutations.createQuestion.isError && <p className="text-sm text-[var(--danger)]" role="alert">{getErrorMessage(mutations.createQuestion.error, 'Could not submit your question.')}</p>}<div className="flex justify-end"><Button type="submit" disabled={mutations.createQuestion.isPending}><MessageCircleQuestion className="h-4 w-4" aria-hidden="true" />{mutations.createQuestion.isPending ? 'Submitting…' : 'Submit question'}</Button></div></form></CardContent></Card>}
      {query.isPending && <PageSkeleton cards={0} rows={4} />}
      {query.isError && <div className="space-y-3 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert"><p className="font-semibold text-[var(--danger)]">Could not load questions.</p><p className="text-sm text-[var(--danger)]">{getErrorMessage(query.error, 'Please retry when connected.')}</p><Button variant="outline" onClick={() => void query.refetch()}>Try again</Button></div>}
      {!query.isPending && !query.isError && (query.data ?? []).length === 0 && <EmptyState title="No questions yet" description={manager ? 'Student questions will appear here.' : 'Your submitted questions and teacher answers will appear here.'} />}
      {!query.isPending && !query.isError && (query.data ?? []).length > 0 && <div className="space-y-3">{(query.data ?? []).map((item) => <Card key={item.id}><CardContent className="space-y-3 p-4"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{item.title}</h3><Badge variant={item.status === 'open' ? 'secondary' : 'success'}>{item.status}</Badge><Badge variant="outline">{item.visibility}</Badge></div><p className="whitespace-pre-wrap text-sm text-[var(--text-muted)]">{item.body}</p><p className="text-xs text-[var(--text-subtle)]">Asked by {item.student_name} · {new Date(item.created_at).toLocaleString()}</p>{item.answer_body && <div className="rounded-lg border border-[var(--accent-edge)] bg-[var(--accent-soft)]/20 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">Teacher answer</p><p className="mt-1 whitespace-pre-wrap text-sm">{item.answer_body}</p></div>}{manager && item.can_answer && (answering === item.id ? <div className="space-y-2"><textarea className="min-h-24 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-3 text-sm" aria-label={`Answer ${item.title}`} value={answer} onChange={(event) => setAnswer(event.target.value)} /><div className="flex gap-2"><Button size="sm" onClick={() => submitAnswer(item.id)} disabled={mutations.answerQuestion.isPending}>Answer</Button><Button size="sm" variant="outline" onClick={() => { setAnswering(null); setAnswer(''); }}>Cancel</Button></div></div> : <Button size="sm" variant="outline" onClick={() => setAnswering(item.id)}>Answer question</Button>)}</CardContent></Card>)}</div>}
    </section>
  );
}
