# Alumni network

The standalone Alumni Network is available to authenticated portal users at `/alumni`. Existing alumni events, news, scholarships, mentorship, registration, and approval flows remain available under the existing `/alumni/*` endpoints.

## Directory API

All API paths are prefixed with `/api/v1`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/alumni/batches` | Public | Generated batch years from 2010 through the current year, with visible active-alumni counts |
| `GET` | `/alumni/batches/{year}/summary` | Public | Total, employed, higher-study, abroad, top organizations and countries |
| `GET` | `/alumni/` | Authenticated | Paginated directory filtered by `batch`, `company`, `country`, `sector`, `q`, `page`, and `page_size` |
| `GET` | `/alumni/{id}` | Authenticated | Visible profile with career timeline |
| `GET` | `/alumni/me` | Authenticated | Current user's alumni profile |
| `PATCH` | `/alumni/me` | Authenticated | Edit the current user's own profile and privacy settings |
| `GET` | `/alumni/me/employments` | Authenticated | Current user's career timeline |
| `PUT` | `/alumni/me/employments` | Authenticated | Replace the current user's career timeline; at most one row may be current |
| `PATCH` | `/alumni/admin/{id}/verify` | Super admin | Verify an alumni profile |
| `PATCH` | `/alumni/admin/{id}/reject` | Super admin | Reject an alumni profile |
| `POST` | `/alumni/admin/import/preview` | Super admin | Validate a CSV without writing data |
| `POST` | `/alumni/admin/import` | Super admin | Import a validated CSV |

Directory results include the current organization, position, sector and location when available. Email and phone are returned only to authenticated callers when the alumnus enabled the matching visibility flag. A profile owner can see their own saved contact fields while editing.

## Data and migration

Run the normal migration gate:

```bash
docker compose run --rm migrate
```

Migration `20261005_0009_alumni_directory_rebuild` adds profile location, biography, contact privacy, verification state and the `alumni_employments` timeline. Existing `current_company`/`designation` records are copied into one current employment row when a company exists. Existing alumni columns remain for compatibility with the registration and legacy directory flows.

The database enforces:

- `batch_year >= 2010`.
- Employment sectors: `industry`, `academia`, `government`, `startup`, `higher_study`, or `other`.
- Employment end dates cannot precede start dates.
- A partial unique index allows at most one `is_current = true` employment per alumnus.
- Trigram indexes support name and organization search; existing full-text directory search remains intact.

## CSV import

Required columns:

```text
email,full_name,batch_year,department,graduation_date
```

Optional columns include `current_city`, `current_country`, `bio`, `phone`, `email_visible`, `phone_visible`, `linkedin_url`, `organization`, `position`, `sector`, `employment_city`, `employment_country`, `start_date`, `end_date`, and `is_current`. Existing users are updated by email; new imported alumni receive an active verified account with a random password and should use the normal account-recovery flow. The preview endpoint must return zero invalid rows before the import endpoint is enabled in the UI.

Imports are limited to 5 MB. Invalid dates, batch years, sectors, emails, required fields, and row-level values are reported with their CSV row number. No database rows are written during preview.
