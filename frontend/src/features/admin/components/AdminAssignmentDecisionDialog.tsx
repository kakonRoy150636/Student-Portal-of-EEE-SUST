import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import type { TeacherAssignmentRequest } from '@/types/academic';

export function AdminAssignmentDecisionDialog({
  request,
  decision,
  pending,
  error,
  onOpenChange,
  onApprove,
  onReject,
}: {
  request: TeacherAssignmentRequest | null;
  decision: 'approve' | 'reject' | null;
  pending: boolean;
  error?: string;
  onOpenChange: (open: boolean) => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
}) {
  const [reason, setReason] = useState('');

  useEffect(() => setReason(''), [request, decision]);

  if (!request || !decision) return null;
  const approving = decision === 'approve';

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{approving ? 'Approve teacher assignment?' : 'Reject teacher assignment?'}</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-[var(--text-muted)]">
          {approving
            ? `${request.teacher_name} will be assigned to ${request.course_code} for ${request.semester_title}.`
            : `Provide an optional reason for rejecting ${request.teacher_name}'s request for ${request.course_code}.`}
        </p>
        {!approving && (
          <div className="mt-4">
            <label htmlFor="assignment-rejection-reason" className="mb-1.5 block text-sm font-medium">Rejection reason (optional)</label>
            <textarea
              id="assignment-rejection-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              maxLength={1000}
              rows={4}
              disabled={pending}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:ring-2 focus:ring-[var(--ring)]"
              placeholder="Explain the decision for the teacher (optional)."
            />
            <p className="mt-1 text-xs text-[var(--text-muted)]">{reason.length}/1000</p>
          </div>
        )}
        {error && <p className="mt-3 text-sm text-[var(--danger)]" role="alert">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
          <Button
            variant={approving ? 'default' : 'destructive'}
            onClick={() => approving ? onApprove() : onReject(reason.trim())}
            disabled={pending}
          >
            {pending ? 'Saving…' : approving ? 'Approve request' : 'Reject request'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
