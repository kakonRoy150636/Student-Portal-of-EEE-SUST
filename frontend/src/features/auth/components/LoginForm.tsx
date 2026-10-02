import React, { useId, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { errorCode } from '@/lib/axios';

const fieldClass =
  'h-11 w-full rounded-lg border border-white/12 bg-white/[0.04] px-3.5 text-sm text-white ' +
  'placeholder:text-white/45 transition-colors ' +
  'focus:border-accent focus:bg-accent-soft focus:outline-none focus:ring-[3px] focus:ring-accent/20';

export const LoginForm = () => {
  const { login, completeMfaLogin } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  // Set once the password has been accepted but a second factor is required.
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');

  // useId guarantees a stable, unique id so each <label for> actually binds.
  const idField = useId();
  const pwField = useId();
  const codeField = useId();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const outcome = await login({ identifier, password });
      if (outcome.mfaRequired && outcome.mfaToken) {
        setMfaToken(outcome.mfaToken);
        return;
      }
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(
        errorCode(err) === 'mfa_enrollment_required'
          ? 'Sign in again to finish setting up your second factor.'
          : 'Invalid ID or password. Please try again.'
      );
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!mfaToken) return;
    try {
      await completeMfaLogin(mfaToken, mfaCode.trim());
      navigate('/dashboard', { replace: true });
    } catch {
      setError('That code is not valid or has expired. Try again, or use a recovery code.');
    }
  };

  if (mfaToken) {
    return (
      <form onSubmit={handleMfaSubmit} className="space-y-5" noValidate>
        <div>
          <label
            htmlFor={codeField}
            className="mb-2 block text-[11px] font-medium uppercase tracking-[0.14em] text-slate1"
          >
            Authenticator code
          </label>
          <input
            id={codeField}
            name="code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
            placeholder="123456"
            required
            autoFocus
            className={fieldClass}
          />
          <p className="mt-2 text-xs text-slate1">
            Enter the six-digit code from your authenticator app, or one of your recovery codes.
          </p>
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
          className="w-full rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ink active:bg-[#2F5D99] disabled:opacity-50"
        >
          Verify and sign in
        </button>

        <button
          type="button"
          onClick={() => {
            setMfaToken(null);
            setMfaCode('');
            setError('');
          }}
          className="w-full text-center text-[13px] text-slate1 underline-offset-4 hover:text-white hover:underline"
        >
          Back to password
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div>
        <label
          htmlFor={idField}
          className="mb-2 block text-[11px] font-medium uppercase tracking-[0.14em] text-slate1"
        >
          Student ID / Employee Email
        </label>
        <input
          id={idField}
          name="identifier"
          type="text"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          autoComplete="username"
          spellCheck={false}
          autoCapitalize="none"
          placeholder="2023338049"
          required
          className={fieldClass}
        />
      </div>

      <div>
        <label
          htmlFor={pwField}
          className="mb-2 block text-[11px] font-medium uppercase tracking-[0.14em] text-slate1"
        >
          Password
        </label>
        <div className="relative">
          <input
            id={pwField}
            name="password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            placeholder="••••••••"
            required
            className={`${fieldClass} pr-11`}
          />
          <button
            type="button"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((visible) => !visible)}
            className="absolute right-1.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-white/45 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
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
        className="w-full rounded-lg bg-accent-deep px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ink active:bg-[#2F5D99] disabled:opacity-50"
      >
        Sign in
      </button>

      <p className="text-center text-[13px] text-slate1">
        <Link
          to="/auth/forgot-password"
          className="underline-offset-4 hover:text-white hover:underline"
        >
          Forgot your password?
        </Link>
      </p>
    </form>
  );
};
