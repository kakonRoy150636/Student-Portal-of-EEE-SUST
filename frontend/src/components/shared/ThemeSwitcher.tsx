import React from 'react';
import { CircleDot, Moon, Sun } from 'lucide-react';
import { THEMES, THEME_LABELS, useTheme, type ThemeMode } from '@/contexts/ThemeContext';

const ICONS: Record<ThemeMode, React.ComponentType<{ className?: string }>> = {
  graphite: CircleDot,
  brass: Sun,
  midnight: Moon,
};

/**
 * Segmented three-mode control. Rendered as a radiogroup so the active mode is
 * announced to screen readers instead of relying on color alone.
 */
export const ThemeSwitcher = ({ className = '' }: { className?: string }) => {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Color mode"
      className={`inline-flex max-w-full flex-wrap items-center gap-1 rounded-lg border border-white/10 bg-black/30 p-1 ${className}`}
    >
      {THEMES.map((mode) => {
        const Icon = ICONS[mode];
        const active = theme === mode;
        return (
          <button
            key={mode}
            type="button"
            role="radio"
            aria-checked={active}
            title={`${THEME_LABELS[mode]} mode`}
            onClick={() => setTheme(mode)}
            className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors sm:px-2.5 ${
              active
                ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-bright)] border border-[color:var(--accent-edge)]'
                : 'text-slate-400 hover:text-slate-200 border border-transparent'
            }`}
          >
            <Icon className="h-3 w-3 shrink-0" />
            {/* Labels stay visible at every width; the switcher wraps onto its
                own line inside the hero card instead of overflowing. */}
            <span>{THEME_LABELS[mode]}</span>
          </button>
        );
      })}
    </div>
  );
};
