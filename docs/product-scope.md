# Product scope

## Product vision and intended users

LifeLenz-AI helps people organize personal lifestyle records and inspect descriptive patterns
in their own data. MVP1 is a beta-stage general-wellness product for manual tracking, deliberate
CSV imports, personal baselines, and self-reflection. The longer-term vision includes richer
explainable observations across longitudinal data; those capabilities require separate design
and evaluation and are not all implemented.

Initial users include people who track habits, consolidate structured records, or want to
review personal trends. MVP1 does not promise every device, vendor export, or tracking workflow.

## Implemented MVP1 capabilities

| Capability | Implemented behavior | Boundary |
| --- | --- | --- |
| Accounts | Registration, login, current-user restoration, and protected browser routes. | Registration creates an account only; no password reset, email verification, MFA, or refresh tokens. |
| Profile onboarding and preferences | Separate creation of one primary owned profile; review and replacement of display name, time zone, measurement system, week start, and tracked areas. | Presentation/grouping preferences are stored; summary unit conversion and profile-based calendar grouping are not implemented. |
| Manual records | Entry, recent/full history, record-type/date filtering, correction, and confirmed deletion for all ten types below. | Corrections retain identity, type, and original source; record deletion is not account deletion or complete data export. |
| CSV v1 | Local file selection, authenticated validation, issue/duplicate review, and explicit atomic commit for six categories. | Exact versioned schema; no universal vendor-export compatibility. |
| User-defined goals | List, create, read, fully replace, change status, and confirm deletion. | Targets, direction, dates, and status are user-supplied; progress and achievement are not evaluated. |
| Personal analytics | Canonical samples, descriptive baselines, mathematical trends, and typed structured summaries. | No health scoring, target comparison, cross-metric correlation, prediction, recommendation, or narrative report. |
| Dashboard | Server-derived coverage, baseline ranges with mean/median markers, and trend details; explicit empty/error states. | No historical sample-series visualization contract or invented time-series points. |

The [browser routes](../web/src/app/router.tsx) expose Home (`/app`), Records (`/app/records`),
CSV import (`/app/records/import`), Goals (`/app/goals`), and Profile (`/app/profile`) after
authentication. Profile onboarding is required before records, goals, imports, and summaries.

### Records and CSV categories

The [record contracts](../src/lifelenz/repositories/contracts.py) and
[manual form registry](../web/src/records/recordEntryRegistry.ts) cover:

| Record type | Manual entry/history/correction/deletion | CSV v1 |
| --- | --- | --- |
| Sleep | Yes | Yes |
| Daily Activity | Yes | Yes |
| Workout | Yes | No |
| Hydration | Yes | Yes |
| Meal | Yes | No |
| Daily Nutrition | Yes | Yes |
| Body Measurement | Yes | Yes |
| Subjective Wellness Check-In | Yes | Yes |
| Menstrual Bleeding | Yes | No |
| Menstrual Cycle | Yes | No |

Records preserve explicitly supplied values, aware metadata timestamps, and source provenance.
Check-ins capture mood, energy, stress, and optional motivation; cycle dates remain user-supplied,
without cycle or fertility prediction. Date filtering uses metadata timestamps with
start-inclusive/end-exclusive bounds. Browser-local datetimes are sent with an explicit offset;
the saved profile time zone does not override that browser-local input behavior.

[CSV schema v1](csv-import-v1.md) defines exact headers and supported normalization. Each file
contains one category. Validation never writes records; any validation issue prevents commit.
Semantic duplicates against existing owned records or earlier file rows are skipped separately
from errors. Commit saves all ready rows in one atomic batch: storage failure leaves prior data
unchanged and returns HTTP 503. See the
[authenticated import service](../src/lifelenz/application/authenticated_imports.py) and
[architecture flow](architecture.md#csv-validate-review-and-atomic-commit).

### Analytics and summaries

[Personal baselines](../src/lifelenz/analytics/baselines.py) describe a person's own recorded
samples using count, mean, median, minimum, maximum, and population standard deviation.
One sample is sufficient for a baseline, with standard deviation zero; this is not evidence
of a stable habitual range or clinical significance. At least two samples produce a
[mathematical trend](../src/lifelenz/analytics/trends.py): first/last values, absolute change,
percentage change when defined, least-squares slope per day, and neutral direction.

[Structured summaries](../src/lifelenz/application/summaries.py) assemble supported metrics in
canonical units. Meal events are excluded in favor of daily nutrition totals; menstrual records
have no direct numeric mapping. Optional motivation and other stored fields do not automatically
become analytics metrics. Samples use record metadata timestamps, without calendar aggregation
or reconciliation of overlapping daily-activity and workout observations. Summary record counts
can include records that contribute no metric. No supported observations yields an unavailable
summary and a browser empty state.

The [dashboard](../web/src/pages/DashboardPage.tsx) shows the server's summary coverage, observed
ranges, mean/median, and trend details. Successful record mutations and CSV imports invalidate
record and summary queries so later dashboard reads retrieve current data. Goals are managed
separately; marking a goal completed records the user's choice rather than measured achievement.
Stored imperial/metric and week-start preferences do not convert summaries or create weekly views.

## Privacy and security already implemented

[Authentication](../src/lifelenz/application/authentication.py) validates passwords of 12 through
256 characters; [security adapters](../src/lifelenz/security/) hash passwords with Argon2 and
issue short-lived signed HS256 bearer tokens. Validation checks signature, required claims,
issuer, audience, and expiry, then resolves the authoritative active account. An explicit
[ownership mapping](../src/lifelenz/application/ownership.py) scopes wellness operations to the
authenticated primary profile. Clients cannot choose another profile ID, and cross-account
record/goal lookups return not-found without exposing resource existence.

The browser stores its access token in `sessionStorage`; script access remains a risk. Logout
clears client authentication and query state without server-side revocation of issued tokens.
The default token lifetime is 30 minutes. There is no refresh-token rotation, password-reset,
email-verification, MFA, or social-login workflow.

[Production configuration](../src/lifelenz/api/config.py) requires disabled API docs, an absolute
SQLite path, and a signing secret of at least 48 UTF-8 bytes. The same-origin gateway applies
CSP and related browser headers. These are implemented controls, not a comprehensive security
or regulatory certification. Active SQLite storage is not encrypted by this implementation.
External HTTPS/HSTS, access policy, off-host backup encryption/retention, monitoring, incident
response, and abuse controls remain [deployment responsibilities](deployment.md#current-limitations).

Users can correct and delete individual records and goals. MVP1 does not implement account
deletion, a complete personal-data export workflow, or a comprehensive retention/erasure service.
The operator's database backup helper is not a user-facing export feature.

## Future direction and explicit non-goals

The [roadmap](roadmap.md) describes longer-term direction. Its partially implemented insight
milestone refers to structured summaries; MVP1 has no separate insight-rule engine. Future work
includes:

- automatic goal-progress evaluation, target comparison, or achievement detection;
- cross-metric correlations or observations about co-occurring patterns;
- weekly narrative reports and richer evidence-facing insight rules;
- historical time-series contracts and visualizations;
- forecasting, recommendations, ML inference, or LLM explanations;
- direct wearable integrations, selected vendor adapters, and broader export compatibility.

For example, comparing hydration against a goal, associating energy with sleep, or generating a
weekly narrative are future scenarios. The current product stores those inputs and describes
supported metrics independently. Correlations would not establish causation; causal observations
are not an implemented capability or an intended health claim.

Medical diagnosis, disease prediction, treatment or medication advice, emergency guidance,
clinical decision support, and replacing qualified medical care are explicit non-goals.
Cloud synchronization, notifications, and native mobile applications remain outside MVP1.

## Safety boundary and product principles

LifeLenz-AI supports general-wellness reflection and education. Descriptive statistics and
increasing/decreasing/stable trends do not classify health, imply causation, or recommend action.
User-defined targets are not assessed for suitability. Sparse or incomplete data must remain
visible rather than being turned into medical or coaching conclusions.

Prefer inspectable calculations, explicit ownership, minimal necessary data, conservative
language, and deliberate correction/deletion controls. Future observations must expose their
supporting evidence, period, calculation/rule, and uncertainty before more complex techniques
are adopted. These principles do not imply features beyond the implemented table above.

Medical questions belong with qualified healthcare professionals. Urgent situations require
appropriate local emergency services, not product output. Repository release validation also
does not establish public-host readiness; see [Release readiness](release-readiness.md).
