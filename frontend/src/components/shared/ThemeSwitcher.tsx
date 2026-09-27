import React from 'react';
import { Moon, Sun } from 'lucide-react';
import { THEMES, THEME_LABELS, useTheme, type ThemeMode } from '@/contexts/ThemeContext';

const ICONS: Record<ThemeMode, React.ComponentType<{ className?: string }>> = {
  dark: Moon,
  light: Sun,
};

/**
 * Segmented light/dark control. Rendered as a radiogroup so the active mode is
 * announced to screen readers instead of relying on color alone.
 */
export const ThemeSwitcher = ({ className = '' }: { className?: string }) => {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Color mode"
      className={`inline-flex items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-1 ${className}`}
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
            aria-label={`${THEME_LABELS[mode]} mode`}
            onClick={() => setTheme(mode)}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
              active
                ? 'bg-[var(--surface)] text-[var(--text)] shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text)]'
            }`}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span>{THEME_LABELS[mode]}</span>
          </button>
        );
      })}
    </div>
  );
};
