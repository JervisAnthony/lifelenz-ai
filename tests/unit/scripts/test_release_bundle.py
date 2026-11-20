import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "release_bundle.py"
BUNDLE = runpy.run_path(str(SCRIPT))
BundleError = BUNDLE["BundleError"]
package_bundle = BUNDLE["package_bundle"]
verify_bundle = BUNDLE["verify_bundle"]

NAMES = (
    "lifelenz_ai-0.1.0-py3-none-any.whl",
    "lifelenz_ai-0.1.0.tar.gz",
    "lifelenz-web-mvp1-0.1.0.tar.gz",
    "manifest.json",
    "release-evidence.json",
    "RELEASE_NOTES_v0.1.0.md",
)


@pytest.fixture
def downloaded(tmp_path: Path) -> Path:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    assets = []
    for name in NAMES:
        path = inputs / name
        path.write_bytes(f"representative payload: {name}".encode())
        assets.append(path)
    bundle = tmp_path / "bundle"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "package", "--output", str(bundle), *map(str, assets)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    download = tmp_path / "fresh-download"
    download.mkdir()
    for path in bundle.iterdir():
        shutil.copyfile(path, download / path.name)
    return download


def test_flat_download_verifies_exact_files_and_stable_manifest(downloaded: Path) -> None:
    files = verify_bundle(downloaded)
    assert {path.name for path in files} == {*NAMES, "SHA256SUMS"}
    lines = (downloaded / "SHA256SUMS").read_text().splitlines()
    assert [line[66:] for line in lines] == sorted(NAMES)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", str(downloaded)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("fault", ["tampered", "missing", "unexpected", "duplicate", "directory"])
def test_reject_invalid_download(downloaded: Path, fault: str) -> None:
    payload = downloaded / NAMES[0]
    checksums = downloaded / "SHA256SUMS"
    if fault == "tampered":
        payload.write_bytes(b"tampered")
    elif fault == "missing":
        payload.unlink()
    elif fault == "unexpected":
        (downloaded / "extra.txt").write_bytes(b"unexpected")
    elif fault == "directory":
        payload.unlink()
        payload.mkdir()
    else:
        checksums.write_text(checksums.read_text() + checksums.read_text().splitlines()[0] + "\n")
    with pytest.raises(BundleError):
        verify_bundle(downloaded)


@pytest.mark.parametrize(
    "name", ["/absolute", "../escape", "dist/asset.whl", "nested\\asset", "C:\\asset", ".."]
)
def test_reject_unsafe_checksum_paths(downloaded: Path, name: str) -> None:
    (downloaded / "SHA256SUMS").write_text("0" * 64 + "  " + name + "\n")
    with pytest.raises(BundleError, match="unsafe"):
        verify_bundle(downloaded)


@pytest.mark.parametrize("entry", ["", "invalid", "0" * 64 + "  SHA256SUMS\n"])
def test_reject_invalid_checksum_manifest(downloaded: Path, entry: str) -> None:
    (downloaded / "SHA256SUMS").write_text(entry)
    with pytest.raises(BundleError):
        verify_bundle(downloaded)


def test_package_rejects_duplicate_basenames_before_copying(tmp_path: Path) -> None:
    assets = []
    for name in ("first", "second"):
        directory = tmp_path / name
        directory.mkdir()
        asset = directory / "same.whl"
        asset.write_bytes(b"payload")
        assets.append(asset)
    output = tmp_path / "bundle"
    with pytest.raises(BundleError, match="duplicate"):
        package_bundle(assets, output)
    assert not output.exists()


def test_package_rejects_missing_assets_and_existing_payloads(downloaded: Path) -> None:
    with pytest.raises(BundleError, match="missing"):
        package_bundle([downloaded / "missing"], downloaded / "output")
    with pytest.raises(BundleError, match="empty directory"):
        package_bundle([downloaded / NAMES[0]], downloaded)


def test_verifier_cli_fails_closed(downloaded: Path) -> None:
    (downloaded / NAMES[0]).write_bytes(b"tampered")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", str(downloaded)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "checksum mismatch" in result.stderr
