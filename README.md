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
