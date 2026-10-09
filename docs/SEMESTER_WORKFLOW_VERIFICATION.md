# Semester course workflow verification

This guide records the repeatable full-flow check for the semester course
workflow. It uses a disposable PostgreSQL/Redis/MinIO Compose project and does
not touch the normal development volumes.

## Prepare the disposable stack

From the repository root:

```bash
docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml \
  up --build -d --wait postgres redis minio minio-init migrate backend

docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml \
  --profile dev-seed run --rm --no-deps seed-dev
```

The development seed creates the five manual accounts and four catalogue
courses. Add a disposable fifth catalogue course so the browser test can
exercise **create offering** rather than colliding with a seeded offering:

```bash
docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml \
  exec -T postgres psql -U migration_test -d migration_test -v ON_ERROR_STOP=1 \
  -c "INSERT INTO courses (id, course_code, title, credit_hours, type, description)
      VALUES ('10000000-0000-0000-0000-000000000399', 'EEE 399',
              'Workflow Verification Course', 3.0, 'theory',
              'Disposable end-to-end workflow verification course.');"
```

## Run the real browser workflow

The opt-in test uses the UI for login, offering creation/publication,
assignment request/approval, course selection, drop, and reselect. It uses the
real API for read-back assertions, notifications, credits, dashboard totals,
and authorization checks. It does not intercept API responses.

```bash
docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml \
  run -d --no-deps \
  --name semester-flow-live-backend -p 18000:8000 \
  -e CORS_ORIGINS='["http://127.0.0.1:4173"]' backend

VITE_API_BASE_URL=http://127.0.0.1:18000/api/v1 \
  npm --prefix frontend run build

VITE_API_BASE_URL=http://127.0.0.1:18000/api/v1 \
SEMESTER_E2E=1 \
SEMESTER_E2E_API_ORIGIN=http://127.0.0.1:18000 \
SEMESTER_E2E_COURSE_CODE=EEE\ 399 \
  npm --prefix frontend run test:e2e -- semester-workflow.spec.ts
```

The test logs in as the seeded admin, teacher, two students, and a second
teacher. It verifies:

1. Admin creates and publishes an offering.
2. Teacher requests assignment; admin approves it.
3. Both active students receive `course_assignment` notifications.
4. Student sees the published offering and selects it.
5. Student and approved teacher receive `course_enrollment` notifications.
6. Active credits and the student dashboard total increase.
7. Drop removes the credits; reselect restores them using the same enrollment.
8. Unauthenticated and wrong-role API calls return `401`/`403`.
9. Wrong-role page visits redirect to `/dashboard`.

## Cleanup

```bash
docker rm -f semester-flow-live-backend
docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml down -v
```

The fixed credentials in `database/dev/seed.sql` are for disposable
development databases only.
