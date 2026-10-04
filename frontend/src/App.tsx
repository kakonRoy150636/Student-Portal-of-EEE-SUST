import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { router } from '@/routes';
import { NotificationProvider } from '@/features/notifications/NotificationContext';
import { PushProvider } from '@/contexts/PushContext';
import { PwaUpdater } from '@/components/shared/PwaControls';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <PushProvider>
            <NotificationProvider>
              <PwaUpdater />
              <RouterProvider router={router} />
            </NotificationProvider>
          </PushProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
