# MVP1 beta release candidate

Commit 39 establishes the first reproducible LifeLenz MVP1 beta release candidate.

Candidate identifier: `mvp1-0.1.0-rc.1`

Product version: `0.1.0`

This candidate is a reviewed source-and-artifact state for final MVP1 validation. It is not a public production launch, a medical-device release, a regulatory claim, or a promise of unrestricted internet readiness.

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

No new wellness feature is introduced by Commit 39.

## Candidate manifest

`release/manifest.json` is the authoritative static release-candidate contract. It records:

- candidate identifier;
- product version;
- beta release channel;
- Python 3.13 runtime;
- Node.js 22 runtime;
- Python and Node version constraints;
- the single-API-instance SQLite storage contract.

`scripts/validate_release_candidate.py` checks this manifest against `pyproject.toml`, `web/package.json`, and `web/package-lock.json`. It also requires the Python package metadata to identify the project as beta-stage software.

The candidate identifier is intentionally separate from the package product version. Commit 40 is responsible for final MVP1 promotion and the public repository release/tag decision; Commit 39 does not create a GitHub Release or final `v0.1.0` tag.

## Candidate artifacts

The `Release Candidate` GitHub Actions workflow builds and retains a short-lived CI artifact bundle containing:

- Python wheel;
- Python source distribution;
- production-built web bundle archive;
- static candidate manifest;
- runtime/source evidence JSON for the exact workflow SHA;
- SHA-256 checksums for the packaged artifacts.

The workflow artifact is CI evidence, not a public distribution channel. Commit 40 decides what, if anything, is published as the final repository release.

## Backup and restore evidence

The candidate includes `deploy/sqlite_maintenance.py`, a deployment helper with three explicit operations:

- `backup` creates an SQLite backup using SQLite's backup API and validates the resulting file with `PRAGMA integrity_check`;
- `verify` validates an SQLite database or backup without logging its contents;
- `restore` validates the backup, requires explicit confirmation that API writers are stopped, removes stale WAL/SHM sidecars when replacing an existing database, restores through SQLite's backup API, and validates the restored file.

The Release Candidate workflow proves the procedure against the actual production Compose topology:

1. boot the production candidate images with fresh masked CI-only credentials;
2. register and authenticate a synthetic account through the web gateway;
3. create an integrity-checked SQLite backup inside the API container;
4. copy that backup outside the named data volume;
5. independently verify the exported backup;
6. destroy the original Compose data volume;
7. restore the backup into a fresh named volume while the API is stopped;
8. restart the production stack;
9. authenticate the same synthetic account from the restored database;
10. delete the temporary backup and destroy the disposable CI environment.

The workflow does not upload the synthetic SQLite backup as a CI artifact.

## Automated release-candidate gates

Commit 39 does not replace the existing CI. The candidate must pass all of these independent gates on the exact PR head:

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

A candidate with a failing gate is not promotable.

## Manual and hosting-specific gates

The repository can establish a beta release candidate without pretending that host-specific or human validation has already happened.

Before exposing the candidate to beta users, the operator must still complete and record:

- public HTTPS termination and the resulting public-origin security-header check;
- HSTS configuration at the trusted TLS terminator after HTTPS is guaranteed;
- off-volume/off-host backup storage and retention policy;
- access-control ownership for the host, runtime secrets, database volume, and backups;
- review of deployed logs for accidental credentials, request bodies, JWT material, or wellness payloads;
- rollback procedure using the prior known-good image and compatible database state;
- keyboard-only review of all critical workflows;
- responsive review near 375 px, 768 px, and desktop widths;
- basic screen-reader landmark and heading review.

These items are not silently waived by a green CI run.

## Promotion to Commit 40

Commit 40 may promote this candidate only after:

- Commit 39 is merged to `main`;
- post-merge CI remains green;
- no release-blocking issue is discovered during candidate review;
- the final release notes accurately describe implemented behavior and explicit non-claims;
- the repository version/tag/release state is made internally consistent.

Any code change required after Commit 39 must be treated as a new candidate state and revalidated rather than being silently inserted into the final release.
