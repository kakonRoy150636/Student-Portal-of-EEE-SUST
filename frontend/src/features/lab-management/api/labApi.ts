import { api } from '@/lib/axios';

export const labApi = {
  getEquipment: () => api.get('/labs/equipment'),
};
