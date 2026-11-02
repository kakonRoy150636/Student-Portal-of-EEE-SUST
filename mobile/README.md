# SUST EEE Portal — Mobile (Expo)

React Native / Expo client for the SUST EEE Smart Student Portal. It talks to the
same FastAPI backend as `frontend/` and uses the same token-based auth, so an
account works on both clients without any extra setup.

## Run

```bash
cd mobile
npm install
cp .env.example .env      # then set EXPO_PUBLIC_API_BASE_URL
npx expo start
```

`EXPO_PUBLIC_API_BASE_URL` must include the `/api/v1` prefix:

| Target            | Value                                  |
| ----------------- | -------------------------------------- |
| Android emulator  | `http://10.0.2.2:8000/api/v1`          |
| iOS simulator     | `http://localhost:8000/api/v1`         |
| Physical device   | `http://<your-lan-ip>:8000/api/v1`     |
| Production        | `https://api.example.com/api/v1`       |

The current value is shown on the login screen and in Profile, so a build that
cannot reach the API is diagnosable without a debugger.

## Auth

`POST /auth/login` accepts an **institutional identifier** (student ID,
`faculty-…` handle, or admin username) — *not* an email address — and returns:

```json
{ "user": { "...": "..." }, "tokens": { "access_token": "…" } }
```

The rotating refresh token is set as an **HttpOnly cookie** scoped to
`/api/v1/auth`; it is deliberately never placed in the response body. The
client therefore:

- keeps the 15-minute access token in memory, mirrored to `expo-secure-store`
  on iOS/Android so a cold start does not need a round trip;
- calls `/auth/refresh` with credentials when a request 401s, replaying the
  original request afterwards;
- collapses concurrent 401s into a single refresh, because the backend rotates
  the token on every use and replays the family as theft;
- drops the session only when the server actually rejects the refresh — a
  timeout or 502 leaves the user signed in.

On web (`npx expo start --web`) the access token is kept in memory only: there
is no `localStorage` write, so a reload recovers through the refresh cookie
instead of leaving a readable token in the page.

Teacher and CR accounts remain inactive until an administrator approves them,
so a first sign-in from a freshly registered account is expected to fail with
"Invalid institutional identifier or password".

## Screens

| Route                  | Data source                                   |
| ---------------------- | --------------------------------------------- |
| `(auth)/login`         | `POST /auth/login`                            |
| `(tabs)/index`         | `GET /dashboard/summary` (role-scoped)        |
| `(tabs)/courses`       | `GET /course-offerings/enrollments/me[/credits]` |
| `(tabs)/schedule`      | `GET /schedules/my-routine`                    |
| `(tabs)/profile`       | cached session + `GET /notifications/summary` |
| `notifications`        | `GET /notifications/summary`, read receipts   |

Every screen renders loading, error and empty states; the dashboard never shows
a placeholder number when the API is unreachable, and a `null` attendance
percentage reads as "no classes recorded yet" rather than 0%.

Role handling is honest: `/dashboard/summary` only populates the section for the
caller's role, and the courses tab explains that enrolments belong to student
and CR accounts instead of firing a request the backend would reject with 403.

## Structure

```
app/                Expo Router routes (auth group, tab group, stack screens)
src/api/            One module per backend resource
src/components/     Shared UI: screen shell, cards, tiles, state views
src/hooks/          Zustand auth store + React Query hooks
src/lib/            Axios client, session storage, pure helpers
src/types/          Types mirroring backend/app/schemas
```

## Install on a phone

### Fastest: Expo Go (no build)

Expo Go runs the JS bundle straight from a Metro dev server, so the phone and the
machine running `npm start` must be able to reach each other.

```bash
cd mobile
cp .env.example .env    # EXPO_PUBLIC_API_BASE_URL must be reachable *from the phone*
npx expo start
```

Scan the printed QR with Expo Go (Android) or the Camera app (iOS). If the phone
is on a different network than the dev machine, use `npx expo start --tunnel`.

Note that `localhost` in `EXPO_PUBLIC_API_BASE_URL` resolves to the *phone*
itself, so a laptop-hosted API must be addressed by its LAN IP
(`http://192.168.x.x:8000/api/v1`) or a tunnel.

### Installable APK (no Play Store, no local Android SDK)

`eas.json` defines a `preview` profile that builds a real APK. This needs a free
Expo account and an EAS project link, which the first command creates:

```bash
npm install -g eas-cli
eas login
eas build:configure          # writes extra.eas.projectId into app.json
npx eas build -p android --profile preview
```

The build finishes with a download URL; open it on the phone to install the APK.
The `preview` profile is `distribution: internal`, so the build is private to the
Expo account rather than published to a store.

For iOS, `npx eas build -p ios --profile preview` requires an Apple Developer
account and registered device UDIDs.

### Web build

```bash
npx expo export --platform web
```

The exported `dist/` runs in a mobile browser and can be added to the home
screen. The access token is memory-only there, so a reload re-authenticates
through the refresh cookie.

### What the app needs from the API

All three routes above talk to whatever `EXPO_PUBLIC_API_BASE_URL` was set to
**at bundle time** — it is inlined, not read at runtime. Changing it requires a
restart (`expo start`) or a new build. The current value is shown on the login
screen and in Profile, so a misconfigured build is diagnosable without a
debugger.

Teacher and CR accounts also need an administrator to approve them before their
first sign-in succeeds.

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run lint        # eslint (expo config)
npm test            # jest-expo, unit tests for pure helpers
```

CI runs all three in the `mobile` job of `.github/workflows/ci.yml`.

## Not implemented yet

- **Push notifications.** In-app notifications and the unread badge work, but
  device registration does not: `POST /notifications/register-device` expects a
  raw FCM token, so the client needs a decision between Expo Push and direct
  FCM before `expo-notifications` earns its place as a dependency.
- **Refresh-token lifetime on native.** The refresh token lives in a cookie.
  Where a platform's cookie jar drops it (some Android configurations), the
  user is asked to sign in again after the 15-minute access token expires.
  Fixing that properly means returning a refresh token to native clients only,
  which is an API-surface decision rather than a mobile one.
