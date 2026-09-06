export interface Room {
  id: number;
  room_number: string;
  capacity: number;
  is_lab: boolean;
}

export interface Reservation {
  id: string;
  room_id: number;
  room_number?: string;
  purpose: string;
  status: string;
}
