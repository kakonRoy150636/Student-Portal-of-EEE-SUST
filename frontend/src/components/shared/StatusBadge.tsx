import React from 'react';
import { Badge } from '@/components/ui/badge';

const SUCCESS = new Set(['approved', 'present', 'operational', 'available', 'active', 'verified']);
const DANGER = new Set(['rejected', 'absent', 'cancelled', 'under_repair', 'needs attention']);

export const StatusBadge = ({ status }: { status: string }) => {
  const key = status.toLowerCase();
  const variant = SUCCESS.has(key) ? 'success' : DANGER.has(key) ? 'danger' : 'secondary';
  return (
    <Badge variant={variant} className="capitalize">
      {status.replace(/_/g, ' ')}
    </Badge>
  );
};
