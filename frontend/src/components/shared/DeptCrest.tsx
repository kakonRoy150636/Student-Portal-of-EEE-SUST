import React from 'react';
import crestColour from '@/assets/images/dept-crest.png';
import crestMono from '@/assets/images/dept-crest-mono.png';
import { cn } from '@/lib/utils';

type DeptCrestProps = {
  /**
   * `colour` keeps the department's own blue/red/green. `mono` is the white
   * silhouette, which is what the dark shell wants: it takes its tint from
   * the surrounding text or accent rather than fighting it.
   */
  variant?: 'colour' | 'mono';
  className?: string;
  /** Decorative by default; pass a string to name it for screen readers. */
  alt?: string | null;
};

/**
 * The SUST EEE department crest.
 *
 * The source was a photograph of the crest, not artwork: it had a light grey
 * paper background and a soft scan edge. Both were removed when the asset was
 * cut (see the alpha matte baked into the PNG), so the image drops straight
 * onto the dark shell without a pale square behind it.
 *
 * The white silhouette is the default because the shell is dark and a
 * colour crest at watermark opacity turns muddy; `mono` still picks up
 * `text-currentColor`-style tinting from whatever accent is applied.
 */
export const DeptCrest = ({ variant = 'mono', className, alt = null }: DeptCrestProps) => (
  <img
    src={variant === 'colour' ? crestColour : crestMono}
    alt={alt ?? ''}
    aria-hidden={alt === null ? 'true' : undefined}
    className={cn('select-none object-contain', className)}
    draggable={false}
  />
);
