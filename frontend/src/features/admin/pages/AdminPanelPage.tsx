import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';
import { authApi } from '@/features/auth/api/authApi';

export default function AdminPanelPage() {
  const [pending, setPending] = useState<any[]>([]);

  useEffect(() => {
    authApi.pendingApprovals().then(({ data }) => setPending(data)).catch(() => setPending([]));
  }, []);

  const approve = async (id: string) => {
    await authApi.approveUser(id);
    setPending((users) => users.filter((user) => user.id !== id));
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">System Administration</h1>
      <Card>
        <CardContent className="p-5">
          <p className="font-bold text-sm">SUST EEE Administration Console</p>
          <p className="text-xs text-slate-400 mt-1">Manage student batches, approve room allocations, configure semester offerings.</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-5 space-y-3">
          <div><h2 className="font-bold text-sm">Pending account approvals</h2><p className="text-xs text-slate-400 mt-1">Teacher and CR accounts remain inactive until approved.</p></div>
          {pending.length === 0 && <p className="text-xs text-slate-500">No pending approvals.</p>}
          {pending.map((user) => <div key={user.id} className="flex items-center justify-between gap-3 border-t border-slate-200 dark:border-slate-800 pt-3"><div><p className="text-sm font-medium">{user.full_name}</p><p className="text-xs text-slate-500">{user.identifier} · {user.email} · {user.role}</p></div><Button size="sm" onClick={() => approve(user.id)}>Approve</Button></div>)}
        </CardContent>
      </Card>
    </div>
  );
}
