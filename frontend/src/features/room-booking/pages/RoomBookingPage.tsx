import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { Badge } from '@/components/ui/badge';
import { bookingApi } from '../api/bookingApi';
import { BookingModal } from '../components/BookingModal';

const amenityList = (amenities: Record<string, unknown>) => {
  const names = Object.entries(amenities)
    .filter(([, value]) => Boolean(value))
    .map(([key]) => key.replace(/_/g, ' '));
  return names.length ? names.join(', ') : 'No amenities listed';
};

export default function RoomBookingPage() {
  const rooms = useQuery({
    queryKey: ['rooms'],
    queryFn: async () => (await bookingApi.getRooms()).data,
    retry: false,
  });
  const reservations = useQuery({
    queryKey: ['rooms', 'reservations'],
    queryFn: async () => (await bookingApi.getMyReservations()).data,
    retry: false,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Campus"
        title="Room booking"
        description="Reserve a lecture room or lab. Requests stay pending until staff decide."
        action={<BookingModal rooms={rooms.data ?? []} />}
      />

      {rooms.isLoading && <PageSkeleton cards={2} rows={2} />}
      {rooms.isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load rooms.
        </p>
      )}
      {!rooms.isLoading && !rooms.isError && (rooms.data ?? []).length === 0 && (
        <EmptyState title="No rooms listed" description="The facilities catalogue is empty." />
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {(rooms.data ?? []).map((room) => (
          <article key={room.id} className="surface p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text)]">{room.room_number}</h3>
                <p className="mt-1 text-sm text-[var(--text-muted)]">{room.building}</p>
              </div>
              <Badge variant={room.is_lab ? 'secondary' : 'outline'}>{room.is_lab ? 'Lab' : 'Lecture'}</Badge>
            </div>
            <p className="mt-3 text-sm text-[var(--text-muted)]">Capacity {room.capacity}</p>
            <p className="mt-1 text-xs text-[var(--text-subtle)]">{amenityList(room.amenities ?? {})}</p>
          </article>
        ))}
      </div>

      <section className="space-y-3">
        <h2 className="font-display text-base font-semibold">Your reservations</h2>
        {reservations.isLoading && <div className="h-16 animate-pulse rounded-xl bg-[var(--surface-muted)]" />}
        {reservations.isError && (
          <p className="text-sm text-[var(--danger)]" role="alert">Could not load reservations.</p>
        )}
        {!reservations.isLoading && !reservations.isError && (reservations.data ?? []).length === 0 && (
          <EmptyState title="No reservations yet" description="Submit a booking request to see it here." />
        )}
        <div className="space-y-3">
          {(reservations.data ?? []).map((item) => (
            <article key={item.id} className="surface flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold">{item.room_number}</p>
                <p className="text-sm text-[var(--text-muted)]">{item.purpose}</p>
              </div>
              <div className="text-right">
                <Badge variant="secondary" className="capitalize">{item.status}</Badge>
                <p className="mt-1 text-xs text-[var(--text-subtle)]">
                  {new Date(item.start_time).toLocaleString()} – {new Date(item.end_time).toLocaleTimeString()}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
