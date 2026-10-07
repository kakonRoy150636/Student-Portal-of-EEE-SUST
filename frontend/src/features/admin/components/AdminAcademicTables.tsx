import React from 'react';
import { DataTable } from '@/components/shared/DataTable';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { Button } from '@/components/ui/button';
import type { CourseOffering, TeacherAssignmentRequest } from '@/types/academic';

export function AdminCourseOfferingTable({
  offerings,
  busyOfferingId,
  onEdit,
  onTogglePublication,
}: {
  offerings: CourseOffering[];
  busyOfferingId: string | null;
  onEdit: (offering: CourseOffering) => void;
  onTogglePublication: (offering: CourseOffering) => void;
}) {
  return (
    <DataTable
      data={offerings}
      emptyMessage="No course offerings have been created yet."
      columns={[
        {
          header: 'Course',
          cell: (offering) => (
            <div className="min-w-40">
              <p className="font-mono text-sm font-semibold">{offering.course_code}</p>
              <p className="mt-1 font-medium">{offering.course_title}</p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">{offering.credit_hours} credits · {offering.course_type}</p>
            </div>
          ),
        },
        { header: 'Semester', cell: (offering) => offering.semester_title },
        {
          header: 'Teachers',
          cell: (offering) => offering.assigned_teachers.length
            ? offering.assigned_teachers.map((teacher) => teacher.teacher_name).join(', ')
            : <span className="text-[var(--text-muted)]">Unassigned</span>,
        },
        { header: 'Status', cell: (offering) => <StatusBadge status={offering.publication_status} /> },
        {
          header: 'Actions',
          cell: (offering) => {
            const busy = busyOfferingId === offering.id;
            return (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => onEdit(offering)} disabled={busyOfferingId !== null}>
                  Edit
                </Button>
                <Button
                  size="sm"
                  variant={offering.publication_status === 'published' ? 'destructive' : 'default'}
                  onClick={() => onTogglePublication(offering)}
                  disabled={busyOfferingId !== null}
                  aria-label={`${offering.publication_status === 'published' ? 'Unpublish' : 'Publish'} ${offering.course_code}`}
                >
                  {busy ? 'Updating…' : offering.publication_status === 'published' ? 'Unpublish' : 'Publish'}
                </Button>
              </div>
            );
          },
        },
      ]}
    />
  );
}

export function AdminAssignmentRequestTable({
  requests,
  busyRequestId,
  onApprove,
  onReject,
}: {
  requests: TeacherAssignmentRequest[];
  busyRequestId: string | null;
  onApprove: (request: TeacherAssignmentRequest) => void;
  onReject: (request: TeacherAssignmentRequest) => void;
}) {
  return (
    <DataTable
      data={requests}
      emptyMessage="No assignment requests match this status."
      columns={[
        {
          header: 'Teacher',
          cell: (request) => (
            <div className="min-w-36">
              <p className="font-medium">{request.teacher_name}</p>
              <p className="text-xs text-[var(--text-muted)]">{request.course_code} · {request.course_title}</p>
            </div>
          ),
        },
        { header: 'Semester', accessorKey: 'semester_title' },
        { header: 'Status', cell: (request) => <StatusBadge status={request.status} /> },
        {
          header: 'Decision',
          cell: (request) => request.status === 'pending' ? (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={() => onApprove(request)}
                disabled={busyRequestId !== null}
                aria-label={`Approve ${request.teacher_name} for ${request.course_code}`}
              >
                {busyRequestId === request.id ? 'Working…' : 'Approve'}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onReject(request)}
                disabled={busyRequestId !== null}
                aria-label={`Reject ${request.teacher_name} for ${request.course_code}`}
              >
                Reject
              </Button>
            </div>
          ) : request.rejection_reason ? (
            <span className="max-w-48 text-xs text-[var(--text-muted)]">{request.rejection_reason}</span>
          ) : (
            <span className="text-xs text-[var(--text-muted)]">Decision recorded</span>
          ),
        },
      ]}
    />
  );
}
