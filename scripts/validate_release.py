"""Validate the static LifeLenz MVP1 release contract."""

from __future__ import annotations

import argparse
import json
import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "release" / "manifest.json"
PYPROJECT_PATH = ROOT / "pyproject.toml"
WEB_PACKAGE_PATH = ROOT / "web" / "package.json"
WEB_LOCK_PATH = ROOT / "web" / "package-lock.json"
BETA_CLASSIFIER = "Development Status :: 4 - Beta"


class ReleaseValidationError(RuntimeError):
    """Raised when final release metadata is inconsistent."""


def _load_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseValidationError(f"unable to read JSON metadata: {path}") from error


def _require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ReleaseValidationError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def validate_release(expected_tag: str | None = None) -> dict[str, object]:
    """Validate final release metadata against Python, npm, and runtime contracts."""
    manifest = _load_json(MANIFEST_PATH)
    with PYPROJECT_PATH.open("rb") as stream:
        pyproject = tomllib.load(stream)
    web_package = _load_json(WEB_PACKAGE_PATH)
    web_lock = _load_json(WEB_LOCK_PATH)

    project = pyproject["project"]
    root_package = web_lock["packages"][""]

    _require_equal(manifest.get("schema_version"), 1, "manifest schema_version")
    _require_equal(manifest.get("status"), "release", "manifest status")
    _require_equal(manifest.get("release_channel"), "beta", "manifest release_channel")
    _require_equal(
        manifest.get("storage_contract"),
        "sqlite-single-api-instance",
        "manifest storage_contract",
    )

    product_version = manifest.get("product_version")
    if not isinstance(product_version, str) or not product_version:
        raise ReleaseValidationError("manifest product_version must be a non-empty string")

    _require_equal(project["version"], product_version, "Python product version")
    _require_equal(web_package["version"], product_version, "web product version")
    _require_equal(web_lock["version"], product_version, "npm lockfile version")
    _require_equal(root_package["version"], product_version, "npm root package version")

    _require_equal(
        project["requires-python"],
        manifest.get("python_requires"),
        "Python requirement",
    )
    _require_equal(web_package["engines"]["node"], manifest.get("node_engine"), "Node engine")
    _require_equal(manifest.get("python_runtime"), "3.13", "release Python runtime")
    _require_equal(manifest.get("node_runtime"), "22", "release Node runtime")

    classifiers = project.get("classifiers", [])
    if BETA_CLASSIFIER not in classifiers:
        raise ReleaseValidationError(f"missing beta classifier: {BETA_CLASSIFIER}")

    release = manifest.get("release")
    _require_equal(release, f"mvp1-{product_version}", "release identifier")

    release_tag = manifest.get("release_tag")
    _require_equal(release_tag, f"v{product_version}", "release tag")
    if expected_tag is not None:
        _require_equal(expected_tag, release_tag, "workflow tag")

    promoted_from = manifest.get("promoted_from")
    expected_prefix = f"mvp1-{product_version}-rc."
    if not isinstance(promoted_from, str) or not promoted_from.startswith(expected_prefix):
        raise ReleaseValidationError(f"manifest promoted_from must start with {expected_prefix!r}")

    source_sha = os.environ.get("LIFELENZ_RELEASE_SOURCE_SHA") or os.environ.get(
        "GITHUB_SHA", "local"
    )

    return {
        "product_version": product_version,
        "promoted_from": promoted_from,
        "python_runtime": manifest["python_runtime"],
        "release": release,
        "release_channel": manifest["release_channel"],
        "release_tag": release_tag,
        "source_sha": source_sha,
        "status": manifest["status"],
        "storage_contract": manifest["storage_contract"],
        "node_runtime": manifest["node_runtime"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--expected-tag")
    args = parser.parse_args(argv)

    try:
        evidence = validate_release(expected_tag=args.expected_tag)
    except (KeyError, TypeError, ReleaseValidationError) as error:
        parser.exit(2, f"error: release validation failed: {error}\n")

    serialized = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.evidence_out is not None:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
