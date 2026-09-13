import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { authApi } from '../api/authApi';
import { CourseSelection } from '@/types/auth';

type SignupRole = 'teacher' | 'student';

const parseCourseSelections = (value: string): CourseSelection[] => {
  if (!value.trim()) return [];
  const parsed: unknown = JSON.parse(value);
  if (!Array.isArray(parsed)) throw new Error('Course selections must be a JSON array.');
  return parsed as CourseSelection[];
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const [signupRole, setSignupRole] = useState<SignupRole>('student');
  const [isCr, setIsCr] = useState(false);
  const [fullName, setFullName] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [sessionYear, setSessionYear] = useState('');
  const [currentTerm, setCurrentTerm] = useState('');
  const [avatarKey, setAvatarKey] = useState('');
  const [courseSelections, setCourseSelections] = useState('[]');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setIsSubmitting(true);
    try {
      const response = signupRole === 'teacher'
        ? await authApi.registerTeacher({ full_name: fullName, email, password, avatar_key: avatarKey || undefined })
        : await authApi.registerStudent({
            full_name: fullName,
            identifier,
            email,
            password,
            role: isCr ? 'cr' : 'student',
            session_year: sessionYear,
            current_term: currentTerm,
            avatar_key: avatarKey || undefined,
            course_selections: parseCourseSelections(courseSelections),
          });
      setMessage(response.data.message);
      if (!response.data.requires_approval) {
        window.setTimeout(() => navigate('/auth/login'), 1200);
      }
    } catch (err) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      setError(axiosError.response?.data?.detail || (err instanceof Error ? err.message : 'Registration failed.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="text-center">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-emerald-500">EEE portal access</p>
        <h1 className="mt-2 text-2xl font-bold">Create your account</h1>
        <p className="mt-1 text-xs text-slate-500">Teacher and CR accounts require admin approval.</p>
      </div>

      <div className="grid grid-cols-2 gap-2 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
        {(['student', 'teacher'] as SignupRole[]).map((role) => (
          <button
            key={role}
            type="button"
            onClick={() => setSignupRole(role)}
            className={`rounded-md px-3 py-2 text-sm font-semibold capitalize transition ${signupRole === role ? 'bg-emerald-600 text-white' : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'}`}
          >
            {role === 'student' ? 'Student / CR' : 'Teacher'}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block text-xs font-semibold">Full name<Input value={fullName} onChange={(event) => setFullName(event.target.value)} required /></label>
        {signupRole === 'student' && (
          <>
            <label className="block text-xs font-semibold">Student ID<Input value={identifier} onChange={(event) => setIdentifier(event.target.value)} minLength={3} maxLength={32} required /></label>
            <label className="flex items-center gap-2 text-xs font-semibold"><input type="checkbox" checked={isCr} onChange={(event) => setIsCr(event.target.checked)} /> Register as CR <span className="font-normal text-slate-500">(admin approval)</span></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-xs font-semibold">Session year<Input value={sessionYear} onChange={(event) => setSessionYear(event.target.value)} placeholder="2021-22" required /></label>
              <label className="block text-xs font-semibold">Current term<Input value={currentTerm} onChange={(event) => setCurrentTerm(event.target.value)} placeholder="1-1" required /></label>
            </div>
            <label className="block text-xs font-semibold">Course selections <span className="font-normal text-slate-500">(JSON, optional)</span><textarea value={courseSelections} onChange={(event) => setCourseSelections(event.target.value)} className="mt-1 min-h-20 w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 font-mono text-xs dark:border-slate-800" placeholder={'[{"course_offering_id":"uuid","enrollment_type":"main"}]'} /></label>
          </>
        )}
        <label className="block text-xs font-semibold">Email<Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
        <label className="block text-xs font-semibold">Password<Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={6} required /></label>
        <label className="block text-xs font-semibold">Avatar key <span className="font-normal text-slate-500">(optional upload key)</span><Input value={avatarKey} onChange={(event) => setAvatarKey(event.target.value)} /></label>
        {error && <p className="rounded-md bg-rose-500/10 px-3 py-2 text-xs text-rose-500">{error}</p>}
        {message && <p className="rounded-md bg-emerald-500/10 px-3 py-2 text-xs text-emerald-500">{message}</p>}
        <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting ? 'Creating account...' : 'Create account'}</Button>
      </form>

      <p className="text-center text-xs text-slate-500">Already registered? <Link className="font-semibold text-emerald-600 hover:underline" to="/auth/login">Sign in</Link></p>
    </div>
  );
}