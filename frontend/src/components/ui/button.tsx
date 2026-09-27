import * as React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'secondary' | 'destructive';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-1.5 rounded-lg text-sm font-semibold transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]',
        'disabled:pointer-events-none disabled:opacity-50',
        variant === 'default' && 'bg-[var(--primary)] text-[var(--primary-fg)] hover:opacity-90',
        variant === 'outline' &&
          'border border-[var(--border)] bg-transparent text-[var(--text)] hover:bg-[var(--surface-muted)]',
        variant === 'ghost' && 'bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]',
        variant === 'secondary' && 'bg-[var(--accent-soft)] text-[var(--accent-bright)] hover:bg-[var(--accent-edge)]',
        variant === 'destructive' && 'bg-[var(--danger)] text-white hover:opacity-90',
        size === 'default' && 'h-10 px-4 py-2',
        size === 'sm' && 'h-8 rounded-md px-3 text-xs',
        size === 'lg' && 'h-11 px-5',
        size === 'icon' && 'h-10 w-10',
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = 'Button';
