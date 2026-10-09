# Durable notifications

## Deployment

Run the existing one-shot migration service before the updated API/workers:

```bash
docker compose run --rm migrate
docker compose up --build -d backend celery_worker celery_beat frontend
```

Production uses `docker compose -f docker-compose.prod.yml ...` instead. Revision
`20261003_0007` adds `notification_log`, `notification_batches`,
`notification_deliveries`, `device_tokens`, preferences columns and scanner
indexes. Active legacy `user_devices` are copied with IDs/timestamps preserved.
Downgrade removes the new outbox/preferences/tokens; it is destructive to new
notification history and newly registered devices. Legacy device rows remain.

Configure `FIREBASE_CREDENTIALS_PATH` to a service-account JSON file mounted
read-only into **Celery workers**, or set it empty to use Google Application
Default Credentials. Enable FCM HTTP v1 for that Firebase project. Never commit
credentials. The Firebase Admin SDK uses OAuth-backed FCM HTTP v1, not a legacy
FCM server key. Without working credentials, deliveries are recorded as failed
configuration attempts, not falsely reported as delivered.

## Producers, scheduling and priority

Internal application code should enqueue through:

```python
from app.tasks.notifications import create_notification

create_notification.delay(
    str(user_id), str(stable_event_uuid), "announcement", "high"
)
```

Allowed types: `class_reminder`, `lab_reminder`, `exam_reminder`, `announcement`,
`course_assignment`, `course_enrollment`.
There is deliberately no arbitrary title/body/data argument. The event UUID
must remain stable across producer retries. Separate event occurrences need
different UUIDs.

- **High:** persisted and queued for immediate push; no digest wait.
- **Medium:** persisted for grouping; digest runs every five minutes, groups by
  user/type, and sends one count-only summary to each registered device. Items
  become eligible five minutes after enqueue, so normal delay is 5–10 minutes.
- **Low:** in-app only, even if push is enabled for that type.
- Quiet hours defer high/medium pushes until the quiet period ends. They do not
  delay the in-app inbox. All channel preferences are checked on creation and
  push preferences are rechecked immediately before delivery.

The class scanner runs once per minute. It selects active-term schedules within
the next ten minutes in **Asia/Dhaka**, including a window crossing midnight,
and active enrolled/main/improvement students. It derives a UUID from schedule
ID + local occurrence date: duplicate scans produce one log, while next week's
class produces a new log. No grades, student names, course titles or room details
are included in the message. Generic messages remain accurate after quiet-hour
deferral. Inactive users and dropped enrollments are excluded.

Course workflow producers use the same durable outbox:

- approving a teacher assignment enqueues one `course_assignment` event per
  active student and CR;
- enrolling or reselecting enqueues one `course_enrollment` event for the
  student and each active teacher assigned to the offering;
- event IDs are deterministic from the assignment request or enrollment
  transition, so retries cannot create duplicate inbox rows or push batches;
- these notifications use the safe `/notifications` internal URL and contain
  no course names, identifiers, grades or client-supplied text.

### Course workflow contract

| Event | Recipients | When it is created |
|---|---|---|
| `course_assignment` | Every active `STUDENT` and `CR` account | A pending teacher assignment request is approved |
| `course_enrollment` | The student and every active teacher assigned to the offering through an approved request (legacy assignments without a request remain supported) | An enrollment or reselection becomes `enrolled`, `main`, or `improvement` |

Dropped enrollments do not create an active-enrollment event. An initial `drop`
selection is persisted without a notification, `drop()` only changes the
enrollment state, and reselection creates one new event for the new active
transition. All recipients of one transition share the same deterministic event
UUID; the recipient/event/type uniqueness constraint prevents duplicate inbox
rows, batches, and device-delivery rows on retries.

Both course event types use fixed generic templates and the relative URL
`/notifications` in the in-app payload and FCM data. The URL is never accepted
from a caller, and no course title, user identifier, email, grade, or
client-supplied rejection text is copied into notification content. Per-type
preferences are applied independently for every recipient: disabling both
channels completes the log without an inbox item or push batch; in-app-only
still reaches the inbox/SSE stream; push-enabled recipients use the normal
high-priority outbox and delivery state machine.

UTC-aware timestamps are stored; Celery's timezone and scheduled wall-clock
logic use Asia/Dhaka. A minute outbox recovery task republishes due pending
batches if a producer committed the DB transaction but failed to publish to Redis.

## Preferences and devices

All endpoints require an active signed-in user and operate only on that user:

| Method/path (under `/api/v1`) | Behavior |
|---|---|
| POST `/notifications/devices/register` | Upsert opaque FCM token, platform (`web`, `android`, `ios`) and UTC last_seen |
| GET `/notifications/preferences` | Effective per-type defaults and quiet hours |
| PUT `/notifications/preferences` | Replace preferences; unspecified types default enabled |
| GET `/notifications` | Most recent 100 in-app notifications for the caller |

Example preferences:

```json
{
  "per_type": {
    "announcement": {"push": false, "in_app": true},
    "class_reminder": {"push": true, "in_app": true}
  },
  "quiet_start": "22:00",
  "quiet_end": "07:00"
}
```

Supply both quiet-hour endpoints or neither; equal times disable quiet hours.
Daytime and overnight intervals use inclusive start/exclusive end. Legacy push
flags are honored until the user saves the new per-type preferences.

The Notifications page exposes these controls and reports save errors. Device
registration is ready for native/web clients supplying an FCM token; automatic
browser token acquisition and service-worker provisioning are now implemented
by the PWA. See [PWA setup](PWA.md) for Firebase web configuration and installation.

## Idempotency and failure behavior

`notification_log` has database-enforced uniqueness `(user_id, event_id, type)`.
Inbox creation, high-priority batch creation and device-delivery records commit
with the log. Concurrent digest workers serialize grouping with a PostgreSQL
advisory lock. A unique `(batch_id, device_id)` delivery ledger prevents a retry
from resending to a device that already succeeded.
Device recipients are snapshotted when a batch is created; newly registered
devices do not receive older completed alerts retroactively.

Each device attempt is durably claimed **before** calling FCM. Confirmed temporary
provider rejections use Celery autoretry with exponential backoff (60, 120, 240,
480, 960 seconds), maximum six attempts. Persisted retry times/attempt counts
also protect against duplicate Celery tasks or the outbox recovery task.

- `UNREGISTERED` or an explicit `message.token` validation error deletes the
  token (and matching legacy registration). Generic `INVALID_ARGUMENT` may be a
  payload bug and does **not** delete unrelated valid tokens.
- Successful devices are marked `sent` (FCM accepted, not proof of display).
- Authentication/payload errors become `failed`, with only sanitized error codes.
- Timeout/unknown acceptance becomes `unknown` and is not retried. A worker
  interrupted while `inflight` is similarly quarantined after five minutes.
- Preferences changed to opt-out mark unattempted device deliveries suppressed.

**Exactly-once delivery cannot be guaranteed across PostgreSQL and FCM**, which
has no caller-controlled idempotency transaction. To honor duplicate avoidance,
an uncertain send is not automatically repeated; this can lose an alert after
a crash-before-send. SDK HTTP retries are disabled through a tested isolated
adapter so hidden POST retries cannot bypass this rule. FCM itself and client
display behavior remain external boundaries.

Only allowlisted generic templates and an opaque batch ID/type are sent. No
caller-provided personal data, grade, name, email, arbitrary text or raw exception
message is placed in notification content or application delivery logs.

## Single active Beat and query indexes

Both Compose files select `app.core.beat:SingletonScheduler`. Production also
sets one Beat replica. A Redis owner-token lease with atomic compare/renew/delete
allows only one active scheduler; standby instances do not publish. Polling is
bounded to five seconds. Redis failure/lost ownership fails closed. Expiry lets
a standby take over after a crash. The scheduler bounds broker/socket/tick time.

A Redis lease is not broker-side fencing across arbitrary VM pauses or Redis
failover. The deployment's single replica and worker/database idempotency remain
necessary safeguards. Do not run embedded `worker -B` alongside dedicated Beat.

Indexes cover `(day_of_week,start_time)`, active enrollment recipients, active
semesters, device user lookup, pending log/due batches, and per-batch retry state.

## Verification

Tests use real migrated PostgreSQL/Redis and a mocked FCM boundary. Coverage:
concurrent scan and delivery deduplication, next-week occurrences, Dhaka midnight,
device upsert/last_seen, token deletion, per-type channels, high/medium/low,
quiet hours and delayed digests, provider error classification, bounded retries,
worker interruption, broker publication failure recovery, singleton Beat ownership,
scanner indexes and migration backfill/downgrade/schema parity.

Course workflow coverage additionally checks the exact active `STUDENT`/`CR`
assignment recipient set, approved-teacher enrollment filtering, student and
teacher inbox rows, initial-drop suppression, reselection transitions,
preference API readback, deterministic idempotency including outbox rows, safe
`/notifications` URLs in inbox and FCM payloads, and transaction rollback when
notification enqueueing fails.

Run `docker-compose.test.yml` as documented in README. Transport/Celery unit
tests additionally live in `backend/tests/test_notification_transport.py`.
Live FCM acceptance/device display requires real credentials and a registered
device; no live-push verification is claimed by mocked transport tests.

Latest verification: **199 passed, 1 skipped, 4 existing unrelated xfails** in
the full backend suite. The skip is the optional MinIO upload integration test;
the remaining xfails concern lab-bench/prerequisite/credit-limit work. Ruff,
mypy (95 application files), frontend ESLint/typecheck and production build passed.

The tested backend command (with disposable database/Redis URLs exported) was:

```bash
python -m pytest tests -q --tb=short -p no:cacheprovider
python -m ruff check app tests alembic
python -m mypy app
```

Frontend checks from `frontend/`: `npm run lint`, `npm run typecheck`,
`npm run build`. Browser interaction with the new preferences form was not
automated; API save/readback and user isolation were tested against PostgreSQL.
