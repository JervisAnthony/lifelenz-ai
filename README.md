# LifeLenz-AI

LifeLenz-AI is an early-stage personal wellness intelligence project. It is intended to
help people organize longitudinal lifestyle data, understand patterns relative to their
own baselines, and receive transparent, non-diagnostic observations.

The core value proposition is context: instead of treating sleep, activity, hydration,
mood, energy, and stress as isolated readings, LifeLenz-AI aims to make changes and
co-occurring patterns understandable over time. Observations will use conservative
language and expose the data and rules behind them.

## Project status

LifeLenz-AI is at version 0.1.0 and in the foundation stage. The repository currently
contains an installable `lifelenz` Python package, development tooling, and a controlled
taxonomy for wellness categories, metrics, units, data sources, confidence, and insight
severity. Shared domain foundations provide record identifiers, aware time ranges, common
metadata, and reusable validation. Concrete domain records capture completed sleep sessions,
daily activity totals, completed workouts, hydration events, meal nutrition, and daily
nutrition summaries, neutral body measurements, and subjective mood, energy, stress, and
optional motivation check-ins with explicitly validated values. They also capture menstrual
bleeding observations, user-supplied menstrual-cycle date ranges, and privacy-conscious
wellness profiles with tracking preferences, plus user-defined wellness goals. Framework-independent
repository contracts define storage-neutral operations for profiles, goals, and wellness records.
Deterministic in-memory implementations support tests and early application development; they are
process-local, non-durable, and lose all data when the process ends. Durable SQLite repositories now
store profiles, goals, and wellness records in a local database file using explicit deterministic
JSON serialization. They preserve typed domain values, canonical units, original aware timestamp
offsets, and data across repository instances and process restarts. This local persistence backend is
suitable for development and local API composition, but it is not encrypted by this
implementation and is not a hosted or multi-user database service. Framework-independent
application services coordinate repositories, enforce profile existence for profile-owned
operations, and translate
expected missing-entity failures. The profile, goal, and record services do not calculate analytics
or goal progress. Deterministic
personal-baseline analytics summarize supported canonical metrics from a person's own recorded
observations using count, mean, median, minimum, maximum, and population standard deviation.
Baselines preserve canonical units and use record metadata timestamps; they provide no medical
interpretation, population comparison, recommended target, or health classification. Deterministic
basic trend analytics report first and last values, absolute and percentage change when defined,
least-squares slope per day, and neutral increasing, decreasing, or stable direction for supported
canonical metrics. Optional time ranges use metadata timestamps. Direction is purely mathematical:
increasing does not mean healthy, decreasing does not mean unhealthy, and trends neither predict
future values nor recommend actions. A framework-independent wellness-summary workflow now requires
an existing profile, reads its stored records with optional metadata-time filtering, and produces one
structured canonical-unit summary per supported metric. Metrics with at least one sample include a
baseline, while metrics with at least two samples also include a trend. The result is structured data,
not user-facing medical or coaching text. Framework-independent account identity, Argon2 password
hashing, short-lived signed access tokens, durable accounts, and explicit profile ownership are now
available. Account registration does not create a wellness profile: authentication establishes
identity, while a separate `UserId -> ProfileId` mapping establishes authorization context. Hosted
database deployment, cloud synchronization, goal progress, correlations,
recommendations, predictions, import workflows, notifications, production monitoring, complete web
workflows, mobile applications (including Android and iOS), and medical decision support do not yet
exist. The project does not yet claim production readiness,
regulatory compliance, encryption at rest, cloud backup, or cross-repository transaction coordination.

LifeLenz-AI now also includes a versioned FastAPI foundation for local development. Alongside public
system metadata, liveness, and SQLite-readiness endpoints, it supports account registration, login,
bearer-protected current-user retrieval, explicit primary-profile onboarding and replacement, and
owned wellness-record creation, listing, and retrieval for all ten current record types. Every
wellness-resource route requires bearer authentication and resolves ownership from the account;
clients cannot choose a profile identifier. Owned wellness-goal management and a deterministic,
structured wellness-summary endpoint now expose the existing goal, baseline, and trend application
capabilities without adding medical interpretation or generated recommendations. The local SQLite
content is not encrypted.

A React and TypeScript web application now provides a restrained public landing page, account
registration and login, authoritative current-user restoration, protected routing, first-time
wellness-profile onboarding, profile-preference editing, and a responsive authenticated application
shell. Its initial dashboard presents real structured wellness summaries when records exist and an
honest empty state when they do not. Summary measurements remain in the backend's canonical units;
the stored measurement-system preference does not yet convert them in the browser. A focused record
entry foundation now supports Sleep, Hydration, and Subjective wellness check-in creation through
the authenticated backend, plus a restrained recent-record list for all current record types. The
remaining seven creation forms, record editing or deletion, full history and filtering, goal-management
UI, and analytics visualizations remain future web milestones.

The planned MVP capability areas are:

- Structured records for sleep, activity, hydration, basic nutrition, body measurements,
  mood, energy, and stress
- Personal profiles and goals
- Personal-baseline analytics and trend summaries
- Deterministic, explainable wellness observations
- Typed wellness summaries

Manual entry and structured-data imports are planned for the MVP. Direct wearable
connections and broad wellness-platform integrations are future work, not current
capabilities.

## Architecture

The backend uses a layered, standard-library-first design. Domain types and validation form the base;
repository abstractions manage records; pure analytics calculate baselines and trends; deterministic
rules produce explainable observations; and services coordinate these parts into summaries. The
`web/` application is a separate Vite build with a typed API-client boundary, centralized
authentication state, TanStack Query server-state orchestration, React Router routes, and lightweight
CSS design tokens. The backend remains authoritative for identity and wellness data.

See [Architecture](docs/architecture.md) for the intended dependency direction and design
decisions.

## Development setup

LifeLenz-AI requires Python 3.13 or later. In Windows PowerShell, create and activate a
virtual environment, then install the package with development dependencies:

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

The current web alpha stores its short-lived bearer access token in browser `sessionStorage` through a
single storage abstraction. Closing the browser session clears that storage, but `sessionStorage` does
not eliminate cross-site scripting risk. There are no refresh tokens or server-side revocation/logout
sessions yet; logout clears client state but cannot revoke an already-issued token. The server remains
authoritative through `/api/v1/auth/me`, and production authentication hardening will be revisited
before public deployment. Passwords, account objects, wellness data, and signing secrets are not
persisted in browser storage.

After authentication, the web application derives onboarding state from the server-owned profile
identifiers returned by `/api/v1/auth/me`. Users without a profile are guided through the existing
profile API; configured users can review their preferences and open a summary-backed dashboard. The
web interface provides Home, Records, and Profile destinations. Records are persisted by the existing
authenticated API; successful creation refreshes the server-owned record list and invalidates the
structured summary so the dashboard can retrieve current analytics. Browser-local datetimes are sent
with an explicit UTC offset, and canonical units are preserved. Record editing and deletion, advanced
history and filtering, the remaining record-entry types, goal-management UI, and chart-based
visualization are not yet implemented.

## Continuous integration

Pull requests, pushes to `main`, and manual workflow runs use Python 3.13, the runtime declared by
the project metadata. CI runs Ruff lint and formatting checks, the full pytest suite, an enforced
98% coverage floor, focused SQLite persistence and schema-migration tests, focused API and
authentication tests, dependency consistency checks, deterministic project-specific security
invariants, and wheel/source-distribution build verification. A separate Node.js 22 `Web` job installs
the npm lockfile and runs ESLint, Prettier, strict TypeScript, Vitest, and the production Vite build.
Dependency caching is an optimization; each job installs from its ecosystem metadata independently.

Dependabot checks Python, GitHub Actions, and npm dependencies under `/web` weekly. GitGuardian
remains a complementary external secret-scanning check. These automated checks are not a formal
security certification, complete static analysis, penetration test, production-hardening assessment,
regulatory-compliance validation, or deployment validation.

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
record type or a start-inclusive/end-exclusive aware timestamp range. Cross-account record lookups
return the same not-found response as nonexistent records to avoid revealing resource existence.

Goal routes also derive the primary profile from the authenticated account. They support create,
list, read, immutable replacement, and deletion through the existing goal application/repository
contracts; callers cannot choose profile ownership. Cross-account goal lookups use the same
not-found response as nonexistent goals. The summary route accepts optional repeated `metric`
parameters and an aware `start`/`end` window. It returns canonical-unit baselines and optional
mathematical trends from the existing analytics layer. A single sample produces a baseline without
a trend. These calculations are structured descriptive data, not diagnosis, medical advice,
prediction, a health score, or an AI-generated recommendation.

Interactive documentation is available at `/docs` and `/redoc` unless documentation is disabled.
This is not a complete authentication lifecycle, backend, or public production service. Password
reset, email verification, MFA, social login, refresh-token rotation, rate limiting, CORS,
standalone baseline/trend endpoints, generated advice, hosted deployment, cloud synchronization,
notifications, production monitoring, complete profile/record/goal/summary web workflows, mobile UI
(including Android and iOS), and medical decision support remain out of scope. No production-grade
security, regulatory compliance, or encrypted SQLite storage claim is made.

More contributor guidance is available in [Development standards](docs/development.md).

## Documentation

- [Product scope](docs/product-scope.md) defines the intended users, MVP, non-goals, and
  safety boundary.
- [Architecture](docs/architecture.md) describes the intended first-phase design.
- [Development standards](docs/development.md) defines the contributor workflow and
  engineering expectations.
- [Roadmap](docs/roadmap.md) separates near-term milestones from future work.

## Wellness and medical disclaimer

LifeLenz-AI is intended for general wellness reflection and education. It is not a medical
device and is not intended to diagnose, predict, treat, or prevent disease; recommend
medications or treatments; provide emergency guidance; or replace qualified medical
advice. Users should consult an appropriate healthcare professional about medical concerns
and contact local emergency services when urgent help is needed.

## License

LifeLenz-AI is available under the [MIT License](LICENSE).
