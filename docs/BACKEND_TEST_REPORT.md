# Critical backend integration tests

**Notification follow-up:** the former NOT-1 scanner stub is now implemented
and its xfail has been replaced with passing behavioral tests. See
[Notifications](NOTIFICATIONS.md). Counts/coverage below are the historical
2026-10-03 test-suite baseline, not the later expanded notification suite.

Verified 2026-10-03 against real PostgreSQL 16 (pgvector image) and Redis 7.

## Result

**31 passed, 5 xfailed; 0 unexpected failures** (36 cases, ~21 seconds).
Four xfails exercise real failing contracts. One explicitly records a blocked
prerequisite test; it does not claim to verify a nonexistent policy.
The older fast regression suite separately reported **130 passed, 11 skipped**
with its optional external-service test URLs unset.

Run from the repository root:

```bash
mkdir -p coverage/backend
docker compose -p portal-critical-tests -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from tests
docker compose -p portal-critical-tests -f docker-compose.test.yml down -v
```

The measured run used `TEST_BASE_IMAGE=sust-eee-migration-check-backend:latest`
to reuse locally installed dependencies; that image is optional and not required
by the default configuration. All application/test source was rebuilt into the
runner. Infrastructure failures fail the Docker run; they are not silently skipped.

## Coverage (integration suite only)

| Module | Covered executable lines | Combined line/branch coverage |
|---|---:|---:|
| Booking service | 56/67 | 80% |
| Attendance service | 63/66 | 92% |
| Attendance repository | 17/17 | 100% |
| Auth service | 101/130 | 73% |
| Auth/RBAC dependencies | 46/76 | 57% |
| Redis request budgets | 15/20 | 71% |
| Notification task | 6/6 | 100% — **historical log-only stub, not current feature coverage** |
| Total selected modules | 304/382 | **75.2%** |

Statement coverage is **79.6%**; branch coverage is **60.0%**. No 100% target is
imposed. Coverage includes lines reached by expected-failure tests; neither high
coverage nor an expected failure proves a feature works. Missing prerequisite
code cannot contribute coverage. HTML, XML, JSON and JUnit outputs are generated
under `coverage/backend/` and ignored by Git; this summary is retained in source.

## What the tests prove

- **Room and lab-room GiST:** raw overlapping inserts raise SQLSTATE `23P01`.
  Adjacent `[start,end)` slots, distinct rooms and cancelled/rejected rows are
  allowed. Two independent transactions contend on the actual database constraint.
  PostgreSQL may abort one as a deadlock victim (`40P01`), with exactly one row
  committed. HTTP tests synchronize both requests after the friendly SELECT so
  only GiST can choose the winner: one 200, one 409, one persisted reservation.
  Approval, owner/staff cancellation, slot reuse and invalid durations are covered.
- **Enrollment:** 15 and 24 credits accepted, persisted row counts checked;
  duplicate/nonexistent offerings rejected atomically before creating a user.
  Real out-of-range submissions currently expose missing limits (below).
- **Attendance:** no sessions, no attendance, full attendance, exactly 75%,
  66.67% rounding, late/excused statuses, missing marks, multiple students,
  teacher summaries and correction expiry. Existing policy counts late as
  attended and excused as non-attended; no-session state is not ineligible.
- **RBAC:** student denied teacher/admin operations; assigned teacher and admin
  allowed; unrelated teacher denied. Attendance writes don't occur on rejection.
- **Auth:** real login, hashed refresh storage, rotation, sequential replay,
  concurrent replay, unaffected independent device family, expiry and logout.
  Actual Redis counter blocks login before authentication work after 30 attempts.
- **Notifications (2026-10-03 baseline):** two real concurrent inserts produce
  one stored alert under the unique constraint. The scanner test required a
  positive first notification before checking deduplication, so a log-only task
  could not vacuously pass.

## Historical baseline gaps (2026-10-03)

| ID | Expected failure / blocked behavior | Needed implementation |
|---|---|---|
| LAB-1 | Separate `lab_bench_reservations` allows overlapping reservations | A bench-level exclusion constraint and booking API; lab-room reservations are already covered and passing |
| ENR-1 | 13.5-credit nonempty course selection accepted | Minimum 15-credit enforcement for the applicable term/workflow |
| ENR-2 | 25.5-credit selection accepted | Maximum 24-credit enforcement |
| ENR-3 | Prerequisite behavior cannot be arranged/tested | Prerequisite relationship, completion/result data and policy; no fake validator or invented schema was substituted |
| NOT-1 | Scanner produces zero alerts | Real due-class scan and transactional idempotency before FCM dispatch |

In the 2026-10-03 baseline, LAB-1, ENR-1, ENR-2 and NOT-1 were
`xfail(strict=True)` with narrowly specified assertion failure types. Unexpected
database/programming errors still failed the run. The later notification
follow-up implemented the scanner and replaced NOT-1 with passing behavioral
tests; the current expected xfails are LAB-1 and ENR-3. ENR-1 and ENR-2 were
implemented by the Phase 1 credit-boundary follow-up. ENR-3
explicitly calls `pytest.xfail` as a blocked-case marker; replace it with
unmet/met-prerequisite behavior tests when the domain model exists. It is not a
tested prerequisite check.

## Phase 1 follow-up verification (2026-10-11)

- The isolated backend suite reports **316 passed, 1 skipped, 2 xfailed**. The
  remaining expected failures are the lab-bench contract (`LAB-1`) and the
  prerequisite-model blocker (`ENR-3`).
- Registration now rejects non-empty selections below 15 active credits or above
  24 active credits. Normal enrollment and reselection reject loads above 24;
  per-student row locking serializes concurrent credit-load mutations.
- The Phase 1 frontend auth lifecycle suite covers slow login/logout races,
  stale bootstrap invalidation, queued login supersession, and cleanup ordering.

In the 2026-10-03 baseline, the notification uniqueness key referenced the
recurring schedule rather than a dated occurrence. The current scanner derives
event identity from schedule ID plus local occurrence date; external FCM remains
a mocked boundary, so no live push delivery is claimed.

## Teacher/senior-eligibility verification (2026-10-11)

- Full isolated backend suite: **387 passed, 1 skipped, 2 xfailed** in 180.90
  seconds. The optional upload test needs isolated MinIO configuration; LAB-1
  and ENR-3 remain the expected gaps. No new coverage percentage was measured.
- New API tests exercise all eight ordered terms for student/CR lists and
  enrollment, invalid/missing profiles, legacy unscoped semesters, teacher-only
  provision, exact notification recipients, voluntary enrollment, and retained
  credit boundaries. Junior registration/reselection failures leave no partial
  account, enrollment, or notification changes.
- New PostgreSQL integration tests repeat the term/recipient/rollback contracts
  against migrated schema and real request transactions, not SQLite substitutes.
- Ruff and mypy (100 source files) passed. Frontend verification reports 71 unit
  tests and two separately executed live semester workflows passing; see
  [workflow verification](SEMESTER_WORKFLOW_VERIFICATION.md). These results do
  not replace the historical coverage table or claim live FCM delivery.

## Course Workspace verification (2026-10-12)

- Full isolated backend suite: **409 passed, 1 skipped, 2 xfailed**. The
  optional MinIO upload test remains skipped; LAB-1 and ENR-3 remain the two
  documented expected gaps.
- Course Workspace tests cover offering-scope authorization, teacher provider /
  approved-assignment access, active learner scope, announcement lifecycle and
  deterministic notification behavior, plain-text sanitization, resources,
  events/reminder scheduling, and moderated student questions/answers.
- Alembic migration `20261012_0012_course_workspace` creates announcement/read,
  offering-resource, event, and question tables with foreign keys, indexes,
  check constraints, and a safe downgrade.
- Ruff and mypy (104 source files) passed. Frontend reports **78 unit tests**,
  typecheck, ESLint, production build, and the Course Workspace Playwright smoke
  test passing. Live FCM/device acceptance is not claimed.

## Bugs fixed while establishing the tests

1. ORM string columns did not match PostgreSQL `reservation_status` and
   `attendance_status` enums, causing real queries to fail. Models now use the
   database enums. Booking/attendance-session models also no longer assume an
   `updated_at` column absent from the deployed schema. No SQL schema change was
   needed; the mappings now match it.
2. Booking conflict handling now recognizes both exclusion violations and
   PostgreSQL deadlock victims while allowing unrelated DB errors to propagate.
3. Student summaries previously joined classmates' records and omitted unmarked
   sessions. The join now filters the target student and retains unmarked sessions.
4. Teacher summaries no longer classify a student with zero classes as ineligible.

## Fixture design

- Alembic-migrated template + random per-test database; no `metadata.create_all`,
  SQLite type substitutions, transaction rollback trick or mocked constraints.
- Raw-SQL factory builds valid rows against the deployed schema, exposing ORM
  drift instead of reproducing it. Real bcrypt is used for test identities.
- Separate session per HTTP request and separate connections for race tests.
- Real Redis DB 15 reset between cases, scoped to the disposable test stack.
- APIs run in process through ASGITransport; bootstrap lifespan is excluded.
- No shared developer DB, published ports, user `.env` or production volumes.
