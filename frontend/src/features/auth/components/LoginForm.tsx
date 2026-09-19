import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export const LoginForm = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('2023338049');
  const [password, setPassword] = useState('Password123!');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login({ identifier, password });
    navigate('/dashboard', { replace: true });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="text-xs font-semibold">Student ID / Employee Email</label>
        <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
      </div>
      <div>
        <label className="text-xs font-semibold">Password</label>
        <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </div>
      <Button type="submit" className="w-full">Sign In to Portal</Button>
    </form>
  );
};
