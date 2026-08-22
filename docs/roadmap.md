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
- Dashboard for structured summaries and recent wellness data — implemented foundation
- Manual entry for all ten current record types — implemented
- Full record history and filtering — implemented
- Record correction and deliberate deletion — implemented
- Wellness-goal management — implemented
- CSV import web workflow — implemented
- Analytics visualizations — planned
- Production deployment and release hardening — planned

## Phase 5 — Advanced intelligence

Explore later capabilities only after deterministic wellness intelligence can be evaluated:

- Forecasting with explicit uncertainty and failure criteria
- Correlation exploration that avoids causal claims
- Personal recommendation ranking within the general-wellness boundary
- Carefully evaluated machine-learning components for demonstrated use cases
- An optional natural-language explanation layer grounded in deterministic evidence

These are future possibilities, not commitments or implemented AI features. Each requires a
separate safety, privacy, explainability, and evaluation plan before adoption.
