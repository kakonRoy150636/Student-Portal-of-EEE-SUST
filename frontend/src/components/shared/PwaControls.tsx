import React, { useEffect, useState } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';
import { Button } from '@/components/ui/button';
import { usePushState } from '@/contexts/PushContext';
import { isIOS, isInstalled } from '@/lib/pushSession';

export function PwaControls() {
  const push = usePushState();
  const install = push.installPrompt;
  const [installed, setInstalled] = useState(isInstalled);
  useEffect(() => {
    const done = () => setInstalled(true);
    window.addEventListener('appinstalled', done);
    return () => window.removeEventListener('appinstalled', done);
  }, []);
  return <section className="surface max-w-3xl space-y-3 p-5" aria-label="Install and push notifications">
    <h2 className="text-lg font-semibold">Install & web push</h2>
    {isIOS() && !installed && <div className="rounded-lg border border-[var(--border)] p-3">
      <h3 className="font-semibold">Install on iPhone or iPad</h3>
      <ol className="list-inside list-decimal text-sm">
        <li>Open this portal in Safari.</li><li>Tap Share, then Add to Home Screen.</li><li>Open the installed app and sign in, then enable push here.</li>
      </ol><p className="mt-2 text-sm">iOS web push requires iOS/iPadOS 16.4 or newer and a Home Screen app.</p>
    </div>}
    {install && !installed && <Button onClick={async () => { await install.prompt(); await install.userChoice; push.clearInstall(); }}>Install portal</Button>}
    {!install && !installed && !isIOS() && <p className="text-sm">Use your browser’s Install app menu when available. Open Class routine online to save it for offline use.</p>}
    {installed && <p className="text-sm" role="status">Portal is running as an installed app.</p>}
    {!push.configured ? <p className="text-sm">Web push is not configured on this deployment yet.</p>
      : !push.supported ? <p className="text-sm">Push requires a supported browser, HTTPS and, on iPhone, installation to Home Screen.</p>
      : <Button disabled={push.busy} onClick={() => void (push.enabled ? push.disable() : push.enable())}>
        {push.busy ? 'Updating…' : push.enabled ? 'Disable push on this device' : 'Enable push on this device'}
      </Button>}
    {push.enabled && <p className="text-sm" role="status">This device is registered for push.</p>}
    {push.error && <p role="alert" className="text-sm text-[var(--danger)]">{push.error}</p>}
  </section>;
}

/** Register at app startup without ever requesting notification permission. */
export function PwaUpdater() {
  const { needRefresh: [refresh], updateServiceWorker } = useRegisterSW();
  return refresh ? <div className="fixed bottom-20 right-4 z-50 surface p-4" role="status">
    <p>A portal update is ready.</p><Button onClick={() => void updateServiceWorker(true)}>Update app</Button>
  </div> : null;
}
