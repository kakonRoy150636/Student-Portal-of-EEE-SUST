import React, { createContext, useContext, useEffect, useState } from 'react';
import { usePushNotifications } from '@/hooks/usePushNotifications';

export type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };
const PushContext = createContext<(ReturnType<typeof usePushNotifications> & { installPrompt: InstallPrompt | null; clearInstall: () => void }) | null>(null);
export function PushProvider({ children }: { children: React.ReactNode }) {
  const state = usePushNotifications();
  const [installPrompt, setInstallPrompt] = useState<InstallPrompt | null>(null);
  useEffect(() => {
    const available = (event: Event) => { event.preventDefault(); setInstallPrompt(event as InstallPrompt); };
    const installed = () => setInstallPrompt(null);
    window.addEventListener('beforeinstallprompt', available);
    window.addEventListener('appinstalled', installed);
    return () => { window.removeEventListener('beforeinstallprompt', available); window.removeEventListener('appinstalled', installed); };
  }, []);
  return <PushContext.Provider value={{ ...state, installPrompt, clearInstall: () => setInstallPrompt(null) }}>{children}</PushContext.Provider>;
}
export function usePushState() {
  const value = useContext(PushContext);
  if (!value) throw new Error('PushProvider required');
  return value;
}
