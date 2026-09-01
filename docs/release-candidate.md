# MVP1 beta release candidate — historical record

Commit 39 established the first reproducible LifeLenz MVP1 beta release candidate.

Candidate identifier: `mvp1-0.1.0-rc.1`

Product version: `0.1.0`

The candidate was the reviewed source-and-artifact state used for final MVP1 promotion. Commit 40 promotes this candidate into release `mvp1-0.1.0` with expected Git tag `v0.1.0`. The final release process is documented in `docs/release.md`.

This candidate never represented a public-production launch, a medical-device release, a regulatory claim, or a promise of unrestricted internet readiness.

## Candidate scope

The candidate contains the implemented MVP1 product surface:

- account registration, login, and authenticated current-user restoration;
- explicit profile onboarding and profile preference editing;
- manual entry for all ten current wellness record types;
- full record history, filtering, correction, and confirmed deletion;
- CSV schema v1 validation and import for six supported record categories;
- deterministic personal baselines, mathematical trends, and structured summaries;
- wellness-goal creation, replacement, status management, and deletion;
- dashboard descriptive analytics based only on server-derived summary data;
- real Chromium critical-path validation;
- provider-neutral single-host Docker deployment;
- fail-closed production configuration and browser-facing security headers;
- keyboard skip navigation for authentication and authenticated layouts.

No new wellness feature was introduced by Commit 39.

## Candidate contract

The Commit 39 manifest recorded:

- candidate identifier `mvp1-0.1.0-rc.1`;
- product version `0.1.0`;
- beta release channel;
- Python 3.13 runtime;
- Node.js 22 runtime;
- Python and Node version constraints;
- the single-API-instance SQLite storage contract.

The candidate validator checked that contract against `pyproject.toml`, `web/package.json`, and `web/package-lock.json`, and required beta-stage Python package metadata.

Commit 40 replaces the active candidate contract with the final release contract. The candidate identifier is retained in the final manifest as `promoted_from` so the promotion remains traceable.

## Candidate artifacts and recovery evidence

The Release Candidate workflow built and retained short-lived CI evidence containing:

- Python wheel;
- Python source distribution;
- production-built web bundle archive;
- candidate manifest;
- exact-source evidence JSON;
- SHA-256 checksums.

It also proved the SQLite recovery procedure against the production Compose topology:

1. boot the production candidate images with fresh masked CI-only credentials;
2. register and authenticate a synthetic account through the web gateway;
3. create an integrity-checked SQLite backup inside the API container;
4. copy that backup outside the named data volume;
5. independently verify the exported backup;
6. destroy the original Compose data volume;
7. restore the backup into a fresh named volume while API writers are stopped;
8. restart the production stack;
9. authenticate the same synthetic account from the restored database;
10. delete the temporary backup and destroy the disposable CI environment.

The synthetic SQLite backup was never uploaded as a retained artifact.

## Candidate gates

The exact candidate source passed the repository gates used for promotion:

- Quality;
- Tests on Python 3.13;
- coverage threshold;
- Persistence & Migrations;
- API & Authentication;
- Security Invariants;
- Package Integrity;
- Node.js 22 Web validation;
- real Chromium Browser E2E;
- Production Compose deployment validation;
- Release Candidate artifact and backup/restore validation;
- GitGuardian secret scanning.

## Remaining boundaries after promotion

Promotion to a repository release does not silently complete host-specific or human validation. Before exposing LifeLenz to external beta users, an operator still owns:

- public HTTPS termination and public-origin security-header verification;
- HSTS configuration at the trusted TLS terminator after HTTPS is guaranteed;
- off-host backup storage, retention, encryption, and access policy;
- host, runtime-secret, database-volume, and backup access ownership;
- deployed-log review;
- rollback planning;
- monitoring, alerting, incident response, and abuse-control decisions;
- manual keyboard, responsive, and basic screen-reader review.

See `docs/release-readiness.md` for the current release gates and explicit non-claims.
