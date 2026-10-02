# Code Review — SUST EEE Smart Student Portal

> **Status: remediated.** Every P0 and P1 item in [§6](#6-prioritised-remediation) below, plus the
> implementable P2 items, has since been fixed in the working tree — see
> [§8 Remediation status](#8-remediation-status) for the change and the test that covers it. The
> body of this report is preserved as the original assessment (the findings describe the code as it
> stood at `16bb7ae`), so that the gap between what the README claimed and what the code did stays
> on the record.

**Review date:** 2026-10-02
**Scope:** full repository at `16bb7ae` (backend 8,019 Python LOC / 104 files, frontend 4,973 TS/TSX LOC / 95 files, SQL schema + 7 migrations, Docker/compose, tests)
**Reviewer method:** static read of every backend module and every frontend feature API client, plus executed checks (see [Method & evidence](#method--evidence))

---

## 1. Headline verdict

| Dimension | Score | Grade | One-line summary |
|---|---|---|---|
| **Security** | **7.0 / 10** | **B−** | Genuinely well-thought-out auth/RBAC/upload hardening for a student project — undone by a publicly committed `super_admin` password hash, no security headers, a token in `localStorage`, and unthrottled bcrypt on the event loop |
| **Features** | **5.5 / 10** | **C+** | Very broad surface (56 API routes, 15 domains) but roughly **a third of it is hardcoded stub data**, and the headline AI / FCM / FTS / presigned-upload claims are not implemented |
| **Overall** | **6.4 / 10** | **C+ / B−** | Excellent bones and above-average security engineering culture; breadth is advertised, depth is not delivered |

**Short read:** the *finished* half of this project (auth, dashboard, alumni, booking, attendance reads) is better than most university capstones — real SQL aggregates, real constraints, real security tests. The *unfinished* half is presented in the README as if it shipped: the AI assistant returns a canned string, notifications print to stdout, the schedule and career pages return literal constants. Fix the eight P0/P1 items in [§6](#6-prioritised-remediation) and this is a 8/10 security / 7/10 feature codebase.

### Score breakdown (weighted)

**Security (7.0)**

| Sub-area | Score | Notes |
|---|---|---|
| Authentication & session management | 8.5 | Refresh rotation + **reuse detection**, hashed tokens, token-type separation; − no reset/verification/MFA, access token revocable only by expiry |
| Authorization / access control | 8.5 | `RequireRole` + per-object checks, IDOR regressions tested; − self-enrolment into arbitrary offerings |
| Injection & validation | 8.5 | Zero raw SQL, SQLAlchemy expression language everywhere, Pydantic v2 on all bodies |
| Secrets & configuration hygiene | 5.0 | Committed `super_admin` bcrypt hash seeded on boot, default DB/MinIO creds, incomplete prod compose |
| Browser/transport hardening | 4.5 | **No CSP/HSTS/nosniff/X-Frame-Options anywhere**; access token in `localStorage`; public-read bucket |
| Abuse resistance / DoS | 5.5 | Best-in-class login throttle design; − bcrypt blocks the event loop, register/AI/upload unthrottled |
| Dependencies & supply chain | 5.0 | 13 npm advisories (5 high), unused `firebase` dep, no CI, root containers |
| Error handling & data exposure | 7.5 | Generic auth errors, docs off in prod, no tracebacks leaked; − unhandled `IntegrityError` → 500, no audit log |
| Security verification (tests) | 8.5 | 10 dedicated security tests (several parametrized), bandit clean; − no CI, no dependency scanning |

**Features (5.5)** — *breadth A−, depth C*

| Domain | Score | Delivered? |
|---|---|---|
| Role-aware dashboard (live aggregates) | 8.5 | ✅ Real SQL per role |
| Alumni portal | 7.5 | ✅ Most complete domain (FTS directory, verification, events, scholarships, mentorship) |
| Room booking | 7.5 | ✅ GiST exclusion + pre-flight + staff decisions (UI lacks the decision screen) |
| Frontend architecture & UX | 8.0 | ✅ Strict TS, lazy routes, skeletons, empty states, a11y labels; builds clean |
| Attendance | 6.5 | 🟡 Real reads/threshold/correction window; no UI to *record* attendance |
| Admin | 6.0 | 🟡 Approval queues real; no user/role management or analytics |
| Labs / equipment | 4.0 | 🟡 Inventory list only; borrow/checkout/damage models unused |
| Notifications | 3.0 | 🟡 DB rows + device registration real; **push send is `print()`**, Celery beat job is a print |
| Courses / Schedule | 3.0 | 🔴 Hardcoded constants, unused `ScheduleRepository` |
| Career / Projects | 2.5 | 🔴 Hardcoded constants |
| Resources | 2.5 | 🔴 Search real (title ILIKE only); **upload/finalize return fake values, no download route** |
| AI assistant | 1.5 | 🔴 Backend returns `"Grounded response for EEE students: <your prompt>"`; no retrieval, no embeddings; UI admits it isn't wired |
| README accuracy | 4.0 | 🔴 Overstates AI/pgvector/FCM/FTS/presigned upload as shipped |

---

## 2. What is genuinely good (credit where it is due)

1. **Refresh-token design is textbook.** `auth_service.py:96-130` rotates on every use, stores only SHA-256 hashes (`security.py:9`), and on replay of a rotated token revokes the **whole family** — real theft detection, with a regression test (`test_auth.py:127`).
2. **Token-type scoping.** Access, `avatar_upload`, and refresh tokens are distinguished by a `type` claim; `get_current_user` rejects anything but `access` (`dependencies.py:22-33`), and the upload token is accepted only by the two avatar routes. A refresh-shaped JWT cannot be traded for a write primitive (tested).
3. **Login throttling is genuinely thought through** (`core/rate_limit.py`). Two independent counters (per-account + per-IP) so credential-stuffing from one address is caught even when each account counter is fresh; grace windows sized for campus NAT; **correct passwords are exempt from the delay** so an attacker cannot lock a named account out; account identifiers are hashed before becoming Redis keys; XFF is only trusted from an explicit `TRUSTED_PROXIES` allowlist.
4. **Avatar upload hardening** (`endpoints/auth.py:109-285`): authentication required, extension→Content-Type pinned server-side (client `content_type` ignored), ownership prefix check on finalize, server-side size measurement with deletion of oversized objects, magic-byte check, and an honest comment about what magic bytes do *and do not* stop.
5. **No SQL injection surface.** Every query uses SQLAlchemy expression-language bound parameters; `grep` for `text(`, f-string SQL, and `%`-formatting found nothing (bandit: **0 medium/high findings**).
6. **Production guard rails in config** (`core/config.py:52-70`): refuses to boot with the committed dev `SECRET_KEY` or non-HTTPS CORS origins when `ENVIRONMENT=production`; docs disabled in production.
7. **Real database constraints, not app-level hope:** GiST `EXCLUDE` for room overlap (`schema.sql:136`), unique `(course_offering_id, student_id)`, generated `tsvector` columns with GIN indexes, FK `ON DELETE` semantics.
8. **Security test culture:** 10 focused regressions in `tests/test_security.py` (several parametrized across role matrices) (avatar auth, token-type confusion, cross-user key probing, login-message uniformity, attendance IDOR, both-counter throttle) plus `test_alumni_auth.py` authorization matrix. 84 passing in this sandbox.
9. **Frontend quality is above the backend average:** clean feature-folder architecture, `tsc --noEmit` clean, Vite build clean, `react-query` with explicit error/empty/loading states, `useId`-bound labels, object-URL revocation, no `dangerouslySetInnerHTML` anywhere.

---

## 3. Security findings

Severity is my assessment of **impact × exploitability in a real deployment**, not a CVSS score.

### High

#### H-1 · A `super_admin` bcrypt hash is committed and auto-seeded on every boot
`database/seed.sql` inserted four accounts — including a `super_admin` tied to a real personal address — that **all shared one bcrypt hash**. (The hash is deliberately not reproduced here; it has been removed from the repository, and repeating credential material in a report would just move the leak.) The file is mounted as a Postgres init script in `docker-compose.yml:15`, so *every* fresh deployment — including the public demo — has a super-admin whose credential material is published. The README claims "Demo credentials are intentionally not published in the repository"; the hash is exactly the secret the claim refers to. I could not crack it with a 35-candidate list (bcrypt cost 12), but a published hash is crackable offline at leisure, and the shared hash across accounts multiplies the blast radius.
**Fix:** delete the hash from the seed; create the bootstrap admin from environment variables at first boot (or force a password change on first login); never reuse one hash across accounts.

#### H-2 · No security headers anywhere in the request path
`frontend/nginx.conf` sets **zero** `add_header` directives — no `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, or HSTS. The app is click-jackable, MIME-sniffable, and a successful script injection has no CSP to fight. The code comments in `auth.py:212,259-263` acknowledge nosniff is missing for MinIO-served avatars but nothing stacks up at the edge either.
**Fix:** add the header block to `nginx.conf` (and mirror it in whatever terminates TLS in production).

#### H-3 · Access token in `localStorage`, no CSP to compensate
`AuthContext.tsx:79` and `lib/axios.ts:40` persist the JWT in `localStorage`. Any future XSS (or a malicious dependency) exfiltrates a 15-minute session token instantly. The HttpOnly refresh cookie (`auth.py:45-53`) limits persistence, which is good, but the combo of *no CSP* + *token in JS-readable storage* is the classic avoidable pair.
**Fix:** keep the access token in memory only and let the refresh cookie re-mint it on reload (the interceptor already handles 401→refresh→replay), and ship the CSP from H-2.

### Medium

#### M-1 · bcrypt runs on the asyncio event loop
`verify_password` / `get_password_hash` (`core/security.py:17-31`) are synchronous C calls invoked directly from `async def` code (`auth_service.py:72`, `:153`, `:182`). At cost 12 that is ~150–300 ms of **blocking CPU per call**, during which the whole worker serves nobody. The throttle cannot save this: the delay is applied *after* the hash, and `asyncio.sleep` does not stop other tasks from queueing behind the blocking call. A few hundred concurrent login or registration attempts are a cheap availability attack (and registration is not throttled at all).
**Fix:** wrap hashing in `await anyio.to_thread.run_sync(...)` (or `loop.run_in_executor`), and rate-limit `/auth/register/*`.

#### M-2 · Registration is unthrottled and self-service students activate instantly
`/auth/register/student` and `/auth/register/teacher` have no throttle (only login does), and student accounts are created `is_active=True` (`auth_service.py:184`) with **no email verification**. Anyone can mint unlimited active accounts that can read the alumni directory, resource keys, room inventory, career and project data. Combined with M-1 this is both spam and CPU-DoS.
**Fix:** throttle registration, verify institutional email (or gate until admin approval like CR/ER), and add a signup cap per IP/domain.

#### M-3 · Public-read object bucket + `file_key` handed to every authenticated user
`docker-compose.yml:63` runs `mc anonymous set download` on the bucket. `GET /resources/search` returns ORM rows with no `response_model` (`endpoints/resources.py:11-14`), so the payload includes internal columns such as `file_key` and `uploaded_by`. Anyone authenticated — including the throwaway accounts from M-2 — can read any resource object if the key leaks, and nothing enforces per-role resource access.
**Fix:** make the bucket private and serve downloads through the API (presigned GET with an authorization check), or at minimum add response models that omit `file_key`.

#### M-4 · Unhandled integrity errors surface as HTTP 500
A student registration pointing at a non-existent `course_offering_id` is accepted on SQLite (FK off) and would raise `IntegrityError` → unhandled 500 on Postgres. I verified the API accepts arbitrary `course_offering_id` values and any-length `session_year`/`current_term` (probe returned `201`). There is no existence/capacity/advisor check, so self-enrolment into any offering is possible.
**Fix:** validate the offering exists (and has room), bound the string fields in the Pydantic schema, and add an `IntegrityError` → 422 handler.

#### M-5 · 13 npm advisories (5 high) and an unused Firebase dependency
`npm audit --omit=dev`: 13 vulnerabilities — 5 high (`@firebase/firestore`, `@grpc/grpc-js` <1.13.6, `undici` insufficient randomness, `firebase`), 8 moderate (incl. `react-router` open-redirect GHSA-wrjc-x8rr-h8h6). `firebase` is imported **nowhere** in `frontend/src` — it is dead weight carrying most of those advisories. No CI runs any of this automatically.
**Fix:** `npm audit fix`, upgrade react-router, drop `firebase` until FCM is real, add `npm audit` + `pip-audit` to CI.

#### M-6 · `docker-compose.prod.yml` is not runnable and is missing the hardening it implies
The prod backend service sets only `ENVIRONMENT: production` with no `env_file` and no `environment:` wiring for `DATABASE_URL`/`SECRET_KEY`/S3 — so it boots with in-repo defaults and **crash-loops on the weak-key guard** (which is the guard doing its job, but the file is unusable as written). Redis, MinIO, Celery and healthchecks are absent while the app depends on Redis for throttling; `443:443` is exposed but nginx only listens on `80`; containers run as **root** (`backend/Dockerfile`, no `USER`); no TLS, no resource limits on the backend.

### Low / hygiene

| # | Finding | Location |
|---|---|---|
| L-1 | Webhook signature verifier is dead code and throws `ValueError` on a malformed header (`signature_header.split('=')`), i.e. a 500 if ever wired to a route | `integrations/github_client.py:7` |
| L-2 | FCM token prefix logged to stdout in the mock sender | `integrations/firebase_client.py:3` |
| L-3 | Dev defaults `postgres/postgres` and `minioadmin/minioadmin` are used as fallbacks and the ports are published to the host (5433/6380/9000/9001) | `docker-compose.yml:7-8,35-38` |
| L-4 | `ILIKE f"%{q}%"` without escaping `%`/`_`, and no max length on `q` for resource search — wildcard abuse / unindexed scan | `repositories/resource_repository.py:13` |
| L-5 | `document_chunks.embedding vector(768) NOT NULL` exists in SQL but not in the ORM model — an insert would fail; parity tests only cover alumni tables | `database/schema.sql:362` vs `models/ai_knowledge.py` |
| L-6 | Empty pg_dump artifacts committed (`\restrict` tokens, 0 data rows) — clutter plus a production schema snapshot | `.backups/*.sql` (not gitignored) |
| L-7 | Password policy is `min_length=6` with no complexity/breach check; login error messages are correctly uniform (good) but registration returns "Email already in use" (enumeration trade-off) | `schemas/auth.py:7-8`, `auth_service.py:145` |
| L-8 | No audit logging, no session/device revocation UI, no refresh-token cleanup job (expired rows accumulate) | — |
| L-9 | No CI at all (`.github/workflows` absent) — tests, build, lint, audit are all manual | `.github/` |

---

## 4. Feature-by-feature reality check

Legend: ✅ real · 🟡 partial · 🔴 stub/hardcoded

| Endpoint / feature | Status | Evidence |
|---|---|---|
| `POST /auth/login·refresh·logout`, `/auth/me` | ✅ | Real, with rotation + family revocation |
| `POST /auth/register/{student,teacher}` + approvals | ✅ | Real; students auto-active (see M-2) |
| `POST /auth/avatar-upload[/finalize]` | ✅ | Genuinely hardened presigned flow |
| `GET /dashboard/summary` | ✅ | Real per-role SQL aggregates, no fake zeros (`test_dashboard_summary.py`) |
| Alumni: register/claim/approve/reject/directory/visibility | ✅ | FTS with `plainto_tsquery` + ILIKE fallback for SQLite |
| Alumni: events/RSVP/capacity, scholarships/apply/review, mentorship, news, gallery | ✅ | Real service + repository layers |
| `GET·POST /rooms`, `/rooms/reservations[/decide/cancel]` | ✅ | GiST exclusion + friendly pre-flight 409; staff decisions API exists but **no frontend for approve/reject** |
| `GET /attendance/my-summary`, `/courses/{id}/summary`, `POST /attendance/sessions`, `PUT /attendance/sessions/{id}` | ✅ | Real aggregation, 75% threshold, 48 h correction window, IDOR fixed |
| `GET /labs/equipment` | ✅ | Real join (inventory only) |
| `GET/POST /notifications` | 🟡 | DB read + device registration real; **`dispatch_push_notification` is `print()`** |
| `GET /courses` | 🔴 | Returns two literal dicts (`"EEE 311"`, `"EEE 312"`) |
| `GET /schedules/my-routine` | 🔴 | Comment says "Sample routine aligned with SUST EEE 3-1 syllabus"; `ScheduleRepository` unused |
| `GET /career/opportunities` | 🔴 | One hardcoded internship (`career_service.py:8`) |
| `GET /projects` | 🔴 | One hardcoded capstone (`project_service.py:8`) |
| `GET /resources/search` | 🟡 | Real query, but title-ILIKE only — the `tsv_search` column + GIN index in `schema.sql:212` are never used |
| `POST /resources/presigned-upload`, `/resources/finalize` | 🔴 | Returns `http://localhost:9000/.../{file_name}` (unsigned, hardcoded host, unvalidated name) and `{"resource_id": "res-123"}`; **no download route exists** |
| `POST /ai/query` | 🔴 | `generate_gemini_response()` returns `f"Grounded response for EEE students: {prompt}. (Armature reaction …)"`; no retrieval, no embeddings, no `google.generativeai` call. UI `ChatWindow` answers with "The live RAG endpoint is not wired on this screen yet." |
| Celery worker + beat | 🔴 | Both tasks are `print()` statements |
| Firebase Cloud Messaging | 🔴 | Mock function; `firebase` npm package unused |
| Frontend: 16 lazy routes, role guards, a11y, empty/error/loading states | ✅ | Builds clean, no TS errors |
| Frontend admin panel | 🟡 | Approval queue only; `adminApi.getStats()` targets a non-existent `/admin/stats` route (dead code) |

**README vs code:** "Google Gemini with pgvector and full-text hybrid retrieval", "Firebase Cloud Messaging with Celery worker and Beat scheduling", "Presigned S3/MinIO uploads and PostgreSQL full-text search" (for resources), "Supervisor workflows, and GitHub integration", and "lab inventory, equipment checkout, damage reports" overstate what is implemented. The alumni, dashboard, booking and auth claims are accurate.

---

## 5. Test & tooling results (executed)

```
backend:  84 passed, 7 skipped in 31.0s
          coverage: 69% of app/ (2728 stmts, 841 missed)
          skipped = Postgres-only GiST/TSTZRANGE booking tests (no PG in sandbox)
bandit:   0 high, 0 medium, 1 low (false positive: literal "access" flagged as a password)
npm audit --omit=dev:  13 vulnerabilities (5 high, 8 moderate)
frontend: npx tsc --noEmit  → clean
          npm run build     → built in 3.65s, code-split chunks
routes:   56 documented API paths (openapi.json)
```

Coverage is uneven where it matters most: `booking_service` 29%, `alumni_service` 25%, `auth_service` 41%, `schedule_repository` 0% (nothing calls it). `test_schema_parity.py` is a good idea but only covers the alumni tables, which is how L-5 slipped through.

---

## 6. Prioritised remediation

**P0 — before this is shown to anyone outside the department**
1. Remove the seeded `super_admin` hash (`database/seed.sql:2`); bootstrap the admin from env + force password change.
2. Add the security-header block to `nginx.conf` (CSP, HSTS, nosniff, `X-Frame-Options: DENY`, `Referrer-Policy`).
3. Move the access token out of `localStorage` into memory.
4. Offload bcrypt to a thread pool and throttle `/auth/register/*`.
5. Make the MinIO bucket private and/or stop returning `file_key` from `/resources/search`.

**P1 — make the product match its description**
6. Either implement or explicitly relabel the stubs: AI/RAG, FCM push, Celery jobs, resource upload/download, courses, schedule, career, projects. A `docs/IMPLEMENTED_VS_PLANNED.md` table (reuse §4) is honest and cheap.
7. Validate `course_offering_id` on registration, add an `IntegrityError` handler, bound free-text fields.
8. `npm audit fix`, upgrade `react-router`, delete the unused `firebase` dependency.
9. Repair `docker-compose.prod.yml`: env wiring, Redis + MinIO + worker services, healthchecks, non-root `USER`, TLS termination.
10. Add CI: pytest, `tsc`, `vite build`, `bandit`, `pip-audit`, `npm audit` on every PR.

**P2 — hardening & polish**
11. Password reset + email verification; MFA for `super_admin`; audit log for approvals/decisions.
12. Escape ILIKE wildcards; add max lengths to query params; use the existing `tsv_search` for resource search.
13. Session management UI, refresh-token cleanup job, pagination limits on list endpoints.
14. Remove `.backups/` from git (or move to external storage) and add it to `.gitignore`; delete the dead `github_client` verifier or wire it properly.
15. Reconcile `document_chunks.embedding` between SQL, Alembic and ORM; extend `test_schema_parity.py` to all tables.

---

## 7. Method & evidence

Reviewed: all 104 backend Python files (endpoints, services, repositories, models, schemas, core, integrations, tasks, middlewares), all frontend feature API clients and pages, `schema.sql` + 7 SQL migrations + 6 Alembic revisions, both compose files, both Dockerfiles, nginx config, seed/backup SQL, docs, and the test suite.

Executed in-sandbox: `pytest` (84 passed/7 skipped), `pytest --cov`, `bandit -r app`, `npm ci` + `tsc --noEmit` + `vite build`, `npm audit --omit=dev`, `app.openapi()` route enumeration, targeted probe tests for registration validation and ORM serialization, and a 35-candidate bcrypt dictionary check against the committed hash.

**Limitations:** no Docker/Postgres/MinIO/Redis in the sandbox, so the live stack was not exercised end-to-end and the 7 Postgres-only booking tests (GiST exclusion constraint) were skipped; the MinIO/MinIO-policy behaviour quoted in code comments was not independently re-verified; the committed bcrypt hash was not cracked (small wordlist only), so H-1 is rated on exposure, not on a demonstrated password.

---

## 8. Remediation status

Recorded 2026-10-02 after implementing the plan in §6. "Verified by" names the test or command that
demonstrates the fix; the full backend suite is **139 passed / 7 skipped** and the frontend
`tsc --noEmit` + `npm run build` are clean.

### P0 — all fixed

| # | Finding | Fix | Verified by |
|---|---|---|---|
| 1 | Committed `super_admin` bcrypt hash (`H-1`) | All four seeded accounts **removed** from `database/seed.sql`, which now contains reference data only. `app/core/bootstrap.py` creates the first administrator from `BOOTSTRAP_ADMIN_*` with `must_change_password=True`; nothing in the repo holds a usable credential | `test_account_security.py::test_bootstrap_admin_is_created_once_with_forced_change`, `::test_bootstrap_refuses_a_short_password`, `::test_bootstrap_is_skipped_when_an_admin_exists` |
| 2 | No security headers (`H-2`) | `frontend/nginx.conf` now sets CSP, nosniff, `X-Frame-Options: DENY`, Referrer-Policy and Permissions-Policy; the API sets the same set in `SecurityHeadersMiddleware` (HSTS stays at the TLS terminator) | `test_hardening.py::test_security_headers_are_present_on_success_and_failure` |
| 3 | Access token in `localStorage` (`H-3`) | Token lives in a module-level variable; page load restores the session with one silent `/auth/refresh` against the HttpOnly cookie; no storage API is used | `grep -rn localStorage frontend/src` returns only the theme preference |
| 4 | bcrypt on the event loop + unthrottled registration (`M-1`, `M-2`) | `app/core/passwords.py` runs bcrypt in AnyIO's worker thread (and burns a dummy hash when the account does not exist); `/auth/register/*`, `/auth/refresh`, `/auth/password-reset/request`, avatar and resource uploads and `/ai/query` all have fixed-window ceilings | `test_security.py`, `test_hardening.py::test_duplicate_signup_message_does_not_confirm_the_account`, `test_account_security.py` |
| 5 | Public bucket + internal columns in `/resources/search` (`M-3`) | MinIO grants anonymous read to the `avatars/` prefix only; `ResourceResponse` is a response model without `file_key`/`uploaded_by`, and downloads go through a 300 s presigned attachment URL | `test_resources.py`, `docker-compose.yml` minio-init |

### P1 — all fixed

| # | Finding | Fix | Verified by |
|---|---|---|---|
| 6 | Stub features presented as shipped | Every endpoint in §4 is now either backed by real data or explicitly labelled: resources upload/verify/download, role-scoped courses, the real timetable, career and project reads, FCM dispatch with device deactivation, Celery class-alert + orphan sweeps, and a retrieval-first assistant (`mode=extractive` when no Gemini key). `docs/IMPLEMENTED_VS_PLANNED.md` is the line-by-line status | `test_academic_surfaces.py`, `test_ai_assistant.py`, `test_resources.py`, `test_notifications.py` |
| 7 | Unvalidated offerings, bare `IntegrityError`, unbounded text | Offering ids are checked before the account is written (422), `IntegrityError` maps to 409, `UnexpectedError` to a generic 500, and every free-text field has a max length | `test_hardening.py` (13 tests) |
| 8 | Vulnerable/unused frontend deps | `npm audit --omit=dev` → 0 vulnerabilities; unused `firebase` removed; `react-router-dom` upgraded | `npm audit`, `npm run build` |
| 9 | Unusable `docker-compose.prod.yml` | Env wiring (`${VAR:?}`), Redis + MinIO + Celery worker/beat, healthchecks, non-root images, TLS left to the fronting proxy, and the new bootstrap/SMTP/MFA variables | `docker compose config` is not runnable here (no Docker in the environment); reviewed by hand and mirrored in `.env.example` |
| 10 | No CI | `.github/workflows/ci.yml`: pytest, bandit, `pip-audit`, `tsc`, `vite build`, `npm audit --audit-level=high` | workflow file |

### P2 — fixed where the code allows

| # | Finding | Fix | Verified by |
|---|---|---|---|
| 11 | No reset/enumeration/MFA/audit story | Self-service reset (`/auth/password-reset/{request,confirm}`, hashed single-use tokens, all other sessions revoked), TOTP MFA with recovery codes and a server-side enrolment gate for super admins, `audit_logs` with `GET /admin/audit-logs`, and a 15-second grace window so two tabs refreshing at once are not mistaken for token theft | `test_account_security.py` (13 tests) |
| 12 | ILIKE wildcards, unbounded params, unused `tsv_search` | `_escape_like` + `ESCAPE '\'`, per-term scoring, `tsv_search` used first with an ILIKE fallback, all query params bounded | `test_resources.py`, `test_schema_parity.py` |
| 13 | No session UI, token growth, unbounded lists | `/auth/sessions` + revoke, the account-security screen, daily `cleanup_expired_tokens` task, and `limit`/`offset` (max 200) on every list endpoint | `test_account_security.py::test_session_list_marks_the_current_device_and_revokes_others`, `::test_cleanup_prunes_dead_tokens_but_keeps_live_ones` |
| 14 | `.backups/` in git, dead webhook verifier | Backup artefacts removed from the repository and ignored; the unused GitHub verifier deleted rather than left as a trap | `git ls-files`, `git check-ignore` |
| 15 | `document_chunks.embedding` / schema drift | `Vector(768)` mapped (nullable) with a portable SQLite fallback, and the parity test now walks **every** table and column — which caught 16 `updated_at` columns that existed in the ORM but not in `schema.sql` (migration `009`, Alembic `20261002_0008`) | `test_schema_parity.py` (19 tests) |

Two items remain genuinely open and are recorded in the README roadmap rather than pretended away:
self-service **email verification** (students are active at signup; no SMTP story for verification
codes), and **end-to-end mail delivery** — the reset flow is complete, but without `SMTP_*`
configured the link is only written to the dev log.
