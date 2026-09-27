import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/**
 * Two academic color modes on the same token set.
 *
 *   dark  : default — navy/charcoal surfaces, gold accent
 *   light : paper/cream surfaces, navy primary, gold accent
 *
 * Older graphite/brass/midnight values stored in localStorage map to dark so
 * existing sessions do not land on an unknown theme.
 *
 * The mode is written to <html data-theme> and the `dark` class so both CSS
 * variables and Tailwind `dark:` utilities stay aligned.
 */
export const THEMES = ['dark', 'light'] as const;
export type ThemeMode = (typeof THEMES)[number];

const STORAGE_KEY = 'eee-portal-theme';
const DEFAULT_THEME: ThemeMode = 'dark';

const LEGACY_THEMES: Record<string, ThemeMode> = {
  graphite: 'dark',
  brass: 'dark',
  midnight: 'dark',
};

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
    if (isThemeMode(stored)) return stored;
    if (stored && stored in LEGACY_THEMES) return LEGACY_THEMES[stored];
    return DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
};

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const [theme, setThemeState] = useState<ThemeMode>(readStoredTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    root.classList.toggle('dark', theme === 'dark');
    root.style.colorScheme = theme;
    const themeColor = theme === 'light' ? '#f3efe6' : '#0b1120';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', themeColor);
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
  dark: 'Dark',
  light: 'Light',
};
