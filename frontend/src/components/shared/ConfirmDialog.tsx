import React from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export const ConfirmDialog = ({
  title,
  message,
  open,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  open?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) => (
  <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      <p className="text-sm text-[var(--text-muted)]">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button size="sm" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button size="sm" variant="destructive" onClick={onConfirm}>
          Confirm
        </Button>
      </div>
    </DialogContent>
  </Dialog>
);
