import React, { ReactNode } from 'react';

export const EmptyState = ({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) => (
  <div className="surface px-6 py-10 text-center">
    <h4 className="font-display text-base font-semibold text-[var(--text)]">{title}</h4>
    <p className="mx-auto mt-1 max-w-md text-sm text-[var(--text-muted)]">{description}</p>
    {action && <div className="mt-4 flex justify-center">{action}</div>}
  </div>
);
