"""Require successful latest main-push workflows for an exact release source."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from email.message import Message
from http.client import HTTPException
from typing import BinaryIO, NamedTuple, NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/deployment.yml",
    ".github/workflows/release.yml",
)
PER_PAGE = 100
MAX_PAGES = 10
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 10
API_VERSION = "2026-03-10"


class SourceCIError(RuntimeError):
    """A diagnostic containing only trusted text or validated evidence."""


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
        self.exit(2, "Release source CI: invalid command-line arguments.\n")


class Run(NamedTuple):
    id: int
    workflow_id: int
    number: int
    attempt: int
    path: str
    status: str
    conclusion: str | None


def _integer(value: object, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise SourceCIError("Invalid integer in API evidence.")
    return value


def _object(value: object) -> dict:
    if not isinstance(value, dict):
        raise SourceCIError("Invalid API response schema.")
    return value


def parse_run(value: object, repository: str, sha: str) -> Run:
    """Validate query identity independently of the server-side filters."""
    run = _object(value)
    if (
        _object(run.get("repository")).get("full_name") != repository
        or run.get("head_sha") != sha
        or run.get("event") != "push"
        or run.get("head_branch") != "main"
    ):
        raise SourceCIError("Run does not match the requested main-push source.")
    if (
        not isinstance(run.get("path"), str)
        or not run["path"]
        or not isinstance(run.get("status"), str)
        or "conclusion" not in run
        or (run["conclusion"] is not None and not isinstance(run["conclusion"], str))
    ):
        raise SourceCIError("Invalid run fields in API evidence.")
    return Run(
        _integer(run.get("id")),
        _integer(run.get("workflow_id")),
        _integer(run.get("run_number")),
        _integer(run.get("run_attempt")),
        run["path"],
        run["status"],
        run["conclusion"],
    )


def _workflow(path: str) -> str | None:
    for expected in WORKFLOWS:
        if path in (expected, expected + "@main", expected + "@refs/heads/main"):
            return expected
    return None


def select_latest(runs: list[Run]) -> list[Run]:
    """Select by run number, never by a successful status or response ordering."""
    ids: set[int] = set()
    identities: set[tuple[int, int]] = set()
    workflow_paths: dict[int, str] = {}
    selected: dict[str, Run] = {}
    for run in runs:
        identity = (run.workflow_id, run.number)
        if run.id in ids or identity in identities:
            raise SourceCIError("Duplicate or conflicting run identity.")
        ids.add(run.id)
        identities.add(identity)
        path = _workflow(run.path)
        canonical = path or run.path
        if workflow_paths.setdefault(run.workflow_id, canonical) != canonical:
            raise SourceCIError("Conflicting workflow identity.")
        if path is None:
            continue
        previous = selected.get(path)
        if previous is not None:
            if previous.workflow_id != run.workflow_id or previous.number == run.number:
                raise SourceCIError("Ambiguous workflow evidence.")
            if previous.number > run.number:
                continue
        selected[path] = run
    if any(path not in selected for path in WORKFLOWS):
        raise SourceCIError("Missing required workflow evidence.")
    return [selected[path] for path in WORKFLOWS]


def require_success(run: Run) -> None:
    if run.status != "completed" or run.conclusion != "success":
        raise SourceCIError("Latest main-push workflow is not completed successfully.")


def _json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceCIError("Duplicate JSON field in API evidence.")
        result[key] = value
    return result


def _get(opener: object, url: str, token: str) -> tuple[dict, str | None]:
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "LifeLenz-release-source-ci",
        },
    )
    try:
        try:
            response = opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS)
        except HTTPError as error:
            response = error
        with response:
            status = response.getcode()
            if type(status) is not int or not 100 <= status <= 599:
                raise SourceCIError("Malformed HTTP response status.")
            if status != 200:
                raise SourceCIError(f"HTTP {status}: source evidence unavailable.")
            content_type = response.headers.get_content_type()
            if content_type not in {"application/json", "application/vnd.github+json"}:
                raise SourceCIError("Expected a JSON API response.")
            lengths = response.headers.get_all("Content-Length", [])
            if len(lengths) > 1 or (
                lengths
                and (
                    re.fullmatch(r"[0-9]{1,10}", lengths[0]) is None
                    or int(lengths[0]) > MAX_RESPONSE_BYTES
                )
            ):
                raise SourceCIError("Invalid or excessive response length.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise SourceCIError("API response exceeds the size limit.")
            if lengths and len(body) != int(lengths[0]):
                raise SourceCIError("Truncated or inconsistent response length.")
            links = response.headers.get_all("Link", [])
            if len(links) > 1:
                raise SourceCIError("Ambiguous pagination headers.")
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=_json_object)
            return _object(payload), links[0] if links else None
    except (
        URLError,
        OSError,
        HTTPException,
        ValueError,
        TypeError,
        AttributeError,
        RecursionError,
    ):
        raise SourceCIError("Network, decoding, or protocol failure.") from None


def _pagination(link: str | None, endpoint: str, query: dict, page: int, pages: int) -> None:
    """Check Link consistency without ever using a supplied URL for a request."""
    relations: dict[str, int] = {}
    if link is not None:
        if any(ord(character) < 32 or ord(character) == 127 for character in link):
            raise SourceCIError("Malformed pagination header.")
        for part in link.split(","):
            match = re.fullmatch(r'\s*<([^<>]+)>;\s*rel="(next|prev|first|last)"\s*', part)
            if match is None or match[2] in relations:
                raise SourceCIError("Malformed pagination evidence.")
            try:
                parsed = urlsplit(match[1])
                values = parse_qs(parsed.query, strict_parsing=True, keep_blank_values=True)
            except ValueError:
                raise SourceCIError("Malformed pagination target.") from None
            page_values = values.pop("page", [])
            if (
                parsed.scheme != "https"
                or parsed.netloc != "api.github.com"
                or parsed.path != urlsplit(endpoint).path
                or parsed.fragment
                or values != {key: [str(value)] for key, value in query.items()}
                or len(page_values) != 1
                or re.fullmatch(r"[1-9][0-9]*", page_values[0]) is None
                or len(page_values[0]) > 2
            ):
                raise SourceCIError("Unexpected pagination target.")
            relations[match[2]] = int(page_values[0])
    expected = {"next": page + 1, "prev": page - 1, "first": 1, "last": pages}
    if ("next" in relations) != (page < pages) or any(
        value != expected[relation] or not 1 <= value <= pages or (relation == "prev" and page == 1)
        for relation, value in relations.items()
    ):
        raise SourceCIError("Inconsistent or truncated pagination.")


def check_release_source_ci(repository: str, sha: str) -> None:
    if (
        type(repository) is not str
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", repository) is None
        or repository.split("/")[1] in {".", ".."}
    ):
        raise SourceCIError("Repository must be an owner/name pair.")
    if type(sha) is not str or re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise SourceCIError("Source SHA must be 40 canonical lowercase hexadecimal characters.")
    token = os.environ.get("GH_TOKEN", "")
    if (
        not token
        or not token.isascii()
        or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in token
        )
    ):
        raise SourceCIError("GH_TOKEN is missing or invalid.")
    endpoint = f"https://api.github.com/repos/{repository}/actions/runs"
    query = {"branch": "main", "event": "push", "head_sha": sha, "per_page": PER_PAGE}
    opener = build_opener(_NoRedirects())
    runs: list[Run] = []
    total = None
    for page in range(1, MAX_PAGES + 1):
        payload, link = _get(opener, endpoint + "?" + urlencode({**query, "page": page}), token)
        count = _integer(payload.get("total_count"), minimum=0)
        if count > MAX_PAGES * PER_PAGE or (total is not None and count != total):
            raise SourceCIError("Listing changed or exceeds the page limit.")
        total = count
        items = payload.get("workflow_runs")
        if not isinstance(items, list) or len(items) != min(PER_PAGE, count - len(runs)):
            raise SourceCIError("Incomplete or malformed workflow listing.")
        pages = max(1, math.ceil(count / PER_PAGE))
        _pagination(link, endpoint, query, page, pages)
        runs.extend(parse_run(item, repository, sha) for item in items)
        if page == pages:
            break
    selected = select_latest(runs)
    for run in selected:
        require_success(run)
        payload, _ = _get(opener, f"{endpoint}/{run.id}", token)
        current = parse_run(payload, repository, sha)
        # A changed attempt, even if successful, requires a new consistent read.
        if current[:5] != run[:5]:
            raise SourceCIError("Run identity or attempt changed during verification.")
        require_success(current)
    for path, run in zip(WORKFLOWS, selected, strict=True):
        print(f"Release source CI: {path} SHA {sha} run {run.id} attempt {run.attempt}: success.")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args(argv)
    try:
        check_release_source_ci(args.repository, args.sha)
    except SourceCIError as error:
        print(f"Release source CI: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
