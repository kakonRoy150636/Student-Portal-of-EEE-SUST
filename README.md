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

**Try it locally:** `docker compose up --build -d`
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
| Authentication | JWT access tokens, rotated refresh tokens, HttpOnly refresh cookies, and RBAC |
| Academic operations | Course enrolment, schedules, attendance, credit-hour validation, and department dashboards |
| Booking | Room and lab booking with PostgreSQL GiST conflict prevention |
| Resources | Presigned S3/MinIO uploads and PostgreSQL full-text search |
| Projects | Capstone lifecycle, supervisor workflows, and GitHub integration |
| Career | Opportunities, JSON-Resume profiles, and public portfolios |
| Notifications | Firebase Cloud Messaging with Celery worker and Beat scheduling |
| AI assistant | Google Gemini with pgvector and full-text hybrid retrieval |
| Alumni portal | Alumni verification, directory search, visibility controls, events, mentorship, scholarships, news, and gallery foundations |

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

The backend is organised by domain across API endpoints, schemas, services, repositories, models, and tasks. Alembic owns database upgrades; `database/schema.sql` is a reference snapshot, not a container init script. The older numbered SQL migrations remain as historical references.

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

Update `.env` before using external services. At minimum, change `SECRET_KEY` for any non-local environment. Gemini and Firebase credentials are optional for the core dashboard, but required by their respective integrations.

### Run the local stack

The core application services are:

```bash
docker compose up --build -d
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

The `migrate` service runs `alembic upgrade head` after PostgreSQL is healthy.
Backend and Celery services start only after it exits successfully. `minio-init`
creates the private bucket using the `mc` binary included in the MinIO image.

### Database migrations

Alembic uses the async SQLAlchemy/asyncpg `DATABASE_URL` from `.env`. The
PostgreSQL image includes pgvector; the migration user needs permission to
create the `vector`, `btree_gist` and `uuid-ossp` extensions.

`20260911_0001` now contains a complete, frozen baseline of the schema at
2026-10-02, including enums, generated tsvectors, the GIN index, sequences,
foreign keys and both GiST exclusion constraints. Its SQL is packaged in
`backend/alembic/sql/20260911_0001_baseline.sql`; it does not depend on a host
mount. Existing revision IDs are retained. Later historical revisions still
run, including the notification recipient/read index added after the baseline.
Future schema changes belong in **new revisions**, not edits to this snapshot.

```bash
# Start PostgreSQL, then apply all pending migrations (also automatic on up).
docker compose up -d postgres
docker compose run --rm migrate

# Show applied revision and available history.
docker compose run --rm migrate alembic current
docker compose run --rm migrate alembic history

# Create a new revision; the dev mount writes it into backend/alembic/versions/.
docker compose run --rm migrate alembic revision -m "describe schema change"
# Optional starting point from ORM metadata (review generated SQL carefully):
docker compose run --rm migrate alembic revision --autogenerate -m "describe schema change"

# Upgrade / roll back one revision. Stop API/workers before rolling back.
docker compose run --rm migrate alembic upgrade head
docker compose stop backend celery_worker celery_beat
docker compose run --rm migrate alembic downgrade -1
```

Autogenerate is a draft: the ORM does not represent every SQL-only object.
Review generated drops/type changes and hand-write `op.execute` for extensions,
generated columns, specialized indexes and exclusion constraints. Keep the
reference schema aligned when adding a new revision. Rebuild/redeploy to ship
new revisions to production; plain `docker compose restart` does not rerun a
completed one-shot migration service. Explicitly run `migrate` for each release.

Downgrades can remove data. Some historical revisions are intentionally
additive/partially reversible; inspect their `downgrade()` before using them.
`alembic downgrade base` removes portal tables and enums and is for disposable
databases only. Shared extensions are retained. Migration commands use a
PostgreSQL advisory lock so concurrent deployments cannot race the version table.

#### Existing databases created by schema.sql

Back up the database first. If `alembic current` already reports a revision,
use `upgrade head` without stamping. For an **unversioned database matching the
current schema.sql**, adopt it once, then apply incremental revisions:

```bash
docker compose up -d postgres
docker compose run --rm migrate alembic stamp 20260911_0001
docker compose run --rm migrate alembic upgrade head
docker compose up --build -d
```

`stamp` records a version; it does not create or validate objects. Compare a
schema-only dump against `database/schema.sql` before using it. Older/partial
schemas need reconciliation against their original schema and the historical
revisions first; do not blindly stamp them or stamp `head` to hide missing
objects. The baseline refuses an unversioned non-empty database rather than
silently skipping or overwriting its tables.

#### Development-only seed

Reference/demo rows moved to `database/dev/seed.sql`. Seeding is optional,
transactional and repeatable; it creates no user accounts.

```bash
docker compose --profile dev-seed run --rm seed-dev
```

The wrapper refuses any environment other than `development`. Neither schema
nor seed is mounted into `docker-entrypoint-initdb.d`. The production Compose
file has **no seed service or seed mount**, and the backend image does not
contain the dev seed. Use the production file on its own:

```bash
docker compose -f docker-compose.prod.yml up --build -d
# Explicit migration command for an existing production deployment:
docker compose -f docker-compose.prod.yml run --rm migrate
```

#### Reproduce the fresh-volume migration check

Requires Docker Compose 2.24.4+ (`docker compose`, the modern equivalent of
`docker-compose`). The overlay uses test-only credentials, no published ports,
and project-scoped containers/volumes. Run from the repository root:

```bash
docker compose -p sust-eee-migration-check -f docker-compose.yml -f docker-compose.migration-test.yml up --build -d --wait
docker compose -p sust-eee-migration-check -f docker-compose.yml -f docker-compose.migration-test.yml logs migrate
docker compose -p sust-eee-migration-check -f docker-compose.yml -f docker-compose.migration-test.yml exec -T backend \
  env MIGRATION_TEST_DATABASE_URL=postgresql://migration_test:migration_test@postgres:5432/migration_test \
  python -m pytest -q tests/test_migrations_postgres.py
# Remove only this disposable verification project's volumes when finished.
docker compose -p sust-eee-migration-check -f docker-compose.yml -f docker-compose.migration-test.yml down -v
```

Use a new project name for a fresh volume if that test project already exists.
The PostgreSQL test compares the baseline's actual catalogs against a separate
database created from schema.sql, exercises GiST/full-text behavior, upgrades
to head, checks repeated/concurrent upgrades, adopts an existing populated
database, and tests downgrade/re-upgrade. It creates and removes its own random
databases; it does not alter the database named in the test URL.

Verification result (2026-10-03): isolated fresh-volume `docker compose up -d
--wait` exited successfully; migration reached `20260918_0006`, then the API
and frontend became healthy. Users, courses and rooms were all empty before
opt-in seeding. The backend suite, with the PostgreSQL migration lifecycle test
enabled, reported **98 passed, 7 skipped** (the separate legacy PostgreSQL
fixtures were not configured). The development seed inserted 1 semester,
3 courses and 4 rooms; its production environment guard rejected execution.

### Frontend-only development

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

### Backend tests

The backend image installs the development extras from `backend/pyproject.toml`.

```bash
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python -m pytest -q tests/test_schema_parity.py
```

The schema parity test checks that ORM columns and the bootstrap schema remain aligned. Test failures involving external services require the relevant Redis, PostgreSQL, MinIO, Firebase, or Gemini configuration.

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
      schema.sql               Reference schema (not executed at startup)
      dev/                     Opt-in development seed and environment guard
      migrations/              Historical SQL migrations
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

- Domain-oriented backend structure with thin API endpoints.
- Async database access with SQLAlchemy 2 and PostgreSQL constraints for conflict prevention.
- Versioned Alembic upgrades gated before API/worker startup, with real PostgreSQL migration lifecycle tests.
- Security-sensitive uploads use ownership checks, server-side object validation, and presigned storage.
- Focused tests cover authentication, security, dashboard contracts, alumni flows, and ORM/schema parity.

## Roadmap

- Complete public alumni landing content and media management
- Expand alumni events, scholarship applications, mentorship flows, and career bridging
- Add production observability and department analytics
- Improve mobile navigation and PWA support
- Support additional university departments after EEE validation
- Add automated CI checks for backend tests and frontend builds
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
