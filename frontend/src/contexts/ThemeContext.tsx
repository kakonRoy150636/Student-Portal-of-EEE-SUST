import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/**
 * Three "Instrument Panel" color modes, all graded from the same campus
 * photograph so the plate, accents and chrome always read as one image.
 *
 *   graphite : default — blue/steel accents, the coolest of the three
 *   brass    : warm brass/copper accents
 *   midnight : deep violet/aurora accents, highest contrast
 *
 * The mode is written to <html data-theme> so Tailwind + CSS vars pick it up,
 * and mirrored to localStorage so a reload (and the login screen) keeps it.
 */
export const THEMES = ['graphite', 'brass', 'midnight'] as const;
export type ThemeMode = (typeof THEMES)[number];

const STORAGE_KEY = 'eee-portal-theme';
const DEFAULT_THEME: ThemeMode = 'graphite';

type ThemeContextValue = {
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  cycleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const isThemeMode = (value: unknown): value is ThemeMode =>
  typeof value === 'string' && (THEMES as readonly string[]).includes(value);

const readStoredTheme = (): ThemeMode => {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isThemeMode(stored) ? stored : DEFAULT_THEME;
  } catch {
    // Private mode / disabled storage — fall back to the default silently.
    return DEFAULT_THEME;
  }
};

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const [theme, setThemeState] = useState<ThemeMode>(readStoredTheme);

  // Reflect the mode on <html> so the CSS variable blocks in index.css apply.
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    root.style.colorScheme = theme === 'midnight' ? 'dark' : 'dark';
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Persistence is best-effort; the in-memory mode still works.
    }
  }, [theme]);

  const setTheme = useCallback((mode: ThemeMode) => setThemeState(mode), []);

  const cycleTheme = useCallback(
    () => setThemeState((current) => THEMES[(THEMES.indexOf(current) + 1) % THEMES.length]),
    [],
  );

  const value = useMemo(() => ({ theme, setTheme, cycleTheme }), [theme, setTheme, cycleTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useTheme = (): ThemeContextValue => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
};

export const THEME_LABELS: Record<ThemeMode, string> = {
  graphite: 'Graphite',
  brass: 'Brass',
  midnight: 'Midnight',
};
