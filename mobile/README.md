# SUST EEE Portal — Mobile (Expo)

React Native / Expo client reusing the SUST EEE Portal backend API and auth.

## Run

```bash
cd mobile
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_BASE_URL` to point at your backend.

## Auth

Mobile uses token-based auth (access + refresh tokens stored in `expo-secure-store`).
Backend endpoint: `POST /api/v1/auth/login` must return `{ access_token, refresh_token, user }`.

## Structure

- `app/` — Expo Router routes
- `src/lib/` — API client + auth helpers
- `src/hooks/` — Zustand stores
- `src/types/` — shared types
