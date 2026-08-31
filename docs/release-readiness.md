# MVP1 release-readiness gates

This checklist defines the minimum evidence expected before LifeLenz is promoted from the implemented MVP to a beta release candidate. It is intentionally conservative and does not replace hosting-specific security, legal, privacy, or operational review.

## Repository gates

Before creating a beta release candidate:

- `main` must contain only reviewed, merged changes intended for the candidate.
- Required independent pull-request approvals must be satisfied.
- No unresolved review thread may remain on the release-candidate change.
- GitGuardian must report no committed secrets.
- The repository Security Invariants job must pass.
- Python quality, tests, coverage, persistence/migration, API/authentication, and package-integrity jobs must pass.
- The Node 22 web job must pass linting, formatting, strict TypeScript, unit/component tests, and the production build.
- The real Chromium Browser E2E journey must pass.
- Deployment Validation must build and smoke-test the production Compose stack successfully.
- Release Candidate validation must produce internally consistent candidate metadata, build candidate artifacts, and complete the SQLite backup/restore drill successfully.

## Production configuration gates

A candidate production environment must:

- set `LIFELENZ_ENVIRONMENT=production`;
- use an absolute durable SQLite path;
- disable API documentation;
- inject a unique JWT signing secret of at least 48 UTF-8 bytes through trusted runtime secret handling;
- expose only the web gateway from the bundled Compose topology;
- run exactly one API instance for each SQLite database volume;
- terminate public traffic through trusted HTTPS infrastructure before internet exposure.

Do not commit production `.env` files, JWT signing secrets, account passwords, wellness exports, or database files.

## Browser and accessibility gates

Before beta release, manually verify at minimum:

- keyboard-only navigation through registration, login, onboarding, dashboard, records, imports, goals, and profile;
- the `Skip to main content` control works on authentication and authenticated layouts;
- visible focus is not lost behind fixed or responsive navigation;
- form labels, validation errors, confirmations, and destructive actions remain understandable without relying only on color;
- layouts remain usable at approximately 375 px, 768 px, and desktop widths;
- no critical workflow introduces page-level horizontal scrolling;
- basic screen-reader landmark and heading structure is coherent.

Automated tests provide regression evidence but are not a formal WCAG conformance audit.

## Deployment and data gates

Before exposing a candidate to beta users:

- verify the deployed `/healthz` and `/api/v1/ready` endpoints;
- verify the production security-header baseline through the public HTTPS origin;
- configure HSTS at the trusted TLS terminator only after HTTPS is guaranteed for the public origin;
- define and test an operational SQLite backup and restore procedure appropriate to the hosting platform;
- confirm container/runtime logs do not capture request bodies, credentials, JWT secrets, or wellness payloads;
- define who can access the host, runtime secrets, database volume, and backups;
- retain an explicit rollback path to the prior known-good application image and compatible database state.

Commit 39 provides and CI-tests the repository's Docker-host SQLite backup/restore procedure. A real beta environment must still choose where exported backups are retained, who can access them, how they are encrypted if required, and how restore/rollback responsibilities are assigned.

## Commit 39 release-candidate evidence

The `mvp1-0.1.0-rc.1` candidate adds three pieces of evidence that were intentionally absent before this milestone:

- a static release manifest validated against Python and npm metadata plus the Python 3.13 / Node 22 runtime contracts;
- reproducible Python and web candidate artifacts with SHA-256 checksums and source-SHA evidence;
- an end-to-end SQLite backup/restore drill that destroys the original disposable Compose volume, restores an exported backup into a fresh volume, and proves the same synthetic account can authenticate afterward.

The candidate workflow never uploads the temporary SQLite backup as a retained artifact.

These automated checks establish a reproducible repository release candidate. They do not establish public-host readiness or complete the manual browser/accessibility gates above.

## Explicit non-claims

Passing this checklist does not establish:

- medical-device status or clinical suitability;
- regulatory compliance;
- horizontal scalability or high availability;
- automated disaster recovery;
- penetration-test certification;
- formal WCAG conformance;
- production monitoring or incident-response maturity.

Commit 39 records remaining host-specific and manual blockers rather than silently waiving them. Commit 40 may promote the candidate only after the exact merged candidate state remains green and the final release metadata accurately reflects those limitations.
