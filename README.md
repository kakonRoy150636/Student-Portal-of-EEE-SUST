# SUST EEE Smart Student Portal

The SUST EEE Smart Student Portal is a full-stack academic platform for the Department of Electrical and Electronic Engineering at Shahjalal University of Science and Technology, Sylhet, Bangladesh.

It brings course planning, attendance, room and lab booking, resources, projects, career services, AI-assisted academic search, notifications, and alumni engagement into one role-aware portal.

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

Update `.env` before using external services. At minimum, change `SECRET_KEY` for any non-local environment. Gemini and Firebase credentials are optional for the core dashboard, but required by their respective integrations.

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
      schema.sql               Fresh-install bootstrap schema
      migrations/              Numbered idempotent SQL migrations
frontend/src/
      features/                Domain pages and API clients
      components/              Shared UI and layout components
      routes/                  React Router configuration
      contexts/                Auth and theme state
```

## Database Migration Rules

Every schema change must remain in lockstep across:

1. `database/schema.sql`
2. `database/migrations/NNN_name.sql`
3. `backend/alembic/versions/`

SQL migrations should be idempotent, use UTC `TIMESTAMPTZ` values, and keep status fields as `VARCHAR` with explicit `CHECK` constraints. Do not apply a migration to a live database as a dry run; PostgreSQL DDL is real and must be inspected after deliberate application.

## Roadmap

- Complete public alumni landing content and media management
- Expand alumni events, scholarship applications, mentorship flows, and career bridging
- Add production observability and department analytics
- Improve mobile navigation and PWA support
- Support additional university departments after EEE validation

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
<div align="center">

# ⚡ SUST EEE Smart Student Portal

**A production-grade academic ecosystem for the Department of Electrical & Electronic Engineering**
Shahjalal University of Science and Technology (SUST), Sylhet, Bangladesh

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-GiST%20%2B%20pgvector-336791?logo=postgresql&logoColor=white)](database)
[![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-blueviolet)](CONTRIBUTING.md)

*One platform for authentication, course enrollment, room booking, attendance, lab management, career services, and an AI academic assistant — built for real departmental scale.*

[Overview](#-overview) •
[Modules](#-modules) •
[Architecture](#-architecture) •
[Tech Stack](#-tech-stack) •
[Getting Started](#-getting-started) •
[Roles](#-user-roles) •
[Roadmap](#-roadmap) •
[Contributing](#-contributing)

</div>

---

## 📖 Overview

The **SUST EEE Smart Student Portal** replaces the scattered mix of spreadsheets, notice boards, and messaging groups that most university departments run on with a single, coherent system. It's designed as a final-year engineering project but built with the discipline of a production system — real conflict-prevention at the database layer, real-time notifications, and an AI assistant that actually understands the syllabus.

It serves four distinct user roles — **Student, Class Representative (CR), Teacher, and Admin** — each with a purpose-built workflow rather than a single generic dashboard reused everywhere.

## 🧩 Modules

| # | Module | What it does |
|---|--------|---------------|
| 1 | **Authentication & RBAC** | JWT auth with refresh token rotation; role-based access for all four user types |
| 2 | **Course & Schedule Management** | Prerequisite checking, credit-hour boundaries (15–24), weekly routine generation |
| 3 | **Room & Lab Booking** | Conflict-free scheduling via PostgreSQL GiST exclusion constraints, teacher auto-approval |
| 4 | **Attendance System** | Roll-call sessions, attendance summaries, live eligibility percentage gauge |
| 5 | **Smart Notifications** | Firebase Cloud Messaging v1 + Celery Beat scanning every minute for 10-minute pre-class alerts |
| 6 | **Resource Sharing & Book Exchange** | S3 presigned uploads/downloads, Postgres full-text search (tsvector) |
| 7 | **Smart Lab Management** | QR-coded equipment inventory, checkout/check-in, damage reporting, bench reservation |
| 8 | **Project Hub** | Capstone thesis lifecycle, supervisor proposals, GitHub webhook commit ingestion |
| 9 | **Career Portal & Portfolio Builder** | Job/scholarship board, JSON-Resume CV builder, public student portfolios |
| 10 | **AI Academic Assistant** | Google Gemini API + pgvector hybrid search (dense + BM25 via RRF) for syllabus Q&A |

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌────────────────────┐
│  Frontend   │ ───▶ │   Backend API     │ ───▶ │   PostgreSQL        │
│ (Dashboard) │      │  JWT + RBAC       │      │  GiST + pgvector     │
└─────────────┘      └──────────────────┘      └────────────────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
      ┌───────────────┐ ┌───────────┐  ┌─────────────────┐
      │ Celery Beat    │ │  AWS S3    │  │ Google Gemini    │
      │ + FCM v1       │ │ Presigned  │  │ API (RAG search) │
      │ (notifications)│ │ Uploads    │  │                  │
      └───────────────┘ └───────────┘  └─────────────────┘
```

**Design direction:** the dashboard follows an *"Instrument Panel"* aesthetic — a dark graphite base with brass/copper accents, aiming for a precision-instrument feel rather than a generic SaaS look.

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology |
|-------|-----------|
| **Auth** | JWT, Refresh Token Rotation, RBAC |
| **Database** | PostgreSQL (GiST exclusion constraints, pgvector, tsvector FTS) |
| **Notifications** | Firebase Cloud Messaging v1, Celery Beat |
| **Storage** | AWS S3 (presigned URLs) |
| **AI / Search** | Google Gemini API, pgvector hybrid search (Dense + BM25 via RRF) |
| **Integrations** | GitHub Webhooks, JSON-Resume |
| **Infra** | Docker, docker-compose (dev + prod) |

</div>

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/kakonRoy150636/Student-Portal-of-EEE-SUST.git
cd Student-Portal-of-EEE-SUST

# 2. Configure environment variables
cp .env.example .env

# 3. Build and run with Docker
docker-compose up -d --build
```

For a production deployment, use the dedicated compose file instead:

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## 👥 User Roles

| Role | Access |
|------|--------|
| 🎓 **Student** | Enrollment, attendance view, room/lab booking requests, resource sharing, career portal, AI assistant |
| 📋 **CR (Class Representative)** | Everything a Student has, plus class-level coordination and scheduling requests |
| 👨‍🏫 **Teacher** | Course management, attendance roll-call, room/lab approvals, project supervision |
| 🛡️ **Admin** | Full system control — user management, department-wide scheduling, analytics |

## 🗺️ Roadmap

- [ ] Public beta rollout within the EEE department
- [ ] Mobile-responsive PWA support
- [ ] Analytics dashboard for department administrators
- [ ] Multi-department expansion beyond EEE

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. If you'd like to contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.

## 👤 Author

**Kakon Roy**
EEE, SUST | [GitHub](https://github.com/kakonRoy150636)

---

<div align="center">

*Built to make department life run on software instead of spreadsheets.*

</div>
