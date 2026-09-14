import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '@/lib/axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Role = 'teacher' | 'student' | 'cr';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [role, setRole] = useState<Role>('student');
  const [form, setForm] = useState({ full_name: '', identifier: '', email: '', password: '', session_year: '', current_term: '' });
  const [avatar, setAvatar] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const uploadAvatar = async () => {
    if (!avatar) return undefined;
    const { data } = await api.post('/auth/avatar-upload', null, { params: { filename: avatar.name, content_type: avatar.type } });
    await fetch(data.upload_url, { method: 'PUT', headers: { 'Content-Type': avatar.type }, body: avatar });
    return data.file_key as string;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      const avatar_key = await uploadAvatar();
      const payload = { ...form, ...(avatar_key ? { avatar_key } : {}) };
      const endpoint = role === 'teacher' ? '/auth/register/teacher' : '/auth/register/student';
      const body = role === 'teacher' ? { full_name: payload.full_name, email: payload.email, password: payload.password, avatar_key } : { ...payload, role, course_selections: [] };
      const { data } = await api.post(endpoint, body);
      setMessage(data.message);
      if (!data.requires_approval) window.setTimeout(() => navigate('/auth/login'), 1200);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Registration failed. Please check your details and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-emerald-500">New account</p>
        <h1 className="text-2xl font-bold">Join the EEE Portal</h1>
        <p className="text-xs text-slate-500 mt-1">Teacher and CR accounts require administrator approval.</p>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {(['student', 'cr', 'teacher'] as Role[]).map((option) => (
          <Button key={option} type="button" variant={role === option ? 'default' : 'outline'} size="sm" onClick={() => setRole(option)}>
            {option === 'cr' ? 'Student / CR' : option[0].toUpperCase() + option.slice(1)}
          </Button>
        ))}
      </div>
      <form onSubmit={submit} className="space-y-3">
        <Input placeholder="Full name" value={form.full_name} onChange={(event) => update('full_name', event.target.value)} required />
        {role !== 'teacher' && <Input placeholder="Student ID" value={form.identifier} onChange={(event) => update('identifier', event.target.value)} required />}
        <Input type="email" placeholder="Institutional email" value={form.email} onChange={(event) => update('email', event.target.value)} required />
        <Input type="password" placeholder="Password (minimum 6 characters)" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={6} required />
        {role !== 'teacher' && <div className="grid grid-cols-2 gap-2"><Input placeholder="Session year" value={form.session_year} onChange={(event) => update('session_year', event.target.value)} required /><Input placeholder="Current term" value={form.current_term} onChange={(event) => update('current_term', event.target.value)} required /></div>}
        <Input type="file" accept="image/*" onChange={(event) => setAvatar(event.target.files?.[0] || null)} />
        {error && <p className="text-xs text-rose-500">{error}</p>}
        {message && <p className="text-xs text-emerald-500">{message}</p>}
        <Button type="submit" className="w-full" disabled={submitting}>{submitting ? 'Creating account...' : 'Create account'}</Button>
      </form>
      <p className="text-center text-xs text-slate-500">Already registered? <Link className="text-emerald-500 hover:underline" to="/auth/login">Sign in</Link></p>
    </div>
  );
}
