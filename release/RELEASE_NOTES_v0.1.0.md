# LifeLenz MVP1 v0.1.0

LifeLenz MVP1 v0.1.0 is the first repository release of the project. It promotes the validated `mvp1-0.1.0-rc.1` candidate without adding new wellness functionality.

## What ships

- account registration, login, short-lived bearer sessions, and authenticated current-user restoration;
- explicit wellness-profile onboarding and profile preference editing;
- manual creation for all ten current wellness-record types;
- recent and full record history, filtering, correction, and deliberate deletion;
- CSV schema v1 validation/import for six supported record categories;
- user-defined wellness-goal management;
- deterministic personal baselines, mathematical trends, and structured wellness summaries;
- descriptive dashboard visualizations derived only from server-returned analytics;
- real Chromium critical-path validation;
- provider-neutral Docker Compose deployment with separate unprivileged API and web containers;
- fail-closed production configuration and browser-facing security headers;
- keyboard skip navigation;
- SQLite backup, integrity verification, guarded restore, and destructive recovery validation.

## Release evidence

The release workflow validates the exact release source against Python 3.13 and Node.js 22 contracts, builds the Python wheel/source distribution and production web bundle, records source-SHA evidence, produces SHA-256 checksums, builds and boots the production Compose images, and repeats the destructive SQLite recovery drill before a tagged release can be published.

A `v0.1.0` tag must match the manifest version and belong to `main` history. The tag-triggered workflow publishes only artifacts rebuilt and validated from that exact tagged source.

## Product boundary

LifeLenz is a general-wellness project. This release provides descriptive, deterministic wellness data organization and analytics. It does not diagnose, predict disease, prescribe treatment, provide emergency guidance, or generate medical recommendations.

## Known limitations

MVP1 deliberately does not include password reset, email verification, MFA, refresh-token rotation, server-side token revocation, direct wearable integrations, vendor-specific export compatibility, historical server-side time-series endpoints, recommendations, forecasting, correlation analysis, production monitoring/alerting, rate limiting/abuse controls, managed-database failover, horizontal scaling, or mobile applications.

SQLite remains the durable backend and supports one API instance per database volume. The repository does not provide encrypted SQLite storage, automated off-host backup retention, public TLS termination, HSTS at the bundled HTTP gateway, high availability, or disaster-recovery guarantees.

## Hosting note

The repository release is not an unrestricted public-production certification. Any public beta deployment still requires trusted HTTPS termination, public-origin security-header verification, host/secret/database access ownership, off-host backup and retention decisions, deployed-log review, rollback ownership, monitoring/alerting decisions, and the remaining manual accessibility/responsive checks documented in `docs/release-readiness.md`.

## Compatibility

- Python runtime contract: 3.13
- Python requirement: >=3.13
- Node.js runtime contract: 22
- Node.js engine: >=22.13 <23
- Storage contract: one API instance per SQLite database volume

## Upgrade note

This is the first repository release, so there is no prior public release upgrade path. Future releases must preserve or explicitly document database migration and compatibility requirements.
