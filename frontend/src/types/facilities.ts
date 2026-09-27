export interface Room {
  id: number;
  room_number: string;
  building: string;
  capacity: number;
  is_lab: boolean;
  amenities: Record<string, unknown>;
}

export interface Reservation {
  id: string;
  room_id: number;
  room_number: string;
  purpose: string;
  start_time: string;
  end_time: string;
  status: string;
}

export interface LabEquipment {
  tag: string;
  model: string;
  category: string;
  lab: string;
  status: string;
}
