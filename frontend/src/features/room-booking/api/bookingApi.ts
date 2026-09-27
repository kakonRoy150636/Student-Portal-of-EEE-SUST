import { api } from '@/lib/axios';
import type { Reservation, Room } from '@/types/facilities';

export const bookingApi = {
  getRooms: () => api.get<Room[]>('/rooms'),
  getMyReservations: () => api.get<Reservation[]>('/rooms/reservations'),
  createReservation: (data: { room_id: number; purpose: string; start_time: string; end_time: string }) =>
    api.post('/rooms/reservations', data),
};
