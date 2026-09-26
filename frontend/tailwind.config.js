/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0F2557',
          foreground: '#ffffff'
        },
        accent: {
          DEFAULT: '#C9A227',
          bright: '#E2C45C',
          deep: '#927516',
          soft: 'rgba(201, 162, 39, 0.13)',
          edge: 'rgba(226, 196, 92, 0.28)'
        },
        sand: '#D4A017',
        ink: '#0B1120',
        slate1: '#A8B3C7'
      }
    },
  },
  plugins: [],
}
