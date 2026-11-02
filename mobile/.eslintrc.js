/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  extends: ['expo', 'eslint:recommended'],
  ignorePatterns: ['/dist/*', '/.expo/*', 'node_modules/', 'babel.config.js', 'metro.config.js', 'tailwind.config.js'],
  rules: {
    // The portal's API layer is typed; `any` in a screen is a bug, not a style choice.
    '@typescript-eslint/no-explicit-any': 'error',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
  },
};
