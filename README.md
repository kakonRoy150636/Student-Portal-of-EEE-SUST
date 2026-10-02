# SUST EEE Smart Student Portal

The SUST EEE Smart Student Portal is a full-stack academic platform for the Department of Electrical and Electronic Engineering at Shahjalal University of Science and Technology, Sylhet, Bangladesh.

It brings course planning, attendance, room and lab booking, resources, projects, career services, AI-assisted academic search, notifications, and alumni engagement into one role-aware portal.

[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](backend)
[![React](https://img.shields.io/badge/UI-React%20%2B%20TypeScript-61DAFB?logo=react&logoColor=111827)](frontend)
[![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL%2016-336791?logo=postgresql&logoColor=white)](database)
[![License](https://img.shields.io/badge/license-MIT-C9A227)](LICENSE)

> A department-focused portal that turns everyday academic work into one clear, measurable workflow.

![SUST EEE student dashboard preview](frontend/src/assets/images/login-hero.jpg)

**Try it locally:** `docker compose up --build -d postgres redis minio backend celery_worker celery_beat frontend`
**Open the app:** [localhost:5173](http://localhost:5173)

## Product Preview

The screenshots below are captured from the running local application, not mockups.

### Sign in

![SUST EEE Portal login page](docs/screenshots/login-page.png)

### Student home

![SUST EEE Portal student dashboard](docs/screenshots/student-homepage.png)

The student home combines a campus-led visual introduction with live academic metrics, quick actions, today's classes, and attendance status. Demo credentials are intentionally not published in the repository.

## What It Includes

| Area | Highlights |
| --- | --- |
| Authentication | JWT access tokens, rotated refresh tokens with family-wide replay revocation, HttpOnly refresh cookies, and RBAC |
| Academic operations | Course enrolment with server-side offering validation, role-scoped course lists, the real weekly timetable, attendance, and department dashboards |
| Booking | Room and lab booking with PostgreSQL GiST conflict prevention and staff decisions |
| Resources | Multipart upload, server-side verification (extension allowlist, size cap, magic bytes), PostgreSQL full-text search, and short-lived attachment-only download URLs |
| Projects | Projects read from the database with supervisor, team size and repository link |
| Career | Verified, unexpired opportunities from the database, most urgent first |
| Notifications | Firebase Cloud Messaging dispatch with device deactivation, Celery Beat class-alert scanner, in-app notification rows |
| AI assistant | Retrieval-first answers with citations over an indexed document library; Google Gemini when a key is configured, extractive quoting when it is not |
| Alumni portal | Alumni verification, full-text directory search, visibility controls, events, mentorship, scholarships, news, and gallery |

Every one of those rows is backed by a database table and a test; see
[`docs/IMPLEMENTED_VS_PLANNED.md`](docs/IMPLEMENTED_VS_PLANNED.md) for the
line-by-line status of each endpoint, including the parts that are deliberately
not built yet.

## Dashboard Experience

The signed-in frontend uses an academic editorial direction rather than a generic admin template:

- SUST campus image-led student homepage
- Navy and muted amber palette
- Serif academic headings, readable sans-serif body copy, and tabular mono data
- Live dashboard metrics from `GET /api/v1/dashboard/summary`
- Role-specific sections for students, CRs, teachers, lab assistants, alumni, and admins
- Schedule, attendance, resources, AI assistant, and career quick actions
- Loading skeletons and explicit empty states instead of fabricated numbers

## Product Highlights

### A dashboard that explains itself

The first screen is designed for a real student workflow: a campus-led welcome area, an academic snapshot, today's classes, attendance standing, and shortcuts to the tools students use most. The interface favours hierarchy and whitespace over noisy decoration.

### Trustworthy data states

- Attendance percentages are calculated from recorded attendance rows.
- Schedule cards are scoped to the signed-in student's enrolments.
- Empty databases show `No data` or a useful empty state instead of invented metrics.
- Admin and alumni counts are returned by protected, role-aware API endpoints.

### Premium interaction details

- Skeleton loading states keep the layout stable while data loads.
- Subtle border and elevation changes provide feedback without distracting glow effects.
- Deep-linkable cards take users directly to schedule, attendance, resources, career, or the AI assistant.
- Responsive layouts preserve the visual hierarchy on laptop, tablet, and mobile screens.

## Why This Project

University departments often split attendance, schedules, notices, rooms, resources, and alumni records across spreadsheets and chat groups. This project treats those workflows as one connected system, with permissions and database constraints designed around the people who use it.

The goal is not only to show screens. It is to make the important answers easy to find:

- What classes do I have today?
- Is my attendance on track?
- Which resources or opportunities are relevant to me?
- What needs an admin's approval?
- How can alumni stay visible, connected, and useful to current students?

## Share This Project

Short description for LinkedIn, Facebook, or a portfolio:

> I built the SUST EEE Smart Student Portal, a full-stack academic platform for the Department of EEE at SUST. It combines JWT/RBAC authentication, live role-based dashboards, attendance and scheduling, conflict-aware bookings, resources, career tools, an AI academic assistant, and an alumni portal using FastAPI, React, PostgreSQL, Redis, Celery, and Docker.

Suggested tags: `#FastAPI` `#ReactJS` `#TypeScript` `#PostgreSQL` `#Docker` `#EdTech` `#OpenSource`

## Architecture

```text
React + TypeScript + Vite
                              |
                              v
FastAPI + SQLAlchemy async + JWT/RBAC
                              |
                              +--> PostgreSQL 16 + pgvector + GiST + tsvector
                              +--> Redis --> Celery worker / Beat
                              +--> MinIO or AWS S3 presigned storage
                              +--> Firebase Cloud Messaging
                              +--> Google Gemini API
```

The backend is organised by domain across API endpoints, schemas, services, repositories, models, and tasks. Database changes are mirrored in `database/schema.sql`, numbered SQL migrations, and Alembic revisions.

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite, React Router, Tailwind CSS, TanStack Query, Lucide icons
- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2 async, Pydantic v2, Alembic
- **Database:** PostgreSQL 16, `btree_gist`, `vector`, GiST exclusion constraints, PostgreSQL full-text search
- **Infrastructure:** Docker Compose, Redis, Celery, MinIO/AWS S3
- **Integrations:** Firebase FCM, Google Gemini, GitHub webhooks

## Getting Started

### Prerequisites

- Docker Engine and Docker Compose v2
- Git

### Configure

```bash
git clone https://github.com/kakonRoy150636/Student-Portal-of-EEE-SUST.git
cd Student-Portal-of-EEE-SUST
cp .env.example .env
```

Update `.env` before using external services. At minimum, change `SECRET_KEY` for any non-local environment.

Everything except the assistant runs without third-party credentials:

| Variable | Without it |
| --- | --- |
| `GEMINI_API_KEY` | The assistant still retrieves and answers, quoting the indexed passages instead of generating prose |
| `FIREBASE_CREDENTIALS_PATH` | Notifications are stored in-app; push dispatch logs `fcm_not_configured` and is skipped |
| `S3_*` | Resource and avatar uploads fail with 409/503; the rest of the portal is unaffected |

No account is seeded. `database/seed.sql` contains reference data only (courses,
rooms, semesters); the first administrator is created from the environment:

```bash
BOOTSTRAP_ADMIN_EMAIL=you@sust.edu
BOOTSTRAP_ADMIN_PASSWORD=<at least 12 bytes>
```

On the first start the API creates that account with `must_change_password`, so
the environment value is a one-time handover credential: until it is replaced,
the account can only reach the password-change and MFA-enrolment routes. Remove
the variables afterwards — they are ignored once a super_admin exists. Everyone
else registers through the portal and is approved by an administrator.

`SECRET_KEY` must be replaced outside development — the app refuses to start with
the development key when `ENVIRONMENT=production`.

### Run the local stack

The core application services are:

```bash
docker compose up --build -d postgres redis minio backend celery_worker celery_beat frontend
```

Open:

- Frontend: <http://localhost:5173>
- Backend health: <http://localhost:8000/health>
- API documentation: <http://localhost:8000/api/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- MinIO API: <http://localhost:9000>
- MinIO console: <http://localhost:9001>
- PostgreSQL: `localhost:5433`
- Redis: `localhost:6380`

The compose file also contains a `minio-init` bucket initializer. If the `minio/mc` image is unavailable in your registry, start the core services with the command above and create the `sust-eee-resources` bucket from the MinIO console before testing uploads.

### Frontend-only development

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

### Backend tests

The image installs `backend/requirements-dev.txt`, which includes the test extras.

```bash
# inside the compose stack
docker compose exec -T backend python -m pytest -q

# or on the host, with a virtualenv
cd backend && python -m pytest -q
```

The suite runs on in-memory SQLite and needs no Redis, MinIO, Gemini or Firebase
credentials; the seven tests that require PostgreSQL's GiST exclusion constraint
skip themselves unless `TEST_DATABASE_URL` points at a real database. The schema
parity test fails the build if any ORM table or column is missing from
`database/schema.sql` — that check is what caught the missing `updated_at`
columns described in `database/migrations/009_add_missing_updated_at.sql`.

### Build the frontend

```bash
npm --prefix frontend run build
```

## User Roles

| Role | Main access |
| --- | --- |
| Student | Enrolment, schedule, attendance, room booking, resources, projects, career, and AI assistant |
| Class Representative | Student workflows plus class coordination and CR tools |
| Teacher | Course and attendance management, approvals, lab workflows, and project supervision |
| Lab Assistant / ER | Lab inventory, equipment checkout, damage reports, and assigned lab workflows |
| Alumni | Verified alumni profile, directory, alumni events, mentorship, scholarships, and alumni dashboard |
| Super Admin | User approval, department configuration, analytics, and administrative controls |

## Repository Layout

```text
backend/
      app/api/v1/endpoints/    FastAPI route modules
      app/models/              SQLAlchemy models
      app/repositories/        Database access
      app/schemas/             Pydantic request/response models
      app/services/            Domain logic
      app/tasks/               Celery tasks
      tests/                   Pytest suite
database/
      schema.sql               Fresh-install bootstrap schema
      migrations/              Numbered idempotent SQL migrations
frontend/src/
      features/                Domain pages and API clients
      components/              Shared UI and layout components
      routes/                  React Router configuration
      contexts/                Auth and theme state
```

## Suggested Demo Flow

Use this short path when presenting the project:

1. Sign in as a student and show the campus-led dashboard.
2. Point out the live academic snapshot and explain where each value comes from.
3. Open today's schedule and attendance to demonstrate role-scoped data.
4. Use a quick action to open resources or the AI assistant.
5. Sign in as an admin to show approval queues and department-level summaries.
6. Sign in as an alumni user to show the verified profile and directory experience.

## Engineering Quality

- Domain-oriented backend structure with thin API endpoints; services own the rules, repositories own the queries.
- Async database access with SQLAlchemy 2 and PostgreSQL constraints for conflict prevention (GiST exclusion on room slots, unique keys on refresh tokens and class alerts).
- bcrypt runs in a worker thread, so a login cannot stall every other request on the event loop.
- Idempotent SQL migrations mirrored across bootstrap SQL, numbered migrations, and Alembic — with a parity test that fails if the ORM and `schema.sql` ever drift again.
- Uploads (avatars and resources) are verified server-side: authentication, ownership, extension allowlist, size measurement and magic-byte checks.
- Focused tests cover authentication, security regressions, dashboard contracts, resources, the assistant, alumni flows, and ORM/schema parity.

## Security

- **Sessions:** 15-minute access tokens (in memory on the client), 7-day refresh tokens stored only as SHA-256 hashes, rotated on every use. Presenting a rotated token revokes the whole family (theft detection).
- **Token scoping:** a `type` claim separates access, refresh and the short-lived avatar-upload token; each route accepts exactly one.
- **Throttling:** two independent login counters (per account and per IP) with a delay schedule that exempts correct passwords, plus fixed-window ceilings on registration, refresh, AI queries and uploads.
- **Enumeration resistance:** login returns one message for unknown, wrong-password and inactive accounts, and always performs a bcrypt comparison so response timing does not leak existence. Signup collisions do not confirm that an address has an account.
- **Storage:** the bucket is private; only the `avatars/` prefix is anonymously readable and everything else is served through short-lived, attachment-disposition URLs.
- **Transport/browser:** security headers are set by both nginx and the API (CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; HSTS in production).
- **Errors:** constraint violations map to 409, unexpected exceptions to a generic JSON 500 with the traceback kept in the structured log.
- **Second factor:** TOTP for administrators, with ten single-use recovery codes stored only as SHA-256 hashes. A privileged account that has not enrolled is confined to the enrolment routes.
- **Sessions:** a per-device list (`/auth/sessions`) built from refresh-token families, with metadata and one-click revocation; changing a password or completing a reset ends every other session.
- **Audit trail:** approvals, booking decisions, file deletions, password changes/resets and MFA changes are recorded in `audit_logs` and readable by administrators at `GET /admin/audit-logs`.
- **Housekeeping:** a daily Celery Beat task prunes expired/revoked refresh tokens and spent reset tokens.
- **CI:** tests, bandit, `pip-audit`, `tsc`, the production build and `npm audit --audit-level=high` run on every push.

## Roadmap

- Postgres-backed CI job for the booking exclusion constraint (currently skipped without a database)
- Supervisor workflow UI (proposals exist in the schema; no screen yet) and GitHub webhook handling for project repositories
- Equipment checkout and damage-report screens (models and tables exist; only the inventory list is exposed)
- Email verification for self-service student signup (password reset is implemented; the email itself is logged when SMTP is unconfigured, see below)
- Production observability: OpenTelemetry traces and an error tracker behind the existing correlation-id middleware
- Improve mobile navigation and PWA support
- Support additional university departments after EEE validation
- Publish a short product demo and screenshots for each role

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-change`.
3. Run the focused tests and frontend build.
4. Keep migrations, ORM models, and bootstrap SQL aligned.
5. Open a pull request with the motivation, implementation, and validation steps.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).

## Author

**Kakon Roy**
EEE, SUST | [GitHub](https://github.com/kakonRoy150636)
