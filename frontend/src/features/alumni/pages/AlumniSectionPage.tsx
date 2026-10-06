import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, RotateCcw, Upload, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { alumniApi, type EmploymentSector } from '../api/alumniApi';
import { BatchSelector } from '../components/BatchSelector';
import { AlumniCard } from '../components/AlumniCard';
import { AlumniSummaryCards } from '../components/AlumniSummaryCards';
import { useAuth } from '@/contexts/AuthContext';

const sectors: { value: EmploymentSector; label: string }[] = [
  { value: 'industry', label: 'Industry' }, { value: 'academia', label: 'Academia' },
  { value: 'government', label: 'Government' }, { value: 'startup', label: 'Startup' },
  { value: 'higher_study', label: 'Higher study' }, { value: 'other', label: 'Other' },
];

export default function AlumniSectionPage() {
  const { role } = useAuth();
  const [batch, setBatch] = useState('all');
  const [q, setQ] = useState('');
  const [company, setCompany] = useState('');
  const [country, setCountry] = useState('');
  const [sector, setSector] = useState('all');
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ q: '', company: '', country: '', sector: 'all', batch: 'all' });
  const batches = useQuery({ queryKey: ['alumni', 'batches'], queryFn: async () => (await alumniApi.batches()).data, retry: false });
  const currentYear = useMemo(() => batches.data?.[batches.data.length - 1]?.year, [batches.data]);
  useEffect(() => { if (batch === 'all' && currentYear) setBatch(String(currentYear)); }, [batch, currentYear]);
  const selectedYear = filters.batch === 'all' ? undefined : Number(filters.batch);
  const directory = useQuery({
    queryKey: ['alumni', 'standalone', filters, page],
    queryFn: async () => (await alumniApi.standaloneDirectory({
      batch: selectedYear, q: filters.q || undefined, company: filters.company || undefined,
      country: filters.country || undefined, sector: filters.sector === 'all' ? undefined : filters.sector as EmploymentSector,
      page, page_size: 12,
    })).data,
    retry: false,
  });
  const summary = useQuery({
    queryKey: ['alumni', 'summary', selectedYear],
    queryFn: async () => (await alumniApi.summary(selectedYear!)).data,
    enabled: selectedYear !== undefined,
    retry: false,
  });
  const apply = (event: React.FormEvent) => { event.preventDefault(); setPage(1); setFilters({ q: q.trim(), company: company.trim(), country: country.trim(), sector, batch }); };
  const clear = () => { setQ(''); setCompany(''); setCountry(''); setSector('all'); setBatch('all'); setPage(1); setFilters({ q: '', company: '', country: '', sector: 'all', batch: 'all' }); };
  const items = directory.data?.items ?? [];
  return <div className="space-y-6">
    <PageHeader kicker="Alumni network" title="SUST EEE alumni" description="A searchable record of the people, careers, and journeys connected to the department."
      action={role === 'super_admin' ? <Link to="/admin/alumni/import"><Button size="sm" variant="outline"><Upload className="h-4 w-4" /> Import CSV</Button></Link> : undefined} />
    <section className="surface grid gap-4 p-5 md:grid-cols-[1fr_auto] md:items-center">
      <div><p className="kicker">Connected by cohort</p><h2 className="mt-1 font-display text-2xl font-bold">Find the right EEE connection</h2><p className="mt-2 max-w-xl text-sm text-[var(--text-muted)]">Search across batches by name, organization, country, or sector. Contact details appear only when alumni have opted in.</p></div>
      <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]"><Users className="h-5 w-5 text-[var(--accent-bright)]" />{batches.data?.reduce((sum, item) => sum + item.alumni_count, 0) ?? '—'} visible profiles</div>
    </section>
    <div className="flex flex-wrap gap-2" aria-label="Batch shortcuts">
      {batches.data?.slice(-6).reverse().map((item) => <button key={item.year} type="button" onClick={() => { setBatch(String(item.year)); setFilters((old) => ({ ...old, batch: String(item.year) })); setPage(1); }} className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${filters.batch === String(item.year) ? 'border-[var(--accent-bright)] bg-[var(--accent-soft)] text-[var(--accent-bright)]' : 'border-[var(--border)] text-[var(--text-muted)]'}`}>{item.year} · {item.alumni_count}</button>)}
    </div>
    <BatchSelector batches={batches.data ?? []} value={batch} onChange={(value) => { setBatch(value); setFilters((old) => ({ ...old, batch: value })); setPage(1); }} />
    <AlumniSummaryCards summary={summary.data} loading={summary.isLoading && selectedYear !== undefined} />
    <form onSubmit={apply} className="surface grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-[1.5fr_1fr_1fr_1fr_auto] xl:items-end">
      <label className="text-xs text-[var(--text-subtle)]">Search all batches<Input className="mt-1" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Name, role, organization" /></label>
      <label className="text-xs text-[var(--text-subtle)]">Company<Input className="mt-1" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="BUET, Grameenphone…" /></label>
      <label className="text-xs text-[var(--text-subtle)]">Country<Input className="mt-1" value={country} onChange={(event) => setCountry(event.target.value)} placeholder="Bangladesh" /></label>
      <label className="text-xs text-[var(--text-subtle)]">Sector<Select value={sector} onValueChange={setSector}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All sectors</SelectItem>{sectors.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select></label>
      <div className="flex gap-2"><Button type="submit" size="sm" disabled={directory.isFetching}><Search className="h-4 w-4" /> Search</Button><Button type="button" size="sm" variant="outline" onClick={clear} aria-label="Clear filters"><RotateCcw className="h-4 w-4" /></Button></div>
    </form>
    {directory.isLoading && <PageSkeleton cards={6} rows={0} />}
    {directory.isError && <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">The alumni directory could not be loaded.</p>}
    {!directory.isLoading && !directory.isError && items.length === 0 && <EmptyState title="No alumni found" description="Try a different batch, company, country, or search term." />}
    {items.length > 0 && <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <AlumniCard key={item.id} alumni={item} />)}</div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-4"><p className="text-sm text-[var(--text-muted)]">Page {directory.data?.page} of {directory.data?.pages} · {directory.data?.total} profiles</p><div className="flex gap-2"><Button size="sm" variant="outline" disabled={page <= 1 || directory.isFetching} onClick={() => setPage((value) => value - 1)}>Previous</Button><Button size="sm" variant="outline" disabled={page >= (directory.data?.pages ?? 1) || directory.isFetching} onClick={() => setPage((value) => value + 1)}>Next</Button></div></div>
    </>}
    {summary.data && <div className="grid gap-4 md:grid-cols-2"><div className="surface p-5"><p className="kicker">Top organizations</p><div className="mt-3 flex flex-wrap gap-2">{summary.data.top_companies.length ? summary.data.top_companies.map((item) => <Badge key={item.name} variant="secondary">{item.name} · {item.count}</Badge>) : <span className="text-sm text-[var(--text-muted)]">No current employment data.</span>}</div></div><div className="surface p-5"><p className="kicker">Top countries</p><div className="mt-3 flex flex-wrap gap-2">{summary.data.top_countries.length ? summary.data.top_countries.map((item) => <Badge key={item.name} variant="secondary">{item.name} · {item.count}</Badge>) : <span className="text-sm text-[var(--text-muted)]">No country data.</span>}</div></div></div>}
  </div>;
}
