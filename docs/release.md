# MVP1 release

The LifeLenz MVP1 release contract declares product version `0.1.0` and expected Git tag `v0.1.0`. These values do not establish that the tag or a published GitHub Release exists; publication requires the tag-triggered workflow below.

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

The [MVP1 Release workflow](../.github/workflows/release.yml) validates pull requests, pushes to `main`, manual runs, and release tags.

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
12. uploads the validated release bundle as the named `lifelenz-mvp1-0.1.0` GitHub Actions artifact;
13. validates the upload's artifact ID as exactly one positive decimal integer;
14. creates a fresh, empty directory under `RUNNER_TEMP`, requires archive readiness, and downloads that exact artifact from the same repository/run using authenticated `actions/download-artifact@v7` lookup;
15. verifies the downloaded bundle's exact flat contents and checksums, then compares its `SHA256SUMS` byte-for-byte with the original bundle's manifest.

This hosted upload/download verification is mandatory on pull-request, `main`, manual, and tag validation runs. A missing artifact, unexpected or nested files, altered payloads, invalid checksums, or a different checksum manifest fails `validate-release`. Failure prevents validation succeeding and therefore blocks tag publication. The earlier local canonical-bundle and copied flat-layout checks remain additional checks; a local copy does not prove a GitHub artifact round trip. Hosted evidence is established only when the workflow actually passes.

The upload step's `artifact-id` is the identity used by both downloads. The validation job
exposes it as `release-artifact-id`, which the tag-only publishing job receives through
`needs.validate-release.outputs.release-artifact-id`. Before each download, a mandatory Bash
check requires exactly one positive decimal integer. Missing, zero, negative, whitespace-containing,
comma-separated, or otherwise malformed IDs fail before the download action runs. Neither download
falls back to artifact-name, pattern, or all-artifact selection.

Immediately before **both** download actions, the mandatory
[readiness helper](../scripts/wait_for_release_artifact.py) probes GitHub's artifact ZIP endpoint
with an authenticated GET using only the step-scoped `GH_TOKEN` and actual upload-produced ID.
It validates the repository, ID, and credentials before making requests, disables automatic
redirects, and accepts only HTTP 302 with a nonempty `Location` as ready. It neither follows nor
prints the signed redirect URL and does not read response bodies or print response headers.

Only HTTP 404 is retried: at most five attempts, a five-second timeout per request, and five
seconds between attempts (at most four sleeps). Authentication/authorization failures, all other
HTTP statuses, malformed responses or missing redirect locations, and network/timeout errors fail
immediately. Exhausting the 404 budget also fails. Readiness failure blocks the download and
publication; there are no retries around bundle verification or integrity failures, and the
helper makes no API writes or artifact deletions.

Observed evidence showed that artifact lookup succeeded while its archive endpoint returned 404;
a later authenticated download and checksum verification succeeded. This does not establish the
underlying service cause. The bounded probe addresses that observed readiness boundary without
guaranteeing a subsequent download will succeed. Both downloads, the fresh flat destination,
exact-file verifier, SHA256SUMS checks, and checksum-manifest comparison remain mandatory.

Both downloads supply `artifact-ids`, `github-token: github.token`, `repository: github.repository`,
and `run-id: github.run_id` as action inputs (the values use GitHub expressions). This explicitly
binds authenticated lookup to the same repository and workflow run. Each job grants only the
additional `actions: read` permission needed for lookup, alongside its existing contents scope;
tokens are passed only to the steps that need them. The
[v7 download implementation](https://github.com/actions/download-artifact/blob/v7/src/download-artifact.ts)
extracts a single matched ID directly into the requested path, preserving the flat destination
without merging unrelated artifacts.

The corrected authenticated path still requires hosted evidence on the eventual PR and on the
exact squash-merged `main` source. A green PR run alone is insufficient evidence for the merged
source. ID-based selection clarifies artifact identity; it does not prove a GitHub service root
cause or guarantee service availability.

When the workflow is triggered by `v0.1.0`, it additionally verifies that the tagged commit belongs to `main` history. Only after the validation job succeeds does a separate least-privilege publishing job receive `contents: write` permission and create the GitHub Release from the validated artifact bundle.

The publishing job does not build a second, unvalidated copy of the application. It validates the propagated artifact ID, requires archive readiness, independently downloads that exact artifact from the successful validation job, verifies the exact bundle contents and SHA-256 checksums again, and attaches those exact files to the GitHub Release.

## Release artifacts

The release bundle contains:

- Python wheel;
- Python source distribution;
- production-built web archive;
- release manifest;
- release evidence JSON containing the exact source SHA;
- release notes;
- SHA-256 checksums.

Assets are packaged into one canonical flat directory (`release-bundle/`):

```text
lifelenz_ai-0.1.0-py3-none-any.whl
lifelenz_ai-0.1.0.tar.gz
lifelenz-web-mvp1-0.1.0.tar.gz
manifest.json
release-evidence.json
RELEASE_NOTES_v0.1.0.md
SHA256SUMS
```

Download all assets into a fresh directory and run from that directory:

```sh
sha256sum -c SHA256SUMS
```

`SHA256SUMS` lists each payload once using its final filename, in sorted order, and excludes
itself. To additionally reject extra files, duplicate entries, and unsafe paths, run
`python /path/to/reviewed/source/scripts/release_bundle.py verify .`.
Before upload, the workflow verifies the canonical bundle and a locally copied flat layout.
After upload, PR, `main`, manual, and tag validation runs download the single uploaded artifact
by its validated ID into the fresh, empty directory and run `scripts/release_bundle.py verify`
there to reject missing, unexpected, nested, or invalid files. They also run
`sha256sum -c SHA256SUMS` inside that
directory and use `cmp` to require its checksum manifest to match `release-bundle/SHA256SUMS`
byte-for-byte. This ties the independently verified downloaded payloads to the original bundle.
The tag-only publishing job retains its separate download and revalidation, then publishes
exactly those files without rebuilding or modifying payloads.

The temporary SQLite database used to prove backup and restore is never retained as a release artifact.

## Release sequence

The intended promotion sequence is:

1. merge the Commit 41 hardening pull request after the required reviews and all exact-head gates pass;
2. confirm the merged `main` state containing both Commit 41 fixes remains green;
3. create Git tag `v0.1.0` on that reviewed merged commit;
4. allow the tag-triggered `MVP1 Release` workflow to rebuild and validate the exact tagged source;
5. publish the GitHub Release only after release validation succeeds;
6. verify the resulting release assets and checksums.

A release tag must not be moved after publication. A defect discovered after release should be corrected through a new version rather than rewriting `v0.1.0`.

## Public-host boundary

A repository release and a public production deployment are separate decisions.

Release validation also does not exercise GitHub Desktop UI behavior; that remains a separate
manual verification.

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

See [Release readiness](release-readiness.md) and [Deployment](deployment.md) for those boundaries.

## Product boundary

MVP1 remains intentionally deterministic and general-wellness focused. Predictions, recommendations, correlation exploration, machine-learning components, and an optional natural-language explanation layer remain future work that require separate safety, privacy, explainability, and evaluation plans.
