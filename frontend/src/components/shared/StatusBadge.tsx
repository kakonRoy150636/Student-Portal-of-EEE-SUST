import React from 'react';
import { Badge } from '@/components/ui/badge';

export const StatusBadge = ({ status }: { status: string }) => {
  return (
    <Badge variant={status === 'approved' || status === 'present' ? 'default' : 'secondary'} className="capitalize">
      {status}
    </Badge>
  );
};
