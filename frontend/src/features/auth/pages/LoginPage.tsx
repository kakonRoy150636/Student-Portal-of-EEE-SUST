import React from 'react';
import { Link } from 'react-router-dom';
import { LoginForm } from '../components/LoginForm';

const ROLES = ['Student', 'Class Rep', 'Teacher', 'ER'] as const;

export default function LoginPage() {
  return (
    <div>
      <header className="mb-8">
        <h1 className="text-[1.75rem] font-semibold leading-tight tracking-[-0.015em] text-white">
          Welcome back
        </h1>
        <p className="mt-1.5 text-sm text-slate1">
          Sign in with your institutional ID or registered email.
        </p>
      </header>

      <LoginForm />

      <div className="mt-8 flex flex-wrap gap-1.5" aria-label="Account roles">
        {ROLES.map((role) => (
          <span
            key={role}
            className="rounded-full border border-white/12 bg-white/[0.03] px-2.5 py-1 text-[11px] text-slate1"
          >
            {role}
          </span>
        ))}
      </div>

      <p className="mt-8 text-[13px] text-slate1">
        New here?{' '}
        <Link
          to="/auth/register"
          className="font-medium text-accent-bright underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ink"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}
