import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '@/lib/axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar } from '@/components/shared/Avatar';
import { ACCEPTED_AVATAR_TYPES, MAX_AVATAR_BYTES } from '@/lib/avatar';

type Role = 'teacher' | 'student' | 'cr' | 'er';

const formatBytes = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

export default function RegisterPage() {
  const navigate = useNavigate();
  const [role, setRole] = useState<Role>('student');
  const [form, setForm] = useState({ full_name: '', identifier: '', email: '', password: '', session_year: '', current_term: '' });
  const [avatar, setAvatar] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  // Object URLs are revoked on change, otherwise every picked image leaks a
  // blob for the lifetime of the page.
  useEffect(() => {
    if (!avatar) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(avatar);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [avatar]);

  const handleAvatar = (file: File | null) => {
    setAvatarError('');
    if (!file) {
      setAvatar(null);
      return;
    }
    if (!file.type.startsWith('image/')) {
      setAvatar(null);
      setAvatarError('That file is not an image. Choose a JPG, PNG, WebP or GIF.');
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setAvatar(null);
      setAvatarError(`That image is ${formatBytes(file.size)}. The limit is ${formatBytes(MAX_AVATAR_BYTES)}.`);
      return;
    }
    setAvatar(file);
  };

  /**
   * Upload straight to object storage using the presigned URL.
   *
   * Two failure modes here are worth separating, because they have different
   * fixes: a storage outage (no URL available) should not block registration,
   * whereas a failed PUT means the object is missing and must not be linked.
   */
  const uploadAvatar = async (): Promise<string | undefined> => {
    if (!avatar) return undefined;

    let data: { file_key: string; upload_url: string };
    try {
      ({ data } = await api.post('/auth/avatar-upload', null, {
        params: { filename: avatar.name, content_type: avatar.type, size_hint: avatar.size },
      }));
    } catch {
      setAvatarError('We could not reach image storage, so your account was created without a photo. You can add one later.');
      return undefined;
    }

    // The presigned URL is signed for this exact length, so send the same one.
    const uploadResponse = await fetch(data.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': avatar.type },
      body: avatar,
    });
    if (!uploadResponse.ok) {
      throw new Error('Your photo could not be uploaded. Please try again, or continue without a photo.');
    }
    return data.file_key;
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setMessage('');
    setAvatarError('');
    try {
      const avatar_key = await uploadAvatar();
      const payload = { ...form, ...(avatar_key ? { avatar_key } : {}) };
      const endpoint = role === 'teacher' ? '/auth/register/teacher' : '/auth/register/student';
      const body = role === 'teacher'
        ? { full_name: payload.full_name, email: payload.email, password: payload.password, avatar_key }
        : { ...payload, role: role === 'er' ? 'er' : role, course_selections: [] };
      const { data } = await api.post(endpoint, body);
      setMessage(data.message);
      if (!data.requires_approval) window.setTimeout(() => navigate('/auth/login'), 1200);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || requestError?.message || 'Registration failed. Please check your details and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-emerald-500">New account</p>
        <h1 className="text-2xl font-bold">Join the EEE Portal</h1>
        <p className="text-xs text-slate-500 mt-1">Teacher, CR and ER accounts require administrator approval.</p>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {(['student', 'cr', 'teacher', 'er'] as Role[]).map((option) => (
          <Button key={option} type="button" variant={role === option ? 'default' : 'outline'} size="sm" onClick={() => setRole(option)}>
            {option === 'cr' ? 'CR' : option === 'er' ? 'ER' : option[0].toUpperCase() + option.slice(1)}
          </Button>
        ))}
      </div>
      <form onSubmit={submit} className="space-y-3">
        <Input placeholder="Full name" value={form.full_name} onChange={(event) => update('full_name', event.target.value)} required />
        {role !== 'teacher' && <Input placeholder="Student ID" value={form.identifier} onChange={(event) => update('identifier', event.target.value)} required />}
        <Input type="email" placeholder="Institutional email" value={form.email} onChange={(event) => update('email', event.target.value)} required />
        <Input type="password" placeholder="Password (minimum 6 characters)" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={6} required />
        {role !== 'teacher' && <div className="grid grid-cols-2 gap-2"><Input placeholder="Session year" value={form.session_year} onChange={(event) => update('session_year', event.target.value)} required /><Input placeholder="Current term" value={form.current_term} onChange={(event) => update('current_term', event.target.value)} required /></div>}

        {/* Profile photo: chosen file is previewed and its size stated, so it is
            obvious what will be saved before the account is created. */}
        <div className="flex items-center gap-4 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
          {preview ? (
            <img src={preview} alt="Selected profile photo preview" className="h-16 w-16 rounded-lg object-cover" />
          ) : (
            <Avatar fullName={form.full_name} className="h-16 w-16 text-base" alt={null} />
          )}
          <div className="flex-1 space-y-1">
            <label htmlFor="avatar" className="block text-xs font-medium">Profile photo (optional)</label>
            <input
              id="avatar"
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_AVATAR_TYPES}
              aria-describedby="avatar-help"
              onChange={(event) => handleAvatar(event.target.files?.[0] || null)}
              className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-md file:border-0 file:bg-slate-200 file:px-3 file:py-1.5 file:text-xs file:font-medium dark:file:bg-slate-800"
            />
            <p id="avatar-help" className="text-[11px] text-slate-500">
              {avatar ? `${avatar.name} · ${formatBytes(avatar.size)}` : `JPG, PNG, WebP or GIF up to ${formatBytes(MAX_AVATAR_BYTES)}.`}
            </p>
          </div>
          {avatar && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setAvatar(null);
                setAvatarError('');
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
            >
              Remove
            </Button>
          )}
        </div>

        {avatarError && <p role="alert" className="text-xs text-amber-500">{avatarError}</p>}
        {error && <p role="alert" className="text-xs text-rose-500">{error}</p>}
        {message && <p role="status" className="text-xs text-emerald-500">{message}</p>}
        <Button type="submit" className="w-full" disabled={submitting}>{submitting ? 'Creating account...' : 'Create account'}</Button>
      </form>
      <p className="text-center text-xs text-slate-500">Already registered? <Link className="text-emerald-500 hover:underline" to="/auth/login">Sign in</Link></p>
    </div>
  );
}
