import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../api/authApi';

const fieldClass =
  'h-11 w-full rounded-lg border border-white/12 bg-white/[0.04] px-3.5 text-sm text-white ' +
  'placeholder:text-white/45 transition-colors ' +
  'focus:border-accent focus:bg-accent-soft focus:outline-none focus:ring-[3px] focus:ring-accent/20';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await authApi.requestPasswordReset(email);
    } finally {
      // The response is identical whether or not the address exists, and the
      // UI mirrors that: it must not become an account-existence oracle.
      setSent(true);
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <div>
        <h1 className="text-[1.75rem] font-semibold leading-tight tracking-[-0.015em] text-white">
          Check your inbox
        </h1>
        <p className="mt-3 text-sm text-slate1">
          If an account exists for {email}, a reset link is on its way. The link expires in 30
          minutes and can be used once.
        </p>
        <Link
          to="/auth/login"
          className="mt-8 inline-block text-[13px] font-medium text-accent-bright underline-offset-4 hover:underline"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-8">
        <h1 className="text-[1.75rem] font-semibold leading-tight tracking-[-0.015em] text-white">
          Reset your password
        </h1>
        <p className="mt-1.5 text-sm text-slate1">
          Enter the email address on your account and we will send a reset link.
        </p>
      </header>

      <form onSubmit={submit} className="space-y-5" noValidate>
        <div>
          <label
            htmlFor="reset-email"
            className="mb-2 block text-[11px] font-medium uppercase tracking-[0.14em] text-slate1"
          >
            Email
          </label>
          <input
            id="reset-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
            className={fieldClass}
            placeholder="you@sust.edu"
          />
        </div>

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ink active:bg-[#2F5D99] disabled:opacity-50"
        >
          {busy ? 'Sending…' : 'Send reset link'}
        </button>
      </form>

      <p className="mt-8 text-[13px] text-slate1">
        <Link to="/auth/login" className="underline-offset-4 hover:text-white hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}
