import React from 'react';
import { Button } from '@/components/ui/button';

export const ConfirmDialog = ({ title, message, onConfirm, onCancel }: any) => (
  <div className="p-4 border rounded-lg bg-white dark:bg-slate-900 space-y-3">
    <h3 className="font-bold text-sm">{title}</h3>
    <p className="text-xs text-slate-500">{message}</p>
    <div className="flex gap-2 justify-end">
      <Button size="sm" variant="outline" onClick={onCancel}>Cancel</Button>
      <Button size="sm" variant="destructive" onClick={onConfirm}>Confirm</Button>
    </div>
  </div>
);
