# Architecture

This document describes the intended architecture for LifeLenz-AI's first development
phase. The repository currently contains only the initial `lifelenz` package foundation;
the layers and packages below are planned and will be introduced incrementally.

## Architectural goals

- Strong domain modelling with explicit wellness concepts and invariants
- Clear separation of responsibilities and dependency direction
- Testability through small interfaces and deterministic behavior
- Explainable calculations and observations
- Deterministic analytics for repeatable results
- Minimal dependencies and operational complexity
- Incremental extensibility as real capabilities are implemented

## Initial logical layers

### 1. Domain layer

The domain layer will define wellness records, controlled types, validation rules, personal
profiles, and goals. It owns the vocabulary and invariants shared by the rest of the system,
without storage, framework, or user-interface concerns.

### 2. Repository layer

Repository interfaces will describe how validated wellness records are stored and queried.
An in-memory implementation is planned first to support application behavior and tests.
Future persistence implementations should conform to the same domain-oriented contracts
without leaking infrastructure details into domain types.

### 3. Analytics layer

The analytics layer will calculate personal baselines, aggregations, trends, and statistical
summaries. Calculations should be pure functions where practical, explicit about their input
windows and missing-data behavior, and deterministic for the same ordered inputs.

### 4. Insight layer

The insight layer will apply deterministic rules to analytics results. Each observation
should include evidence, relevant periods and comparisons, and confidence and importance
metadata whose meanings are explicitly defined. Output must use neutral, non-diagnostic
language and distinguish insufficient evidence from a meaningful result.

### 5. Service layer

Services will coordinate profiles, goals, repositories, analytics, and insight rules. They
will define application use cases and produce typed wellness summaries without embedding
domain validation or statistical logic that belongs in lower layers.

## Dependency direction

The intended dependency flow is:

```text
Services -> Insights / Analytics / Repositories -> Domain
```

Services may compose the other layers. Insight and analytics code may consume domain types,
and repository contracts are expressed in domain terms. The domain layer must not depend on
application services, persistence implementations, external frameworks, or other
infrastructure. Cross-layer contracts should not introduce reverse dependencies.

## Data flow

```mermaid
flowchart LR
    A[Wellness data] --> B[Validated domain records]
    B --> C[Repository]
    C --> D[Baseline analytics]
    D --> E[Explainable insight generation]
    E --> F[Wellness summary]
```

Validation must occur before a record enters a repository. Analytics transforms a defined
selection of records into baseline and trend results. Insight rules evaluate those results
and retain evidence needed for the final summary.

## Initial package direction

The planned package structure is:

```text
src/lifelenz/
|-- analytics/
|-- domain/
|-- insights/
|-- repositories/
`-- services/
```

This is a direction, not the current filesystem. A package will be created only when its
first real implementation is added; empty placeholders are intentionally avoided.

## Architectural decisions

### Standard-library first

Use the Python standard library unless an implemented capability has a concrete need that a
dependency addresses better. This keeps the early model and calculations easy to inspect.

### `src` package layout

Production package code remains under `src/lifelenz/`. This prevents accidental imports
from the repository root and supports testing the installed package shape.

### Timezone-aware timestamps

Recorded instants must use timezone-aware datetimes. Local calendar concepts should retain
the timezone or explicit date context needed to interpret them; ambiguous naive timestamps
should be rejected at boundaries.

### Value-oriented domain records

Domain records should be fully typed and immutable or otherwise value-oriented where
practical. Construction must enforce invariants so downstream layers can rely on valid data.

### Pure analytics where practical

Analytics should receive explicit data and configuration and return typed results without
hidden state or I/O. This supports reproducible calculations and focused tests.

### No premature infrastructure

The first phase does not introduce an API framework, database, machine-learning stack,
cloud platform, or wearable integration before a working capability requires it. FastAPI,
PostgreSQL, LLMs, and wearable APIs are not present components of the current architecture.

### Explainability before predictive complexity

Deterministic, evidence-backed summaries come before forecasting or predictive models. Any
future advanced technique must have a defined benefit, evaluation method, failure behavior,
and safe explanation strategy.
