"""Validate the static LifeLenz MVP1 release-candidate contract."""

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


class ReleaseCandidateError(RuntimeError):
    """Raised when release-candidate metadata is inconsistent."""


def _load_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError(f"unable to read JSON metadata: {path}") from error


def _require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ReleaseCandidateError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def validate_release_candidate() -> dict[str, object]:
    """Validate candidate metadata against Python, npm, and runtime contracts."""
    manifest = _load_json(MANIFEST_PATH)
    with PYPROJECT_PATH.open("rb") as stream:
        pyproject = tomllib.load(stream)
    web_package = _load_json(WEB_PACKAGE_PATH)
    web_lock = _load_json(WEB_LOCK_PATH)

    project = pyproject["project"]
    root_package = web_lock["packages"][""]

    _require_equal(manifest.get("schema_version"), 1, "manifest schema_version")
    _require_equal(manifest.get("status"), "release-candidate", "manifest status")
    _require_equal(manifest.get("release_channel"), "beta", "manifest release_channel")
    _require_equal(
        manifest.get("storage_contract"),
        "sqlite-single-api-instance",
        "manifest storage_contract",
    )

    product_version = manifest.get("product_version")
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
    _require_equal(manifest.get("python_runtime"), "3.13", "candidate Python runtime")
    _require_equal(manifest.get("node_runtime"), "22", "candidate Node runtime")

    classifiers = project.get("classifiers", [])
    if BETA_CLASSIFIER not in classifiers:
        raise ReleaseCandidateError(f"missing beta classifier: {BETA_CLASSIFIER}")

    candidate = manifest.get("candidate")
    if not isinstance(candidate, str) or not candidate.startswith("mvp1-"):
        raise ReleaseCandidateError(
            "manifest candidate must be an MVP1 release-candidate identifier"
        )

    source_sha = os.environ.get("LIFELENZ_RC_SOURCE_SHA") or os.environ.get("GITHUB_SHA", "local")

    return {
        "candidate": candidate,
        "product_version": product_version,
        "python_runtime": manifest["python_runtime"],
        "node_runtime": manifest["node_runtime"],
        "storage_contract": manifest["storage_contract"],
        "source_sha": source_sha,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args(argv)

    try:
        evidence = validate_release_candidate()
    except (KeyError, TypeError, ReleaseCandidateError) as error:
        parser.exit(2, f"error: release-candidate validation failed: {error}\n")

    serialized = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.evidence_out is not None:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
