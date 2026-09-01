# MVP1 release-readiness gates

This checklist defines the minimum evidence expected for LifeLenz MVP1 release promotion. It is intentionally conservative and does not replace hosting-specific security, legal, privacy, accessibility, or operational review.

## Repository gates

Before promoting MVP1:

- `main` must contain only reviewed, merged changes intended for the release source;
- required independent pull-request approvals must be satisfied;
- no unresolved review thread may remain on the release change;
- GitGuardian must report no committed secrets;
- Security Invariants must pass;
- Python quality, Python 3.13 tests, coverage, persistence/migration, API/authentication, and package-integrity jobs must pass;
- the Node.js 22 web job must pass linting, formatting, strict TypeScript, unit/component tests, and the production build;
- the real Chromium Browser E2E journey must pass;
- Deployment Validation must build and smoke-test the production Compose stack successfully;
- MVP1 Release Validation must validate final release metadata, build release artifacts, and complete the SQLite backup/restore drill successfully.

A failing gate is release-blocking. Do not lower or bypass a gate to complete a release.

## Final release metadata gates

The final source must keep these values internally consistent:

- product version `0.1.0` in Python and web package metadata;
- release identifier `mvp1-0.1.0`;
- Git tag `v0.1.0`;
- release channel `beta`;
- Python runtime 3.13 and requirement `>=3.13`;
- Node.js runtime 22 and engine `>=22.13 <23`;
- storage contract `sqlite-single-api-instance`;
- promotion source `mvp1-0.1.0-rc.1`.

The final tag must match the tag declared in `release/manifest.json` and must point to a commit in `main` history. The tag-triggered workflow rebuilds and revalidates that exact source before publishing a GitHub Release.

## Production configuration gates

A production-shaped environment must:

- set `LIFELENZ_ENVIRONMENT=production`;
- use an absolute durable SQLite path;
- disable API documentation;
- inject a unique JWT signing secret of at least 48 UTF-8 bytes through trusted runtime secret handling;
- expose only the web gateway from the bundled Compose topology;
- run exactly one API instance for each SQLite database volume;
- terminate public traffic through trusted HTTPS infrastructure before internet exposure.

Do not commit production `.env` files, JWT signing secrets, account passwords, wellness exports, or database files.

## Browser and accessibility gates

Before exposing the release to external beta users, manually verify at minimum:

- keyboard-only navigation through registration, login, onboarding, dashboard, records, imports, goals, and profile;
- the `Skip to main content` control works on authentication and authenticated layouts;
- visible focus is not lost behind fixed or responsive navigation;
- form labels, validation errors, confirmations, and destructive actions remain understandable without relying only on color;
- layouts remain usable at approximately 375 px, 768 px, and desktop widths;
- no critical workflow introduces page-level horizontal scrolling;
- basic screen-reader landmark and heading structure is coherent.

Automated tests provide regression evidence but are not a formal WCAG conformance audit.

## Deployment and data gates

Before exposing the release to external beta users:

- verify deployed `/healthz` and `/api/v1/ready` endpoints;
- verify the security-header baseline through the public HTTPS origin;
- configure HSTS at the trusted TLS terminator only after HTTPS is guaranteed for the public origin;
- choose operational off-host backup storage, retention, encryption, and access policy;
- confirm container/runtime logs do not capture request bodies, credentials, JWT secrets, or wellness payloads;
- define who can access the host, runtime secrets, database volume, and backups;
- retain an explicit rollback path to the prior known-good application image and compatible database state;
- define monitoring, alerting, incident-response, and abuse-control ownership appropriate to the deployment.

The repository provides and CI-tests a Docker-host SQLite backup/restore primitive. It does not provide a scheduled off-host backup service or disaster-recovery guarantee.

## Commit 39 release-candidate evidence

Candidate `mvp1-0.1.0-rc.1` established:

- a static manifest validated against Python/npm metadata and the Python 3.13 / Node.js 22 runtime contracts;
- reproducible Python and web candidate artifacts with SHA-256 checksums and source-SHA evidence;
- an end-to-end SQLite backup/restore drill that destroys the original disposable Compose volume, restores an exported backup into a fresh volume, and proves the same synthetic account can authenticate afterward.

The temporary SQLite backup is never retained as a workflow artifact.

## Commit 40 release-promotion evidence

Commit 40 promotes the candidate contract into final MVP1 release metadata and adds a release workflow that:

- validates the exact source SHA used for the release;
- requires `v0.1.0` to match the release manifest;
- requires a tag-triggered release source to belong to `main` history;
- rebuilds the Python and web release artifacts from the exact source;
- repeats production Compose and destructive SQLite recovery validation;
- publishes the GitHub Release from the already validated artifact bundle through a separate job with `contents: write` permission only on tag-triggered runs.

The final release notes preserve the product's explicit limitations instead of converting repository release status into a public-production claim.

## Explicit non-claims

Passing this checklist does not establish:

- medical-device status or clinical suitability;
- regulatory compliance;
- horizontal scalability or high availability;
- automated disaster recovery;
- penetration-test certification;
- formal WCAG conformance;
- exhaustive cross-browser certification;
- public-host monitoring or incident-response maturity;
- unrestricted public-production readiness.

Repository release promotion and public-host readiness remain separate decisions.
