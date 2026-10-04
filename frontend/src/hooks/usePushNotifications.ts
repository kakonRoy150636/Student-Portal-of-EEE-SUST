import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { firebaseConfigured } from '@/lib/firebase';
import { activatePushUser, refreshPushDevice, pushSupported, disablePushDevice, setPushOptOut, pushSessionRevision, pushSessionMatches } from '@/lib/pushSession';

export function usePushNotifications() {
  const { user } = useAuth();
  const [supported, setSupported] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    activatePushUser(user.id);
    let cancelled = false;
    const refresh = async () => {
      try {
        const available = await pushSupported();
        if (!cancelled) setSupported(available);
        // Existing consent only: NEVER request permission on startup/focus.
        if (available && Notification.permission === 'granted') {
          const registered = await refreshPushDevice(user.id);
          if (!cancelled) setEnabled(registered);
        }
      } catch { if (!cancelled) setError('Could not register this device. Retry when connected.'); }
    };
    void refresh();
    const visible = () => { if (document.visibilityState === 'visible') void refresh(); };
    window.addEventListener('online', refresh);
    document.addEventListener('visibilitychange', visible);
    return () => {
      cancelled = true;
      window.removeEventListener('online', refresh);
      document.removeEventListener('visibilitychange', visible);
    };
  }, [user]);

  const enable = async () => {
    if (!user || busy || !supported) return;
    setBusy(true); setError('');
    try {
      activatePushUser(user.id);
      const revision = pushSessionRevision();
      // This is called directly by the Enable push button after login.
      const permission = await Notification.requestPermission();
      if (!pushSessionMatches(user.id, revision)) return; // account changed during the prompt
      if (permission !== 'granted') { setError('Notifications are blocked. Change this site’s browser notification setting to allow them.'); return; }
      setPushOptOut(false);
      setEnabled(await refreshPushDevice(user.id));
    } catch { setError('Could not enable push. Check your connection and Firebase configuration.'); }
    finally { setBusy(false); }
  };
  const disable = async () => {
    setPushOptOut(true);
    setBusy(true); setError('');
    try { await disablePushDevice(); setEnabled(false); }
    catch { setError('Could not remove the device registration. Try again when connected.'); }
    finally { setBusy(false); }
  };
  return { configured: firebaseConfigured, supported, enabled, busy, error, enable, disable };
}
