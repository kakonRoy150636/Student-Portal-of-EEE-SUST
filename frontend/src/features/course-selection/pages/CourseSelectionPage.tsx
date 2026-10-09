import React, { useId, useState } from 'react';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getErrorMessage } from '@/lib/errors';
import { CourseSelectionTable, type CourseSelectionRow } from '../components/CourseSelectionTable';
import { isOfferingSelectable, isSelectionConflict, useCourseSelection, type SelectionAction } from '../hooks/useCourseSelection';

const successMessages: Record<SelectionAction, string> = {
  select: 'Course selected.', drop: 'Course dropped.', reselect: 'Course reselected.',
};

export default function CourseSelectionPage() {
  const { query, mutation } = useCourseSelection();
  const [dropTarget, setDropTarget] = useState<CourseSelectionRow | null>(null);
  const dropDescriptionId = useId();
  const snapshot = query.data;
  const semesters = snapshot?.semesters.filter((semester) => semester.is_active) ?? [];
  const enrollments = new Map(snapshot?.enrollments.map((enrollment) => [enrollment.course_offering_id, enrollment]));
  const rows: CourseSelectionRow[] = (snapshot?.offerings ?? []).map((offering) => ({
    id: offering.id,
    course_code: offering.course_code,
    course_title: offering.course_title,
    credit_hours: offering.credit_hours,
    semester_title: offering.semester_title,
    offering,
    enrollment: enrollments.get(offering.id),
    selectable: isOfferingSelectable(offering, semesters),
  }));
  const offeredIds = new Set(rows.map((row) => row.id));
  for (const enrollment of enrollments.values()) {
    if (!offeredIds.has(enrollment.course_offering_id)) rows.push({
      ...enrollment, id: enrollment.course_offering_id, enrollment, selectable: false,
    });
  }
  const disabled = query.isFetching || query.isError || mutation.isPending;
  const act = (action: SelectionAction, row: CourseSelectionRow) => {
    if (disabled || !row.selectable) return;
    if (action === 'drop') { mutation.reset(); setDropTarget(row); }
    else mutation.mutate({ action, offeringId: row.id });
  };
  const refresh = () => { mutation.reset(); void query.refetch(); };

  return <div className="space-y-6">
    <PageHeader kicker="Academic" title="Course selection"
      description="Select published courses for your semester, manage your enrollments, and review your active credits."
      action={<Button variant="outline" onClick={refresh} disabled={query.isFetching || mutation.isPending}>
        {query.isFetching && !query.isPending ? 'Refreshing…' : 'Refresh'}
      </Button>} />

    {mutation.isError && <div role="alert" className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4 text-sm text-[var(--danger)]">
      <p className="font-semibold">{isSelectionConflict(mutation.error) ? 'Course selection conflict' : 'Could not update course selection'}</p>
      <p className="mt-1">{getErrorMessage(mutation.error, 'Please try again.')}</p>
      {isSelectionConflict(mutation.error) && <p className="mt-1">Review the refreshed course list before trying again.</p>}
    </div>}
    {mutation.isPending && <p role="status" className="text-sm text-[var(--text-muted)]">Updating course selection…</p>}
    {mutation.isSuccess && <p role="status" className="text-sm text-[var(--success)]">
      {successMessages[mutation.variables.action]}
    </p>}

    {query.isPending && <PageSkeleton cards={2} rows={3} />}
    {query.isError && <div role="alert" className="surface space-y-3 p-5">
      <p className="font-semibold text-[var(--danger)]">Could not load course selection.</p>
      <p className="text-sm text-[var(--text-muted)]">{getErrorMessage(query.error, 'Please retry when connected.')}</p>
      <Button variant="outline" onClick={refresh} disabled={query.isFetching}>Try again</Button>
    </div>}

    {!query.isPending && !query.isError && snapshot && <>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Your semester</CardTitle></CardHeader>
          <CardContent>
            {semesters.length > 0 ? <ul className="space-y-2">
              {semesters.map((semester) => <li key={semester.id} className="font-medium">{semester.title}</li>)}
            </ul> : <p className="text-sm text-[var(--text-muted)]">No active semester for your semester selection.</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Total active credits</CardTitle></CardHeader>
          <CardContent>
            <p className="font-mono text-3xl font-semibold tabular-nums" aria-label={`Total active credits: ${snapshot.activeCreditTotal}`}>
              {snapshot.activeCreditTotal}
            </p>
            <p className="mt-2 text-sm text-[var(--text-muted)]">Reported by the server for active enrollments; dropped courses are excluded.</p>
          </CardContent>
        </Card>
      </div>
      {!(snapshot.offerings.some((offering) => isOfferingSelectable(offering, semesters))) && <EmptyState
        title={semesters.length ? 'No courses published' : 'No active semester'}
        description={semesters.length ? 'Course offerings for your semester will appear here after they are published.' : 'Course selection will be available when your semester is active and its offerings are published.'} />}
      {rows.length > 0 && <Card>
        <CardHeader>
          <CardTitle>Course offerings and your enrollments</CardTitle>
          <p className="text-sm text-[var(--text-muted)]">Previous or unpublished enrollments remain visible for reference.</p>
        </CardHeader>
        <CardContent className="p-0">
          <CourseSelectionTable rows={rows} disabled={disabled}
            pending={mutation.isPending ? mutation.variables : undefined} onAction={act} />
        </CardContent>
      </Card>}
    </>}

    <Dialog open={Boolean(dropTarget)} onOpenChange={(open) => { if (!open) setDropTarget(null); }}>
      <DialogContent aria-describedby={dropDescriptionId}>
        <DialogHeader><DialogTitle>Drop {dropTarget?.course_code}?</DialogTitle></DialogHeader>
        <p id={dropDescriptionId} className="text-sm text-[var(--text-muted)]">
          {dropTarget?.course_title} will no longer count toward your active credits. You can reselect it while the offering is published in an active semester.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDropTarget(null)}>Cancel</Button>
          <Button variant="destructive" disabled={disabled || !dropTarget} onClick={() => {
            if (dropTarget) { mutation.mutate({ action: 'drop', offeringId: dropTarget.id }); setDropTarget(null); }
          }}>Confirm drop</Button>
        </div>
      </DialogContent>
    </Dialog>
  </div>;
}
