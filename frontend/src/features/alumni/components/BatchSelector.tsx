import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { AlumniBatch } from '../api/alumniApi';

export function BatchSelector({ batches, value, onChange }: {
  batches: AlumniBatch[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="min-w-[10rem]">
      <label htmlFor="alumni-batch" className="mb-1 block text-xs text-[var(--text-subtle)]">Batch</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger id="alumni-batch" aria-label="Alumni batch"><SelectValue placeholder="All batches" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All batches</SelectItem>
          {[...batches].reverse().map((batch) => (
            <SelectItem key={batch.year} value={String(batch.year)}>{batch.year} · {batch.alumni_count}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
