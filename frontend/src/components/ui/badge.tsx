import * as React from 'react';
import { cn } from '@/lib/utils';

export const Badge = ({
  className,
  variant = 'default',
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { variant?: 'default' | 'secondary' | 'outline' | 'danger' | 'success' }) => (
  <div
    className={cn(
      'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold',
      variant === 'default' && 'border-transparent bg-[var(--accent-soft)] text-[var(--accent-bright)]',
      variant === 'secondary' && 'border-transparent bg-[var(--surface-muted)] text-[var(--text-muted)]',
      variant === 'outline' && 'border-[var(--border)] text-[var(--text)]',
      variant === 'danger' && 'border-transparent bg-[var(--danger-soft)] text-[var(--danger)]',
      variant === 'success' && 'border-transparent bg-[var(--success-soft)] text-[var(--success)]',
      className,
    )}
    {...props}
  />
);
