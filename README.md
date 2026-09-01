# LifeLenz-AI

LifeLenz-AI is a beta-stage personal wellness intelligence project. It is intended to
help people organize longitudinal lifestyle data, understand patterns relative to their
own baselines, and receive transparent, non-diagnostic observations.

The core value proposition is context: instead of treating sleep, activity, hydration,
mood, energy, and stress as isolated readings, LifeLenz-AI aims to make changes and
co-occurring patterns understandable over time. Observations use conservative language
and expose the data and rules behind them.

## Project status

LifeLenz-AI is at product version `0.1.0`. Commit 40 promotes the validated
`mvp1-0.1.0-rc.1` candidate into the first MVP1 repository release,
`mvp1-0.1.0`, with expected Git tag `v0.1.0`. The release workflow rebuilds and validates
the exact tagged source before publishing a GitHub Release. Repository release status remains
separate from public-host production readiness.

The repository contains an installable `lifelenz` Python package, development tooling, and a
controlled taxonomy for wellness categories, metrics, units, data sources, confidence, and insight
severity. Shared domain foundations provide record identifiers, aware time ranges, common metadata,
and reusable validation. Concrete domain records capture completed sleep sessions, daily activity
totals, completed workouts, hydration events, meal nutrition, daily nutrition summaries, neutral
body measurements, and subjective mood, energy, stress, and optional motivation check-ins with
explicitly validated values. They also capture menstrual bleeding observations, user-supplied
menstrual-cycle date ranges, privacy-conscious wellness profiles with tracking preferences, and
user-defined wellness goals.

Framework-independent repository contracts define storage-neutral operations for profiles, goals,
and wellness records. Deterministic in-memory implementations support tests and application
composition. Durable SQLite repositories store profiles, goals, accounts, ownership mappings, and
wellness records in a local database file using explicit deterministic serialization and schema
migrations. They preserve typed domain values, canonical units, original aware timestamp offsets,
and data across repository instances and process restarts. The active SQLite persistence is not
encrypted by this implementation and deliberately supports one API instance per database volume;
LifeLenz does not claim horizontal database scaling or managed-database failover.

Framework-independent application services coordinate repositories, enforce profile existence and
ownership boundaries, and translate expected missing-entity failures. Deterministic personal-baseline
analytics summarize supported canonical metrics from a person's own recorded observations using
count, mean, median, minimum, maximum, and population standard deviation. Baselines preserve
canonical units and use record metadata timestamps; they provide no medical interpretation,
population comparison, recommended target, or health classification. Deterministic basic trend
analytics report first and last values, absolute and percentage change when defined, least-squares
slope per day, and neutral increasing, decreasing, or stable direction for supported canonical
metrics. Direction is purely mathematical: increasing does not mean healthy, decreasing does not
mean unhealthy, and trends neither predict future values nor recommend actions. A wellness-summary
workflow produces structured canonical-unit summaries from stored records. Metrics with at least one
sample include a baseline, while metrics with at least two samples also include a trend. The result
is structured descriptive data, not user-facing medical or coaching text.

Framework-independent account identity, Argon2 password hashing, short-lived signed access tokens,
durable accounts, and explicit profile ownership are implemented. Account registration does not
create a wellness profile: authentication establishes identity, while a separate
`UserId -> ProfileId` mapping establishes authorization context. Password reset, email verification,
MFA, refresh-token rotation, cloud synchronization, correlations, recommendations, predictions,
direct wearable integrations, vendor-specific wellness export compatibility, notifications,
production monitoring, mobile applications, and medical decision support remain outside MVP1.

LifeLenz-AI includes a versioned FastAPI API with public system metadata, liveness, and
SQLite-readiness endpoints; account registration and login; bearer-protected current-user retrieval;
explicit primary-profile onboarding and replacement; owned wellness-record creation, listing,
retrieval, correction, and deletion for all ten current record types; authenticated CSV schema v1
validate/commit ingestion for six stable record categories; wellness-goal management; and
deterministic structured wellness summaries. Every wellness-resource route requires bearer
authentication and resolves ownership from the account; clients cannot choose a profile identifier.
CSV v1 provides row-level validation, semantic duplicate detection, canonical-unit normalization,
and `csv_import` provenance. The local SQLite content is not encrypted.

A React and TypeScript web application provides a restrained public landing page, account
registration and login, authoritative current-user restoration, protected routing, first-time
wellness-profile onboarding, profile-preference editing, and a responsive authenticated application
shell. Its dashboard presents real structured wellness summaries when records exist and an honest
empty state when they do not. Descriptive analytics show server-derived record/metric coverage,
baseline ranges with minimum/maximum plus mean/median markers, and mathematical trend details using
first/last values and change. These visuals do not invent time-series samples, evaluate health, or
recommend targets. Summary measurements remain in the backend's canonical units; the stored
measurement-system preference does not yet convert them in the browser.

Manual record entry supports all ten current record types: Sleep, Daily Activity, Workout,
Hydration, Meal, Daily Nutrition, Body Measurement, Subjective Wellness Check-In, Menstrual
Bleeding, and Menstrual Cycle. Recent and full record history cover the same types, with
record-type/date filtering, owned-record correction, and deliberate confirmed deletion. A protected
CSV workflow supports local file selection, server validation, issue and duplicate review, and
explicit import for the six CSV v1 categories. Authenticated wellness-goal management supports
listing, creation, full-field replacement, status changes, and deliberate confirmed deletion.

A CI-enforced real-browser critical journey composes registration, login, profile onboarding,
record creation/correction/deletion, CSV validation/import, dashboard refresh, goal creation,
logout, protected-route redirection, and keyboard skip navigation against live FastAPI, SQLite,
and a built Vite application. A provider-neutral Docker Compose deployment builds separate
unprivileged API and web containers, exposes only the same-origin web gateway, persists SQLite in a
named volume, applies a browser-facing security-header baseline, and fails closed on unsafe
production configuration. The SQLite maintenance helper provides tested backup, verify, and restore
operations, and release validation destroys the original disposable data volume, restores an
exported backup into fresh storage, and proves the same synthetic account can authenticate afterward.

This release does **not** claim unrestricted public production readiness. Public HTTPS/HSTS,
off-host backup retention and encryption policy, host/secret/database access ownership, production
monitoring and alerting, rate limiting/abuse controls, formal accessibility certification,
regulatory compliance, and medical-device readiness remain outside the repository's automated
release evidence.

The MVP1 capability areas are:

- structured records for sleep, activity, hydration, basic nutrition, body measurements,
  mood, energy, and stress;
- personal profiles and goals;
- personal-baseline analytics and trend summaries;
- deterministic, explainable wellness observations;
- typed wellness summaries;
- authenticated browser workflows for entry, history, correction, deletion, CSV import, and goals;
- a production-shaped single-host deployment with tested SQLite recovery;
- reproducible release artifacts and exact-source release validation.

Direct wearable connections, vendor-specific formats, broad wellness-platform integrations, and
advanced predictive/recommendation capabilities remain future work.

## Architecture

The backend uses a layered, standard-library-first design. Domain types and validation form the base;
repository abstractions manage records; pure analytics calculate baselines and trends; deterministic
rules produce explainable observations; and services coordinate these parts into summaries. The
`web/` application is a separate Vite build with a typed API-client boundary, centralized
authentication state, TanStack Query server-state orchestration, React Router routes, and lightweight
CSS design tokens. The backend remains authoritative for identity and wellness data.

See [Architecture](docs/architecture.md) for the intended dependency direction and design decisions.

## Development setup

LifeLenz-AI requires Python 3.13 or later. In Windows PowerShell, create and activate a virtual
environment, then install the package with development dependencies:

```powershell
py -3.13 -m venv lifelenz-env
.\lifelenz-env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the test suite, lint checks, and formatting check:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Apply the configured formatter when needed:

```powershell
python -m ruff format .
```

## Web development

The web application requires a maintained Node.js 22 release. Install its locked npm dependencies and
start Vite from the repository root:

```powershell
cd web
npm install
npm run dev
```

Vite serves the application at `http://localhost:5173` and proxies same-origin `/api` requests to the
local backend at `http://127.0.0.1:8000`; start that backend with the command in [Local API](#local-api).
Copy `web/.env.example` only when an explicit API origin is needed. The browser-visible
`VITE_LIFELENZ_API_BASE_URL` value is configuration, never a secret; leave it empty for the local
development proxy.

Run frontend validation from `web/`:

```powershell
npm run lint
npm run format:check
npm run typecheck
npm run test:run
npm run build
```

The current web beta release stores its short-lived bearer access token in browser `sessionStorage`
through a single storage abstraction. Closing the browser session clears that storage, but
`sessionStorage` does not eliminate cross-site scripting risk. There are no refresh tokens or
server-side revocation/logout sessions yet; logout clears client state but cannot revoke an already-
issued token. The server remains authoritative through `/api/v1/auth/me`. Passwords, account objects,
wellness data, and signing secrets are not persisted in browser storage.

After authentication, the web application derives onboarding state from the server-owned profile
identifiers returned by `/api/v1/auth/me`. Users without a profile are guided through the existing
profile API; configured users can review their preferences and open a summary-backed dashboard. The
web interface provides Home, Records, Goals, and Profile destinations. Records supports manual entry,
recent and full history, record-type/date filtering, correction, confirmed deletion, and a protected
CSV validate/review/commit subworkflow. Records and goals are persisted by the authenticated API;
successful record mutations and CSV imports invalidate the server-owned record list and structured
summary so the dashboard can retrieve current analytics. Browser-local datetimes are sent with an
explicit UTC offset, and canonical units are preserved. The dashboard visualizes deterministic
summary baselines as observed ranges with mean/median markers and displays server-provided
mathematical trend change without inventing a historical series. Rich historical time-series charts
remain a possible future capability. The critical MVP browser journey is covered by the isolated
Playwright workflow documented in [Browser end-to-end validation](docs/browser-e2e.md).

## Production-shaped deployment

The provider-neutral Docker Compose deployment is documented in
[Production deployment](docs/deployment.md). It builds a Python 3.13/FastAPI API image and a Node 22
build served by an unprivileged Nginx web image. Only the web gateway is published to the host; `/api`
traffic remains same-origin and is reverse-proxied internally. SQLite persists in a named volume and
is intentionally limited to one API instance per database volume.

Production startup fails closed unless API documentation is disabled, the SQLite path is absolute,
and the JWT signing secret contains at least 48 UTF-8 bytes. The gateway applies CSP and related
browser security headers. HSTS belongs at the trusted external TLS terminator because the bundled
gateway serves HTTP only.

The SQLite maintenance helper provides explicit backup, verification, and restore operations using
SQLite's backup API plus integrity checks. The release workflow proves recovery into a fresh data
volume. This is a tested recovery primitive, not a scheduled/off-host backup service or a
disaster-recovery guarantee.

## Continuous integration and release validation

Pull requests, pushes to `main`, and manual workflow runs use Python 3.13, the runtime declared by
the project metadata. CI runs Ruff lint and formatting checks, the full pytest suite, an enforced
98% coverage floor, focused SQLite persistence and schema-migration tests, focused API and
authentication tests, dependency consistency checks, deterministic project-specific security
invariants, and wheel/source-distribution build verification. A separate Node.js 22 `Web` job installs
the npm lockfile and runs ESLint, Prettier, strict TypeScript, Vitest, and the production Vite build.
After the Python and Web suites pass, a `Browser E2E` job builds the web application, starts a live
FastAPI process and isolated SQLite database, serves the built bundle with `vite preview`, installs the
pinned Playwright Chromium runtime, and drives the critical synthetic MVP journey through the real UI.

`Deployment Validation` independently builds and boots the production Compose stack, verifies
production configuration rejection, gateway/API readiness, security headers, authentication,
SQLite persistence across restart, and disabled production documentation. `MVP1 Release Validation`
validates the final release contract, builds release artifacts and SHA-256 checksums, and proves
backup/restore after destruction of the original disposable data volume. A tag-triggered run also
requires the tag to match the manifest and belong to `main` history. Only after validation succeeds
does a separate tag-only publishing job receive `contents: write` permission and create the GitHub
Release from the validated artifact bundle. The temporary SQLite backup is not retained.

Dependabot checks Python, GitHub Actions, and npm dependencies under `/web` weekly. GitGuardian
remains a complementary external secret-scanning check. These automated checks are not a formal
security certification, complete static analysis, penetration test, regulatory-compliance validation,
formal WCAG certification, exhaustive cross-browser certification, or proof of unrestricted public
production readiness.

## Local API

Generate a signing secret and set it before constructing the API. The secret is required, has no
built-in fallback, and must not be committed:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:LIFELENZ_JWT_SECRET = "<generated value>"
```

Then start the development API from the activated project environment:

```powershell
python -m uvicorn lifelenz.api.app:create_app --factory --reload
```

The default database is `./data/lifelenz.db`. Explicit application construction creates its parent
directory when needed. Configuration is read from `LIFELENZ_ENVIRONMENT`,
`LIFELENZ_DATABASE_PATH`, `LIFELENZ_API_PREFIX`, `LIFELENZ_DOCS_ENABLED`,
`LIFELENZ_JWT_SECRET`, `LIFELENZ_JWT_ISSUER` (default `lifelenz-api`),
`LIFELENZ_JWT_AUDIENCE` (default `lifelenz-clients`), and `LIFELENZ_ACCESS_TOKEN_MINUTES` (default
`30`, allowed `5` through `1440`); no `.env` parser is included.

Available routes are:

```text
GET /
GET /health
GET /ready
GET /api/v1
GET /api/v1/health
GET /api/v1/ready
POST /api/v1/auth/register
POST /api/v1/auth/login
GET /api/v1/auth/me
POST /api/v1/profile
GET /api/v1/profile
PUT /api/v1/profile
POST /api/v1/records
GET /api/v1/records
GET /api/v1/records/{record_id}
PUT /api/v1/records/{record_id}
DELETE /api/v1/records/{record_id}
POST /api/v1/imports/csv
POST /api/v1/goals
GET /api/v1/goals
GET /api/v1/goals/{goal_id}
PUT /api/v1/goals/{goal_id}
DELETE /api/v1/goals/{goal_id}
GET /api/v1/summary
```

Registration creates an account only and does not invent a wellness profile. Login returns a
short-lived access token; there is no refresh token yet. `/api/v1/auth/me` requires `Authorization:
Bearer <token>` and returns safe account identity plus owned profile identifiers, never passwords,
hashes, or wellness content.

Profile onboarding is a separate authenticated step and permits one primary wellness profile per
account. Profile requests contain only the existing wellness preferences; profile and ownership IDs
are server-controlled. The record endpoints use an explicit `record_type` discriminator, generate
record IDs on the server, preserve deterministic repository ordering, and optionally filter lists by
record type or a start-inclusive/end-exclusive aware timestamp range. Corrections preserve the
server-controlled record ID, concrete type, and original source provenance. Cross-account record
lookups and mutations return the same not-found response as nonexistent records to avoid revealing
resource existence. CSV imports derive profile ownership from the authenticated account and support
schema v1 validation and explicit commit for six categories; duplicate rows are skipped separately
from validation errors.

Goal routes also derive the primary profile from the authenticated account. They support create,
list, read, immutable replacement, and deletion through the existing goal application/repository
contracts; callers cannot choose profile ownership. Cross-account goal lookups use the same
not-found response as nonexistent goals. The summary route accepts optional repeated `metric`
parameters and an aware `start`/`end` window. It returns canonical-unit baselines and optional
mathematical trends from the existing analytics layer. A single sample produces a baseline without
a trend. These calculations are structured descriptive data, not diagnosis, medical advice,
prediction, a health score, or an AI-generated recommendation.

Interactive documentation is available at `/docs` and `/redoc` unless documentation is disabled.
Production configuration requires it to be disabled. This is not a complete authentication lifecycle
or unrestricted public production service. Password reset, email verification, MFA, social login,
refresh-token rotation, rate limiting, generated advice, public-host monitoring, historical time-series
charts, exhaustive browser coverage, mobile UI, and medical decision support remain out of scope.
No regulatory-compliance, medical-device, encrypted-SQLite, high-availability, or unrestricted
production-readiness claim is made.

More contributor guidance is available in [Development standards](docs/development.md).

## Documentation

- [Product scope](docs/product-scope.md) defines the intended users, MVP, non-goals, and safety boundary.
- [Architecture](docs/architecture.md) describes the intended first-phase design.
- [Development standards](docs/development.md) defines the contributor workflow and engineering expectations.
- [CSV schema v1](docs/csv-import-v1.md) documents supported categories, exact headers, validation, normalization, and duplicate semantics.
- [Browser end-to-end validation](docs/browser-e2e.md) documents the isolated Chromium critical-path journey and its CI/local runtime contract.
- [Production deployment](docs/deployment.md) documents the single-host container topology, production configuration, security headers, and SQLite recovery procedure.
- [MVP1 release](docs/release.md) documents the final release contract, exact-source validation, tag promotion, artifact publication, and public-host boundary.
- [MVP1 v0.1.0 release notes](release/RELEASE_NOTES_v0.1.0.md) summarize shipped capabilities and known limitations.
- [MVP1 beta release candidate](docs/release-candidate.md) preserves Commit 39 candidate and recovery evidence as a historical record.
- [Release readiness](docs/release-readiness.md) defines the minimum evidence and explicit non-claims for MVP1 promotion and external beta hosting.
- [Roadmap](docs/roadmap.md) separates implemented milestones from future work.

## Wellness and medical disclaimer

LifeLenz-AI is intended for general wellness reflection and education. It is not a medical device and
is not intended to diagnose, predict, treat, or prevent disease; recommend medications or treatments;
provide emergency guidance; or replace qualified medical advice. Users should consult an appropriate
healthcare professional about medical concerns and contact local emergency services when urgent help
is needed.

## License

LifeLenz-AI is available under the [MIT License](LICENSE).
