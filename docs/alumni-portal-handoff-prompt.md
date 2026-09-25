# Alumni Portal — Handoff Prompt (Steps 1–9)

Copy everything below the line into your other AI. It is written to be
self-contained: verified repo facts, current state, decisions, and one step at
a time with a hard stop between steps.

---

## YOUR TASK

Extend the existing FastAPI + React project **Student-Portal-of-EEE-SUST**
("SUST EEE Smart Student Portal") with an **Alumni Portal** module modelled on
the Dhaka University Alumni Association site (duaa-bd.org): a public landing
page plus a separate authenticated members' area, with directory, events,
mentorship, scholarships, and news.

Build this in 9 steps, **one at a time**. After each step, STOP and show the
output. Do not start the next step. For each step: generate the code, explain
schema/API decisions, and flag anything needing a decision from the user
before proceeding.

## EXISTING STACK (verified in this repo)

- FastAPI backend, SQLAlchemy 2.x async, Alembic, Pydantic v2
- JWT auth with refresh-token rotation, HttpOnly refresh cookie
- RBAC via `UserRole` enum + `RequireRole` dependency
- PostgreSQL 16 with `btree_gist` and `vector` extensions
- GiST exclusion constraints for booking conflicts
- FCM v1 + Celery Beat for notifications
- S3/MinIO presigned uploads with server-side finalize verification
- Postgres tsvector full-text search, GIN indexes
- Google Gemini API + pgvector hybrid search (AI academic assistant)
- JSON-Resume Career Portal
- Frontend: React + TypeScript + Vite + React Router, Tailwind
- Frontend design system: **"Instrument Panel"** — dark graphite base with
  brass/copper accents. Two themes exist: `data-theme='graphite'` and
  `data-theme='brass'`, defined in `frontend/src/index.css`.

## REPO LAYOUT (verified — use these exact paths)

Backend:
```
backend/app/main.py
backend/app/core/{config,database,security,celery_app,rate_limit,exceptions,logging}.py
backend/app/api/v1/router.py              # include new routers here
backend/app/api/dependencies.py           # get_current_user, RequireRole, get_avatar_actor
backend/app/api/v1/endpoints/             # auth, users, courses, schedules, rooms,
                                          # attendance, notifications, resources,
                                          # labs, projects, career, ai
backend/app/models/                       # base, user, academic, attendance, resource,
                                          # facility, notification, project, career,
                                          # ai_knowledge, alumni
backend/app/schemas/                      # one pydantic module per domain
backend/app/services/                     # *_service.py per domain
backend/app/repositories/                 # *_repository.py
backend/app/tasks/                        # notifications.py, ai_ingestion.py
backend/alembic/versions/
database/schema.sql                       # single bootstrap file, 10 numbered sections
database/migrations/                      # NNN_name.sql, plain SQL
backend/tests/                            # pytest
```

Frontend:
```
frontend/src/routes/index.tsx             # createBrowserRouter
frontend/src/routes/ProtectedRoute.tsx     # supports roles=[...]
frontend/src/layouts/{AppLayout,AuthLayout}.tsx
frontend/src/features/<domain>/pages/...  # lazy-loaded per feature
frontend/src/components/ui/               # button, card, input, select, table,
                                          # dialog, badge
frontend/src/components/shared/           # DataTable, Avatar, StatCard, PageHeader,
                                          # StatusBadge, EmptyState, ConfirmDialog,
                                          # ThemeSwitcher, DepartmentWatermark
frontend/src/contexts/ThemeContext.tsx
frontend/src/index.css                    # design tokens
frontend/src/types/auth.ts                # UserRole mirror
```

## CONVENTIONS YOU MUST MATCH

1. **Migrations are duplicated on purpose.** Every schema change lands in all
   three places, and they must stay in lockstep:
   - `database/schema.sql` (fresh install)
   - `database/migrations/NNN_*.sql` (plain SQL, numbered)
   - `backend/alembic/versions/<date>_<rev>_<slug>.py` (Alembic)

2. **SQL migrations must be idempotent.** Use `IF NOT EXISTS` on
   `CREATE TABLE`/`CREATE INDEX`/`ADD COLUMN`, and guard constraint
   replacement with a `DO $$ ... IF EXISTS (SELECT 1 FROM pg_constraint ...) $$`
   block. This is required because a database may already be bootstrapped from
   `schema.sql`. A test enforces the `ADD COLUMN IF NOT EXISTS` form.

3. **Status fields are `VARCHAR` + `CHECK`, not Postgres enums.** Matches the
   rest of this codebase. Keep the vocabulary small and explicit.

4. **Timestamps are `TIMESTAMPTZ` (UTC)** everywhere. The API converts to
   `Asia/Dhaka` only at display time.

5. **Schemas, services, repositories are one file per domain.** Endpoints stay
   thin: validate with Pydantic, delegate to a service, return a response
   model.

6. **Tests**: `backend/tests/`, pytest, mirroring existing
   `test_auth.py` / `test_security.py` style. Add a
   `test_schema_parity.py`-style guard if you add ORM columns, so ORM/DB drift
   cannot return. **Note: the suite cannot currently run** — the backend image
   is missing `pytest_asyncio`, so `tests/conftest.py` fails at import. Fix
   that first (add it to `backend/pyproject.toml` dev deps and rebuild) or you
   have no regression signal at all.

7. **Security posture is deliberate and documented in this repo.** Follow it:
   - Never trust a client-supplied content type; derive it from a server-side
     extension allowlist (see `auth.py` avatar flow).
   - S3 presigned PUT cannot enforce size, so **measure server-side on
     finalize** (`head_object`) and delete oversized/invalid objects.
   - Ownership prefixes are checked explicitly on finalize.
   - Refresh cookie is `HttpOnly`, `SameSite=Lax`, `Secure` in production,
     path-scoped to `/api/v1/auth`.
   - `get_client_ip` returns a throttle key only, never an identity, and
     honours X-Forwarded-For **only** when `TRUSTED_PROXIES` is configured.

## CURRENT STATE — READ THIS FIRST

Step 1 is **done and applied to the live database**. Do not redo it.

- `backend/app/models/alumni.py` — full ORM for all 9 alumni tables.
- `user_role` already includes `'alumni'` in `schema.sql` and in the live DB.
- `database/migrations/003_alumni_portal.sql` + Alembic
  `20260914_0002_alumni_portal_schema.py` — base tables.
- `database/migrations/004_alumni_model_parity.sql` + Alembic
  `20260915_0003_alumni_model_parity.py` — **applied to live DB** by me:
  `is_visible`, `events.event_type/capacity/announced_at`,
  `event_rsvps.slot_range` + GiST `no_double_booked_event_seats`,
  `scholarship_applications.document_key/document_name`, status vocabulary
  fix to `submitted/under_review/approved/rejected`, and
  `membership_status` now allows `rejected`. I also added
  `ix_alumni_profiles_is_visible` to both 004 files and `schema.sql`.

Existing tables: `alumni_profiles`, `events`, `event_rsvps`, `scholarships`,
`scholarship_applications`, `mentorship_pairs`, `news_posts`,
`gallery_albums`, `gallery_photos`.

Status vocabularies now live:
- `membership_status`: `pending | active | expired | rejected`
- `rsvp_status`: `attending | interested | not_attending`
- scholarship application `status`: `submitted | under_review | approved | rejected`
- `mentorship_pairs.status`: `requested | active | ended`
- `event_type`: `reunion | webinar | meetup`

### ⚠️ BLOCKER 1 — the FTS config mismatch is real and now unfixed

`005_alumni_search_and_career.sql` and `schema.sql` both build
`alumni_profiles.search_tsv` with **`'english'`**. But
`backend/app/repositories/alumni_repository.py` queries with
**`plainto_tsquery('simple', q)`** against an expression built with
**`to_tsvector('simple', ...)`** and a docstring claiming it matches
`ix_alumni_profiles_fts`.

That index **does not exist** in `schema.sql` or in the live DB. The only GIN
index present is `ix_alumni_profiles_search` on the stored `search_tsv`
column. So the directory query as written **cannot use the index at all**, and
mixing `'simple'` and `'english'` between index and query is a correctness
problem, not just a performance one: a token stemmed by one config and queried
with another silently fails to match.

Pick one config and make index, generated column, and query agree:
- `'simple'` — better for proper nouns, company names, "EEE", "Grameenphone".
- `'english'` — matches the rest of this repo (`academic_resources.tsv_search`
  and `document_chunks.tsv_content` both use `'english'`).

Whichever wins, also fix the stale `ix_alumni_profiles_fts` reference in the
repository docstring. A `search_directory_fallback` ILIKE path already exists
in that file for the SQLite test suite — use it, do not write a second one.

**This is a correctness bug, not just a slow query.** Verified against the
live DB:

```
to_tsvector('english','power systems engineering') @@ plainto_tsquery('simple','engineering')  -> false
to_tsvector('simple', 'power systems engineering') @@ plainto_tsquery('simple','engineering')  -> true
```

A column indexed with `'english'` and queried with `'simple'` silently returns
**no matches**. So as written today, searching the directory for
"engineering" returns nothing even for profiles that contain it.

### ⚠️ BLOCKER 2 — `005` is only half-applicable and was applied by mistake

`005_alumni_search_and_career.sql` has two parts. Part 1 (`search_tsv` + GIN
index) succeeded against the live DB. **Part 2 failed**:

```
ERROR:  relation "career_opportunities" does not exist
```

`career_opportunities` is defined in `schema.sql` but **was never created in
the live DB**. In fact most of the portal is missing from the live database —
27 of the 48 tables in `schema.sql` do not exist live, including
`academic_resources`, `projects`, `notifications`, `user_devices`,
`document_chunks`, and the whole career and AI sections. The live DB is
roughly the identity + academics + alumni slice only.

So: `search_tsv` is now live, `career_opportunities.updated_at` is not, and
the migration is **partially applied and currently in an inconsistent
state**. Do not assume any migration is "done" — verify with
`\d <table>` before relying on it.

Note also that `005`'s comment claims the `career_opportunities` fix is needed
because "the original CREATE TABLE only had created_at". That was true at some
point, but `schema.sql` now already declares `updated_at`, so 005's fix is
belt-and-braces for older databases only.

### ✅ RESOLVED — the duplicate-`005` conflict is gone

Earlier this document reported two conflicting `005` migrations. That is now
resolved: only `005_alumni_search_and_career.sql` and Alembic
`20260916_0004_alumni_search_and_career.py` remain. `005_alumni_directory_search.sql`
and `20260916_0004_alumni_directory_search.py` have been deleted.
**`'simple'` vs `'english'` and the `mentorship_pairs` `'declined'` status are
still open** (see BLOCKER 1).

## THE 9 STEPS

### STEP 1 — Database schema ✅ ALREADY DONE
`alumni_profiles`, `events`, `event_rsvps`, `scholarships`,
`scholarship_applications`, `mentorship_pairs`, `news_posts`,
`gallery_albums`, `gallery_photos` all exist and are live. Do not redo.

### STEP 2 — Auth & RBAC extension
- `alumni` is already in `UserRole`, in `schema.sql`'s `user_role`, and in
  the live DB enum. Verify it is also mirrored in
  `frontend/src/types/auth.ts` and anywhere roles are enumerated
  (`AppLayout`, `ProtectedRoute`, admin panel).
- Alumni signup flow: user registers, submits batch/department claim,
  status = `pending` until Admin approves.
- Admin endpoints to approve/reject alumni verification.
- **Already written, unread, and unverified:**
  `backend/app/schemas/alumni.py` defines `AlumniRegisterRequest`,
  `AlumniProfileCreate`, `AlumniProfileUpdate`, `AlumniUserSummary`,
  `AlumniProfileResponse`, and `AlumniVerificationDecision`. Read it before
  writing anything. `AlumniRepository.list_pending_verifications()` and
  `get_profile_by_user_id()` already exist.
  There is **no** `alumni_service.py` and **no** `endpoints/alumni.py` yet,
  and `router.py` has not been updated.
- Open questions to raise: does approval set `is_active=true` immediately
  (mirroring the existing teacher/CR approval flow in
  `AuthService.approve_user`)? Should an existing student/CR account be able
  to convert to alumni after graduation, or is alumni signup always a fresh
  account? Should a `rejected` claim be re-submittable?
  Note the existing teacher/CR flow creates the user inactive and flips
  `is_active` on approval — check whether alumni should behave the same, and
  whether a pending alumnus may log in at all.

### STEP 3 — Alumni directory API
- CRUD endpoints for `alumni_profiles`.
- Search endpoint using tsvector full-text search over batch, department,
  company, industry — the Resource Sharing search pattern is
  `backend/app/api/v1/endpoints/resources.py` (`GET /search`) →
  `ResourceService.search_resources(q)` → repository `search`.
- **Mostly written already.** `backend/app/repositories/alumni_repository.py`
  (335 lines) implements `AlumniRepository`, `EventRepository`,
  `ScholarshipRepository`, `MentorshipRepository`, `NewsRepository`, and
  gallery queries. `search_directory()` filters on `is_visible` and
  `membership_status` by default, with a `search_directory_fallback()` ILIKE
  path for SQLite. **Resolve BLOCKER 1 first** — the FTS config mismatch
  means the current query is both unindexed and unreliable.
- Still to do: `alumni_service.py`, `endpoints/alumni.py`, and registering
  the router in `backend/app/api/v1/router.py`.
- The `is_visible` opt-in must be enforced on **every** read path — listing,
  search, stats, and any profile-by-id endpoint. A profile with
  `is_visible = false` must not leak through a direct lookup, and
  `membership_status` should be filtered too, not just `is_visible`.

### STEP 4 — Events module
- CRUD for events (`reunion` / `webinar` / `meetup`).
- RSVP endpoint with capacity limits, reusing the GiST exclusion-constraint
  pattern from Room Booking. The DB already has
  `no_double_booked_event_seats EXCLUDE USING gist (event_id WITH =,
  slot_range WITH &&) WHERE (rsvp_status = 'attending')`, where each
  attending RSVP claims a disjoint seat in `[1..capacity]`. Assign the seat
  in the service layer and translate the exclusion violation into a clean
  409, not a 500. `capacity IS NULL` means unlimited.
- Trigger an FCM notification via Celery Beat when a new event is published.
  `events.announced_at` exists to make the scanner idempotent. The pattern
  already in `backend/app/core/celery_app.py` schedules
  `app.tasks.notifications.scan_upcoming_class_alerts` every minute; follow
  the same shape, adding to `app/tasks/`.

### STEP 5 — Scholarships module
- CRUD for scholarships (admin-managed).
- Application endpoint with S3 presigned upload for documents.
  `scholarship_applications.document_key` / `document_name` already exist.
  Reuse the avatar upload flow's hardening: server-side extension allowlist,
  server-measured size on finalize, ownership check, delete on failure.
- Status tracking: `submitted → under_review → approved | rejected`.

### STEP 6 — Mentorship matching
- `mentorship_pairs` + request/accept flow.
- Optional: pgvector-based mentor suggestions by industry/skills embedding,
  reusing the AI academic assistant's embedding infrastructure
  (`app/services/ai_rag_service.py`, `app/tasks/ai_ingestion.py`,
  the `vector` extension and `document_chunks` embedding column).

### STEP 7 — News & Gallery
- `news_posts` CRUD, authored by admin or an alumni coordinator.
  Decide whether a new role/flag marks "alumni coordinator" — a new role in
  `UserRole` is a heavier change than a boolean on the user, and this is a
  decision to raise, not assume.
- `gallery_albums` / `gallery_photos` using the existing S3 upload flow.
  Note `gallery_photos.photo_key` is `VARCHAR(512) NOT NULL` with no
  separate `file_key` naming column, and `sort_order` defaults to 0.

### STEP 8 — Career Portal bridge
- Let alumni post job openings/referrals into the existing
  `career_opportunities` table, tagged `alumni-posted`.
- Current columns: `posted_by`, `title`, `organization_name`, `type`,
  `location`, `application_deadline`, `application_target`, `description`,
  `tags TEXT[]`, `is_verified BOOLEAN NOT NULL DEFAULT TRUE`,
  `created_at`, `updated_at`.
- Decision to raise: how is "alumni-posted" represented — a `tags` value, a
  new boolean column, or a source enum? Note `is_verified` currently defaults
  to TRUE, which would silently mark unvetted alumni posts as verified. That
  is a trust problem worth raising explicitly.
- Set A's migration (`005`) tries to add a missing `updated_at` to
  `career_opportunities`, and it **fails on the live DB** because that table
  does not exist there at all. See BLOCKER 2. Decide whether to bootstrap the
  missing tables (see below) or to defer this fix until `career_opportunities`
  actually exists.

### STEP 9 — Frontend
- **Public alumni landing page** (no auth): hero, stats bar computed **live
  from the DB**, programs overview, news preview, gallery preview.
  "Live from DB" means a real stats endpoint, not hardcoded numbers. Decide
  and state whether the landing page reads only `is_published` + `is_visible`
  content, and whether it is reachable without a session.
- **Authenticated portal dashboard**: directory, my events, my applications,
  mentorship status.
- **Admin views**: verification queue, event/scholarship management.
- Add routes in `frontend/src/routes/index.tsx` using the existing
  `lazy` + `Suspense` + `ProtectedRoute roles={[...]}` pattern, and a feature
  folder per module under `frontend/src/features/`. Public routes go in a
  layout that does **not** require a session.
- Match the "Instrument Panel" design system: dark graphite base, brass/copper
  accents, existing `ui/` and `shared/` components.

## OPEN DECISIONS TO SURFACE (do not silently choose)

1. `membership_status = 'rejected'` vs. leaving a refused claim as `pending`.
2. Alumni approval → immediate `is_active`? Or a separate gate?
3. Can an existing student/CR account convert to alumni?
4. Re-submission after a rejected alumni claim.
5. **The live DB is missing 27 of 48 tables** — should the remaining portal
   sections be bootstrapped, or is the live DB intentionally a partial slice?
   This blocks any work touching career, projects, resources, notifications,
   or the AI/vector stack.
6. `'simple'` vs `'english'` for the alumni directory, so index and query agree.
7. `'declined'` in the mentorship status vocabulary.
8. "Alumni coordinator" as a new role vs. a flag.
9. How `alumni-posted` is represented in the career portal, and the
   `is_verified` default.

## WORKING RULES

- One step at a time. Hard stop after each. Do not chain steps.
- Before editing, read the file. The index holds paths and symbol names only.
- Keep `schema.sql`, `database/migrations/`, and `backend/alembic/versions/`
  in lockstep for every change.
- Run the existing tests and `test_schema_parity.py` after each step.
- The working tree has unrelated uncommitted changes and stray untracked
  files (`.tmp/`, `6.jpg`, `images.jpeg`, `images (1).jpeg`,
  `backend/tests/test_security.py`, several dashboard JPGs). Do not delete or
  commit them.
- **Do not "dry-run" a migration against the live database.** These are real
  DDL statements; running them commits them. `psql -f` has no dry-run mode.
  If you want to know whether a migration applies, read it and test against a
  scratch database, or apply it deliberately and inspect the result with
  `\d <table>`. `005` is currently half-applied as a result of exactly this
  mistake — see BLOCKER 2.
- Apply migrations to the live Postgres deliberately (`docker compose exec -T
  postgres psql -U postgres -d sust_eee_db -f - < database/migrations/NNN.sql`)
  when verification needs real data, and verify with `\d` afterwards.
- Assume no migration is fully applied. The live DB and `schema.sql` have
  drifted; check the actual table before depending on it.
- Do not commit or push unless asked.
