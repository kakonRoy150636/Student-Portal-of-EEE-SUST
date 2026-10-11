# Security audit — 2026-10-11

Scope: follow-up source, configuration, dependency, container and regression review
from the committed baseline `34410d7` through the pushed audit hardening and
Phase 1 follow-up changes.
The original 2026-10-03 findings and verification record remain below for history.
This does not attest to deployed secrets, credential rotation or Git history cleanup.

## Current follow-up changes (2026-10-11)

This follow-up closes the confirmed issues found while reviewing request abuse,
input boundaries, object storage, attendance/event state, and browser session
lifecycle. These changes are committed and pushed as `0dcb65d` (`fix: harden
portal security boundaries`).

| Area | Change |
|---|---|
| Request budgets | Added authenticated budgets for alumni directory search, resource presign/finalize, and avatar upload/finalize, in addition to the existing login, refresh, registration, AI and resource-search limits. |
| Input and object boundaries | Enforced bcrypt's 72-byte password limit, finite attendance statuses and duplicate-free records, active-enrollment checks, bounded attendance text/record counts, and bounded avatar finalization keys. Rejected staging objects are deleted after failed resource finalization. |
| Concurrent state | Serialized finite alumni-event RSVP capacity checks and assigned disjoint PostgreSQL seat ranges. Room reservation decisions/cancellations and attendance updates now lock the row they mutate. Dropped/inactive enrollments no longer contribute to attendance summaries or dashboard totals. |
| Production/browser hardening | Normalized the production switch, require an HTTPS public storage endpoint in production, fail closed on incomplete role data, validate external profile links and presigned upload origins, reject presigned redirects, and prevent stale auth/offline-storage operations from publishing another user's state. |
| Dependencies and quality | Upgraded transitive `source-map-js` to `1.2.2`; corrected the enrollment-reselection type/runtime call caught by mypy. |
| Phase 1 follow-up | Invalidated stale login/logout/bootstrap operations, enforced 15–24 active-credit boundaries with per-student mutation locking, and updated the regression/documentation records. |

## Original findings before fixes (2026-10-03)

| ID | Severity | Finding |
|---|---|---|
| S1 | High | Production Compose requires Postgres/MinIO passwords and publishes only frontend port 80, but JWT `SECRET_KEY`, backend `DATABASE_URL` and S3 credentials are inherited via env_file with development defaults in settings. Require them explicitly and reject known defaults. |
| S2 | High | Login delays happen after bcrypt. Refresh, AI, resource search and alumni signup lack request budgets. Add atomic Redis windows before expensive work, with 429/Retry-After and production fail-closed behavior. |
| S3 | High | Refresh replay revokes families sequentially, but locks only the presented row. Different generations of a family can race/deadlock with rotation. Serialize the family across rotation, replay and logout. |
| S4 | Medium | GitHub HMAC helper exists but no webhook is registered. Malformed non-ASCII signatures can raise. Add a bounded signed receiver; do not pretend a project synchronization workflow exists. |
| S5 | High | Resource finalize trusts Content-Type metadata; avatar does not require key extension/type agreement. A still-live PUT URL can overwrite a finalized object. Validate bytes and publish an immutable, separately named object. |
| S6 | Medium | Lab equipment API accepts every authenticated role although the frontend restricts it to staff. Several other routes intentionally use ownership/authentication rather than role gates; matrix below flags each. |

Current `database/dev/seed.sql` intentionally contains disposable development users
and password hashes. `database/dev/seed.sh` refuses to run unless
`ENVIRONMENT=development`; these accounts are not production credentials.
Bootstrap credentials are unset by default; `admin` is an identifier, not a password.
Historical seeds and tracked `.backups/` data are not used by startup; deployments
created from old revisions need operator credential rotation. Removing a current
seed does not rotate a live password or erase history.

## Endpoint / role matrix (before fixes)

All domain paths below start with `/api/v1`. Roles: A=super_admin,
T=teacher, E=lab_assistant, S=student, C=cr, L=alumni.
ALL means all six **active** roles, verified from DB, not JWT role claims.
`AUTH` explicitly flags no role allowlist: acceptable for shared/self-scoped
features, not automatically an authorization vulnerability. `PUBLIC` means no
role check by design. Checks inside services count as authorization checks.

| Method | Path | Allowed roles / credential | Role-check flag / object scope |
|---|---|---|---|
| POST | /auth/login | Public credentials | PUBLIC; inactive accounts denied |
| POST | /auth/refresh | Refresh cookie | PUBLIC; token/family and active user checked |
| POST | /auth/logout | Optional refresh cookie | PUBLIC; cookie's family only |
| GET | /auth/me | ALL | AUTH; self |
| POST | /auth/register/teacher | Public | PUBLIC; pending approval |
| POST | /auth/register/student | Public | PUBLIC; S active, C/E pending; no A selection |
| POST | /auth/avatar-upload | ALL or scoped registration upload token | AUTH; actor's prefix |
| POST | /auth/avatar-upload/finalize | ALL or scoped registration upload token | AUTH; actor's prefix |
| GET | /auth/admin/pending-approvals | A | Explicit role gate |
| PATCH | /auth/admin/approve/{user_id} | A | Explicit role gate |
| GET | /users/profile | ALL | AUTH; self |
| GET | /courses | ALL | AUTH; shared catalogue |
| GET | /schedules/my-routine | ALL | AUTH; own enrolments |
| GET | /dashboard/summary | ALL | AUTH; role-scoped service data |
| GET | /rooms | ALL | AUTH; catalogue |
| POST | /rooms/reservations | ALL | AUTH; caller is requester; broader than frontend menu |
| GET | /rooms/reservations | ALL | AUTH; caller's reservations |
| GET | /rooms/reservations/all | A,T,E | Explicit role gate |
| POST | /rooms/reservations/{reservation_id}/decide | A,T,E | Explicit role gate |
| POST | /rooms/reservations/{reservation_id}/cancel | Owner or A,T,E | Ownership/staff check |
| GET | /attendance/my-summary | ALL | AUTH; self |
| POST | /attendance/sessions | Assigned T or A | Role + course assignment |
| GET | /attendance/courses/{offering_id}/summary | Assigned T or A | Role + course assignment |
| PUT | /attendance/sessions/{session_id} | Assigned T or A | Session -> course -> assignment |
| POST | /notifications/devices/register | ALL | AUTH; caller's device |
| GET | /notifications | ALL | AUTH; caller's notifications |
| GET | /notifications/summary | ALL | AUTH; caller's inbox and exact unread total |
| GET | /notifications/stream | ALL | AUTH; short-lived caller-only SSE, no bearer token in URL |
| PATCH | /notifications/read-all | ALL | AUTH; caller's inbox only |
| PATCH | /notifications/{notification_id}/read | ALL | AUTH; caller-owned notification or 404 |
| DELETE | /notifications/devices/{device_id} | ALL | AUTH; delete only caller-owned token |
| GET | /notifications/preferences | ALL | AUTH; caller's channel preferences and quiet hours |
| PUT | /notifications/preferences | ALL | AUTH; replaces caller's preferences only |
| GET | /resources/search | ALL | AUTH; department-shared resources |
| POST | /resources/presigned-upload | ALL | AUTH; uploader prefix |
| POST | /resources/finalize | ALL | AUTH; uploader prefix |
| GET | /resources/{resource_id}/download | ALL | AUTH; shared library, not course-private |
| GET | /labs/equipment | ALL | **MISSING staff gate — fix to A,T,E** |
| GET | /projects | ALL | AUTH; shared catalogue; broader than frontend menu |
| GET | /career/opportunities | ALL | AUTH; verified public-to-members listings |
| POST | /ai/query | ALL | AUTH; shared assistant |
| POST | /alumni/register | Public | PUBLIC; pending verification |
| GET | /alumni/landing | Public | PUBLIC; published content/stats |
| GET | /alumni/directory | ALL | AUTH; visible, verified profiles; broader than frontend menu |
| GET | /alumni/directory/{profile_id} | ALL | AUTH; visible active profile |
| GET | /alumni/me | ALL | AUTH; own profile |
| PATCH | /alumni/me | ALL | AUTH; own profile; schema excludes approval fields |
| GET | /alumni/dashboard | L,A | Explicit role gate |
| POST | /alumni/claim | ALL | AUTH; own pending claim, never self-approved |
| GET | /alumni/events | ALL | AUTH; published only except A |
| GET | /alumni/events/{event_id} | ALL | AUTH; published only except A |
| POST | /alumni/events | A | Explicit role gate |
| POST | /alumni/events/{event_id}/rsvp | ALL; L for members-only | Service checks event visibility/membership role |
| GET | /alumni/scholarships | ALL | AUTH; published only except A |
| POST | /alumni/scholarships | A | Explicit role gate |
| POST | /alumni/scholarships/{scholarship_id}/apply | ALL | AUTH; own application, published scholarship |
| PATCH | /alumni/scholarships/applications/{application_id} | A | Explicit role gate |
| GET | /alumni/mentors | L,A | Explicit role gate |
| POST | /alumni/mentorship | L,A | Role gate; verified active mentor |
| PATCH | /alumni/mentorship/{pair_id}/accept | L,A; requested mentor only | Role + ownership (A does not bypass ownership) |
| PATCH | /alumni/mentorship/{pair_id}/decline | L,A; requested mentor only | Role + ownership |
| GET | /alumni/news | Public | PUBLIC; published only |
| GET | /alumni/news/{slug} | Public | PUBLIC; published only |
| GET | /alumni/gallery | Public | PUBLIC; published only |
| GET | /alumni/admin/pending | A | Explicit role gate |
| PATCH | /alumni/admin/approve/{profile_id} | A | Explicit role gate |
| PATCH | /alumni/admin/reject/{profile_id} | A | Explicit role gate |

Framework routes: `GET /health` public; `GET /api/docs`, `/docs/oauth2-redirect`,
`/redoc`, `/openapi.json` public documentation. Initially only `/api/docs` was
disabled in production; disable all documentation routes there consistently.
There is initially **no GitHub webhook route**, only an unused verification helper.
New receiver: `POST /api/v1/webhooks/github`, HMAC-authenticated (no user role).

## Original verification / residual limits (2026-10-03)

### Fixes applied (separate commits)

| Finding | Commit | Result |
|---|---|---|
| S1 | `ae33a4b` | Production Compose requires JWT, DB URL and S3 credentials; runtime rejects default DB/S3 passwords. All API documentation disabled in production. DB/Redis/MinIO remain unexposed. |
| S2 | `a1fec6d` | Atomic Redis Lua counter + expiry. Login 30/IP/min, refresh 60/IP/min, AI 10/user/min, resource search 60/user/min; all registration routes share 20/IP/hour. 429 includes Retry-After; production Redis failure returns 503 rather than bypassing controls. |
| S3 | `804242e` | PostgreSQL transaction advisory lock serializes the whole family before row locking. Rotation, replay and logout share it; replay leaves no active descendants and does not revoke another device's family. |
| S4 | `a896e20` | Signed `POST /api/v1/webhooks/github`, maximum 1 MiB, exact raw-body HMAC-SHA256, constant-time comparison and strict digest syntax. Missing configuration returns 503; invalid signature 401. |
| S5 | `89a8639` | MIME/extension agreement, bounded byte reads and signature/container sanity checks. Validated bytes are published under a new server-only key, preventing staging PUT replay from replacing them. Resource limit 25 MiB; avatar limit 10 MiB; presigned URLs remain 300 seconds. |
| S6 | `3b4ba20` | `/labs/equipment` now explicitly permits only A,T,E. Tests cover all six roles, every non-admin role against administrative routes, and a forged JWT role claim. |

**After-fix matrix change:** the lab equipment row is now A,T,E with an explicit
role check. The webhook row is HMAC-only. Other roles/scopes remain as documented
above; AUTH flags continue to identify routes with no narrower role allowlist.

### Verification performed

- Full backend suite: **134 passed, 7 skipped**. The seven older PostgreSQL fixture
  tests were not enabled; the new migration and refresh concurrency tests ran
  against a real disposable PostgreSQL 16 cluster.
- Real Redis concurrent requests: exactly 5 of 20 accepted for a 5-request budget;
  all others returned 429, and the budget reset after expiry.
- Real MinIO: presigned PUT reused to overwrite staging bytes; published bytes
  remained unchanged, and the invalid replacement could not be published.
- Production Compose rejected missing **and empty** POSTGRES_PASSWORD,
  MINIO_ROOT_PASSWORD, SECRET_KEY, DATABASE_URL, S3_ACCESS_KEY and S3_SECRET_KEY.
- Rendered production configuration publishes no Postgres, Redis or MinIO ports.
- Static route inventory verified that this report documents all **61 domain
  routes**, plus framework routes.

Reproduce the integration-enabled suite on the isolated stack described in README:

```bash
docker compose -p sust-eee-migration-check -f docker-compose.yml -f docker-compose.migration-test.yml exec -T backend \
  env MIGRATION_TEST_DATABASE_URL=postgresql://migration_test:migration_test@postgres:5432/migration_test \
  SECURITY_TEST_REDIS_URL=redis://redis:6379/14 \
  SECURITY_TEST_S3_ENDPOINT=http://minio:9000 \
  python -m pytest -q -p no:cacheprovider
```

### Remaining operational/product limits

- Use the production Compose file standalone, not merged with development's
  published ports. TLS and a browser-reachable private-storage gateway remain
  deployment configuration. Provision a least-privilege S3 service credential;
  do not give the API MinIO root credentials.
- Old deployed admin passwords cannot be inspected/rotated from source alone.
  Rotate any credentials used by historical seeds; `.backups/` and Git history
  need owner review before publishing any real database exports.
- File signatures/container checks are not malware scanning or full image
  decoding. Legacy Office formats share an OLE signature. A presigned PUT can
  still consume staging storage before finalization; apply object-store quotas
  and a lifecycle rule for abandoned staging objects. Oversized/invalid objects
  are rejected before publication. DB failures can leave orphan published objects.
- Shared-library access remains intentional; course-private resources require
  an explicit entitlement policy. Authentication-only catalogue routes are
  flagged above rather than assigned arbitrary new role restrictions.
- Webhook ping verifies delivery. Other signed event types return `ignored`:
  project synchronization was absent and is not invented by this security fix.
- Existing access JWTs expire normally after a family is revoked; family
  revocation prevents further refresh, not already-issued short-lived access.
- Redis fail-closed behavior is production-only; local development retains
  availability when Redis is absent. Exact trusted proxy configuration is
  required for distinct client IP budgets behind a reverse proxy.

## Current follow-up verification (2026-10-11)

- Isolated backend PostgreSQL/Redis suite after the Phase 1 follow-up: **316
  passed, 1 skipped, 2 xfailed** in 211.45 seconds. The one skip is the
  explicitly opt-in MinIO test; the remaining expected xfails are `LAB-1` and
  `ENR-3`.
- The optional isolated MinIO upload-security file passed separately: **12
  passed**.
- CI-aligned backend quality checks passed: Ruff, mypy (**99 source files**),
  and pip-audit (**no known vulnerabilities** after upgrading the disposable
  checker environment's pip/setuptools as CI does).
- Frontend checks passed: TypeScript typecheck, ESLint, **56 Vitest tests**,
  and production build. The default Playwright suite passed **5 tests** and
  intentionally skipped the opt-in live semester test.
- The real browser semester workflow against a fresh PostgreSQL/Redis/MinIO
  stack passed **1 test**. It covered UI login, offering creation/publication,
  assignment approval, notifications, enrollment, drop/reselect credits, and
  wrong-role/unauthenticated access checks.
- `npm audit --audit-level=high` reports **0 vulnerabilities**; the transitive
  `source-map-js` package is locked at **1.2.2**. Trivy HIGH/CRITICAL scans of
  freshly built backend and frontend images both reported **0 findings**.

## Current follow-up residual limits

- The audit is repository- and disposable-environment evidence only. It does
  not prove that a deployed environment uses rotated secrets, TLS, trusted
  proxy addresses, private object storage, least-privilege S3 credentials, or
  the current image/lockfile.
- Production Compose still expects an external TLS terminator; the frontend
  container itself serves HTTP. Staging uploads can consume object-store space
  until an object-store lifecycle/quotas policy removes abandoned keys.
- The lab-bench overlap contract and prerequisite policy remain intentionally
  unimplemented and are represented by the two expected xfails. The 15–24
  active-credit boundary is now enforced for registration and active course
  mutations. Course-private resource authorization is not implemented; the
  resource library remains department-shared by design.
- The implementation, dependency lockfile, and Phase 1 follow-up updates
  described here are committed and pushed on `main`. GitHub-hosted CI was not
  run from this workspace.
