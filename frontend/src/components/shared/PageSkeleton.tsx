import React from 'react';

export const PageSkeleton = ({
  cards = 4,
  rows = 3,
}: {
  cards?: number;
  rows?: number;
}) => (
  <div className="space-y-6" aria-busy="true" aria-live="polite">
    <div className="space-y-2">
      <div className="h-3 w-24 animate-pulse rounded bg-[var(--surface-muted)]" />
      <div className="h-8 w-56 animate-pulse rounded bg-[var(--surface-muted)]" />
      <div className="h-4 w-80 max-w-full animate-pulse rounded bg-[var(--surface-muted)]" />
    </div>
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: cards }).map((_, i) => (
        <div key={i} className="surface h-28 animate-pulse" />
      ))}
    </div>
    <div className="surface space-y-3 p-5">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-lg bg-[var(--surface-muted)]" />
      ))}
    </div>
  </div>
);

export const RouteFallback = () => (
  <div className="mx-auto w-full max-w-6xl">
    <PageSkeleton />
  </div>
);
