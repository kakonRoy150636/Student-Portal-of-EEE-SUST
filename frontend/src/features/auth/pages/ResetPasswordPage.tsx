import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '../api/authApi';

const fieldClass =
  'h-11 w-full rounded-lg border border-white/12 bg-white/[0.04] px-3.5 text-sm text-white ' +
  'placeholder:text-white/45 transition-colors ' +
  'focus:border-accent focus:bg-accent-soft focus:outline-none focus:ring-[3px] focus:ring-accent/20';

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Use at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('The two passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      await authApi.confirmPasswordReset(token, password);
      navigate('/auth/login', { replace: true });
    } catch {
      setError('This reset link is invalid or has expired. Request a new one.');
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div>
        <h1 className="text-[1.75rem] font-semibold text-white">Reset link missing</h1>
        <p className="mt-3 text-sm text-slate1">
          Open the link from your email, or request a new one.
        </p>
        <Link
          to="/auth/forgot-password"
          className="mt-8 inline-block text-[13px] font-medium text-accent-bright underline-offset-4 hover:underline"
        >
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-8">
        <h1 className="text-[1.75rem] font-semibold leading-tight tracking-[-0.015em] text-white">
          Choose a new password
        </h1>
        <p className="mt-1.5 text-sm text-slate1">
          Signing in with the new password will end your other sessions.
        </p>
      </header>

      <form onSubmit={submit} className="space-y-5" noValidate>
        <div>
          <label
            htmlFor="new-password"
            className="mb-2 block text-[11px] font-medium uppercase tracking-[0.14em] text-slate1"
          >
            New password
          </label>
          <input
            id="new-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
            className={fieldClass}
          />
        </div>
        <div>
          <label
            htmlFor="confirm-password"
            className="mb-2 block text-[11px] font-medium uppercase tracking-[0.14em] text-slate1"
          >
            Confirm password
          </label>
          <input
            id="confirm-password"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
            className={fieldClass}
          />
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3.5 py-2.5 text-[13px] text-rose-200"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ink active:bg-[#2F5D99] disabled:opacity-50"
        >
          {busy ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </div>
  );
}
