# MVP1 release

LifeLenz MVP1 is released from the repository as product version `0.1.0` with the Git tag `v0.1.0`.

The release identifier is `mvp1-0.1.0`, promoted from candidate `mvp1-0.1.0-rc.1`.

This is a repository release of the implemented MVP1 product. It is not a claim of unrestricted public-production readiness, regulatory compliance, medical-device suitability, high availability, or formal accessibility certification.

## Release source of truth

`release/manifest.json` is the static release contract. It records:

- the MVP1 release identifier;
- the expected Git tag;
- the release candidate from which the release was promoted;
- product version and beta release channel;
- Python 3.13 and Node.js 22 runtime contracts;
- Python and Node version constraints;
- the single-API-instance SQLite storage boundary.

`scripts/validate_release.py` checks the manifest against `pyproject.toml`, `web/package.json`, and `web/package-lock.json`. On a tag-triggered release it also checks that the actual Git tag equals the tag declared in the manifest.

## Release workflow

`.github/workflows/release.yml` validates pull requests, pushes to `main`, manual runs, and release tags.

The validation job:

1. checks out the exact release source SHA;
2. validates release metadata;
3. builds the Python wheel and source distribution;
4. builds the production web bundle;
5. packages release evidence and SHA-256 checksums;
6. builds the production API and web images;
7. boots the production Compose stack with fresh masked synthetic credentials;
8. creates and verifies an SQLite backup;
9. destroys the original disposable data volume;
10. restores the backup into fresh storage;
11. verifies that the same synthetic account can authenticate from the restored database;
12. uploads the validated release bundle as a GitHub Actions artifact.

When the workflow is triggered by `v0.1.0`, it additionally verifies that the tagged commit belongs to `main` history. Only after the validation job succeeds does a separate least-privilege publishing job receive `contents: write` permission and create the GitHub Release from the validated artifact bundle.

The publishing job does not build a second, unvalidated copy of the application. It downloads the release artifacts produced by the successful validation job and attaches those exact files to the GitHub Release.

## Release artifacts

The release bundle contains:

- Python wheel;
- Python source distribution;
- production-built web archive;
- release manifest;
- release evidence JSON containing the exact source SHA;
- release notes;
- SHA-256 checksums.

The temporary SQLite database used to prove backup and restore is never retained as a release artifact.

## Release sequence

The intended promotion sequence is:

1. merge the Commit 40 pull request after the required reviews and all exact-head gates pass;
2. confirm the merged `main` Commit 40 state remains green;
3. create Git tag `v0.1.0` on that reviewed merged commit;
4. allow the tag-triggered `MVP1 Release` workflow to rebuild and validate the exact tagged source;
5. publish the GitHub Release only after release validation succeeds;
6. verify the resulting release assets and checksums.

A release tag must not be moved after publication. A defect discovered after release should be corrected through a new version rather than rewriting `v0.1.0`.

## Public-host boundary

A repository release and a public production deployment are separate decisions.

Before exposing LifeLenz to external beta users, the operator still owns:

- trusted HTTPS termination;
- HSTS at the trusted TLS terminator after HTTPS is guaranteed;
- verification of security headers through the public origin;
- off-host backup storage, encryption, retention, and access policy;
- host, secret, database, and backup access ownership;
- monitoring, alerting, and incident-response decisions;
- rate limiting and abuse-control decisions;
- deployed-log review;
- rollback ownership;
- remaining manual keyboard, responsive, and screen-reader checks.

See `docs/release-readiness.md` and `docs/deployment.md` for those boundaries.

## Product boundary

MVP1 remains intentionally deterministic and general-wellness focused. Predictions, recommendations, correlation exploration, machine-learning components, and an optional natural-language explanation layer remain future work that require separate safety, privacy, explainability, and evaluation plans.
