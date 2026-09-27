import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { bookingApi } from '../api/bookingApi';
import type { Room } from '@/types/facilities';

export const BookingModal = ({ rooms }: { rooms: Room[] }) => {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [roomId, setRoomId] = useState(rooms[0]?.id ? String(rooms[0].id) : '');
  const [purpose, setPurpose] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [error, setError] = useState('');

  const create = useMutation({
    mutationFn: () =>
      bookingApi.createReservation({
        room_id: Number(roomId),
        purpose,
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['rooms', 'reservations'] });
      setOpen(false);
      setPurpose('');
      setError('');
    },
    onError: () => setError('The booking could not be submitted. Check the times and try again.'),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">New booking request</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request a room</DialogTitle>
        </DialogHeader>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!roomId || !purpose || !startTime || !endTime) {
              setError('All fields are required.');
              return;
            }
            create.mutate();
          }}
        >
          <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">
            Room
            <select
              className="mt-1 h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] px-3 text-sm text-[var(--text)]"
              value={roomId}
              onChange={(event) => setRoomId(event.target.value)}
            >
              <option value="">Select a room</option>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.room_number} · {room.building}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">
            Purpose
            <Input className="mt-1" value={purpose} onChange={(event) => setPurpose(event.target.value)} required />
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">
              Starts
              <Input className="mt-1" type="datetime-local" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
            </label>
            <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">
              Ends
              <Input className="mt-1" type="datetime-local" value={endTime} onChange={(event) => setEndTime(event.target.value)} required />
            </label>
          </div>
          {error && <p className="text-sm text-[var(--danger)]" role="alert">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>{create.isPending ? 'Submitting…' : 'Submit request'}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
