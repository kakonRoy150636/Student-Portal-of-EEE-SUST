import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

type Column<T> = {
  header: string;
  accessorKey?: keyof T & string;
  cell?: (row: T) => React.ReactNode;
};

export function DataTable<T extends { id: string | number }>({
  columns,
  data,
  emptyMessage = 'No items',
}: {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
}) {
  return (
    <>
      <div className="hidden overflow-hidden rounded-card border border-[var(--border)] bg-[var(--surface)] md:block">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((c, idx) => (
                <TableHead key={idx}>{c.header}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-8 text-center text-[var(--text-muted)]">
                  {emptyMessage}
                </TableCell>
              </TableRow>
            ) : (
              data.map((row) => (
                <TableRow key={row.id}>
                  {columns.map((col, idx) => (
                    <TableCell key={idx}>{col.cell ? col.cell(row) : String(row[col.accessorKey as keyof T] ?? '')}</TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 md:hidden">
        {data.length === 0 ? (
          <p className="surface px-4 py-8 text-center text-sm text-[var(--text-muted)]">{emptyMessage}</p>
        ) : (
          data.map((row) => (
            <article key={row.id} className="surface space-y-2 p-4">
              {columns.map((col, idx) => (
                <div key={idx} className="flex items-start justify-between gap-3 text-sm">
                  <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">{col.header}</span>
                  <span className="text-right text-[var(--text)]">
                    {col.cell ? col.cell(row) : String(row[col.accessorKey as keyof T] ?? '')}
                  </span>
                </div>
              ))}
            </article>
          ))
        )}
      </div>
    </>
  );
}
