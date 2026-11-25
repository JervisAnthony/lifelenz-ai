"""Wait for the artifact ZIP endpoint's redirect without following its signed URL."""

from __future__ import annotations

import argparse
import os
import re
import sys
from email.message import Message
from http.client import HTTPException
from time import sleep
from typing import BinaryIO, NoReturn
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_ATTEMPTS = 5
RETRY_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 5


class ArtifactReadinessError(RuntimeError):
    """A safe diagnostic that contains no response data or credentials."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: BinaryIO,
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        return None


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's default error can echo unsupported credential arguments.
        self.exit(2, "Artifact readiness: invalid command-line arguments.\n")


def wait_for_release_artifact(repository: str, artifact_id: str) -> None:
    """Require a 302/Location, retrying only 404 with a fixed five-attempt budget."""
    if (
        type(repository) is not str
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository) is None
        or repository.split("/")[1] in {".", ".."}
    ):
        raise ArtifactReadinessError("Repository must be an owner/name pair.")
    if type(artifact_id) is not str or re.fullmatch(r"[1-9][0-9]*", artifact_id) is None:
        raise ArtifactReadinessError("Artifact ID must be one positive decimal integer.")
    token = os.environ.get("GH_TOKEN", "")
    if (
        not token
        or not token.isascii()
        or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in token
        )
    ):
        raise ArtifactReadinessError("GH_TOKEN is missing or invalid.")

    request = Request(
        f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip",
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "LifeLenz-release-artifact-readiness",
        },
    )
    opener = build_opener(_NoRedirects())
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            try:
                response = opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS)
            except HTTPError as error:
                response = error
            with response:
                status = response.getcode()
                if type(status) is not int or not 100 <= status <= 599:
                    raise ArtifactReadinessError("Malformed HTTP response status.")
                print(
                    f"Artifact readiness attempt {attempt}/{MAX_ATTEMPTS}: HTTP {status}.",
                    flush=True,
                )
                if status == 302:
                    location = response.headers.get("Location")
                    if (
                        not isinstance(location, str)
                        or not location.strip()
                        or any(
                            ord(character) < 32 or ord(character) == 127 for character in location
                        )
                    ):
                        raise ArtifactReadinessError(
                            "Malformed HTTP 302: missing or invalid Location."
                        )
                    return
                if status != 404:
                    raise ArtifactReadinessError(f"HTTP {status} is not retryable.")
        except (URLError, OSError, HTTPException, ValueError, TypeError, AttributeError):
            raise ArtifactReadinessError(
                f"Artifact readiness attempt {attempt}/{MAX_ATTEMPTS}: network or protocol failure."
            ) from None
        if attempt == MAX_ATTEMPTS:
            raise ArtifactReadinessError("Artifact readiness exhausted five HTTP 404 attempts.")
        sleep(RETRY_SECONDS)


def main(argv: list[str] | None = None) -> int:
    """Accept only artifact identity arguments; credentials come only from GH_TOKEN."""
    parser = _SafeArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--artifact-id", required=True)
    args = parser.parse_args(argv)
    try:
        wait_for_release_artifact(args.repository, args.artifact_id)
    except ArtifactReadinessError as error:
        print(f"Artifact readiness: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
