# SUST EEE Smart Student Portal

[![CI](https://github.com/kakonRoy150636/Student-Portal-of-EEE-SUST/actions/workflows/ci.yml/badge.svg)](https://github.com/kakonRoy150636/Student-Portal-of-EEE-SUST/actions/workflows/ci.yml)

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
| Academic operations | Published semester course selection, enrollment lifecycle, schedules, attendance, credit-hour validation, and department dashboards |
| Booking | Room and lab booking with PostgreSQL GiST conflict prevention |
| Resources | Presigned S3/MinIO uploads and PostgreSQL full-text search |
| Projects | Capstone lifecycle, supervisor workflows, and GitHub integration |
| Career | Opportunities, JSON-Resume profiles, and public portfolios |
| Notifications | Firebase Cloud Messaging with Celery worker and Beat scheduling |
| AI assistant | Cited Gemini answers, pgvector/full-text RRF retrieval, safe abstention and Redis quota/cost caps |
| Alumni portal | Standalone batch-aware network, career timelines, privacy-safe directory search, CSV import, verification, events, mentorship, scholarships, news, and gallery foundations |

## Dashboard Experience

The standalone alumni network is documented in [docs/ALUMNI.md](docs/ALUMNI.md), including its batch, directory, profile, career timeline, privacy, and CSV import APIs.

AI setup, ingestion, usage limits and the 25-question retrieval evaluation: [docs/AI_ASSISTANT.md](docs/AI_ASSISTANT.md).

The signed-in frontend uses an academic editorial direction rather than a generic admin template:

- SUST campus image-led student homepage
- Navy and muted amber palette
- Serif academic headings, readable sans-serif body copy, and tabular mono data
- Live dashboard metrics from `GET /api/v1/dashboard/summary`
- Role-specific sections for students, CRs, teachers, lab assistants, alumni, and admins
- Course selection, schedule, attendance, resources, AI assistant, and career quick actions
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
frozen pre-notification baseline** (`backend/alembic/sql/20260911_0001_baseline.sql`),
adopt it once, then apply incremental revisions:

```bash
docker compose up -d postgres
docker compose run --rm migrate alembic stamp 20260911_0001
docker compose run --rm migrate alembic upgrade head
docker compose up --build -d
```

`stamp` records a version; it does not create or validate objects. Compare a
schema-only dump against the corresponding snapshot before using it. A database
created from the **current** `database/schema.sql` already includes the durable
notification tables: only after verifying exact parity, stamp `20261003_0007`
instead. Older/partial
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

### Student course selection

Students and class representatives can open **Course Selection** from the Academic
navigation to review offerings published for the active semester. The page reads
the active semester, course code/title, server-derived credit hours, assigned
teachers, enrollment state, and total active credits from the API. It supports
select, drop, and reselect actions; dropped enrollments remain visible so the
same enrollment record can be reactivated.

Only offerings that are both published and attached to an active semester can be
changed. The server remains the source of truth for eligibility, enrollment
conflicts, credits, and ownership. Successful changes refresh the dashboard,
routine, attendance, and notification queries so related views stay current.

The supporting API contracts are:

```text
GET  /api/v1/course-offerings/semesters/active
GET  /api/v1/course-offerings/published
GET  /api/v1/course-offerings/enrollments/me
GET  /api/v1/course-offerings/enrollments/me/credits
POST /api/v1/course-offerings/{offering_id}/enroll
POST /api/v1/course-offerings/enrollments/{enrollment_id}/drop
POST /api/v1/course-offerings/enrollments/{enrollment_id}/reselect
```

The interface includes loading, empty, API error, and enrollment-conflict
states. A conflict prompts the user to review the refreshed list before trying
again; it does not create a second enrollment row.

### Backend tests

### Durable notifications

The minute scanner, five-minute digest, FCM delivery retries and user preferences
are documented in [Notifications](docs/NOTIFICATIONS.md). Apply `alembic upgrade
head` before starting the updated API/workers. Notification preferences are
available on the Notifications page, with quiet hours interpreted in Asia/Dhaka.

The frontend is an installable PWA with offline class routine, web push opt-in,
and a live notification center. See [PWA setup and audit](docs/PWA.md) for public
Firebase build configuration, iPhone installation steps and verification.


#### Critical integration suite: real PostgreSQL + Redis

```bash
mkdir -p coverage/backend
docker compose -p portal-critical-tests -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from tests
docker compose -p portal-critical-tests -f docker-compose.test.yml down -v
```

This standalone test stack uses `pgvector/pgvector:pg16` and Redis 7 with no
published ports or production credentials/volumes. PostgreSQL data is temporary.
The runner migrates a template database with Alembic, clones a separate database
for each test, uses real committed transactions for races, and cleans it up.
Redis is real; only this disposable test server's DB 15 is flushed between tests.
Do not point `INTEGRATION_REDIS_URL` at a shared/production Redis database.

Factories and fixtures are in `backend/tests/integration/`. Tests call FastAPI
via HTTPX ASGITransport with an independent DB session per request. They are
integration tests, not browser tests or live FCM delivery tests. Run serially;
the dedicated Redis DB is not isolated per pytest-xdist worker.

Coverage artifacts:
- `coverage/backend/html/index.html` — browsable line/branch coverage
- `coverage/backend/coverage.xml` and `coverage.json` — CI/machine-readable
- `coverage/backend/junit.xml` — test results including expected failures

The coverage configuration supports SQLAlchemy's greenlets and task threads;
without that, async SQL execution undercounts exercised code. Coverage is
focused on the critical modules, not an artificial 100% project target.

See [Backend test report](docs/BACKEND_TEST_REPORT.md) for measured coverage,
discovered fixes and explicit feature gaps. Known missing features are not
reported as passing tests. Four strict expected-failure contracts become CI
failures on unexpected pass; a separate prerequisite case records that no
prerequisite/completion model exists to test yet.

For a focused rerun (start disposable services first):

```bash
docker compose -p portal-critical-tests -f docker-compose.test.yml up -d postgres redis
docker compose -p portal-critical-tests -f docker-compose.test.yml run --rm tests python -m pytest tests/integration/test_bookings.py -v --tb=short
```

Optional local build acceleration: set `TEST_BASE_IMAGE` to an existing Python
backend image with dependencies installed; otherwise the test image builds
independently from `python:3.11-slim`. Rebuild the tests image after source changes.

#### Existing fast regression suite

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

### Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request, and can also
be started manually from Actions. Independent jobs run:

- Backend Ruff, mypy and `pip-audit` (installed dependencies, including tools).
- Full pytest suite with PostgreSQL 16/pgvector and Redis 7 service containers;
  legacy booking, migration, refresh concurrency and critical integration tests
  are enabled. The optional MinIO test is skipped in this two-service job.
- Frontend `npm ci`, ESLint, TypeScript, production build and `npm audit`.
- Backend/frontend Docker builds and Trivy OS/library vulnerability scans.

Pip/npm download caches and per-image BuildKit caches speed up repeat runs.
CI does not push images or deploy. It uses read-only repository permissions and
test-only service credentials; pull requests do not need repository secrets.
JUnit/coverage and audit/scan JSON reports are uploaded even when a check fails.

Trivy fails on **HIGH or CRITICAL**, including unfixed findings. npm audit fails
on HIGH/CRITICAL across runtime **and development** packages. pip-audit fails on
any known vulnerability. No audit check uses `continue-on-error` or an ignore
list. Known pytest xfails are documented in the backend test report.

Local equivalents:

```bash
python -m pip install --upgrade pip setuptools
python -m pip install './backend[dev,ci]'
cd backend
python -m ruff check app tests alembic
python -m mypy app
python -m pip_audit --local
```

From the repository root, frontend checks are:

```bash
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend audit --audit-level=high
```

Dependabot checks pip (`backend/`), npm (`frontend/`), Dockerfiles (both folders)
and GitHub Actions weekly. Dependency upgrades are proposed as PRs, not auto-merged.

**Local verification:** Ruff, mypy (92 application files), frontend lint,
typecheck/build and pip-audit passed. The CI-style full test run reported
**171 passed, 1 skipped, 5 xfailed**. Existing Vite/Tailwind build dependencies
currently produce **6 HIGH and 1 MODERATE npm findings**; the new npm gate
correctly fails until those dependencies are remediated. This is not a claim
that the GitHub-hosted workflow has already run or is green.

Both Docker builds also passed locally. Trivy correctly blocked their current
images: frontend **2 HIGH** package findings; backend **100 HIGH and 1 CRITICAL**
package findings. These counts are package/advisory occurrences, not distinct
CVEs. See [CI verification](docs/CI_VERIFICATION.md) for details.

See [Security audit and endpoint role matrix](docs/SECURITY_AUDIT.md) for findings,
fix commits, Redis budgets, webhook configuration and verification results.

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
