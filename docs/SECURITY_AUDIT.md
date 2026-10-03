# Security audit — 2026-10-03

Scope: source/configuration review at `aa6387e`, followed by targeted fixes.
This does not attest to deployed secrets, credential rotation or Git history cleanup.

## Findings before fixes

| ID | Severity | Finding |
|---|---|---|
| S1 | High | Production Compose requires Postgres/MinIO passwords and publishes only frontend port 80, but JWT `SECRET_KEY`, backend `DATABASE_URL` and S3 credentials are inherited via env_file with development defaults in settings. Require them explicitly and reject known defaults. |
| S2 | High | Login delays happen after bcrypt. Refresh, AI, resource search and alumni signup lack request budgets. Add atomic Redis windows before expensive work, with 429/Retry-After and production fail-closed behavior. |
| S3 | High | Refresh replay revokes families sequentially, but locks only the presented row. Different generations of a family can race/deadlock with rotation. Serialize the family across rotation, replay and logout. |
| S4 | Medium | GitHub HMAC helper exists but no webhook is registered. Malformed non-ASCII signatures can raise. Add a bounded signed receiver; do not pretend a project synchronization workflow exists. |
| S5 | High | Resource finalize trusts Content-Type metadata; avatar does not require key extension/type agreement. A still-live PUT URL can overwrite a finalized object. Validate bytes and publish an immutable, separately named object. |
| S6 | Medium | Lab equipment API accepts every authenticated role although the frontend restricts it to staff. Several other routes intentionally use ownership/authentication rather than role gates; matrix below flags each. |

Current `database/dev/seed.sql` contains reference rows, no users or password hashes.
Bootstrap credentials are unset by default; `admin` is an identifier, not a password.
Test passwords are test-only. Historical seeds and tracked `.backups/` data are not
used by startup; deployments created from old revisions need operator credential
rotation. Removing a current seed does not rotate a live password or erase history.

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

## Verification / residual limits

To be updated after separate fix commits. Shared-library access remains intentional;
course-private resources would require an explicit entitlement policy. Production
infrastructure must be deployed using the standalone production Compose file,
not merged with development's published ports.
