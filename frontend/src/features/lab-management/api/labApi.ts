import { api } from '@/lib/axios';
import type { LabEquipment } from '@/types/facilities';

export const labApi = {
  getEquipment: () => api.get<LabEquipment[]>('/labs/equipment'),
};
