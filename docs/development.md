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

1. Verify the repository, all origin fetch/push URLs, linked worktrees, branch, HEAD, and
   clean tracked/untracked/index state. Preserve existing branches and work.
2. Fetch `origin/main` and compare its SHA with the task's reviewed base. Stop on a mismatch.
3. Create a fresh, purpose-specific feature branch with **`--no-track`** from that verified
   `origin/main`; the prior clean checkout may be `main` or an older feature branch.
4. Confirm the new branch, starting SHA, and **absent upstream** before implementation.
5. Implement the scope, tests, and documentation, then run the relevant local checks.
6. Review the complete diff and `git diff --check`; stage only intended paths and run
   `git diff --cached --check`. When working with an agent, stop staged for Jervis's review:
   the agent must not commit, push, or publish the branch.
7. Immediately before committing or pushing, recheck the current branch and upstream. Jervis
   commits reviewed changes in GitHub Desktop, then uses **Publish branch** for first publication.
8. Confirm the published branch tracks `origin/<same-feature-name>`, then open a PR describing
   scope, validation, and limitations. Later pushes must keep that same-named upstream.
9. Merge through GitHub only after the required PR reviews/checks succeed, using the repository's
   squash workflow. Local commits and direct pushes on `main` are not the release workflow.

For example, after confirming that `feature/purpose` does not already exist locally/remotely:

```powershell
git status --short --untracked-files=all
git remote get-url --all origin
git remote get-url --push --all origin
git worktree list --porcelain
git fetch origin main
git rev-parse origin/main
# Compare the fetched SHA with the reviewed task base before continuing.
git switch --no-track -c feature/purpose origin/main
git branch --show-current
git rev-parse HEAD
git for-each-ref --format="%(upstream)" refs/heads/feature/purpose
```

The final command must print an empty value for a newly created branch. Never accept
`origin/main` as a feature branch's upstream. Stop if any command fails or the observed branch,
base, or upstream differs from the intended state.

Immediately before using GitHub Desktop to commit/push, run:

```powershell
git branch --show-current
git for-each-ref --format="%(upstream)" refs/heads/feature/purpose
git status --short --untracked-files=all
git diff --cached --check
```

The current branch must be the reviewed feature branch. Its upstream must be absent before
first publication or `refs/remotes/origin/feature/purpose` afterward. After **Publish branch**,
confirm the actual upstream rather than inferring it from the local branch label:

```powershell
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'
```

Expected output is `origin/feature/purpose`. If it points to `main` or another branch, stop;
do not push to test the configuration. After checking intent, use `git branch --unset-upstream`
and publish to the same-named remote feature branch. If that branch already exists, verify it
before explicitly setting the upstream with `git branch --set-upstream-to=origin/feature/purpose`.
These are deliberate corrections; the installer never changes existing upstreams.

Do not rewrite or discard another contributor's local changes to prepare a branch. Stop and
resolve ownership or scope before proceeding when the working tree is unexpectedly dirty.

## Opt-in local Git guards

Install the [repository hooks](../.githooks/) separately in each clone after review, from its
root or any subdirectory, with Python 3.13 and Git available:

```powershell
python scripts/install_git_guards.py
python scripts/install_git_guards.py --check
```

From a subdirectory, adjust the script's relative path (for example,
`python ../scripts/install_git_guards.py --check` from `docs/`). The
[installer](../scripts/install_git_guards.py) resolves the target repository from the caller's
working directory, including paths with spaces, and requires tracked, executable, LF hook files.
It sets only clone-local configuration:

| Setting | Value | Effect |
| --- | --- | --- |
| `core.hooksPath` | `.githooks` | Enables the repository's pre-commit and pre-push guards. |
| `branch.autoSetupMerge` | `simple` | Automatic tracking is limited to same-named remote branches; still use explicit `--no-track` when creating a feature branch. |
| `push.default` | `simple` | Ordinary pushes use the same-named branch; explicit refspecs are still checked by the hook. |

Before installation, record any existing local values with `git config --local --get-all <key>`
for each setting above; an absent key returns nonzero. Successful installation reports its local
settings. Repeating it is idempotent. `--check` is read-only and returns nonzero for incomplete,
overridden, conflicting, missing, or modified guard setups. No global/system configuration or
existing upstream is changed. Linked worktrees share clone-local configuration; check each
worktree's tracked hook files and branch state before use.

The installer refuses to displace another effective `core.hooksPath` or active default-directory
hooks. Inspect `git config --show-origin --get core.hooksPath` and the existing hook setup,
then reconcile ownership manually; it does not chain, rename, delete, or overwrite unrelated
hooks. Prerequisites are checked before writes, and a failed configuration installation restores
the settings changed by that invocation to their previous local presence/values. Any rollback
failure is reported explicitly and requires manual reconciliation before retrying.

The hooks use POSIX `sh` and Git, without Python, an activated environment, PowerShell, credentials,
or network calls. They are intended to run when GitHub Desktop invokes Git's normal commit/push
hooks; Desktop UI execution still requires a separate manual check on the installed client.

- **Commit rejection:** local commits on `main`, detached HEAD, or a feature branch with a
  differently named upstream are blocked. Switch to the intended feature branch and correct
  an unintended upstream before retrying; first commits with no upstream are supported.
- **Push rejection:** every update/deletion of remote `main` is blocked, regardless of the
  remote or source spelling. Branch updates must come from the checked-out feature branch's
  current HEAD, target the same-named branch, and have no mismatched configured upstream.
  A mixed push with any invalid update is rejected as a whole. Explicit `HEAD` publication to
  the correct branch is supported. Non-main branch deletion is permitted as an explicit
  operation, and same-named lightweight/annotated tag pushes remain supported. Branch/tag
  confusion and malformed hook input are rejected.

Local hooks are bypassable and are **not server-side protection**. The independent safeguard is
an active GitHub ruleset for `main` requiring PRs, two approvals, required checks, and appropriate
bypass restrictions. This tooling neither configures nor asserts that such a ruleset already
exists or is enforced. GitHub-hosted squash merges are unaffected by local commit hooks.

### Hosted Git guard validation

The [CI workflow](../.github/workflows/ci.yml) adds an independent **Git Guards (Windows)**
job on Windows Server 2025 (`windows-2025`) with Python 3.13 and native PowerShell Core.
It runs the existing guard suite from the real repository root on every CI event: pull
requests, pushes to `main`, and manual runs. Existing Linux full-test, coverage, and
security-invariant jobs retain coverage of the same suite, including POSIX-specific
filesystem executability checks.

The Windows job exercises command-line Git and installer behavior using isolated local
repositories/remotes, including rollback, commit/push rejection, and normal feature/tag
operations. The actual-repository regression also checks the source checkout's index entries
for committed hook mode `100755`. Windows validation does not establish POSIX filesystem
execute-bit enforcement.

Hosted tests do not repair source hook modes or activate guards in the real runner checkout;
installation remains confined to synthetic repositories. Developer installation remains opt-in
per clone. GitHub Desktop UI execution is still a manual check: automated Windows CLI testing
is not a Desktop UI test. Workflow success also does not configure or establish server-side
`main` protection.

The new hosted Windows result remains pending until the eventual PR's job actually passes.
Local results do not substitute for it; all existing hosted gates and the new Windows job
must pass before merge.

### Uninstall and recovery

Inspect the local/effective settings before changing them:

```powershell
git config --show-origin --get core.hooksPath
git config --local --get-all core.hooksPath
git config --local --get-all branch.autoSetupMerge
git config --local --get-all push.default
```

Only after confirming that the local `core.hooksPath` still resolves to this clone's `.githooks`,
disable that local setting with `git config --local --unset-all core.hooksPath`. This restores
Git's effective fallback, which may be a global hook path or default-directory hooks; inspect it.
Do not remove a newer, unrelated hook configuration. Restore `branch.autoSetupMerge` and
`push.default` to the values recorded before installation, or unset their local keys if they
were previously absent. Do not delete any hook files, modify global/system settings, change
upstreams, or rewrite remote history as part of uninstall. Reinstall only after resolving any
reported hook conflict. This commit's development/tests never activate the real checkout's hooks.

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
