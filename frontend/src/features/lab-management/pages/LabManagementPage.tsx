import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { DataTable } from '@/components/shared/DataTable';
import { labApi } from '../api/labApi';
import type { LabEquipment } from '@/types/facilities';

export default function LabManagementPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['labs', 'equipment'],
    queryFn: async () => (await labApi.getEquipment()).data,
    retry: false,
  });

  const rows = (data ?? []).map((item) => ({ ...item, id: item.tag }));

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Campus"
        title="Lab management"
        description="Equipment inventory across department labs."
      />
      {isLoading && <PageSkeleton cards={0} rows={5} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load equipment.
        </p>
      )}
      {!isLoading && !isError && rows.length === 0 && (
        <EmptyState title="No equipment listed" description="The inventory is empty, or nothing has been catalogued yet." />
      )}
      {!isLoading && !isError && rows.length > 0 && (
        <DataTable<LabEquipment & { id: string }>
          data={rows}
          emptyMessage="No equipment listed"
          columns={[
            { header: 'Tag', accessorKey: 'tag' },
            { header: 'Model', accessorKey: 'model' },
            { header: 'Category', accessorKey: 'category' },
            { header: 'Lab', accessorKey: 'lab' },
            { header: 'Status', cell: (row) => <StatusBadge status={row.status} /> },
          ]}
        />
      )}
    </div>
  );
}
