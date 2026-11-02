/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,jsx,ts,tsx}', './src/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // Mirrors the web portal's slate/indigo palette so the two clients
        // look like one product.
        portal: {
          bg: '#0f172a',
          surface: '#1e293b',
          accent: '#6366f1',
          muted: '#94a3b8',
        },
      },
    },
  },
  plugins: [],
};
