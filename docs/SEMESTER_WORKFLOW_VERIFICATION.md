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

The development seed creates eight manual accounts and four catalogue
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

The opt-in tests use the UI for login, offering creation/publication,
assignment request/approval, course selection, drop, and reselect. They use the
real API for read-back assertions, notifications, credits, dashboard totals,
and authorization checks. They do not intercept API responses.

```bash
docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml \
  run -d --no-deps \
  --name semester-flow-live-backend -p 127.0.0.1:18000:8000 \
  -e CORS_ORIGINS='["http://127.0.0.1:4173"]' backend

VITE_API_BASE_URL=http://127.0.0.1:18000/api/v1 \
  npm --prefix frontend run build

VITE_API_BASE_URL=http://127.0.0.1:18000/api/v1 \
SEMESTER_E2E=1 \
SEMESTER_E2E_API_ORIGIN=http://127.0.0.1:18000 \
SEMESTER_E2E_COURSE_CODE=EEE\ 399 \
  npm --prefix frontend run test:e2e -- semester-workflow.spec.ts
```

The admin-managed workflow test logs in as the seeded admin, teacher, two
students, and a second teacher. It verifies:

1. Admin creates and publishes an offering.
2. Teacher requests assignment; admin approves it.
3. Both active students receive `course_assignment` notifications.
4. Student sees the published offering and selects it.
5. Student and approved teacher receive `course_enrollment` notifications.
6. Active credits and the student dashboard total increase.
7. Drop removes the credits; reselect restores them using the same enrollment.
8. Unauthenticated and wrong-role API calls return `401`/`403`.
9. Wrong-role page visits redirect to `/dashboard`.

The teacher-provided workflow test in the same file additionally:

1. Registers disposable senior (`4-1`) and junior (`2-2`) student accounts.
2. Logs in as Tasfik and follows **Dashboard → Offer a course** to the form.
3. Publishes a course for target term `3-1`, with code, name, credits, and type.
4. Checks availability notifications for the `3-1` peer and `4-1` senior, with
   no notification for the junior and no automatic enrollments for anyone.
5. Enrolls the peer and senior through the UI; the junior cannot see the course
   and receives `403` when trying its enrollment API directly.
6. Rejects a student's attempt to provide a course and reads back the teacher's
   roster, which contains only the two enrolled students.

Run only this test with `--grep 'live teacher offering'` after the existing
`semester-workflow.spec.ts` argument. It does not require the `EEE 399` insert.

These tests commit their mutations. Use a fresh disposable stack for a complete
rerun instead of running the fixed catalogue/offering setup again on the same
database. Without `SEMESTER_E2E=1`, both live tests are explicitly skipped.

### Verification receipt (2026-10-11)

- Both live browser workflows above passed: **2 passed in 16.5 seconds**, using
  a freshly built API and seeded PostgreSQL/Redis/MinIO stack. The teacher flow
  verified peer/senior enrollment and direct-API rejection for a junior.
- The isolated backend regression suite passed **409 passed, 1 skipped,
  2 xfailed** after the Course Workspace additions. The skip requires opt-in
  MinIO upload-test configuration; LAB-1
  (bench reservation constraint/API) and ENR-3 (prerequisite model) remain known
  gaps, not passing behavior tests.
- Frontend typecheck, ESLint, production build and **78 unit tests** passed.
  Default Playwright checks passed **5 tests**, skipping the two live tests;
  their separate result is recorded above. Ruff and mypy (100 source files)
  passed for the backend.
- Notification inbox readback is verified; live FCM acceptance/device display
  is not. This is local verification, not production deployment or hosted CI.

The Course Workspace API/UI smoke flow is documented separately in
[COURSE_WORKSPACE.md](COURSE_WORKSPACE.md). It covers offering-scoped teacher
authorization, learner enrollment scope, announcement draft/publish/schedule/
archive/pin/read state, course resources, events/reminders, and moderated
questions. The Alembic revision `20261012_0012_course_workspace` must be applied
before starting the updated API and workers.

## Cleanup

```bash
docker rm -f semester-flow-live-backend
docker compose -p semester-flow \
  -f docker-compose.yml -f docker-compose.migration-test.yml down -v

# Restore the default API base in generated frontend artifacts after the live run.
npm --prefix frontend run build
```

The fixed credentials in `database/dev/seed.sql` are for disposable
development databases only.

## Teacher-provided course manual check

The seed also includes these requested development users, all with password
`password123`:

| Role | Login identifier | Name | Target term |
|---|---|---|---|
| Teacher | `tasfik-rahman` | Tasfik Rahman | — |
| Student | `2023338049` | Kakon Chandro Roy | `3-1` |
| CR | `2023338050` | Tanij Roy | `3-1` |

1. Sign in as `tasfik-rahman` and choose **Offer a course** on the dashboard.
   This opens `/teacher-assignment`; the shortcut and page are teacher-only.
2. Choose **Offer a course** and enter the course code, course name, credits,
   course type, description, and the active semester/target term.
3. Submit the form. The offering is published immediately and Tasfik is shown
   as its assigned teacher; no student is enrolled automatically.
4. Sign in as `2023338049` or `2023338050` and open `/course-selection`.
5. Same-term students/CRs and seniors see the new course and its
   `course_available` notification, then can choose **Select** to enroll.
6. Return to Tasfik's account and open the course roster to see only students
   who selected the course.

Teacher-provided courses are scoped to `Semester.target_term`, using this
explicit order rather than string comparison or admission-session year:

`1-1 < 1-2 < 2-1 < 2-2 < 3-1 < 3-2 < 4-1 < 4-2`.

For a `3-1` offering, students/CRs with `profiles_student.current_term` of
`3-1`, `3-2`, `4-1`, or `4-2` qualify. Earlier terms (juniors) do not qualify.
Missing or invalid profile terms also fail closed for scoped offerings.
The same rule governs offering lists, active-semester lists, availability and
assignment notifications, registration selections, enrollment, and reselection.
Draft/inactive offerings remain unavailable; notifications exclude inactive
accounts. Existing semesters with `NULL target_term` retain legacy unrestricted
term eligibility. Teacher provision cannot create such unscoped offerings.

Enrollment remains voluntary. Existing credit limits are unchanged: a nonempty
registration selection requires 15–24 active credits; normal enrollment and
reselection enforce the 24-credit maximum. No schema migration is required for
the senior-eligibility policy. Existing notices are not retroactively resent.
