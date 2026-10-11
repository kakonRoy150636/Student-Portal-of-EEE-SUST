import React, { useEffect, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { EmptyState } from '@/components/shared/EmptyState';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getErrorMessage } from '@/lib/errors';
import type {
  CourseOfferingProvidePayload,
  CourseProvisionType,
  Semester,
} from '@/types/academic';

const EMPTY_FORM = {
  courseCode: '',
  courseName: '',
  credits: '',
  courseType: '' as CourseProvisionType | '',
  semesterId: '',
  description: '',
};

type FormState = typeof EMPTY_FORM;

const controlClassName =
  'h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:border-[var(--accent-edge)] disabled:cursor-not-allowed disabled:opacity-50';

export type ProvisioningSemester = Semester & { target_term: string };

const VALID_TERMS = ['1-1', '1-2', '2-1', '2-2', '3-1', '3-2', '4-1', '4-2'];

export function isProvisioningSemester(semester: Semester): semester is ProvisioningSemester {
  return (
    typeof semester.target_term === 'string' &&
    semester.target_term.trim().length > 0
  );
}

export function getProvisioningSemesters(semesters: Semester[]): ProvisioningSemester[] {
  return semesters
    .filter(isProvisioningSemester)
    .sort((a, b) => {
      const indexA = VALID_TERMS.indexOf(a.target_term);
      const indexB = VALID_TERMS.indexOf(b.target_term);
      if (indexA !== -1 && indexB !== -1) return indexA - indexB;
      return a.target_term.localeCompare(b.target_term);
    });
}

export function isCourseProvisionConflict(error: unknown): boolean {
  if (isAxiosError(error)) return error.response?.status === 409;
  if (typeof error !== 'object' || error === null || !('response' in error)) return false;
  const response = (error as { response?: { status?: unknown } }).response;
  return response?.status === 409;
}

function FieldError({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 text-xs text-[var(--danger)]">{children}</p>;
}

export function TeacherCourseOfferingDialog({
  open,
  semesters,
  semestersLoading = false,
  semesterError,
  pending,
  error,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  semesters: Semester[];
  semestersLoading?: boolean;
  semesterError?: unknown;
  pending: boolean;
  error?: unknown;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: CourseOfferingProvidePayload) => void;
}) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [validationError, setValidationError] = useState('');
  const scopedSemesters = useMemo(() => getProvisioningSemesters(semesters), [semesters]);
  const selectedSemester = scopedSemesters.find((semester) => String(semester.id) === form.semesterId);
  const conflict = isCourseProvisionConflict(error);

  useEffect(() => {
    if (!open) {
      setForm(EMPTY_FORM);
      setValidationError('');
    }
  }, [open]);

  const update = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setValidationError('');
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;

    const courseCode = form.courseCode.trim();
    if (!courseCode) {
      setValidationError('Course code is required.');
      return;
    }
    const courseName = form.courseName.trim();
    if (!courseName) {
      setValidationError('Course name is required.');
      return;
    }
    if (!form.credits.trim()) {
      setValidationError('Credits is required.');
      return;
    }
    const creditHours = Number(form.credits);
    const creditIsInHalf = Math.abs(creditHours * 2 - Math.round(creditHours * 2)) < 1e-8;
    if (!Number.isFinite(creditHours) || creditHours < 0.5 || creditHours > 99.5 || !creditIsInHalf) {
      setValidationError('Credits must be between 0.5 and 99.5 in 0.5 increments.');
      return;
    }
    if (!form.courseType) {
      setValidationError('Course type (theory/lab) is required.');
      return;
    }
    if (!selectedSemester) {
      setValidationError(
        scopedSemesters.length > 0
          ? 'Select a semester with a target term.'
          : 'No semester with a target term is available for course provision.',
      );
      return;
    }

    setValidationError('');
    const payload: CourseOfferingProvidePayload = {
      course_code: courseCode,
      title: courseName,
      credit_hours: creditHours,
      course_type: form.courseType,
      semester_id: selectedSemester.id,
    };
    const description = form.description.trim();
    if (description) payload.description = description;
    onSubmit(payload);
  };

  const dialogError = error ? getErrorMessage(
    error,
    conflict
      ? 'A course offering already exists for this course and semester.'
      : 'Please review the course details and try again.',
  ) : '';

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!pending) onOpenChange(nextOpen);
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto" aria-describedby="teacher-offering-summary">
        <DialogHeader>
          <DialogTitle>Offer a course</DialogTitle>
          <p id="teacher-offering-summary" className="mt-2 text-sm text-[var(--text-muted)]">
            Publish a course immediately with no separate admin approval. Enrollment is voluntary; no student or CR is enrolled automatically.
          </p>
        </DialogHeader>

        {Boolean(semesterError) && (
          <div className="mb-4 space-y-1 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-3" role="alert">
            <p className="font-semibold text-[var(--danger)]">Could not load semesters.</p>
            <p className="text-sm text-[var(--danger)]">{getErrorMessage(semesterError, 'Refresh the page and try again.')}</p>
          </div>
        )}

        {!semestersLoading && !semesterError && scopedSemesters.length === 0 && (
          <div className="mb-4">
            <EmptyState
              title="No course-provision semesters"
              description="A semester with a target term is required before you can offer a course. Ask an administrator to configure one, then refresh."
            />
          </div>
        )}
        {semestersLoading && (
          <p role="status" className="mb-4 text-sm text-[var(--text-muted)]">Loading semesters…</p>
        )}

        <form className="space-y-4" noValidate onSubmit={submit}>
          <div>
            <label htmlFor="teacher-offering-course-code" className="mb-1.5 block text-sm font-medium">Course code</label>
            <Input
              id="teacher-offering-course-code"
              value={form.courseCode}
              onChange={(event) => update('courseCode', event.target.value)}
              disabled={pending}
              required
              autoComplete="off"
            />
          </div>

          <div>
            <label htmlFor="teacher-offering-course-name" className="mb-1.5 block text-sm font-medium">Course name</label>
            <Input
              id="teacher-offering-course-name"
              value={form.courseName}
              onChange={(event) => update('courseName', event.target.value)}
              disabled={pending}
              required
              autoComplete="off"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="teacher-offering-credits" className="mb-1.5 block text-sm font-medium">Credits</label>
              <Input
                id="teacher-offering-credits"
                type="number"
                min="0.5"
                max="99.5"
                step="0.5"
                value={form.credits}
                onChange={(event) => update('credits', event.target.value)}
                disabled={pending}
                required
                inputMode="decimal"
              />
              <p className="mt-1 text-xs text-[var(--text-muted)]">Enter 0.5–99.5 credits in 0.5 increments.</p>
            </div>

            <div>
              <label htmlFor="teacher-offering-course-type" className="mb-1.5 block text-sm font-medium">Course type (theory/lab)</label>
              <select
                id="teacher-offering-course-type"
                className={controlClassName}
                value={form.courseType}
                onChange={(event) => update('courseType', event.target.value as CourseProvisionType | '')}
                disabled={pending}
                required
              >
                <option value="">Select type</option>
                <option value="theory">Theory</option>
                <option value="lab">Lab</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="teacher-offering-semester" className="mb-1.5 block text-sm font-medium">Semester</label>
            <select
              id="teacher-offering-semester"
              className={controlClassName}
              aria-describedby="teacher-offering-semester-hint teacher-offering-eligibility"
              value={form.semesterId}
              onChange={(event) => update('semesterId', event.target.value)}
              disabled={pending || semestersLoading || scopedSemesters.length === 0}
              required
            >
              <option value="">Select a semester</option>
              {scopedSemesters.map((semester) => (
                <option key={semester.id} value={semester.id}>
                  {semester.title} — {semester.target_term}
                </option>
              ))}
            </select>
            <p id="teacher-offering-semester-hint" className="mt-1 text-xs text-[var(--text-muted)]">Select the target semester/term for this course offering.</p>
            <p id="teacher-offering-eligibility" aria-live="polite" className="mt-2 text-sm text-[var(--text-muted)]">
              Students and CRs in {selectedSemester ? `target term ${selectedSemester.target_term}` : 'the target term'} or a later valid current term (seniors) can view this course, receive notices, and choose to enroll. Juniors in earlier terms are excluded.
            </p>
          </div>

          <div>
            <label htmlFor="teacher-offering-description" className="mb-1.5 block text-sm font-medium">Description optional</label>
            <textarea
              id="teacher-offering-description"
              className={`${controlClassName} h-auto min-h-24 resize-y`}
              value={form.description}
              onChange={(event) => update('description', event.target.value)}
              disabled={pending}
              rows={3}
            />
          </div>

          {(validationError || Boolean(error)) && (
            <div className="space-y-1 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-3" role="alert">
              {validationError && <FieldError>{validationError}</FieldError>}
              {Boolean(error) && (
                <>
                  <p className="font-semibold text-[var(--danger)]">
                    {conflict ? 'This course is already offered for that semester.' : 'Could not offer this course.'}
                  </p>
                  <p className="text-sm text-[var(--danger)]">{dialogError}</p>
                  <p className="text-sm text-[var(--danger)]">
                    {conflict
                      ? 'Choose a different course code or semester, or refresh the teacher offerings.'
                      : 'Check the required fields and semester, then try again. Your entries are still here.'}
                  </p>
                </>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>Cancel</Button>
            <Button
              type="submit"
              disabled={pending || semestersLoading || scopedSemesters.length === 0}
            >
              {pending ? 'Offering course…' : 'Offer a course'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}