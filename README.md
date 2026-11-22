# LifeLenz-AI

LifeLenz-AI is a beta-stage personal wellness application for organizing lifestyle records
and reviewing descriptive patterns in a person's own data. MVP1 provides deterministic
personal baselines, mathematical trends, and structured summaries for general-wellness
reflection. It does not generate medical advice, predictions, or recommendations.

## Project status

Product metadata declares version `0.1.0`, release identifier `mvp1-0.1.0`, and expected tag
`v0.1.0`, promoted from candidate `mvp1-0.1.0-rc.1`. These values describe the repository's
release contract; they do not establish that a Git tag or published GitHub Release exists.
Publication is the tag-triggered process in [MVP1 release](docs/release.md): validate the exact
tagged source and publish its verified assets only after validation succeeds. Repository
release status remains separate from public-host production readiness.

The implemented MVP1 includes:

- accounts with Argon2 password hashing, short-lived signed bearer tokens, separate primary-profile
  onboarding, explicit ownership, and editable profile preferences;
- manual entry, recent/full history, type/date filtering, correction, and confirmed deletion for
  Sleep, Daily Activity, Workout, Hydration, Meal, Daily Nutrition, Body Measurement, Subjective
  Wellness Check-In, Menstrual Bleeding, and Menstrual Cycle;
- CSV v1 validate/review/commit for Sleep, Daily Activity, Hydration, Daily Nutrition, Body
  Measurement, and Subjective Wellness Check-In, with normalization and semantic duplicate detection;
- user-defined goal creation, replacement, status changes, and deletion, without automatic progress
  evaluation or target comparison;
- server-derived canonical-unit baselines and trends, with dashboard coverage, observed ranges,
  mean/median markers, and mathematical change; no historical sample-series contract is provided;
- durable SQLite storage, a same-origin container deployment, tested backup/restore primitives,
  and reproducible release packaging and validation.

Commit 41 hardening makes CSV persistence atomic: all ready rows pass through authenticated
application services into one batch, and storage failure rolls back every batch change. Release
assets use one flat directory with SHA-256 checksums verified before upload and again before
publication. See [CSV v1](docs/csv-import-v1.md) and [release assets](docs/release.md#release-artifacts).

Stored measurement-system, time-zone, and week-start preferences do not implement summary unit
conversion or local-calendar grouping. Individual record deletion does not provide account deletion
or complete personal-data export. Richer insight rules, weekly narratives, correlations, wearable
integrations, forecasting, recommendations, ML inference, and LLM explanations remain future work.
See [Product scope](docs/product-scope.md) for the complete capability boundaries.

## Architecture

The React/TypeScript/Vite browser application uses React Router, TanStack Query, and a typed API
client. In the Compose deployment, an unprivileged Nginx gateway serves static assets and proxies
same-origin `/api` calls to an internal FastAPI application. Authenticated application services
resolve profile ownership and coordinate repository contracts, domain validation, CSV ingestion,
and deterministic analytics. SQLite adapters persist accounts, ownership, profiles, goals, and
records through explicit serialization and schema migrations.

Analytics calculate count, mean, median, minimum, maximum, population standard deviation, and
mathematical endpoint change/slope. The summary service assembles those results into typed data;
there is no separate implemented insight-rule engine. Successful record mutations and CSV imports
invalidate browser record and summary queries so subsequent reads retrieve current server results.

The database is not encrypted by this implementation. Run one API instance per SQLite database
volume; horizontal scaling, high availability, and managed failover are outside this architecture.
External HTTPS/HSTS, off-host backup retention/encryption/access policy, monitoring, incident response,
and abuse controls remain operator responsibilities. Successful repository validation does not
establish unrestricted public-production readiness.

See [Architecture](docs/architecture.md) for runtime flow, source dependency direction, and contracts.

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
validates the final release contract, builds flat release assets, verifies their SHA-256 checksums
and a fresh flat download layout, and proves backup/restore after destruction of the original
disposable data volume. A tag-triggered run also requires the tag to match the manifest and
belong to `main` history. Only after validation succeeds
does a separate tag-only publishing job receive `contents: write` permission and create the GitHub
Release from the downloaded, reverified artifact bundle without rebuilding payloads. The temporary
SQLite backup is not retained. See the [release workflow](.github/workflows/release.yml) and
[release guide](docs/release.md) for publication and asset-verification details.

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
from validation errors. All ready rows persist in one atomic batch; storage failure returns HTTP
503 after rollback, preserving pre-existing records. Validate mode never writes records.

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

- [Product scope](docs/product-scope.md) separates implemented MVP1 capabilities from future direction and defines the safety boundary.
- [Architecture](docs/architecture.md) describes the implemented runtime, packages, dependency direction, and persistence contracts.
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
