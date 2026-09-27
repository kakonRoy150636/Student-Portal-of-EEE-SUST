import React, { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export type StatTone = 'accent' | 'warn' | 'muted';

interface StatCardProps {
  title: string;
  /** Pass undefined while loading so the card shows a skeleton, not a fake 0. */
  value?: string | number | null;
  icon: ReactNode;
  /**
   * Short qualifier shown under the value. Only pass something measured --
   * e.g. "EEE 311, EEE 312" -- never a decorative label.
   */
  subtitle?: string;
  tag?: string;
  tone?: StatTone;
  loading?: boolean;
  /** Ties the tile to its page, e.g. "Open attendance". */
  href?: string;
}

const TONE: Record<StatTone, { text: string; bg: string }> = {
  accent: { text: 'var(--accent-bright)', bg: 'var(--accent-soft)' },
  warn: { text: 'var(--danger)', bg: 'var(--danger-soft)' },
  muted: { text: 'var(--text-muted)', bg: 'var(--surface-muted)' },
};

/**
 * Dashboard tile.
 *
 * Accent comes from the active theme tokens so light and dark both recolour
 * the tile. Values stay measured: a missing number is a skeleton or empty
 * state, never an invented figure.
 */
export const StatCard = ({
  title,
  value,
  icon,
  subtitle,
  tag,
  tone = 'accent',
  loading = false,
  href,
}: StatCardProps) => {
  const t = TONE[tone];
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">
            {tag ?? title}
          </p>
          {loading || value === undefined || value === null ? (
            <div className="mt-2 h-8 w-20 animate-pulse rounded bg-[var(--surface-muted)]" aria-hidden="true" />
          ) : (
            <p className="mt-1 font-display text-xl font-bold tabular-nums tracking-tight text-[var(--text)]">
              {value}
            </p>
          )}
        </div>
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
          style={{ backgroundColor: t.bg, color: t.text }}
        >
          {icon}
        </div>
      </div>
      {subtitle && <p className="mt-3 text-sm leading-5 text-[var(--text-muted)]">{subtitle}</p>}
    </>
  );

  const shell = `surface block p-5 ${href ? 'transition-colors hover:border-[var(--accent-edge)]' : ''}`;

  if (href) {
    return (
      <Link to={href} className={shell}>
        {body}
      </Link>
    );
  }
  return <div className={shell}>{body}</div>;
};
