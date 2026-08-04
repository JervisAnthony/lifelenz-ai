# LifeLenz-AI

LifeLenz-AI is an early-stage personal wellness intelligence project. It is intended to
help people organize longitudinal lifestyle data, understand patterns relative to their
own baselines, and receive transparent, non-diagnostic observations.

The core value proposition is context: instead of treating sleep, activity, hydration,
mood, energy, and stress as isolated readings, LifeLenz-AI aims to make changes and
co-occurring patterns understandable over time. Observations will use conservative
language and expose the data and rules behind them.

## Project status

LifeLenz-AI is at version 0.1.0 and in the foundation stage. The repository currently
contains an installable `lifelenz` Python package, development tooling, and a controlled
taxonomy for wellness categories, metrics, units, data sources, confidence, and insight
severity. Shared domain foundations provide record identifiers, aware time ranges, common
metadata, and reusable validation. Concrete domain records capture completed sleep sessions,
daily activity totals, completed workouts, hydration events, meal nutrition, and daily
nutrition summaries, neutral body measurements, and subjective mood, energy, stress, and
optional motivation check-ins with explicitly validated values. They also capture menstrual
bleeding observations, user-supplied menstrual-cycle date ranges, and privacy-conscious
wellness profiles with tracking preferences, plus user-defined wellness goals. Framework-independent
repository contracts define storage-neutral operations for profiles, goals, and wellness records.
Deterministic in-memory implementations support tests and early application development; they are
process-local, non-durable, and lose all data when the process ends. Database and filesystem
persistence and serialization do not yet exist. Framework-independent application services
coordinate repositories, enforce profile existence for profile-owned operations, and translate
expected missing-entity failures. The profile, goal, and record services do not calculate analytics
or goal progress. Deterministic
personal-baseline analytics summarize supported canonical metrics from a person's own recorded
observations using count, mean, median, minimum, maximum, and population standard deviation.
Baselines preserve canonical units and use record metadata timestamps; they provide no medical
interpretation, population comparison, recommended target, or health classification. Deterministic
basic trend analytics report first and last values, absolute and percentage change when defined,
least-squares slope per day, and neutral increasing, decreasing, or stable direction for supported
canonical metrics. Optional time ranges use metadata timestamps. Direction is purely mathematical:
increasing does not mean healthy, decreasing does not mean unhealthy, and trends neither predict
future values nor recommend actions. A framework-independent wellness-summary workflow now requires
an existing profile, reads its stored records with optional metadata-time filtering, and produces one
structured canonical-unit summary per supported metric. Metrics with at least one sample include a
baseline, while metrics with at least two samples also include a trend. The result is structured data,
not user-facing medical or coaching text. Durable and database persistence, serialization,
authentication and user-ownership accounts, goal progress, correlations, recommendations,
predictions, import workflows, REST APIs, web and mobile applications (including Android and iOS),
and medical decision support do not yet exist.

The planned MVP capability areas are:

- Structured records for sleep, activity, hydration, basic nutrition, body measurements,
  mood, energy, and stress
- Personal profiles and goals
- Personal-baseline analytics and trend summaries
- Deterministic, explainable wellness observations
- Typed wellness summaries

Manual entry and structured-data imports are planned for the MVP. Direct wearable
connections and broad wellness-platform integrations are future work, not current
capabilities.

## Architecture

The first development phase uses a layered, standard-library-first design. Domain types
and validation form the base; repository abstractions manage records; pure analytics
calculate baselines and trends; deterministic rules produce explainable observations; and
services coordinate these parts into summaries. Packages for these layers will be added
only with their first working capability.

See [Architecture](docs/architecture.md) for the intended dependency direction and design
decisions.

## Development setup

LifeLenz-AI requires Python 3.13 or later. In Windows PowerShell, create and activate a
virtual environment, then install the package with development dependencies:

```powershell
py -3.13 -m venv lifelenz-env
.\lifelenz-env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the test suite, lint checks, and formatting check:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Apply the configured formatter when needed:

```powershell
python -m ruff format .
```

More contributor guidance is available in [Development standards](docs/development.md).

## Documentation

- [Product scope](docs/product-scope.md) defines the intended users, MVP, non-goals, and
  safety boundary.
- [Architecture](docs/architecture.md) describes the intended first-phase design.
- [Development standards](docs/development.md) defines the contributor workflow and
  engineering expectations.
- [Roadmap](docs/roadmap.md) separates near-term milestones from future work.

## Wellness and medical disclaimer

LifeLenz-AI is intended for general wellness reflection and education. It is not a medical
device and is not intended to diagnose, predict, treat, or prevent disease; recommend
medications or treatments; provide emergency guidance; or replace qualified medical
advice. Users should consult an appropriate healthcare professional about medical concerns
and contact local emergency services when urgent help is needed.

## License

LifeLenz-AI is available under the [MIT License](LICENSE).
