import React from 'react';

export const EmptyState = ({ title, description }: { title: string; description: string }) => (
  <div className="text-center p-8 border rounded-lg bg-white dark:bg-slate-900 space-y-2">
    <h4 className="font-bold text-slate-700 dark:text-slate-300">{title}</h4>
    <p className="text-xs text-slate-400">{description}</p>
  </div>
);
