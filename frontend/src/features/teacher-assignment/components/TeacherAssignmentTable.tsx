import React from 'react';
import { DataTable } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type {
  CourseOffering,
  RosterEntry,
  TeacherAssignmentRequest,
  TeacherAssignmentRequestStatus,
} from '@/types/academic';

export type TeacherAssignmentRow = CourseOffering & {
  ownStatus: TeacherAssignmentRequestStatus | null;
  ownRequest?: TeacherAssignmentRequest;
  isAssigned: boolean;
};

export type RosterRow = RosterEntry & { id: string };

export function TeacherAssignmentTable({
  rows,
  pendingOfferingId,
  onRequest,
  onRoster,
}: {
  rows: TeacherAssignmentRow[];
  pendingOfferingId: string | null;
  onRequest: (offeringId: string) => void;
  onRoster: (offeringId: string) => void;
}) {
  return (
    <DataTable
      data={rows}
      emptyMessage="No course offerings are available."
      columns={[
        {
          header: 'Course',
          cell: (row) => (
            <div className="min-w-40">
              <p className="font-mono text-sm font-semibold">{row.course_code}</p>
              <p className="mt-1 font-medium">{row.course_title}</p>
              <p className="mt-1 text-xs capitalize text-[var(--text-muted)]">{row.course_type}</p>
            </div>
          ),
        },
        {
          header: 'Credit',
          cell: (row) => <span className="tabular-nums">{row.credit_hours}</span>,
        },
        {
          header: 'Semester',
          cell: (row) => (
            <div className="min-w-32 space-y-1">
              <p>{row.semester_title}</p>
              <div className="flex flex-wrap gap-1">
                <StatusBadge status={row.publication_status} />
                {!row.semester_is_active && <Badge variant="secondary">Inactive semester</Badge>}
              </div>
            </div>
          ),
        },
        {
          header: 'Assigned teachers',
          cell: (row) => (
            <div className="min-w-44">
              {row.assigned_teachers.length > 0 ? (
                <ul className="space-y-1">
                  {row.assigned_teachers.map((teacher) => (
                    <li key={`${row.id}-${teacher.teacher_id}`}>
                      <span className="font-medium">{teacher.teacher_name}</span>
                      <span className="ml-1 text-xs text-[var(--text-muted)]">({teacher.role.replace(/_/g, ' ')})</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <span className="text-[var(--text-muted)]">No teachers assigned</span>
              )}
            </div>
          ),
        },
        {
          header: 'Your request',
          cell: (row) => (
            <div className="min-w-28 space-y-1">
              {row.ownStatus ? <StatusBadge status={row.ownStatus} /> : <Badge variant="outline">Not requested</Badge>}
              {row.ownStatus === 'rejected' && row.ownRequest?.rejection_reason && (
                <p className="max-w-48 text-xs text-[var(--text-muted)]">{row.ownRequest.rejection_reason}</p>
              )}
            </div>
          ),
        },
        {
          header: 'Action',
          cell: (row) => {
            const canViewRoster = row.ownStatus === 'approved' || row.isAssigned;
            const isPending = pendingOfferingId === row.id;
            if (canViewRoster) {
              return (
                <Button size="sm" variant="outline" onClick={() => onRoster(row.id)}>
                  View roster
                </Button>
              );
            }
            if (row.ownStatus) {
              return <span className="text-xs text-[var(--text-muted)]">No further action</span>;
            }
            return (
              <Button
                size="sm"
                onClick={() => onRequest(row.id)}
                disabled={pendingOfferingId !== null}
                aria-label={`Request assignment for ${row.course_code}`}
              >
                {isPending ? 'Requesting…' : 'Request assignment'}
              </Button>
            );
          },
        },
      ]}
    />
  );
}

export function TeacherRosterTable({ rows }: { rows: RosterRow[] }) {
  return (
    <DataTable
      data={rows}
      emptyMessage="No enrolled students are in this roster yet."
      columns={[
        {
          header: 'Student',
          cell: (row) => (
            <div>
              <p className="font-medium">{row.full_name}</p>
              <p className="font-mono text-xs text-[var(--text-muted)]">{row.identifier}</p>
            </div>
          ),
        },
        { header: 'Email', accessorKey: 'email' },
        { header: 'Status', cell: (row) => <StatusBadge status={row.status} /> },
        { header: 'Credit', cell: (row) => <span className="tabular-nums">{row.credit_hours}</span> },
      ]}
    />
  );
}
