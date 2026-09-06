import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BookingModal } from '../components/BookingModal';

export default function RoomBookingPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold tracking-tight">Room Allocation</h1>
        <BookingModal />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <h3 className="font-bold text-sm">Room 304 (Lecture Hall)</h3>
            <p className="text-xs text-slate-400">Capacity: 80 | Projector, AC</p>
            <div className="mt-3 flex justify-between items-center">
              <Badge variant="default">Available</Badge>
              <Button size="sm" variant="outline">Reserve</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
