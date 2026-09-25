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

const TONE: Record<StatTone, { text: string; ring: string; dot: string }> = {
  accent: { text: 'var(--accent-bright)', ring: 'var(--accent-edge)', dot: 'var(--accent)' },
  warn: { text: '#FB7185', ring: 'rgba(251,113,133,0.35)', dot: '#FB7185' },
  muted: { text: 'var(--accent-bright)', ring: 'var(--accent-edge)', dot: 'var(--accent-deep)' },
};

/**
 * Dashboard tile.
 *
 * The accent comes from the active theme's CSS variables rather than a fixed
 * hex, so a tile follows Graphite/Brass/Midnight instead of staying magenta
 * while the rest of the shell recolours. The previous version also printed a
 * constant "ID:0x7B2" and an always-animating status dot on every card, which
 * implied a live feed that did not exist.
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
      <div className="flex items-center justify-between pb-3 text-[10px] font-mono tracking-widest text-slate-500 border-b border-slate-800/80">
        <span>{tag ?? title.toUpperCase()}</span>
      </div>

      <div className="mt-4 flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-[11px] font-mono uppercase tracking-wider text-slate-400">{title}</p>
          {loading || value === undefined || value === null ? (
            <div className="h-7 w-24 animate-pulse rounded bg-slate-800/80" aria-hidden="true" />
          ) : (
            <p className="text-2xl font-black tracking-tight text-white font-mono tabular-nums">{value}</p>
          )}
        </div>
        <div
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border"
          style={{ borderColor: t.ring, backgroundColor: 'var(--accent-soft)', color: t.text }}
        >
          {icon}
        </div>
      </div>

      {subtitle && (
        <div className="mt-4 border-t border-slate-800/80 pt-3 text-xs font-mono">
          <span className="text-slate-500 text-[11px] truncate">{subtitle}</span>
        </div>
      )}
    </>
  );

  const shell = `hud-box corner-brackets relative block rounded-xl p-5 overflow-hidden transition-colors ${
    href ? 'hover:border-[var(--accent-edge)]' : ''
  }`;

  if (href) {
    // Link, not <a href>: a plain anchor would throw away the SPA router
    // state and reload the whole app.
    return (
      <Link to={href} className={shell}>
        {body}
      </Link>
    );
  }
  return <div className={shell}>{body}</div>;
};
