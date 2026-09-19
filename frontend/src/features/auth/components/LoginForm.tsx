import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export const LoginForm = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('2023338049');
  const [password, setPassword] = useState('Password123!');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

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

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-xs font-semibold">Student ID / Employee Email</label>
        <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
      </div>
      <div>
        <label className="text-xs font-semibold">Password</label>
        <div className="relative">
          <Input
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="pr-10"
            required
          />
          <button
            type="button"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            onClick={() => setShowPassword((visible) => !visible)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </div>
      {error && <p className="text-sm text-rose-400" role="alert">{error}</p>}
      <Button type="submit" className="w-full">Sign In to Portal</Button>
    </form>
  );
};
