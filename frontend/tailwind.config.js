/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        ink: 'var(--text)',
        muted: 'var(--text-muted)',
        subtle: 'var(--text-subtle)',
        line: 'var(--border)',
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--primary-fg)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          bright: 'var(--accent-bright)',
          deep: 'var(--accent-deep)',
          soft: 'var(--accent-soft)',
          edge: 'var(--accent-edge)',
        },
        danger: {
          DEFAULT: 'var(--danger)',
          soft: 'var(--danger-soft)',
        },
        success: {
          DEFAULT: 'var(--success)',
          soft: 'var(--success-soft)',
        },
        warn: {
          DEFAULT: 'var(--warn)',
          soft: 'var(--warn-soft)',
        },
        sand: '#D4A017',
        slate1: 'var(--text-muted)',
      },
      fontFamily: {
        sans: ['"Instrument Sans"', '"Noto Sans Bengali"', 'system-ui', 'sans-serif'],
        display: ['Newsreader', '"Noto Serif Bengali"', 'Georgia', 'serif'],
        mono: ['"Instrument Sans"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        xs: ['12px', { lineHeight: '1.45', letterSpacing: '0' }],
        sm: ['14px', { lineHeight: '1.5', letterSpacing: '0' }],
        base: ['16px', { lineHeight: '1.6', letterSpacing: '0' }],
        lg: ['20px', { lineHeight: '1.4', letterSpacing: '-0.01em' }],
        xl: ['32px', { lineHeight: '1.2', letterSpacing: '-0.02em' }],
        '2xl': ['40px', { lineHeight: '1.15', letterSpacing: '-0.02em' }],
        '3xl': ['48px', { lineHeight: '1.1', letterSpacing: '-0.025em' }],
      },
      boxShadow: {
        card: 'var(--shadow)',
      },
      borderRadius: {
        card: '0.875rem',
      },
    },
  },
  plugins: [],
};
