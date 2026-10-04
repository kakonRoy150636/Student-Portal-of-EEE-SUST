import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { alumniApi, type AlumniImportPreview, type AlumniImportResult } from '../api/alumniApi';

export default function AlumniImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<AlumniImportPreview | null>(null);
  const previewMutation = useMutation({ mutationFn: (selected: File) => alumniApi.importPreview(selected), onSuccess: ({ data }) => setPreview(data) });
  const importMutation = useMutation({ mutationFn: (selected: File) => alumniApi.importCsv(selected), onSuccess: ({ data }) => setPreview(data) });
  const result = preview && 'imported_rows' in preview ? preview as AlumniImportResult : null;
  return <div className="space-y-6"><PageHeader kicker="Administration · Alumni" title="Import alumni CSV" description="Validate a file first. Import only runs after a clean dry-run preview." /><section className="surface space-y-4 p-5"><p className="text-sm text-[var(--text-muted)]">Required columns: <code>email, full_name, batch_year, department, graduation_date</code>. Optional columns include current role, location, visibility flags, and employment dates.</p><input type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setPreview(null); }} className="block w-full text-sm text-[var(--text-muted)]" /><div className="flex flex-wrap gap-2"><Button disabled={!file || previewMutation.isPending} onClick={() => file && previewMutation.mutate(file)}>Preview validation</Button><Button variant="outline" disabled={!file || !preview || Boolean(preview.invalid_rows) || importMutation.isPending} onClick={() => file && importMutation.mutate(file)}>Import validated rows</Button></div></section>{preview && <section className="surface space-y-4 p-5"><div className="flex flex-wrap gap-2"><Badge variant="success">Valid {preview.valid_rows}</Badge><Badge variant={preview.invalid_rows ? 'danger' : 'secondary'}>Invalid {preview.invalid_rows}</Badge><Badge variant="outline">Total {preview.total_rows}</Badge></div>{preview.errors.length ? <ul className="space-y-2 text-sm text-[var(--danger)]">{preview.errors.map((error) => <li key={`${error.row}-${error.message}`}>Row {error.row}{error.field ? ` · ${error.field}` : ''}: {error.message}</li>)}</ul> : <p className="text-sm text-[var(--success)]">Dry-run passed. The import button is enabled.</p>}{result && <p className="text-sm text-[var(--text-muted)]">Imported {result.imported_rows} new profiles and updated {result.updated_rows} existing profiles.</p>}</section>}</div>;
}
