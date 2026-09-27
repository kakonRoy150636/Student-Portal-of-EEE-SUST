import React from 'react';

export const ErrorBoundary = () => (
  <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-6 text-center">
    <div className="surface max-w-md p-6">
      <h1 className="font-display text-lg font-semibold text-[var(--text)]">Page could not be loaded</h1>
      <p className="mt-2 text-sm text-[var(--text-muted)]">An unexpected navigation error occurred.</p>
    </div>
  </div>
);
