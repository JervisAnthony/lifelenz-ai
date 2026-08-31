# Production deployment foundation

Commit 37 introduces a provider-neutral, production-shaped container deployment for LifeLenz. It is intended to make the current MVP reproducibly deployable on a single Docker host while preserving the existing same-origin web/API boundary and durable SQLite behavior.

This is a deployment foundation, not a claim that LifeLenz is ready for unrestricted public production use. Security, accessibility, operational, and release hardening remain separate work.

## Topology

The Compose stack contains two services:

- `web` builds the React application with Node.js 22 and serves the production bundle from an unprivileged Nginx runtime on port `8080` inside the container.
- `api` runs the installed LifeLenz Python package under Python 3.13 and Uvicorn as an unprivileged user. The API is reachable only from the Compose network; it is not published directly to the host.

The web gateway reverse-proxies `/api/*` to the API service and falls back to `index.html` for client-side application routes. This keeps browser API calls same-origin and does not require a CORS exception.

The API stores SQLite data in the named `lifelenz-data` volume at `/var/lib/lifelenz/lifelenz.db`.

## Important deployment boundary

The current persistence layer is SQLite. Run exactly one LifeLenz API service instance against a given database volume. This deployment does not claim safe horizontal API scaling, shared-network filesystem semantics, multi-region replication, or hosted-database failover.

Moving beyond one API instance requires a separately designed persistence architecture and migration plan.

## Required secret

`LIFELENZ_JWT_SECRET` has no default and must be supplied at runtime. Generate a fresh value using an appropriate secret generator and inject it through the deployment platform or host environment.

For a local Docker-host smoke deployment in PowerShell:

```powershell
$env:LIFELENZ_JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For Bash:

```bash
export LIFELENZ_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
```

Do not commit the generated value. For an actual hosted environment, prefer the platform's secret manager rather than a checked-in `.env` file.

## Optional runtime configuration

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

Back up the SQLite volume using an operationally appropriate process before upgrades or destructive maintenance. This repository does not currently provide automated backup, restore, encryption-at-rest, or disaster-recovery orchestration.

## Health and readiness

The API image uses the existing `/ready` endpoint as its Docker health check. Readiness validates that the durable SQLite schema is accessible.

The web image exposes `/healthz` for gateway liveness. Compose waits for the API to become healthy before starting the web service.

Application-level API health remains available through:

```text
/api/v1/health
/api/v1/ready
```

## Network exposure and TLS

Only the web gateway is published to the host. The API service remains internal to the Compose network.

The supplied stack serves HTTP on the configured host port. Do not expose it directly to the public internet without TLS. A hosted deployment should terminate HTTPS at a trusted platform load balancer, ingress, or reverse proxy and forward traffic to the LifeLenz web gateway.

TLS policy, security headers, rate limiting, abuse controls, and broader production security review are part of subsequent hardening work.

## Logs

Uvicorn and Nginx write operational logs to standard output/error for collection by the container runtime or hosting platform. Request bodies, passwords, JWT signing secrets, and wellness payloads must not be added to deployment logs.

## CI deployment validation

`.github/workflows/deployment.yml` validates this deployment contract on pull requests, pushes to `main`, and manual runs. The workflow:

1. generates fresh masked test-only runtime credentials;
2. renders the Compose configuration;
3. builds both production images;
4. boots the stack with a fresh named volume;
5. checks gateway liveness and API readiness through the reverse proxy;
6. verifies a client-side deep route returns the SPA;
7. registers and logs in a synthetic account through the deployed gateway;
8. restarts the API process and confirms the same account can still log in from SQLite persistence;
9. tears down the stack and test volume.

This validates buildability, process startup, same-origin proxying, basic persistence across an API restart, and the intended single-host topology. It does not replace the existing Chromium Browser E2E journey and does not constitute performance, penetration, disaster-recovery, or multi-host testing.

## Current limitations

Before a public release, LifeLenz still requires the planned hardening milestone. Current deployment limitations include:

- single API instance because SQLite is the active durable backend;
- no automated backup or restore workflow;
- no encryption-at-rest implementation;
- no hosted secret-manager integration in this repository;
- no bundled TLS termination;
- no formal production monitoring or alerting integration;
- no rate limiting or abuse-control layer;
- no claim of regulatory compliance or medical-device readiness.

The deployment foundation is deliberately conservative: it makes the existing MVP reproducible in a production-shaped runtime without overstating operational maturity.
