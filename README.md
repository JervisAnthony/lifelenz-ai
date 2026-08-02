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
metadata, and reusable validation. The first concrete domain record captures completed
sleep sessions with validated durations and optional stage, quality, and interruption data.
Repositories, analytics, insight generation, data ingestion, and user interfaces do not yet
exist.

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
