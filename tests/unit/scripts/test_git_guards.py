"""Exercise opt-in guards with real Git commands and isolated local remotes."""

import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
INSTALLER = ROOT / "scripts" / "install_git_guards.py"
FEATURE = "feature/guard-test"
KEYS = ("core.hooksPath", "branch.autoSetupMerge", "push.default")


class Repository:
    def __init__(self, root: Path, remote: Path) -> None:
        self.root = root
        self.remote = remote

    def git(self, *args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=False
        )
        if success:
            assert result.returncode == 0, result.stderr
        return result

    def ref(self, name: str = "HEAD", *, remote: bool = False) -> str:
        args = ("--git-dir", str(self.remote)) if remote else ()
        return self.git(*args, "rev-parse", "--verify", name).stdout.strip()

    def remote_refs(self) -> str:
        return self.git("--git-dir", str(self.remote), "show-ref").stdout

    def install(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "scripts/install_git_guards.py"), *args],
            cwd=cwd or self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def commit(self) -> str:
        self.git("commit", "--allow-empty", "-m", "Synthetic guard test")
        return self.ref()


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repository:
    for key in tuple(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_ATTR_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    root = tmp_path / "working clone with spaces"
    remote = tmp_path / "synthetic remote.git"
    root.mkdir()
    repo = Repository(root, remote)
    repo.git("-c", "init.templateDir=", "init", "--initial-branch=main")
    for key, value in (
        ("user.name", "Synthetic Guard Tester"),
        ("user.email", "guard-tests@example.invalid"),
        ("user.useConfigOnly", "true"),
        ("commit.gpgsign", "false"),
        ("tag.gpgsign", "false"),
        ("core.autocrlf", "false"),
    ):
        repo.git("config", "--local", key, value)
    for relative in (
        ".githooks/pre-commit",
        ".githooks/pre-push",
        ".gitattributes",
        "scripts/install_git_guards.py",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
        if relative.startswith(".githooks/"):
            destination.chmod(0o755)
    repo.git("add", "--", ".")
    repo.git("update-index", "--chmod=+x", ".githooks/pre-commit", ".githooks/pre-push")
    repo.commit()
    repo.git("-c", "init.templateDir=", "init", "--bare", "--initial-branch=main", str(remote))
    repo.git("remote", "add", "origin", str(remote))
    repo.git("push", "origin", "main")
    repo.git("switch", "--no-track", "-c", FEATURE)
    return repo


@pytest.fixture
def guarded(repository: Repository) -> Repository:
    result = repository.install()
    assert result.returncode == 0, result.stderr
    return repository


def assert_push_rejected(repo: Repository, *refspecs: str, destination: str = "origin") -> None:
    before = repo.remote_refs()
    result = repo.git("push", destination, *refspecs, success=False)
    assert result.returncode != 0
    assert "LifeLenz Git guard:" in result.stderr
    assert repo.remote_refs() == before


def test_install_check_idempotence_and_subdirectory(repository: Repository) -> None:
    repo = repository
    config = repo.root / ".git/config"
    before = config.read_bytes()
    assert repo.install("--check").returncode != 0
    assert config.read_bytes() == before
    subdirectory = repo.root / "scripts"
    result = repo.install(cwd=subdirectory)
    assert result.returncode == 0, result.stderr
    assert "clone-local" in result.stdout
    assert repo.git("config", "--local", "--get", KEYS[0]).stdout.strip() == ".githooks"
    for key in KEYS[1:]:
        assert repo.git("config", "--local", "--get", key).stdout.strip() == "simple"
    installed = config.read_bytes()
    assert repo.install("--check", cwd=subdirectory).returncode == 0
    assert repo.install().returncode == 0
    assert config.read_bytes() == installed
    assert not repo.git(
        "for-each-ref", "--format=%(upstream)", f"refs/heads/{FEATURE}"
    ).stdout.strip()


@pytest.mark.parametrize("scope", ["local", "global"])
def test_conflicting_hook_path_preserved(
    repository: Repository, monkeypatch: pytest.MonkeyPatch, scope: str
) -> None:
    repo = repository
    custom = repo.root / "other hooks"
    custom.mkdir()
    hook = custom / "pre-commit"
    hook.write_bytes(b"#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    if scope == "global":
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(repo.root.parent / "isolated global config"))
    repo.git("config", f"--{scope}", "core.hooksPath", str(custom))
    before = (repo.root / ".git/config").read_bytes()
    for args in ((), ("--check",)):
        result = repo.install(*args)
        assert result.returncode != 0
        assert "core.hooksPath" in result.stderr
        assert (repo.root / ".git/config").read_bytes() == before
        assert hook.read_bytes() == b"#!/bin/sh\nexit 0\n"
    assert repo.git("config", "--get", "core.hooksPath").stdout.strip() == str(custom)


def test_active_default_hook_preserved(repository: Repository) -> None:
    repo = repository
    hook = repo.root / ".git/hooks/pre-commit"
    hook.parent.mkdir(exist_ok=True)
    hook.write_bytes(b"#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    before = (repo.root / ".git/config").read_bytes()
    result = repo.install()
    assert result.returncode != 0
    assert "pre-commit" in result.stderr
    assert hook.read_bytes() == b"#!/bin/sh\nexit 0\n"
    assert (repo.root / ".git/config").read_bytes() == before


def test_identical_absolute_hook_path_is_not_a_conflict(repository: Repository) -> None:
    repo = repository
    path = str(repo.root / ".githooks")
    repo.git("config", "--local", "core.hooksPath", path)
    assert repo.install().returncode == 0
    assert repo.install("--check").returncode == 0
    assert repo.git("config", "--local", "--get", "core.hooksPath").stdout.strip() == path


@pytest.mark.parametrize("fault", ["missing", "crlf", "untracked", "wrong-mode"])
def test_prerequisites_fail_before_config_writes(repository: Repository, fault: str) -> None:
    repo = repository
    hook = repo.root / ".githooks/pre-push"
    if fault == "missing":
        hook.unlink()
    elif fault == "crlf":
        hook.write_bytes(hook.read_bytes().replace(b"\n", b"\r\n"))
    elif fault == "untracked":
        repo.git("rm", "--cached", "--", ".githooks/pre-push")
    else:
        repo.git("update-index", "--chmod=-x", ".githooks/pre-push")
    before = (repo.root / ".git/config").read_bytes()
    assert repo.install().returncode != 0
    assert (repo.root / ".git/config").read_bytes() == before


def test_failed_later_write_restores_prior_local_values(
    repository: Repository, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = repository
    repo.git("config", "--local", "--add", "branch.autoSetupMerge", "false")
    repo.git("config", "--local", "--add", "branch.autoSetupMerge", "true")
    repo.git("config", "--local", "push.default", "current")
    before = {
        key: repo.git("config", "--local", "--get-all", key, success=False).stdout for key in KEYS
    }
    namespace = runpy.run_path(str(INSTALLER))
    main = namespace["main"]
    real_git = main.__globals__["_git"]
    error_type = namespace["GuardInstallError"]
    attempted = []

    def fail_later(root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess:
        if args[:3] == ("config", "--local", "--replace-all"):
            attempted.append(args[3])
            if args[3] == "push.default":
                raise error_type("Synthetic later configuration write failed")
        return real_git(root, *args, **kwargs)

    monkeypatch.setitem(main.__globals__, "_git", fail_later)
    monkeypatch.chdir(repo.root)
    assert main([]) == 1
    assert attempted == list(KEYS)
    assert "prior local settings restored" in capsys.readouterr().err
    after = {
        key: repo.git("config", "--local", "--get-all", key, success=False).stdout for key in KEYS
    }
    assert before == after


def test_effective_override_causes_rollback(
    repository: Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "push.default")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "current")
    result = repo.install()
    assert result.returncode != 0
    for key in KEYS:
        assert repo.git("config", "--local", "--get", key, success=False).returncode == 1


def test_installed_auto_tracking_avoids_main_upstream(guarded: Repository) -> None:
    repo = guarded
    repo.git("switch", "-c", "feature/automatic-tracking", "origin/main")
    assert repo.git("rev-parse", "--abbrev-ref", "@{upstream}", success=False).returncode != 0
    repo.commit()


def test_check_reports_override_without_writes(
    guarded: Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = guarded
    before = (repo.root / ".git/config").read_bytes()
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "push.default")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "current")
    assert repo.install("--check").returncode != 0
    assert (repo.root / ".git/config").read_bytes() == before


def test_no_upstream_then_same_named_upstream_commit_and_push(guarded: Repository) -> None:
    repo = guarded
    first = repo.commit()
    repo.git("push", "--set-upstream", "origin", FEATURE)
    assert repo.ref(f"refs/heads/{FEATURE}", remote=True) == first
    assert (
        repo.git("rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip() == f"origin/{FEATURE}"
    )
    second = repo.commit()
    repo.git("push")
    assert repo.ref(f"refs/heads/{FEATURE}", remote=True) == second


@pytest.mark.parametrize("merge", ["refs/heads/main", "refs/heads/another-feature"])
def test_bad_upstream_blocks_commit_and_explicit_push(guarded: Repository, merge: str) -> None:
    repo = guarded
    repo.commit()
    repo.git("config", "--local", f"branch.{FEATURE}.remote", "origin")
    repo.git("config", "--local", f"branch.{FEATURE}.merge", merge)
    before = repo.ref()
    result = repo.git("commit", "--allow-empty", "-m", "Forbidden", success=False)
    assert result.returncode != 0 and "Upstream branch mismatch" in result.stderr
    assert repo.ref() == before
    assert_push_rejected(repo, f"HEAD:refs/heads/{FEATURE}")


@pytest.mark.parametrize("checkout", ["main", "--detach"])
def test_main_and_detached_commits_and_branch_pushes_blocked(
    guarded: Repository, checkout: str
) -> None:
    repo = guarded
    feature_head = repo.commit()
    if checkout == "main":
        repo.git("update-ref", "refs/heads/main", feature_head)
    repo.git("switch", checkout)
    before = repo.ref()
    result = repo.git("commit", "--allow-empty", "-m", "Forbidden", success=False)
    assert result.returncode != 0 and "LifeLenz Git guard:" in result.stderr
    assert repo.ref() == before
    assert_push_rejected(repo, f"{FEATURE}:refs/heads/{FEATURE}")
    if checkout == "main":
        assert_push_rejected(repo, "main:refs/heads/main")


@pytest.mark.parametrize("source", [FEATURE, "HEAD"])
def test_direct_main_updates_and_different_destination_blocked(
    guarded: Repository, source: str
) -> None:
    repo = guarded
    repo.commit()
    assert_push_rejected(repo, f"{source}:refs/heads/main")
    assert_push_rejected(repo, f"{source}:refs/heads/other-feature")


@pytest.mark.parametrize("source", ["HEAD", "object-id"])
def test_explicit_current_head_publication(guarded: Repository, source: str) -> None:
    repo = guarded
    head = repo.commit()
    repo.git("push", "origin", f"{head if source == 'object-id' else source}:refs/heads/{FEATURE}")
    assert repo.ref(f"refs/heads/{FEATURE}", remote=True) == head


def test_other_named_branch_at_same_commit_rejected(guarded: Repository) -> None:
    repo = guarded
    repo.commit()
    repo.git("branch", "other-feature")
    assert_push_rejected(repo, f"other-feature:refs/heads/{FEATURE}")


def test_old_commit_cannot_replace_current_branch_head(guarded: Repository) -> None:
    repo = guarded
    repo.commit()
    assert_push_rejected(repo, f"HEAD~1:refs/heads/{FEATURE}")


def test_main_blocked_through_other_remote_and_direct_path(guarded: Repository) -> None:
    repo = guarded
    repo.commit()
    repo.git("remote", "add", "other-remote", str(repo.remote))
    assert_push_rejected(repo, "HEAD:refs/heads/main", destination="other-remote")
    assert_push_rejected(repo, "HEAD:refs/heads/main", destination=str(repo.remote))


def test_mixed_push_changes_no_remote_refs(guarded: Repository) -> None:
    repo = guarded
    repo.commit()
    assert_push_rejected(repo, f"{FEATURE}:{FEATURE}", "HEAD:refs/heads/main")


@pytest.mark.parametrize("checkout", ["main", "--detach"])
def test_non_main_deletion_allowed_and_main_deletion_rejected(
    guarded: Repository, checkout: str
) -> None:
    repo = guarded
    repo.commit()
    repo.git("push", "origin", FEATURE)
    repo.git("switch", checkout)
    repo.git("push", "origin", f":refs/heads/{FEATURE}")
    assert (
        repo.git(
            "--git-dir",
            str(repo.remote),
            "show-ref",
            "--verify",
            f"refs/heads/{FEATURE}",
            success=False,
        ).returncode
        != 0
    )
    assert_push_rejected(repo, ":refs/heads/main")


@pytest.mark.parametrize("annotated", [False, True])
def test_same_named_synthetic_tags_supported(guarded: Repository, annotated: bool) -> None:
    repo = guarded
    repo.git("switch", "--detach")
    args = ("-a", "-m", "Synthetic annotation") if annotated else ()
    repo.git("tag", *args, "guard-test-tag")
    repo.git("push", "origin", "refs/tags/guard-test-tag:refs/tags/guard-test-tag")
    assert repo.ref("refs/tags/guard-test-tag", remote=True) == repo.ref("refs/tags/guard-test-tag")


def test_branch_tag_ref_confusion_blocked(guarded: Repository) -> None:
    repo = guarded
    repo.commit()
    repo.git("tag", "guard-test-tag")
    assert_push_rejected(repo, "HEAD:refs/tags/not-a-branch")
    assert_push_rejected(repo, f"refs/tags/guard-test-tag:refs/heads/{FEATURE}")
    assert_push_rejected(repo, "refs/tags/guard-test-tag:refs/tags/renamed-tag")


def posix_shell() -> str:
    shell = shutil.which("sh")
    if shell:
        return shell
    git = shutil.which("git")
    assert git, "Git is required for guard tests"
    for parent in Path(git).resolve().parents:
        candidate = parent / "usr/bin/sh.exe"
        if candidate.is_file():
            return str(candidate)
    pytest.fail("POSIX sh unavailable: direct malformed-input and shell-syntax checks cannot run")


@pytest.mark.parametrize(
    "fault", ["short", "extra", "oid", "zero", "destination", "deletion", "trailing"]
)
def test_malformed_push_input_rejected(guarded: Repository, fault: str) -> None:
    repo = guarded
    head = repo.ref()
    zero = "0" * len(head)
    valid = f"refs/heads/{FEATURE} {head} refs/heads/{FEATURE} {zero}\n"
    inputs = {
        "short": f"HEAD {head}\n",
        "extra": valid.rstrip() + " extra\n",
        "oid": valid.replace(head, "invalid"),
        "zero": valid.replace(head, zero),
        "destination": valid.replace(f"refs/heads/{FEATURE} {zero}", f"invalid {zero}"),
        "deletion": f"(delete) {head} refs/heads/{FEATURE} {head}\n",
        "trailing": valid + "incomplete",
    }
    result = subprocess.run(
        [posix_shell(), str(repo.root / ".githooks/pre-push"), "origin", "unused"],
        cwd=repo.root,
        input=inputs[fault],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0 and "LifeLenz Git guard:" in result.stderr


def test_hook_modes_lf_checkout_and_syntax(repository: Repository) -> None:
    repo = repository
    for name in ("pre-commit", "pre-push"):
        path = f".githooks/{name}"
        assert repo.git("ls-files", "--stage", "--", path).stdout.startswith("100755 ")
        assert repo.git("check-attr", "eol", "--", path).stdout.strip().endswith(": lf")
        repo.git("-c", "core.autocrlf=true", "checkout-index", "--force", "--", path)
        assert b"\r" not in (repo.root / path).read_bytes()
        assert os.access(repo.root / path, os.X_OK)
        result = subprocess.run(
            [posix_shell(), "-n", str(repo.root / path)], capture_output=True, check=False
        )
        assert result.returncode == 0, result.stderr
    assert (
        repo.git("check-attr", "eol", "--", "unrelated.py").stdout.strip().endswith(": unspecified")
    )
