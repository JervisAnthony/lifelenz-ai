import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[3] / "scripts" / "check_security_invariants.py"


def run_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_clean_production_tree_passes(tmp_path: Path) -> None:
    source = tmp_path / "src" / "lifelenz"
    source.mkdir(parents=True)
    (source / "safe.py").write_text("value = 1\n", encoding="utf-8")
    result = run_check(tmp_path)
    assert result.returncode == 0
    assert result.stdout == "Security invariants passed.\n"


def test_unsafe_source_and_artifacts_are_reported_without_secret_content(tmp_path: Path) -> None:
    source = tmp_path / "src" / "lifelenz"
    source.mkdir(parents=True)
    secret = "extremely-sensitive-value"
    (source / "unsafe.py").write_text(
        "import pickle\n"
        f"secret = {secret!r}\n"
        "eval('1 + 1')\n"
        "options = {'verify_signature': False}\n"
        "schema = 'CREATE TABLE accounts (password TEXT)'\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text("SECRET=" + secret, encoding="utf-8")
    (tmp_path / "local.sqlite3").write_bytes(b"SQLite format marker")
    (tmp_path / "private.pem").write_text(
        "-----BEGIN " + "PRIVATE KEY-----\n" + secret,
        encoding="utf-8",
    )
    (tmp_path / "tokens.txt").write_text(
        "Bearer " + "eyJheader.payload.signature", encoding="utf-8"
    )
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert "dynamic-eval" in result.stdout
    assert "pickle-import" in result.stdout
    assert "disabled-jwt-verification" in result.stdout
    assert "plaintext-password-column" in result.stdout
    assert "tracked-environment-file" in result.stdout
    assert "tracked-database-file" in result.stdout
    assert "private-key-material" in result.stdout
    assert "bearer-token-fixture" in result.stdout
    assert secret not in result.stdout
    assert secret not in result.stderr


def test_docs_and_tests_are_not_subject_to_production_code_rules(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs" / "example.txt").write_text("eval('documented only')", encoding="utf-8")
    (tmp_path / "tests" / "fixture.py").write_text("import pickle\n", encoding="utf-8")
    result = run_check(tmp_path)
    assert result.returncode == 0


def test_dynamic_jwt_algorithm_is_rejected_but_fixed_module_constant_is_allowed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src" / "lifelenz"
    source.mkdir(parents=True)
    (source / "safe_token.py").write_text(
        "ALGORITHM = 'HS256'\n"
        "def decode(jwt, token, secret):\n"
        "    return jwt.decode(token, secret, algorithms=[ALGORITHM])\n",
        encoding="utf-8",
    )
    assert run_check(tmp_path).returncode == 0
    (source / "unsafe_token.py").write_text(
        "def decode(jwt, token, secret, algorithm):\n"
        "    return jwt.decode(token, secret, algorithms=[algorithm])\n",
        encoding="utf-8",
    )
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert "jwt-algorithm-not-fixed-hs256" in result.stdout
