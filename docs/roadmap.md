# Roadmap

This roadmap describes direction without assigning dates. Except where a capability is explicitly
marked implemented, items below remain planned or future work. Ordering may change as validation and
design work reveal better boundaries.

## Phase 1 — Foundation and domain

Establish a precise, tested vocabulary for wellness data:

- Project foundation — implemented
- Product and engineering documentation — implemented
- Wellness taxonomy and controlled units — implemented
- Shared domain primitives, validation, and timezone handling — implemented
- Sleep records — implemented
- Activity records — implemented
- Hydration and basic nutrition records — implemented
- Body measurements — implemented
- Mood, energy, and stress records — implemented
- Personal profile and goals — implemented

The phase is complete when these domain concepts have explicit invariants, typed public contracts,
representative validation tests, and documentation that reflects implemented behavior.

## Phase 2 — Wellness intelligence

Build the first end-to-end general-wellness workflow:

- In-memory repository and query contracts — implemented
- Personal-baseline analytics — implemented
- Aggregations and trend calculations — implemented
- Deterministic, explainable insight rules — partially implemented through structured summaries;
  richer evidence-facing observations remain future work
- Typed wellness summary service — implemented
- Integration tests across records, storage, analytics, and summaries — implemented

### First wellness intelligence milestone completion criteria

The milestone is complete when:

- A supported set of validated records can be stored and retrieved in memory.
- Baselines and trends have defined minimum-data, time-window, missing-data, and timezone behavior.
- The same inputs and configuration always produce the same ordered outputs.
- Every generated observation identifies its evidence and rule and uses non-causal,
  non-diagnostic language.
- Empty, invalid, insufficient, and boundary datasets have explicit tested outcomes.
- A service can produce a typed wellness summary across the implemented record categories.
- Unit and integration tests pass with linting, formatting, and public documentation current.
- No output crosses the documented general-wellness and medical safety boundary.

## Phase 3 — Data ingestion

Add deliberate import workflows after domain contracts are stable:

- Versioned CSV schema v1 for six stable MVP record categories — implemented
- Import validation with actionable row-level errors — implemented for CSV v1
- Duplicate detection with documented semantic identity rules — implemented for CSV v1
- Unit and timestamp normalization — implemented for CSV v1
- Authenticated validate/commit API workflow — implemented for CSV v1
- Browser CSV selection, validation review, and commit workflow — implemented
- Support for selected exported wellness-data formats — future work

CSV v1 currently covers Sleep, Daily Activity, Hydration, Daily Nutrition, Body Measurement, and
Subjective Wellness Check-In. It does not promise compatibility with every app or device. Each future
export format or CSV schema expansion requires a documented schema, fixtures, validation behavior,
and provenance rules.

## Phase 4 — Product interfaces

Expose proven application services through product workflows:

- Versioned authenticated REST API — implemented
- Dashboard for structured summaries and descriptive metric visualizations — implemented
- Manual entry for all ten current record types — implemented
- Full record history and filtering — implemented
- Record correction and deliberate deletion — implemented
- Wellness-goal management — implemented
- CSV import web workflow — implemented
- Baseline-range and mathematical trend visualizations — implemented
- Real-browser critical MVP journey — implemented
- Provider-neutral single-host production deployment foundation — implemented
- Public-hosting, security, accessibility, operational, and release hardening — planned

The production deployment foundation builds separate API and web containers, exposes only the web
gateway, reverse-proxies same-origin `/api` traffic, persists SQLite in a named volume, and validates
the stack in CI using a production-shaped Docker Compose smoke test. Because SQLite remains the active
durable backend, this foundation deliberately supports one API instance per database volume and does
not claim horizontal scaling, hosted-database failover, automated backups, encryption at rest, TLS
termination, production monitoring, or public-release readiness.

The browser E2E journey runs Chromium against a live FastAPI process, isolated SQLite database, and
built Vite application. It validates registration, authentication, profile onboarding, record
creation/correction/deletion, CSV validation/import, dashboard refresh, goal creation, logout, and
protected-route redirection using synthetic data. It is a critical-path integration gate rather than
an exhaustive cross-browser suite.

The dashboard visualizes only values already returned by the deterministic summary API. Baseline
range views show minimum, maximum, mean, and median without inventing time-series points. Trend views
show mathematical first/last change and direction without health classification, target comparison,
or recommendations. Rich historical time-series charts remain a possible later capability if an
appropriate server-side series contract is introduced.

## Phase 5 — Advanced intelligence

Explore later capabilities only after deterministic wellness intelligence can be evaluated:

- Forecasting with explicit uncertainty and failure criteria
- Correlation exploration that avoids causal claims
- Personal recommendation ranking within the general-wellness boundary
- Carefully evaluated machine-learning components for demonstrated use cases
- An optional natural-language explanation layer grounded in deterministic evidence

These are future possibilities, not commitments or implemented AI features. Each requires a
separate safety, privacy, explainability, and evaluation plan before adoption.
