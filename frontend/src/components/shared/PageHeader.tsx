import React, { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
  kicker?: string;
}

export const PageHeader = ({ title, description, action, kicker }: PageHeaderProps) => (
  <div className="flex flex-col gap-3 pb-2 sm:flex-row sm:items-end sm:justify-between">
    <div className="min-w-0">
      {kicker && <p className="kicker mb-1">{kicker}</p>}
      <h1 className="font-display text-xl font-bold tracking-tight text-[var(--text)]">{title}</h1>
      {description && <p className="mt-1 max-w-2xl text-sm text-[var(--text-muted)]">{description}</p>}
    </div>
    {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
  </div>
);
