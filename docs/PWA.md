# Installable PWA and web push

## What works

- Vite PWA `injectManifest` builds **one** root-scoped worker,
  `/firebase-messaging-sw.js`, containing Workbox and the bundled Firebase web SDK.
  There are no competing root workers or CDN `importScripts` dependencies.
- The manifest defines name, short name, standalone display, scope/start URL,
  theme/background colors and 192/512 PNG icons plus a safe-zone maskable icon.
- The app shell, lazy route chunks and offline routine shell are precached.
  Online navigations use the network; offline navigations open `offline.html`.
  No authenticated API, session or notification responses are cached.
- Opening Class routine saves the latest timetable in IndexedDB. The offline
  shell shows that copy and its Asia/Dhaka timestamp without restoring a login
  session. It omits instructor/personal names. No saved routine shows an empty
  state. Signing out, rejected session restoration or changing accounts clears
  the snapshot. The routine page explains local storage to the user.
- Notifications exposes **Enable push on this device**, browser-denial errors,
  a device opt-out button, the native install prompt where supported, and
  iPhone/iPad Home Screen instructions.
- Permission is requested only by an explicit button after login. Previously
  granted consent refreshes/re-registers the FCM token and `last_seen` on app
  open, online reconnect and foreground resume. Opt-out persists and prevents
  silent re-enabling. Logout cancels in-flight registration and removes both the
  backend device and Firebase subscription before clearing auth.
- Notification clicks read `data.url`, reuse/focus an existing app window or
  open a new one, and accept only known same-origin pages. Invalid URLs fall
  back to `/notifications`. Backend generic notifications now include their
  destination in both the inbox and FCM data payload.
- One authenticated SSE connection drives the bell badge and notification
  center, with foreground FCM/worker messages and 30-second polling as fallback.
  SSE checks for updates every three seconds, releases DB connections between
  polls, closes after 45 seconds and reauthenticates on reconnect. Reverse-proxy
  buffering is disabled. Bearer tokens remain in Authorization headers, never
  stream URLs. The badge counts **all** unread items, even beyond the 100-row inbox.
- Mark-one/mark-all endpoints and device deletion are caller-scoped. No schema
  migration is required beyond the existing notification migration.

## Firebase and HTTPS deployment

1. In Firebase Console, add a Web app and enable Cloud Messaging HTTP v1.
2. Copy `frontend/.env.example` to `frontend/.env.local` for local builds and
   fill the public Web app config plus the **public** Web Push/VAPID certificate.
   Firebase API keys identify the project; do not put a service-account JSON or
   a private VAPID key in any `VITE_*` value.
3. For Docker/Compose, put those same `VITE_FIREBASE_*` values in the root Compose
   `.env` or shell environment. Both Compose files pass them as frontend build
   arguments. They must be present **at build time**; runtime container variables
   do not change a compiled Vite bundle. Rebuild the frontend after changing them.
4. Configure the worker's backend Firebase service-account/ADC as described in
   [Notifications](NOTIFICATIONS.md). Frontend and backend must use the same
   project. Keep that private credential only in the Celery deployment.
5. Serve through HTTPS. Localhost is a browser secure-context exception for
   development. Keep root scope, `.js` worker MIME type, no-cache worker updates
   and the included narrow Firebase `connect-src` CSP origins.
6. On iPhone/iPad (16.4+), Safari → Share → Add to Home Screen. Open the installed
   app, sign in, visit Notifications and tap Enable push. Plain Safari tabs do
   not support iOS web push.

Without config, the PWA/offline/notification center still works; the push panel
honestly says web push is not configured. This change does not invent project
credentials or claim live FCM/device delivery.

## Verification and audit

From `frontend/`:

```bash
npm ci
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
npm audit --audit-level=high
```

Playwright uses system Chrome locally (`CHROME_PATH` may override it), and its
bundled Chromium in CI after `npx playwright install --with-deps chromium`.
Browser tests run against the production preview with a clearly mocked API,
not a live user account. They verify actual SW control, offline routine reload,
absence of API caching, logout cleanup, live SSE unread/mark-read UI, and iPhone
guidance. Unit tests cover permission denial, no page-load/guest prompting,
granted-consent refresh, opt-out persistence, logout/permission races, click
routing/new-window behavior, and no duplicate Firebase notification display.
Backend integration tests verify actual migrated PostgreSQL ownership, readback,
unread counts, SSE snapshots/HTTP headers and device cleanup.

Lighthouse **11.7.1** was run because modern Lighthouse releases removed the PWA
category. The local production Docker/nginx public login page scored **100/100** for the available
automated PWA audits; three cross-browser/navigation checks are manual, not
claimed as automated passes. Summary: [PWA Lighthouse audit](PWA_LIGHTHOUSE.json).
The full JSON/HTML reports are in `/tmp/opencode/portal-pwa-nginx-lighthouse.report.*`.

Reproduce while the production preview is running on port 4173:

```bash
CHROME_PATH=/usr/bin/google-chrome npx --yes lighthouse@11.7.1 \
  http://127.0.0.1:4173/auth/login --only-categories=pwa \
  --chrome-flags='--headless --no-sandbox' --output=json --output=html \
  --output-path=/tmp/opencode/portal-pwa-lighthouse
```

The production container audit used the same command against local port 4174.
The container served the worker as `application/javascript` with `no-cache`,
the manifest as `application/manifest+json`, and retained the Firebase-aware CSP.

Actual checks on 2026-10-04: **19 frontend unit tests and 3 browser tests passed**;
the full PostgreSQL/Redis backend suite passed **202 tests**, with one optional
MinIO skip and four pre-existing expected feature failures. A fourth new
backend stream/large-unread-count test was subsequently run and passed. Ruff,
mypy (95 files), frontend lint/typecheck/build, Docker frontend build and
`npm audit` (0 vulnerabilities) passed.
Both Compose configurations passed validation with disposable placeholder
credentials; the updated workflow passed actionlint 1.7.7.

Lighthouse does not prove real push delivery. The separate browser offline test
proves cached routine behavior; physical iOS installation, permission acceptance
and FCM reception remain live-device checks needing configured credentials.

The new Firebase package's Firestore-only transitive gRPC dependency was pinned
to the patched compatible `@grpc/grpc-js` 1.14.5+ range via npm overrides, keeping
the existing blocking npm security gate clean.
