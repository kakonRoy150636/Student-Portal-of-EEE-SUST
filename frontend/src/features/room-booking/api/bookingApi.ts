import { api } from '@/lib/axios';

export const bookingApi = {
  getRooms: () => api.get('/rooms'),
  createReservation: (data: any) => api.post('/rooms/reservations', data),
};
