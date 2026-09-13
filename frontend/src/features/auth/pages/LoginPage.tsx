import React from 'react';
import { Link } from 'react-router-dom';
import { LoginForm } from '../components/LoginForm';

export default function LoginPage() {
  return (
    <div className="space-y-4">
      <div className="text-center">
        <h1 className="text-xl font-bold">SUST EEE Student Portal</h1>
        <p className="text-xs text-slate-500">Sign in with institutional credentials</p>
      </div>
      <LoginForm />
      <p className="text-center text-xs text-slate-500">Need an account? <Link className="font-semibold text-emerald-600 hover:underline" to="/auth/register">Register here</Link></p>
    </div>
  );
}
