import React, { useEffect, useState } from 'react';
import { avatarUrl, initialsOf } from '@/lib/avatar';
import { cn } from '@/lib/utils';

type AvatarProps = {
  avatarKey?: string | null;
  fullName?: string | null;
  className?: string;
  /** Accessible label. Pass null for a purely decorative avatar. */
  alt?: string | null;
};

/**
 * Avatar image with an initials fallback.
 *
 * The fallback is not cosmetic: a missing object or a 403 leaves <img> with a
 * broken icon, so the state is tracked explicitly and the initials are shown
 * instead. An empty `alt` would hide the image from screen readers, so when the
 * caller does not supply one we fall back to the user's name.
 */
export const Avatar = ({ avatarKey, fullName, className, alt }: AvatarProps) => {
  const src = avatarUrl(avatarKey);
  const [failed, setFailed] = useState(false);

  // A new key means a new image; retry the load instead of staying broken.
  useEffect(() => {
    setFailed(false);
  }, [src]);

  const showImage = !!src && !failed;

  return (
    <div
      className={cn(
        'relative flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-[var(--accent-edge)] bg-[var(--accent-soft)] text-xs font-bold text-[var(--accent-bright)]',
        className
      )}
    >
      {showImage ? (
        <img
          src={src}
          alt={alt ?? fullName ?? ''}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <span aria-hidden={alt === null ? 'true' : undefined}>{initialsOf(fullName)}</span>
      )}
    </div>
  );
};
