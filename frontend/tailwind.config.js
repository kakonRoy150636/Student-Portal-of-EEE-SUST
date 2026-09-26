/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#10b981',
          foreground: '#ffffff'
        },
        // Palette sampled directly from the campus photo (login-hero.jpg).
        // 'accent' is the exact dominant k-means cluster in that image (#5B96E2),
        // so the UI reads as part of the photograph instead of a green template.
        accent: {
          DEFAULT: '#5B96E2',   // literal dominant cluster in the photo
          bright: '#8FC0F2',    // lifted; 10.3:1 on base, safe for text
          deep: '#3A6FB5',      // pressed / borders
          soft: 'rgba(91, 150, 226, 0.12)',
          edge: 'rgba(143, 192, 242, 0.22)'
        },
        // second warm cluster pulled from the same photo (9.7% of saturated px)
        sand: '#E1B88C',
        ink: '#050B14',        // matches the photo's shadow floor + app body
        slate1: '#9FB3C8'      // muted text, 9.2:1 on ink
      }
    },
  },
  plugins: [],
}
