import React, { useCallback, useEffect, useState } from 'react';
import { KeyRound, Laptop, ShieldCheck, ShieldOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { authApi } from '@/features/auth/api/authApi';
import { SessionSummary } from '@/types/auth';

const fieldClass =
  'h-11 w-full rounded-lg border border-white/12 bg-white/[0.04] px-3.5 text-sm text-white ' +
  'placeholder:text-white/45 transition-colors ' +
  'focus:border-accent focus:bg-accent-soft focus:outline-none focus:ring-[3px] focus:ring-accent/20';

const Card = ({ children, title, icon }: { children: React.ReactNode; title: string; icon: React.ReactNode }) => (
  <section className="rounded-xl border border-white/10 bg-white/[0.03] p-5 sm:p-6">
    <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
      {icon}
      {title}
    </h2>
    {children}
  </section>
);

const Notice = ({ children }: { children: React.ReactNode }) => (
  <p className="mb-4 rounded-lg border border-amber-300/25 bg-amber-400/10 px-3.5 py-2.5 text-[13px] text-amber-100">
    {children}
  </p>
);

export default function AccountSecurityPage() {
  const { user, refreshUser } = useAuth();

  // password
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirmNew, setConfirmNew] = useState('');
  const [passwordMessage, setPasswordMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const [passwordBusy, setPasswordBusy] = useState(false);

  // mfa
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [mfaMessage, setMfaMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const [disablePassword, setDisablePassword] = useState('');

  // sessions
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsError, setSessionsError] = useState('');

  const loadSessions = useCallback(async () => {
    try {
      const { data } = await authApi.sessions();
      setSessions(data);
      setSessionsError('');
    } catch {
      setSessionsError('Could not load your sessions.');
    }
  }, []);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const submitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMessage(null);
    if (next.length < 8) {
      setPasswordMessage({ kind: 'error', text: 'Use at least 8 characters.' });
      return;
    }
    if (next !== confirmNew) {
      setPasswordMessage({ kind: 'error', text: 'The two new passwords do not match.' });
      return;
    }
    setPasswordBusy(true);
    try {
      await authApi.changePassword(current, next);
      setCurrent('');
      setNext('');
      setConfirmNew('');
      await refreshUser();
      setPasswordMessage({ kind: 'ok', text: 'Password updated. Other sessions were signed out.' });
    } catch {
      setPasswordMessage({ kind: 'error', text: 'Current password is incorrect, or the new one was rejected.' });
    } finally {
      setPasswordBusy(false);
    }
  };

  const beginSetup = async () => {
    setMfaMessage(null);
    try {
      const { data } = await authApi.startMfaSetup();
      setSetup(data);
    } catch {
      setMfaMessage({ kind: 'error', text: 'Could not start MFA setup.' });
    }
  };

  const confirmSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setMfaMessage(null);
    try {
      const { data } = await authApi.enableMfa(code.trim());
      setRecoveryCodes(data.recovery_codes as string[]);
      setSetup(null);
      setCode('');
      await refreshUser();
      setMfaMessage({ kind: 'ok', text: 'Two-factor authentication is on.' });
    } catch {
      setMfaMessage({ kind: 'error', text: 'That code is not valid. Check your device clock and try again.' });
    }
  };

  const disable = async (e: React.FormEvent) => {
    e.preventDefault();
    setMfaMessage(null);
    try {
      await authApi.disableMfa(disablePassword);
      setDisablePassword('');
      await refreshUser();
      setMfaMessage({ kind: 'ok', text: 'Two-factor authentication is off.' });
    } catch {
      setMfaMessage({ kind: 'error', text: 'Password is incorrect.' });
    }
  };

  const revoke = async (familyId: string) => {
    await authApi.revokeSession(familyId);
    await loadSessions();
  };

  if (!user) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <header>
        <h1 className="text-2xl font-semibold text-white">Account security</h1>
        <p className="mt-1 text-sm text-slate1">
          Password, second factor and the devices signed in to this account.
        </p>
      </header>

      {user.must_change_password && (
        <Notice>
          Your password was issued by an administrator and must be replaced before you can use the
          rest of the portal.
        </Notice>
      )}
      {user.role === 'super_admin' && !user.mfa_enabled && (
        <Notice>
          Administrators must enrol a second factor before the rest of the portal unlocks.
        </Notice>
      )}

      <Card title="Password" icon={<KeyRound size={16} />}>
        <form onSubmit={submitPassword} className="space-y-4" noValidate>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
            required
            className={fieldClass}
          />
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            placeholder="New password (8+ characters)"
            autoComplete="new-password"
            required
            minLength={8}
            className={fieldClass}
          />
          <input
            type="password"
            value={confirmNew}
            onChange={(e) => setConfirmNew(e.target.value)}
            placeholder="Repeat new password"
            autoComplete="new-password"
            required
            minLength={8}
            className={fieldClass}
          />
          {passwordMessage && (
            <p
              role="status"
              className={
                passwordMessage.kind === 'ok'
                  ? 'text-[13px] text-emerald-300'
                  : 'text-[13px] text-rose-300'
              }
            >
              {passwordMessage.text}
            </p>
          )}
          <button
            type="submit"
            disabled={passwordBusy}
            className="rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent disabled:opacity-50"
          >
            {passwordBusy ? 'Updating…' : 'Update password'}
          </button>
        </form>
      </Card>

      <Card title="Two-factor authentication" icon={<ShieldCheck size={16} />}>
        {recoveryCodes ? (
          <div>
            <p className="text-[13px] text-emerald-300">
              Save these recovery codes now — they are shown once and each works once.
            </p>
            <ul className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm text-white">
              {recoveryCodes.map((item) => (
                <li key={item} className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ) : user.mfa_enabled ? (
          <form onSubmit={disable} className="space-y-4" noValidate>
            <p className="text-[13px] text-slate1">
              Two-factor authentication is enabled. Enter your password to turn it off.
            </p>
            <input
              type="password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              placeholder="Password"
              autoComplete="current-password"
              required
              className={fieldClass}
            />
            <button
              type="submit"
              className="inline-flex items-center gap-2 rounded-lg border border-rose-400/40 px-4 py-2.5 text-sm font-semibold text-rose-200 transition-colors hover:bg-rose-500/10"
            >
              <ShieldOff size={15} /> Disable two-factor
            </button>
          </form>
        ) : setup ? (
          <form onSubmit={confirmSetup} className="space-y-4" noValidate>
            <p className="text-[13px] text-slate1">
              Add this secret to your authenticator app (Google Authenticator, Authy, 1Password),
              then enter the code it shows.
            </p>
            <code className="block break-all rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 font-mono text-sm text-white">
              {setup.secret}
            </code>
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
              autoComplete="one-time-code"
              required
              className={fieldClass}
            />
            <button
              type="submit"
              className="rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent"
            >
              Enable two-factor
            </button>
          </form>
        ) : (
          <div className="space-y-3">
            <p className="text-[13px] text-slate1">
              Not enabled. You will be asked for a code from your authenticator app each time you
              sign in.
            </p>
            <button
              type="button"
              onClick={beginSetup}
              className="rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent"
            >
              Set up two-factor
            </button>
          </div>
        )}
        {mfaMessage && (
          <p
            role="status"
            className={
              mfaMessage.kind === 'ok'
                ? 'mt-3 text-[13px] text-emerald-300'
                : 'mt-3 text-[13px] text-rose-300'
            }
          >
            {mfaMessage.text}
          </p>
        )}
      </Card>

      <Card title="Signed-in devices" icon={<Laptop size={16} />}>
        {sessionsError && <p className="text-[13px] text-rose-300">{sessionsError}</p>}
        <ul className="space-y-3">
          {sessions.map((session) => (
            <li
              key={session.family_id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.02] px-3.5 py-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm text-white">
                  {session.user_agent || 'Unknown device'}
                  {session.is_current && (
                    <span className="ml-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-200">
                      This device
                    </span>
                  )}
                </p>
                <p className="mt-0.5 text-xs text-slate1">
                  {session.ip_address || 'unknown IP'} ·{' '}
                  {session.is_active ? 'active' : 'signed out'}
                </p>
              </div>
              {session.is_active && (
                <button
                  type="button"
                  onClick={() => revoke(session.family_id)}
                  className="rounded-md border border-white/15 px-3 py-1.5 text-xs font-medium text-slate1 transition-colors hover:border-rose-400/40 hover:text-rose-200"
                >
                  Sign out
                </button>
              )}
            </li>
          ))}
          {!sessions.length && !sessionsError && (
            <li className="text-[13px] text-slate1">No sessions to show.</li>
          )}
        </ul>
      </Card>
    </div>
  );
}
