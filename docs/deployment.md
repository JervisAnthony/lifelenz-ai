# Production deployment foundation

LifeLenz provides a provider-neutral, production-shaped container deployment with fail-closed configuration, browser-facing security headers, and an operational SQLite backup/verify/restore helper. Deployment and release workflows validate different parts of this single-host foundation; tag-triggered publication is documented in the [MVP1 release guide](release.md).

This remains a single-host MVP deployment foundation, not a claim that LifeLenz is ready for unrestricted public production use. Public TLS termination, monitoring, abuse controls, off-host backup policy, and hosting-specific release decisions remain separate responsibilities.

## Topology

The Compose stack contains two services:

- `web` builds the React application with Node.js 22 and serves the production bundle from an unprivileged Nginx runtime on port `8080` inside the container.
- `api` runs the installed LifeLenz Python package under Python 3.13 and Uvicorn as an unprivileged user. The API is reachable only from the Compose network; it is not published directly to the host.

The web gateway reverse-proxies `/api/*` to the API service and falls back to `index.html` for client-side application routes. This keeps browser API calls same-origin and does not require a CORS exception.

The API stores SQLite data in the named `lifelenz-data` volume at `/var/lib/lifelenz/lifelenz.db`. See the [Compose definition](../deploy/compose.yml), [API Dockerfile](../deploy/api.Dockerfile), [web Dockerfile](../deploy/web.Dockerfile), and [Nginx configuration](../deploy/nginx.conf) for the runtime contract, or [Architecture](architecture.md) for application and persistence boundaries.

Authenticated CSV v1 commit persists all ready rows through the application services in one atomic SQLite batch. Validation errors write nothing; storage failure rolls back the batch and returns HTTP 503 while preserving pre-existing records. This persistence guarantee does not change the single-instance deployment boundary. See [CSV schema v1](csv-import-v1.md) for validation, duplicate, and retry behavior.

## Important deployment boundary

The current persistence layer is SQLite. Run exactly one LifeLenz API service instance against a given database volume. This deployment does not claim safe horizontal API scaling, shared-network filesystem semantics, multi-region replication, or hosted-database failover.

Moving beyond one API instance requires a separately designed persistence architecture and migration plan.

## Required secret

`LIFELENZ_JWT_SECRET` has no default and must be supplied at runtime. Production configuration requires at least 48 UTF-8 bytes of signing-secret material. Generate a fresh value using an appropriate secret generator and inject it through the deployment platform or host environment.

For a local Docker-host smoke deployment in PowerShell:

```powershell
$env:LIFELENZ_JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For Bash:

```bash
export LIFELENZ_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Do not commit the generated value. For an actual hosted environment, prefer the platform's secret manager rather than a checked-in `.env` file.

## Production configuration invariants

When `LIFELENZ_ENVIRONMENT` is `production` (case-insensitive), API startup now fails closed unless all of these conditions hold:

- API documentation is disabled;
- `LIFELENZ_DATABASE_PATH` resolves to an absolute filesystem path;
- the JWT signing secret contains at least 48 UTF-8 bytes.

The general non-production minimum remains 32 UTF-8 bytes so existing development and test contracts remain unchanged.

Surrounding whitespace in the environment name is rejected rather than allowing a value such as ` production ` to bypass production checks.

The Compose contract fixes these production-safe values:

- `LIFELENZ_ENVIRONMENT=production`
- `LIFELENZ_DATABASE_PATH=/var/lib/lifelenz/lifelenz.db`
- `LIFELENZ_DOCS_ENABLED=false`

The following values may be supplied through the environment:

- `LIFELENZ_HTTP_PORT` — host port for the web gateway; defaults to `8080`
- `LIFELENZ_IMAGE_TAG` — local image tag suffix; defaults to `local`
- `LIFELENZ_JWT_ISSUER` — defaults to `lifelenz-api`
- `LIFELENZ_JWT_AUDIENCE` — defaults to `lifelenz-clients`
- `LIFELENZ_ACCESS_TOKEN_MINUTES` — defaults to `30`

The bundled deployment intentionally keeps the API prefix at `/api/v1`, because the current first-party web client targets that contract.

## Build and start

From the repository root:

```bash
docker compose -f deploy/compose.yml build --pull
docker compose -f deploy/compose.yml up -d
```

Check the public web-gateway liveness endpoint:

```bash
curl --fail http://127.0.0.1:8080/healthz
```

Check API readiness through the same-origin gateway:

```bash
curl --fail http://127.0.0.1:8080/api/v1/ready
```

A client-side route such as `http://127.0.0.1:8080/app/records` should return the built SPA entry point and then apply the normal authentication/profile route guards in the browser.

## Stop, preserve, and destroy data

Stop the stack while preserving the named SQLite volume:

```bash
docker compose -f deploy/compose.yml down
```

Destroying the volume is destructive:

```bash
docker compose -f deploy/compose.yml down -v
```

Do not use `-v` against an environment whose data must be retained.

## SQLite backup, verification, and restore

The production API image includes `deploy/sqlite_maintenance.py`. It uses SQLite's backup API and `PRAGMA integrity_check`; it does not print database rows, credentials, or wellness payloads.

### Create and export a backup

Create a coherent backup while the API is running:

```bash
docker compose -f deploy/compose.yml exec -T api \
  python /app/deploy/sqlite_maintenance.py backup \
  --database /var/lib/lifelenz/lifelenz.db \
  --output /tmp/lifelenz-backup.db
```

Copy the verified backup out of the container and therefore out of the named data volume:

```bash
mkdir -p backups
docker compose -f deploy/compose.yml cp \
  api:/tmp/lifelenz-backup.db \
  ./backups/lifelenz-backup.db
```

Remove the temporary in-container copy:

```bash
docker compose -f deploy/compose.yml exec -T api rm -f /tmp/lifelenz-backup.db
```

The exported file should then be moved into the operator's approved backup storage. This repository does not choose an off-host storage provider, retention period, encryption-at-rest mechanism, or access policy.

### Verify an exported backup

The helper can verify a host-side backup before a destructive operation:

```bash
python deploy/sqlite_maintenance.py verify \
  --database ./backups/lifelenz-backup.db
```

A successful verification prints only the verified file path.

### Restore a backup

Restore is deliberately more restrictive than backup. Stop the API before restore:

```bash
docker compose -f deploy/compose.yml stop api
```

Then run a one-off API image with the backup directory mounted read-only:

```bash
docker compose -f deploy/compose.yml run --rm -T \
  -v "$PWD/backups:/backup:ro" \
  api python /app/deploy/sqlite_maintenance.py restore \
  --input /backup/lifelenz-backup.db \
  --database /var/lib/lifelenz/lifelenz.db \
  --replace \
  --confirm-api-stopped
```

`--confirm-api-stopped` is mandatory. `--replace` is required only when the destination database already exists. A restore validates the source backup, removes stale `-wal`/`-shm` sidecars when replacing a database, restores through SQLite's backup API, and validates the resulting database before returning success.

Restart the stack and verify readiness:

```bash
docker compose -f deploy/compose.yml up -d
curl --fail http://127.0.0.1:8080/api/v1/ready
```

A real recovery runbook should also verify application login and representative owned data after restore.

The helper is an operational primitive, not automated disaster recovery. Scheduling, off-host retention, encryption, access controls, recovery-time objectives, and recovery-point objectives remain hosting decisions.

## Health and readiness

The API image uses the existing `/ready` endpoint as its Docker health check. Readiness validates that the durable SQLite schema is accessible.

The web image exposes `/healthz` for gateway liveness. Compose waits for the API to become healthy before starting the web service.

Application-level API health remains available through:

```text
/api/v1/health
/api/v1/ready
```

## Browser-facing security headers

The Nginx gateway applies a conservative browser security baseline to gateway, SPA, and proxied API responses:

- `Content-Security-Policy`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Resource-Policy: same-origin`
- `Permissions-Policy: camera=(), geolocation=(), microphone=()`
- `Referrer-Policy: no-referrer`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`

The CSP is same-origin by default, denies framing and objects, and does not permit inline scripts. `style-src` currently includes `'unsafe-inline'` because the deterministic dashboard range visualization uses inline positional style values for mean/median markers. Removing that allowance requires a separate rendering refactor rather than silently breaking those visuals.

Nginx server-version tokens are disabled.

`Strict-Transport-Security` is intentionally not emitted by the bundled HTTP-only gateway. A trusted external HTTPS terminator should own HSTS because it is the component that can accurately guarantee TLS for the public origin.

## Network exposure and TLS

Only the web gateway is published to the host. The API service remains internal to the Compose network.

The supplied stack serves HTTP on the configured host port. Do not expose it directly to the public internet without TLS. A hosted deployment should terminate HTTPS at a trusted platform load balancer, ingress, or reverse proxy and forward traffic to the LifeLenz web gateway.

Rate limiting, abuse controls, TLS policy, certificate automation, and external-edge HSTS remain hosting/operational hardening responsibilities.

## Accessibility hardening

The authentication and authenticated application layouts provide a keyboard-reachable `Skip to main content` link targeting one explicit `#main-content` landmark. The target is programmatically focusable so keyboard users can bypass repeated navigation.

The real Chromium MVP journey verifies that the skip link is the first keyboard focus target and that activation transfers focus to the main-content landmark in both authentication and authenticated layouts.

This is targeted accessibility hardening, not a formal WCAG conformance claim. The [release-readiness checklist](release-readiness.md#browser-and-accessibility-gates) still requires final manual keyboard/screen-reader and responsive checks before exposure to beta users.

## Logs

Uvicorn and Nginx write operational logs to standard output/error for collection by the container runtime or hosting platform. Request bodies, passwords, JWT signing secrets, and wellness payloads must not be added to deployment logs.

## CI deployment validation

[Deployment Validation](../.github/workflows/deployment.yml) (`.github/workflows/deployment.yml`, job `Production Compose`) validates the deployment contract on pull requests, pushes to `main`, and manual runs. The workflow:

1. generates fresh masked test-only runtime credentials;
2. renders the Compose configuration;
3. builds both production images;
4. proves unsafe production configuration is rejected;
5. boots the stack with a fresh named volume;
6. checks gateway liveness and API readiness through the reverse proxy;
7. asserts the browser-facing security-header baseline on gateway, API, and SPA responses;
8. verifies a client-side deep route returns the SPA;
9. registers and logs in a synthetic account through the deployed gateway;
10. restarts the API process and confirms the same account can still log in from SQLite persistence;
11. confirms production API documentation remains disabled;
12. tears down the stack and test volume.

`MVP1 Release Validation` is a separate job in [MVP1 Release](../.github/workflows/release.yml) (`.github/workflows/release.yml`). It runs on pull requests, pushes to `main`, manual runs, and `v*` tag pushes. It checks the release contract with [validate_release.py](../scripts/validate_release.py), builds Python/web assets, and packages one canonical flat bundle with SHA-256 checksums using [release_bundle.py](../scripts/release_bundle.py). It verifies both the bundle and a fresh flat download layout before uploading release evidence.

That validation job also boots the production images, registers a synthetic account, exports and verifies an SQLite backup, destroys the original disposable named volume, restores into fresh storage, and proves the same account can authenticate after recovery. It never uploads the temporary SQLite database backup as a retained artifact. This drill proves a specific recovery path; it does not establish recovery of every application workflow or a disaster-recovery guarantee.

`Publish GitHub Release` runs only on a tag-triggered run after release validation succeeds. Tag validation requires a match with the manifest's expected tag and a commit in `main` history. Only this publishing job receives `contents: write`; it downloads the validated flat bundle, verifies the exact file set and checksums again, and attaches those assets without rebuilding payloads. Product version or manifest status alone does not create a tag or a GitHub Release. See [MVP1 release](release.md#release-workflow) and [release assets](release.md#release-artifacts) for the full contract and download-verification commands.

[CI](../.github/workflows/ci.yml), including the [Browser E2E journey](browser-e2e.md), validates backend/web behavior separately. Browser E2E uses live FastAPI, isolated SQLite, and a Vite preview server rather than the production Nginx topology.

Together these workflows provide evidence for buildability, fail-closed configuration, startup, same-origin proxying, response headers, restart persistence, release-asset integrity, and a concrete backup/restore path. They do not constitute performance, penetration, multi-host, or automated disaster-recovery testing, and do not establish unrestricted public-production readiness. The remaining host and human gates are in [Release readiness](release-readiness.md).

## Current limitations

Before unrestricted public release, hosting-specific operational decisions remain. Current deployment limitations include:

- single API instance because SQLite is the active durable backend;
- no scheduled or managed off-host backup service;
- no repository-provided backup encryption or retention policy;
- no encryption-at-rest implementation for the active database volume;
- no hosted secret-manager integration in this repository;
- no bundled TLS termination or HSTS because TLS belongs at the external edge;
- no formal production monitoring or alerting integration;
- no repository-provided incident-response service or assigned operational ownership;
- no rate limiting or abuse-control layer;
- no formal accessibility certification;
- no claim of regulatory compliance or medical-device readiness.

The deployment foundation is deliberately conservative: it makes the existing MVP reproducible, recoverable through a tested SQLite procedure, and more defensive in a production-shaped runtime without overstating operational maturity.
