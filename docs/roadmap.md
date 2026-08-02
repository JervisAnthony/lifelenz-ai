# Roadmap

This roadmap describes direction without assigning dates. Except for the existing project
foundation and this documentation set, the capabilities below are planned or future work;
they are not implemented in version 0.1.0. Ordering may change as validation and design work
reveals better boundaries.

## Phase 1 — Foundation and domain

Establish a precise, tested vocabulary for wellness data:

- Project foundation — implemented
- Product and engineering documentation — defined by this documentation set
- Wellness taxonomy and controlled units
- Shared domain primitives, validation, and timezone handling
- Sleep records
- Activity records
- Hydration and basic nutrition records
- Body measurements
- Mood, energy, and stress records
- Personal profile and goals

The phase is complete when these domain concepts have explicit invariants, typed public
contracts, representative validation tests, and documentation that reflects implemented
behavior.

## Phase 2 — Wellness intelligence

Build the first end-to-end general-wellness workflow:

- In-memory repository and query contracts
- Personal-baseline analytics
- Aggregations and trend calculations
- Deterministic, explainable insight rules
- Typed wellness summary service
- Integration tests across records, storage, analytics, insights, and summaries

### First wellness intelligence milestone completion criteria

The milestone is complete when:

- A supported set of validated records can be stored and retrieved in memory.
- Baselines and trends have defined minimum-data, time-window, missing-data, and timezone
  behavior.
- The same inputs and configuration always produce the same ordered outputs.
- Every generated observation identifies its evidence and rule and uses non-causal,
  non-diagnostic language.
- Empty, invalid, insufficient, and boundary datasets have explicit tested outcomes.
- A service can produce a typed wellness summary across the implemented record categories.
- Unit and integration tests pass with linting, formatting, and public documentation current.
- No output crosses the documented general-wellness and medical safety boundary.

## Phase 3 — Data ingestion

Add deliberate import workflows after domain contracts are stable:

- Versioned CSV schemas for supported record categories
- Import validation with actionable row-level errors
- Duplicate detection with documented identity rules
- Unit and timestamp normalization
- Support for selected exported wellness-data formats

This phase does not promise compatibility with every app or device. Each supported export
format will require a documented schema, fixtures, validation behavior, and provenance rules.

## Phase 4 — Product interfaces

Expose proven application services through product workflows:

- An API shaped around validated service use cases
- A dashboard for data review, trends, evidence, and summaries
- User workflows for entry, import, correction, goals, and export
- Authentication and durable persistence when interface and deployment needs justify them

Interface frameworks, database technology, hosting, and access-control design will be chosen
when requirements are concrete. They are not present in the current foundation.

## Phase 5 — Advanced intelligence

Explore later capabilities only after deterministic wellness intelligence can be evaluated:

- Forecasting with explicit uncertainty and failure criteria
- Correlation exploration that avoids causal claims
- Personal recommendation ranking within the general-wellness boundary
- Carefully evaluated machine-learning components for demonstrated use cases
- An optional natural-language explanation layer grounded in deterministic evidence

These are future possibilities, not commitments or implemented AI features. Each requires a
separate safety, privacy, explainability, and evaluation plan before adoption.
