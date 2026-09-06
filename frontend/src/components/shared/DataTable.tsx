import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

export function DataTable<T extends { id: string | number }>({ columns, data, emptyMessage = "No items" }: any) {
  return (
    <div className="rounded-md border bg-white dark:bg-slate-900">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((c: any, idx: number) => <TableHead key={idx}>{c.header}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.length === 0 ? (
            <TableRow><TableCell colSpan={columns.length} className="text-center py-6">{emptyMessage}</TableCell></TableRow>
          ) : (
            data.map((row: any) => (
              <TableRow key={row.id}>
                {columns.map((col: any, idx: number) => (
                  <TableCell key={idx}>{col.cell ? col.cell(row) : row[col.accessorKey]}</TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
