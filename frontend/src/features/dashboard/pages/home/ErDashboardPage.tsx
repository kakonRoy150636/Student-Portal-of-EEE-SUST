import React from 'react';
import { DashboardHero } from './DashboardHero';
import { StatCard } from '@/components/shared/StatCard';
import { Wrench, AlertTriangle, DoorOpen, PackageCheck } from 'lucide-react';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const ErDashboardPage = () => {
  const { data, isLoading } = useDashboardSummary();
  const e = data?.er;

  return (
    <div className="space-y-6 relative z-10">
      <DashboardHero
        consoleName="04 // ER CONSOLE"
        roleName="ER / LAB ASSISTANT"
        unreadNotifications={e?.unread_notifications}
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Equipment Assets"
          value={isLoading ? undefined : e?.equipment_total ?? 0}
          icon={<Wrench className="h-5 w-5" />}
          subtitle="Tracked across all department labs"
          tag="MEASURED // INVENTORY"
          loading={isLoading}
          href="/labs"
        />
        <StatCard
          title="Needs Attention"
          value={isLoading ? undefined : e?.equipment_under_repair ?? 0}
          icon={<AlertTriangle className="h-5 w-5" />}
          subtitle="Not in operational condition"
          tag="MEASURED // CONDITION"
          tone={(e?.equipment_under_repair ?? 0) > 0 ? 'warn' : 'muted'}
          loading={isLoading}
        />
        <StatCard
          title="Borrow Requests"
          value={isLoading ? undefined : e?.pending_borrow_requests ?? 0}
          icon={<PackageCheck className="h-5 w-5" />}
          subtitle="Awaiting approval"
          tag="MEASURED // QUEUE"
          tone={(e?.pending_borrow_requests ?? 0) > 0 ? 'warn' : 'muted'}
          loading={isLoading}
        />
        <StatCard
          title="Rooms"
          value={isLoading ? undefined : e?.rooms_total ?? 0}
          icon={<DoorOpen className="h-5 w-5" />}
          subtitle={`${e?.pending_room_requests ?? 0} reservation(s) pending`}
          tag="MEASURED // FACILITIES"
          loading={isLoading}
          href="/room-booking"
        />
      </div>
    </div>
  );
};
