# Implemented vs planned

Status of every API surface in the portal, as of 2026-10-02. The point of this
file is to make the gap between "the table exists" and "the feature works" explicit,
so nobody has to guess from the README.

Legend: **✅ implemented** (backed by real data, covered by a test) · **🟡 partial** (works, but a slice is missing) · **🔴 stub** (returns fixed data or is not wired)

## Authentication and accounts

| Surface | Status | Notes |
| --- | --- | --- |
| `POST /auth/login` | ✅ | Access token + refresh cookie; uniform error message; constant-time failure path; two-counter throttle |
| `POST /auth/refresh` | ✅ | Rotation with family-wide revocation on replay; per-IP ceiling |
| `POST /auth/logout` | ✅ | Revokes the presented token's family and clears the cookie |
| `GET /auth/me` | ✅ | — |
| `POST /auth/register/student` | ✅ | 5/hour per IP; offering existence + duplicate checks; students active immediately |
| `POST /auth/register/teacher` | ✅ | 5/hour per IP; account inactive until admin approval |
| `POST /auth/register/alumni` | ✅ | Pending claim + inactive account (see the alumni service docstring) |
| Avatar upload + finalize | ✅ | Presigned PUT with pinned content type, ownership check, post-upload size and magic-byte verification, 10/hour per account |
| Admin approval queue | ✅ | `GET /auth/admin/pending-approvals`, `PATCH /auth/admin/approve/{id}`; the decision is written to the audit log |
| Email verification on self-service signup | 🔴 | Not built; students are active immediately. Tracked in the README roadmap |
| Password reset | ✅ | `POST /auth/password-reset/request` is enumeration-resistant and rate-limited; tokens are hashed, single-use and 30 minutes; the confirm step revokes every other session. The email needs `SMTP_*` (the link is logged in non-production when unset) |
| MFA for privileged roles | ✅ | TOTP enrolment (`/auth/mfa/setup` → `/auth/mfa/enable`), two-step login, ten one-time recovery codes, password-confirmed disable. Super admins are confined to the enrolment routes until enrolled |
| Forced password change | ✅ | `must_change_password` on the bootstrap admin and after a reset; the API refuses everything except the security routes until it is cleared |
| Session list + revoke | ✅ | `GET /auth/sessions` (family, device, IP, last used, current flag) and `DELETE /auth/sessions/{family_id}`; wired into the account-security screen |
| Audit trail | ✅ | `audit_logs` written on approvals, booking decisions, deletions, password/MFA changes; `GET /admin/audit-logs` for super admins |
| Token housekeeping | ✅ | Daily `cleanup_expired_tokens` Celery Beat task |

## Academic

| Surface | Status | Notes |
| --- | --- | --- |
| `GET /courses` | ✅ | Role-scoped: student enrolments, teacher assignments, admin catalogue |
| `GET /schedules/my-routine` | ✅ | Built from `class_schedules`; students see enrolments, teachers their assignments, admins everything |
| `GET /attendance/my-summary` | ✅ | Aggregated from recorded sessions; 75% threshold reported, not decided |
| `GET /attendance/courses/{id}/summary` | ✅ | Teacher-of-record only |
| `POST /attendance/sessions` | ✅ | Teacher-of-record only |
| `PUT /attendance/sessions/{id}` | ✅ | Teacher-of-record only, inside a 48-hour correction window |
| Attendance recording UI | 🔴 | The endpoint works; no screen posts to it yet |
| `GET /labs/equipment` | ✅ | Real inventory join |
| Equipment borrow / checkout / damage reports | 🔴 | Tables and models exist; no endpoints or screens |
| `GET /dashboard/summary` | ✅ | Per-role live aggregates (no hardcoded figures) |

## Booking

| Surface | Status | Notes |
| --- | --- | --- |
| `GET /rooms` | ✅ | — |
| `POST /rooms/reservations` | ✅ | Friendly pre-flight 409 plus the GiST exclusion constraint under concurrency |
| `GET /rooms/reservations` | ✅ | Own reservations only |
| `GET /rooms/reservations/all` | ✅ | Staff/admin only |
| `POST /rooms/reservations/{id}/decide` | ✅ | Staff only; rejects a second decision |
| `POST /rooms/reservations/{id}/cancel` | ✅ | Requester or staff |
| Booking approval screen | 🔴 | The decide endpoint works; the UI only lists a student's own requests |

## Resources

| Surface | Status | Notes |
| --- | --- | --- |
| `GET /resources/search` | ✅ | Ready resources only; Postgres full-text search with an escaped ILIKE fallback |
| `POST /resources` | ✅ | Multipart upload: 25 MB cap, extension allowlist, magic-byte check, per-user quota and rate limit; storage key generated server-side |
| `GET /resources/{id}/download` | ✅ | Short-lived presigned URL, forced `attachment`, download counter |
| `DELETE /resources/{id}` | ✅ | Uploader or admin |
| Presigned client-side upload for large resources | 🔴 | Deliberately proxied through the API so verification happens in the request path |
| Resource moderation/approval workflow | 🔴 | Faculty uploads are auto-marked verified; no review queue for student uploads |

## Assistant

| Surface | Status | Notes |
| --- | --- | --- |
| `POST /ai/query` | ✅ | Retrieval first (pgvector when available, full-text and keyword fallbacks otherwise), citations, per-user hourly cap, exchange persisted |
| `GET /ai/history` | ✅ | Last session, oldest first |
| Gemini generation | 🟡 | Used when `GEMINI_API_KEY` is set; otherwise the answer is an extractive quote labelled `mode=extractive` |
| Embeddings + vector search | 🟡 | Written by the ingestion task when a key is configured; retrieval falls back to full text when it is not |
| Document ingestion pipeline | 🟡 | `ingest_document` task chunks, embeds and stores; there is no upload endpoint or admin screen that triggers it yet |
| Study-plan generation | 🔴 | `GeminiAgentService.generate_study_plan` exists but is not exposed by any route |
| Chat sessions list / rename | 🔴 | One implicit session per student |

## Career, projects, alumni, notifications

| Surface | Status | Notes |
| --- | --- | --- |
| `GET /career/opportunities` | ✅ | Verified, unexpired rows from the database, soonest deadline first |
| Posting/editing opportunities | 🔴 | No endpoint (rows must be inserted directly) |
| `GET /projects` | ✅ | Real rows with supervisor, member count and repository link |
| Supervisor proposals / project membership / publications | 🔴 | Tables and models exist; no endpoints or screens |
| GitHub webhook handling | 🔴 | `verify_github_signature` exists but no route calls it |
| Alumni registration, claims, approval/rejection | ✅ | Pending claims are invisible in the directory until approved |
| Alumni directory + FTS | ✅ | Visible and active profiles only, with an ILIKE fallback for SQLite |
| Alumni events, RSVP, capacity | ✅ | — |
| Scholarship applications and review | ✅ | Deadline, duplicate-application and published-state checks |
| Mentorship request / accept / decline | ✅ | Mentor-only responses, duplicate-pair guard |
| News and gallery | 🟡 | Read paths are public and real; no authoring endpoints |
| `GET/POST /notifications` | ✅ | In-app rows and device registration; push dispatch through FCM when configured (invalid tokens deactivated) |
| Class-alert scanner | ✅ | Celery Beat every minute, idempotent per (recipient, session) |
| Email/push preference screen | 🔴 | `notification_preferences` is respected server-side; no UI writes to it |
| Orphaned-upload sweep | ✅ | Hourly Celery Beat task deletes pending resource rows and their objects |

## Operations

| Surface | Status | Notes |
| --- | --- | --- |
| First-run administrator | ✅ | `BOOTSTRAP_ADMIN_*` environment variables create one forced-change super admin; no credentials are seeded |
| `GET /health` | ✅ | Liveness only |
| Readiness / dependency check | 🔴 | No endpoint reports database, Redis or storage health |
| Metrics / tracing | 🔴 | Structured JSON logs with a correlation id; no metrics or traces |
| CI (tests, bandit, audits, build) | ✅ | `.github/workflows/ci.yml` |
| Production compose | ✅ | Requires `POSTGRES_PASSWORD`, `SECRET_KEY`, `CORS_ORIGINS`, S3 keys; includes Redis, MinIO, Celery, healthchecks |
| TLS termination / HSTS | 🔴 | Assumed to be the deployment's reverse proxy; nginx configured for plain HTTP behind it |
