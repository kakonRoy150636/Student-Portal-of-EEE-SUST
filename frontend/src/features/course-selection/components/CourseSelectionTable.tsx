import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { CourseEnrollment, CourseOffering, EnrollmentStatus } from '@/types/academic';
import type { SelectionAction, SelectionMutation } from '../hooks/useCourseSelection';

export interface CourseSelectionRow {
  id: string;
  course_code: string;
  course_title: string;
  credit_hours: number;
  semester_title: string;
  offering?: CourseOffering;
  enrollment?: CourseEnrollment;
  selectable: boolean;
}

const labels: Record<EnrollmentStatus, string> = {
  enrolled: 'Enrolled', main: 'Main', improvement: 'Improvement', drop: 'Dropped',
};
const actions: Record<SelectionAction, string> = { select: 'Select', drop: 'Drop', reselect: 'Reselect' };
const pendingLabels: Record<SelectionAction, string> = {
  select: 'Selecting…', drop: 'Dropping…', reselect: 'Reselecting…',
};

export function CourseSelectionTable({ rows, disabled, pending, onAction }: {
  rows: CourseSelectionRow[];
  disabled: boolean;
  pending?: SelectionMutation;
  onAction: (action: SelectionAction, row: CourseSelectionRow) => void;
}) {
  return <Table className="block md:table" aria-label="Course offerings and enrollment states">
    <TableHeader className="hidden md:table-header-group">
      <TableRow>
        <TableHead>Course</TableHead><TableHead>Credits</TableHead><TableHead>Assigned teacher</TableHead>
        <TableHead>Enrollment</TableHead><TableHead>Action</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody className="block md:table-row-group">
      {rows.map((row) => {
        const action: SelectionAction = !row.enrollment ? 'select' : row.enrollment.status === 'drop' ? 'reselect' : 'drop';
        const busy = pending?.offeringId === row.id && pending.action === action;
        return <TableRow key={row.id} className="grid grid-cols-2 gap-4 p-4 md:table-row md:p-0">
          <TableCell className="col-span-2 block min-w-0 p-0 md:table-cell md:p-4">
            <p className="font-mono text-sm font-semibold">{row.course_code}</p>
            <p className="mt-1 break-words font-medium">{row.course_title}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">{row.semester_title}</p>
          </TableCell>
          <TableCell className="block p-0 md:table-cell md:p-4">
            <span className="mb-1 block text-xs text-[var(--text-muted)] md:hidden">Credits</span>
            <span className="tabular-nums">{row.credit_hours}</span>
          </TableCell>
          <TableCell className="block min-w-0 p-0 md:table-cell md:max-w-xs md:p-4">
            <span className="mb-1 block text-xs text-[var(--text-muted)] md:hidden">Assigned teacher</span>
            {row.offering ? (row.offering.assigned_teachers.map((teacher) => teacher.teacher_name).join(', ') || 'Not assigned yet') : 'Unavailable'}
          </TableCell>
          <TableCell className="block p-0 md:table-cell md:p-4">
            <span className="mb-1 block text-xs text-[var(--text-muted)] md:hidden">Enrollment</span>
            <Badge variant={!row.enrollment || row.enrollment.status === 'drop' ? 'secondary' : 'success'}>
              {row.enrollment ? labels[row.enrollment.status] : 'Not selected'}
            </Badge>
          </TableCell>
          <TableCell className="block p-0 md:table-cell md:p-4">
            <Button size="sm" variant={action === 'drop' ? 'outline' : 'default'}
              className="w-full md:w-auto" disabled={disabled || !row.selectable}
              aria-label={`${actions[action]} ${row.course_code}`} onClick={() => onAction(action, row)}>
              {busy ? pendingLabels[action] : actions[action]}
            </Button>
            {!row.selectable && <p className="mt-2 max-w-xs text-xs text-[var(--text-muted)]">
              Unavailable: only published offerings in an active semester can be changed.
            </p>}
          </TableCell>
        </TableRow>;
      })}
    </TableBody>
  </Table>;
}
