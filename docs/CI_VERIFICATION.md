# CI implementation and local verification

Verified locally on 2026-10-03. GitHub-hosted execution has not been claimed.

## Added

- `.github/workflows/ci.yml`: push, pull_request and manual triggers.
- Python 3.11 backend lint/types/audit job and independent pgvector PostgreSQL
  16 + Redis 7 test job. Both use pip caching keyed by dependency declarations.
- Node 22 frontend install/lint/typecheck/build/audit job using the npm lockfile
  and npm download cache.
- Matrix backend/frontend image builds using per-image BuildKit caches; Trivy
  OS/library scans fail on HIGH/CRITICAL, including unfixed vulnerabilities.
- Weekly Dependabot updates for pip, npm, Docker and GitHub Actions.
- README CI badge, local commands and uploaded report descriptions.

No deployment, image publishing, secret requirements, vulnerability ignore list
or continue-on-error was added. Jobs are independent so security/test results
remain visible even if another job fails. Within quality jobs later checks still
run after a failure; earlier failed steps continue to fail the job.

## Actual results

| Check | Result |
|---|---|
| actionlint 1.7.7 | Passed |
| Ruff | Passed |
| mypy | Passed, 92 source files |
| Full pytest with real PostgreSQL/Redis | 171 passed, 1 skipped, 5 xfailed |
| npm ci | Passed |
| ESLint / TypeScript / Vite build | Passed |
| pip-audit after upgrading pip/setuptools | No known vulnerabilities |
| npm audit (including dev dependencies) | Gate fails: 6 HIGH, 1 MODERATE; Vite/Tailwind dependency trees |
| Backend Docker build | Passed |
| Frontend Docker build | Passed |
| Frontend Trivy 0.70.0 | Gate fails: 2 HIGH package findings (libexpat, pcre2) |
| Backend Trivy 0.70.0 | Gate fails: 100 HIGH, 1 CRITICAL package findings |

The one skipped test requires MinIO, outside the requested PostgreSQL/Redis CI
services. The five expected/blocked cases are documented in BACKEND_TEST_REPORT.md.
The legacy PostgreSQL tests now run rather than silently skipping: fixtures
install btree_gist and use connection startup search_path settings that survive
rollback after a forbidden request.

Ruff/mypy/ESLint surfaced existing unused imports, SQLAlchemy typing issues and
untyped frontend error handling. Those were fixed so normal lint/typecheck gates
pass without blanket suppressions. Python dependency auditing also exposed old
pip/setuptools in the local base image; the workflow upgrades those before
installing/auditing the environment.

## Remaining blockers to a green CI

The security gates intentionally remain blocking. Frontend build dependencies
need supported Vite/Tailwind upgrades. Container remediation is separate from
host Python dependency auditing: the Dockerfiles/base images contain their own
OS and Python distributions. Backend findings include Debian util-linux,
systemd libraries, ncurses, Perl, kernel development headers, wheel and
jaraco.context. Counts are package/advisory occurrences, not unique CVEs.

Refresh/remediate base images and installed dependencies, then rerun the scans.
No clean-image claim is made. GitHub artifacts retain exact package versions,
advisory IDs and available fixes for the images built by each CI run.
