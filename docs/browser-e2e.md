# Browser end-to-end validation

LifeLenz includes one real-browser MVP journey that runs against a live FastAPI process, an isolated
SQLite database, and the built Vite web application served through `vite preview`. Chromium is driven
with Playwright. The test uses only synthetic account and wellness data.

The journey validates these browser-visible boundaries in sequence:

1. account registration
2. login and protected routing
3. first-time wellness-profile onboarding
4. hydration record creation
5. full-history correction
6. deliberate record deletion
7. CSV v1 validation and explicit import
8. dashboard summary refresh from persisted data
9. user-defined wellness-goal creation
10. logout and protected-route redirection

The E2E harness deliberately does not replace the unit, API, persistence, security, or component test
suites. It verifies that their boundaries compose correctly in a real browser.

## E2E-only dependency

Playwright is pinned separately in `tests/e2e/requirements.txt`. It is not part of the normal
`lifelenz-ai` package dependencies because browser automation is a CI/development concern rather than
a runtime requirement.

Install it in an activated Python 3.13 development environment with:

```powershell
python -m pip install -r tests/e2e/requirements.txt
python -m playwright install chromium
```

## Local run

Use a fresh disposable SQLite path. Never point the E2E journey at a real wellness database. Generate
E2E-only credentials at runtime instead of committing deterministic credential values.

Start the API in one terminal:

```powershell
$env:LIFELENZ_ENVIRONMENT = "e2e"
$env:LIFELENZ_DATABASE_PATH = "$env:TEMP\lifelenz-browser-e2e.db"
$env:LIFELENZ_JWT_SECRET = python -c 'import secrets; print(secrets.token_urlsafe(48))'
$env:LIFELENZ_DOCS_ENABLED = "false"
python -m uvicorn lifelenz.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Build and preview the web app in another terminal:

```powershell
cd web
npm ci
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

The Vite preview server proxies `/api` to the local backend just like the development server, so the
browser exercises same-origin requests without adding a CORS exception.

Run the journey from the repository root in a third terminal:

```powershell
$env:LIFELENZ_E2E_BASE_URL = "http://127.0.0.1:4173"
$env:LIFELENZ_E2E_ACCOUNT_PASSWORD = python -c 'import secrets; print(secrets.token_urlsafe(32))'
python tests/e2e/browser_journey.py
```

The script uses a deterministic synthetic email address but requires the account password from
`LIFELENZ_E2E_ACCOUNT_PASSWORD`. A fresh E2E database is therefore still required for each run. A
failed run writes a screenshot to `.e2e-artifacts` unless `LIFELENZ_E2E_ARTIFACT_DIR` points to another
temporary directory.

## CI contract

The `Browser E2E` CI job uses Python 3.13 and Node 22. It generates an ephemeral signing secret and
synthetic account password for each run, installs locked web dependencies, builds the production Vite
bundle, installs the pinned Playwright Chromium runtime, launches the API and preview server, waits for
both processes to become reachable, and then executes the browser journey. No E2E credential value is
stored in the repository. Service logs are printed when startup or the journey fails.

This is a high-value MVP journey, not exhaustive browser coverage, cross-browser certification,
performance testing, penetration testing, or production-deployment validation.
