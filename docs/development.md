# Development standards

This document defines the contributor workflow and engineering expectations for the
`lifelenz` package. Documentation must be updated when an implemented capability changes
these expectations.

## Environment setup

LifeLenz-AI requires Python 3.13 or later. From the repository root in Windows PowerShell,
create a virtual environment and install the package in editable mode with development
dependencies:

```powershell
py -3.13 -m venv lifelenz-env
.\lifelenz-env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Validation commands

Run the standard test suite:

```powershell
python -m pytest
```

Measure test coverage and display missed lines when useful during review:

```powershell
python -m pytest --cov=lifelenz --cov-report=term-missing
```

Check lint rules and formatting:

```powershell
python -m ruff check .
python -m ruff format --check .
```

Apply the formatter, then inspect whitespace errors in the Git diff:

```powershell
python -m ruff format .
git diff --check
```

Run the relevant checks before requesting review. Do not weaken configuration or suppress a
failure merely to make validation pass; fix the cause or document a deliberate exception.

## Engineering standards

- Provide complete type annotations for public APIs and meaningful internal boundaries.
- Keep modules and functions small, focused, and organized around one responsibility.
- Choose clear domain names; avoid abbreviations that hide meaning.
- Document public APIs with docstrings that explain contracts, important constraints, and
  failure behavior.
- Use timezone-aware datetimes for instants and validate timezone expectations at system
  boundaries.
- Validate inputs explicitly and return or raise well-defined outcomes for invalid data.
- Produce deterministic output, including stable ordering where collections are exposed.
- Avoid hidden global mutable state; pass dependencies and configuration explicitly.
- Add tests alongside every implemented capability and bug fix.
- Write comments to explain decisions and constraints, not to restate the code.

## Testing standards

Tests should cover the behavior relevant to each capability, including:

- Representative happy paths
- Boundary values and period boundaries
- Invalid inputs and invariant violations
- Empty and insufficient datasets
- Expected failure behavior
- Deterministic ordering and repeatability
- Timezone handling, including offsets and calendar transitions where relevant

Prefer observable behavior over implementation details. Tests should make the contract easy
to understand, isolate failures, and remain deterministic. Coverage percentage is a useful
signal for untested code, but a high percentage does not replace meaningful boundary and
failure-case assertions.

## Commit standards

Use a conventional prefix that describes the primary change, for example:

- `chore`: repository or tooling maintenance
- `docs`: documentation only
- `feat`: a new user- or developer-facing capability
- `fix`: a defect correction
- `test`: test-only changes
- `refactor`: internal restructuring without a behavior change

Each commit should contain one coherent, reviewable capability. Its message should explain
the outcome in imperative language, and the committed files should not include unrelated
formatting, generated output, caches, secrets, or local environment state.

## Branch and pull-request workflow

1. Fetch the remote and update `main` with a fast-forward-only pull.
2. Confirm the working tree is clean and local `main` matches `origin/main`.
3. Create a fresh, purpose-specific feature branch.
4. Implement one coherent commit scope with its tests and documentation.
5. Run the relevant local validation commands.
6. Review `git status`, `git diff --check`, and the complete diff.
7. Commit the reviewed changes and push the feature branch.
8. Open a pull request that states the scope, validation, and known limitations.
9. Merge only after review and required checks succeed.

Do not rewrite or discard another contributor's local changes to prepare a branch. Stop and
resolve ownership or scope before proceeding when the working tree is unexpectedly dirty.

## Dependency policy

Add a dependency only when an implemented capability requires it and the standard library or
existing dependencies do not meet the need. Evaluate maintenance health, license, security,
package size, transitive dependencies, and supported Python versions. Keep version constraints
explicit and include the dependency change in the same reviewable capability.

Do not add frameworks or speculative infrastructure for roadmap items that have no current
implementation.

## Documentation discipline

Documentation must label capability status accurately:

- **Implemented** means the behavior exists in the repository and is covered by appropriate
  validation.
- **Planned** means it is within an agreed near-term scope but is not yet available.
- **Future** means it is a possible later direction whose design and delivery are not
  committed.

Avoid examples, integration lists, architecture diagrams, or product claims that imply
unfinished behavior is available. Update affected documents with the implementation that
changes their status.
