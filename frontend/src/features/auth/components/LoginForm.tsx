import React, { useId, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export const LoginForm = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  // useId guarantees a stable, unique id so each <label for> actually binds.
  // The previous markup had <label> with no `for` and inputs with no `id`,
  // so screen readers announced only "textbox" and "Password123!".
  const idField = useId();
  const pwField = useId();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login({ identifier, password });
      navigate('/dashboard', { replace: true });
    } catch {
      setError('Invalid ID or password. Please try again.');
    }
  };

  const fieldClass =
    'h-11 w-full rounded-lg border border-white/12 bg-white/[0.04] px-3.5 text-sm text-white ' +
    'placeholder:text-white/45 transition-colors ' +
    'focus:border-accent focus:bg-accent-soft focus:outline-none focus:ring-[3px] focus:ring-accent/20';

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
    </form>
  );
};
