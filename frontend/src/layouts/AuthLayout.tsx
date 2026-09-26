import React from 'react';
import { Outlet } from 'react-router-dom';
import heroDesktop from '../assets/images/login-hero.jpg';
import heroMobile from '../assets/images/login-hero-768.jpg';

/**
 * Split-screen auth shell.
 *
 * The left panel is the campus photograph; the right panel is the form.
 * Two things matter here and were both found by measuring the real page:
 *
 *  1. `min-h-0` on the image wrapper. Without it a grid child sizes to its
 *     content and the row grows past the viewport, which silently breaks
 *     `object-cover` and crops the image wrong. This is the failure that made
 *     a 2006px panel appear inside an 800px window.
 *  2. The scrim is a CSS overlay, not baked into the image. Baking a heavy
 *     darkening into the JPG flattened the photo (p95 luminance fell 193 -> 31
 *     and the whole scene went featureless), so the file ships near-original
 *     at 32.6 dB and the legibility is handled entirely in CSS.
 */
export const AuthLayout = () => (
  <div className="min-h-screen lg:h-screen lg:overflow-hidden bg-ink lg:grid lg:grid-cols-[1.08fr_1fr]">
    {/* ---------- photographic panel ---------- */}
    <section className="relative hidden lg:block min-h-0" aria-hidden="true">
      <picture>
        <source media="(min-width: 1536px)" srcSet={heroDesktop} />
        <img
          src={heroDesktop}
          alt=""
          className="absolute inset-0 h-full w-full object-cover object-[62%_center]"
        />
      </picture>

      {/* Two-layer scrim: directional for the copy, plus a soft floor.
          The copy sits bottom-left, which is also where the photo measured
          darkest, so the gradient does the most work there. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(155deg, rgba(5,11,20,0.30) 0%, rgba(5,11,20,0.55) 45%, rgba(5,11,20,0.93) 100%)'
        }}
      />
      <div
        className="absolute inset-x-0 bottom-0 h-1/2"
        style={{ background: 'linear-gradient(to top, rgba(5,11,20,0.95), rgba(5,11,20,0) 100%)' }}
      />

      <div className="absolute inset-x-0 bottom-0 z-10 px-12 pb-14 xl:px-16 xl:pb-16">
        <p className="mb-3.5 text-[11px] font-medium uppercase tracking-[0.3em] text-accent-bright">
          Shahjalal University of Science &amp; Technology
        </p>
        <h1 className="max-w-[15ch] text-[clamp(1.9rem,3vw,3.1rem)] font-semibold leading-[1.08] tracking-[-0.02em] text-white">
          Department of Electrical &amp; Electronic Engineering
        </h1>
        <p className="mt-4 max-w-[38ch] text-[15px] leading-relaxed text-slate1">
          One portal for coursework, attendance, labs, rooms and alumni.
        </p>
      </div>
    </section>

    {/* ---------- form panel ---------- */}
    <main className="relative flex min-h-screen flex-col items-center justify-center bg-ink px-5 py-10 sm:px-8 lg:min-h-0 lg:px-12">
      {/* On mobile the photo becomes a short banner instead of disappearing,
          so the page still feels like the same place. */}
      <div className="relative mb-8 h-32 w-full overflow-hidden rounded-lg lg:hidden" aria-hidden="true">
        <img
          src={heroMobile}
          alt=""
          className="absolute inset-0 h-full w-full object-cover object-[62%_center]"
        />
        <div
          className="absolute inset-0"
          style={{ background: 'linear-gradient(180deg, rgba(5,11,20,0.25), rgba(5,11,20,0.85))' }}
        />
        <p className="absolute inset-x-0 bottom-0 px-4 pb-3 text-[10px] uppercase tracking-[0.24em] text-accent-bright">
          SUST &middot; EEE
        </p>
      </div>

      <div className="w-full max-w-[26rem]">
        <Outlet />
      </div>
    </main>
  </div>
);
