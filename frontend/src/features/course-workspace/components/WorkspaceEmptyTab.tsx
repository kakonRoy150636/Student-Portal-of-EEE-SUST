import React from 'react';
import { Link } from 'react-router-dom';
import { EmptyState } from '@/components/shared/EmptyState';

export function WorkspaceAssignments() {
  return (
    <section id="workspace-panel-assignments" role="tabpanel" aria-labelledby="workspace-tab-assignments">
      <EmptyState title="No course assignment feed yet" description="The current backend has no course-scoped assignment model. Use the Project Hub for existing academic work until assignment support is available." action={<Link className="text-sm font-semibold text-[var(--accent-bright)] underline underline-offset-2" to="/projects">Open Project Hub</Link>} />
    </section>
  );
}
