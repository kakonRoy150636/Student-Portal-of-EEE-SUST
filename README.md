# SUST EEE Smart Student Portal

Department of Electrical & Electronic Engineering (EEE)
Shahjalal University of Science and Technology (SUST), Sylhet

A production-ready academic, facility reservation, laboratory inventory, career services, and AI copilot portal.

## Modules Covered
1. **Authentication & RBAC**: JWT, refresh token rotation, student/CR/teacher/admin roles.
2. **Course & Schedule Management**: Prerequisite checking, credit boundaries (15-24), weekly routine timetable.
3. **Room & Lab Booking**: PostgreSQL GiST exclusion conflict prevention, teacher auto-approval.
4. **Attendance System**: Student roll-call, session summaries, eligibility percentage gauge.
5. **Smart Notification System**: Firebase Cloud Messaging (FCM) v1, Celery Beat 1-minute scanner for 10-minute pre-class alerts.
6. **Academic Resource Sharing & Book Exchange**: S3 presigned direct upload/download, tsvector full-text search.
7. **Smart Laboratory Management**: Equipment QR inventory, checkout/check-in, damage reporting, bench reservation.
8. **Project Hub**: Capstone thesis lifecycle, supervisor proposal, GitHub webhook commit ingestion.
9. **Career Portal & Portfolio Builder**: Jobs, scholarships, JSON-Resume CV builder, public student web portfolios.
10. **AI Academic Assistant**: Google Gemini API, pgvector hybrid search (Dense + BM25 via RRF), syllabus Q&A.

## Running Locally
```bash
cp .env.example .env
docker-compose up -d --build
```
