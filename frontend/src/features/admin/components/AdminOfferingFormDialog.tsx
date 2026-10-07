import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import type {
  CourseCatalogueItem,
  CourseOffering,
  CourseOfferingCreatePayload,
  Semester,
} from '@/types/academic';

export function AdminOfferingFormDialog({
  open,
  offering,
  courses,
  semesters,
  pending,
  error,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  offering: CourseOffering | null;
  courses: CourseCatalogueItem[];
  semesters: Semester[];
  pending: boolean;
  error?: string;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: CourseOfferingCreatePayload) => void;
}) {
  const [courseId, setCourseId] = useState('');
  const [semesterId, setSemesterId] = useState('');
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    setCourseId(offering?.course_id ?? '');
    setSemesterId(offering ? String(offering.semester_id) : '');
    setValidationError('');
  }, [offering, open]);

  const editing = Boolean(offering);
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!courseId || !semesterId) {
      setValidationError('Select both a course and a semester.');
      return;
    }
    setValidationError('');
    onSubmit({ course_id: courseId, semester_id: Number(semesterId) });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? 'Edit course offering' : 'Create course offering'}</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={submit}>
          <div>
            <label htmlFor="admin-offering-course" className="mb-1.5 block text-sm font-medium">Course</label>
            <select
              id="admin-offering-course"
              className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)]"
              value={courseId}
              onChange={(event) => setCourseId(event.target.value)}
              disabled={pending}
            >
              <option value="">Select a course</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.course_code} — {course.title} ({course.credits} credits)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="admin-offering-semester" className="mb-1.5 block text-sm font-medium">Semester</label>
            <select
              id="admin-offering-semester"
              className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)]"
              value={semesterId}
              onChange={(event) => setSemesterId(event.target.value)}
              disabled={pending}
            >
              <option value="">Select a semester</option>
              {semesters.map((semester) => (
                <option key={semester.id} value={semester.id}>
                  {semester.title}{semester.is_active ? ' (active)' : ''}
                </option>
              ))}
            </select>
            {semesters.length === 0 && <p className="mt-1 text-xs text-[var(--text-muted)]">No active semesters are available.</p>}
          </div>
          {(validationError || error) && (
            <p className="text-sm text-[var(--danger)]" role="alert">{validationError || error}</p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
            <Button type="submit" disabled={pending || courses.length === 0 || semesters.length === 0}>
              {pending ? (editing ? 'Saving…' : 'Creating…') : (editing ? 'Save changes' : 'Create offering')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
