"""Synthetic exact-source evidence; all network access and sleeps are forbidden."""

import copy
import importlib.util
import io
import json
import runpy
import socket
import sys
import time
from email.message import Message
from http.client import BadStatusLine, IncompleteRead
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPSHandler, OpenerDirector, ProxyHandler, Request, build_opener
from urllib.response import addinfourl

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts/check_release_source_ci.py"
SPEC = importlib.util.spec_from_file_location("check_release_source_ci", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
REPOSITORY = "sample-org/sample-repo"
SHA = "a1" * 20
TOKEN = "synthetic-private-credential"
DETAIL = "synthetic-private-response-detail"
ENDPOINT = f"https://api.github.com/repos/{REPOSITORY}/actions/runs"
QUERY = {"branch": "main", "event": "push", "head_sha": SHA, "per_page": 100}
ARGUMENTS = ["--repository", REPOSITORY, "--sha", SHA]


def run(index: int = 1, **changes: object) -> dict:
    return {
        "id": index,
        "workflow_id": index,
        "run_number": 1,
        "run_attempt": 1,
        "repository": {"full_name": REPOSITORY},
        "head_sha": SHA,
        "event": "push",
        "head_branch": "main",
        "path": HELPER.WORKFLOWS[index - 1] if index <= 3 else ".github/workflows/other.yml",
        "status": "completed",
        "conclusion": "success",
        "name": "Misleading identical display name",
        **changes,
    }


def evidence() -> list[dict]:
    return [run(index) for index in range(1, 4)]


def response(payload: object, link: str | None = None, status: object = 200) -> addinfourl:
    headers = Message()
    headers["Content-Type"] = "application/json"
    headers["X-Sensitive-Detail"] = DETAIL
    if link is not None:
        headers["Link"] = link
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return addinfourl(io.BytesIO(body), headers, ENDPOINT, status)


def listing(items: list[dict], total: int | None = None, link: str | None = None) -> addinfourl:
    return response(
        {"total_count": len(items) if total is None else total, "workflow_runs": items}, link
    )


def next_link(page: int) -> str:
    return "<" + ENDPOINT + "?" + urlencode({**QUERY, "page": page}) + '>; rel="next"'


@pytest.fixture(autouse=True)
def probe(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    forbidden = Mock(side_effect=AssertionError("Real network and sleeps forbidden"))
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(time, "sleep", forbidden)
    opener = Mock(spec=OpenerDirector)
    factory = Mock(return_value=opener)
    monkeypatch.setattr(HELPER, "build_opener", factory)
    return SimpleNamespace(opener=opener, factory=factory, forbidden=forbidden)


def supply(probe: SimpleNamespace, items: list[dict] | None = None) -> None:
    items = evidence() if items is None else items
    probe.opener.open.side_effect = [listing(items), *(response(item) for item in evidence())]


def test_exact_source_success_and_authenticated_bounded_gets(
    probe: SimpleNamespace, capsys
) -> None:
    supply(probe)
    assert HELPER.main(ARGUMENTS) == 0
    requests = probe.opener.open.call_args_list
    assert len(requests) == 4
    assert [item.args[0].full_url for item in requests[1:]] == [
        f"{ENDPOINT}/{index}" for index in range(1, 4)
    ]
    assert parse_qs(urlsplit(requests[0].args[0].full_url).query) == {
        key: [str(value)] for key, value in {**QUERY, "page": 1}.items()
    }
    for item in requests:
        request = item.args[0]
        assert request.get_method() == "GET" and request.data is None
        assert request.get_header("Authorization") == f"Bearer {TOKEN}"
        assert request.get_header("Accept") == "application/vnd.github+json"
        assert request.get_header("X-github-api-version") == "2026-03-10"
        assert request.get_header("User-agent") == "LifeLenz-release-source-ci"
        assert item.kwargs == {"timeout": 10}
    output = capsys.readouterr()
    assert all(path in output.out for path in HELPER.WORKFLOWS)
    assert SHA in output.out
    assert not output.err
    probe.forbidden.assert_not_called()


@pytest.mark.parametrize("index", range(3))
def test_missing_each_workflow(probe, index) -> None:
    items = evidence()
    items.pop(index)
    supply(probe, items)
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("head_sha", "b2" * 20),
        ("repository", {"full_name": "other/repo"}),
        ("event", "pull_request"),
        ("event", "workflow_dispatch"),
        ("head_branch", "feature"),
        ("head_branch", "v0.1.0"),
        ("path", ".github/workflows/other.yml"),
        ("path", ".github/workflows/ci.yml@v0.1.0"),
        ("path", ".github/workflows/ci.yml@refs/tags/v0.1.0"),
        ("path", ".github/workflows/ci.yml@feature"),
        ("path", ".github/workflows/ci.yml@main@main"),
        ("path", ".github/workflows/ci.yml\n"),
    ],
)
def test_wrong_source_and_misleading_display_name(probe, field, value) -> None:
    items = evidence()
    items[0][field] = value
    supply(probe, items)
    assert HELPER.main(ARGUMENTS) == 1


@pytest.mark.parametrize("suffix", ["", "@main", "@refs/heads/main"])
def test_documented_workflow_paths(probe, suffix) -> None:
    items = evidence()
    for item in items:
        item["path"] += suffix
    probe.opener.open.side_effect = [listing(items), *(response(item) for item in items)]
    assert HELPER.main(ARGUMENTS) == 0


@pytest.mark.parametrize(
    ("status", "conclusion"),
    [
        ("completed", value)
        for value in [
            None,
            "failure",
            "cancelled",
            "skipped",
            "neutral",
            "timed_out",
            "action_required",
            "stale",
            "startup_failure",
            DETAIL,
        ]
    ]
    + [
        (value, "success")
        for value in ["queued", "in_progress", "waiting", "pending", "requested", DETAIL]
    ],
)
@pytest.mark.parametrize("newer", [False, True])
def test_no_fallback_for_unsuccessful_latest(probe, status, conclusion, newer, capsys) -> None:
    items = evidence()
    bad = run(status=status, conclusion=conclusion)
    if newer:
        bad.update(id=10, run_number=2)
        items.append(bad)
    else:
        items[0] = bad
    supply(probe, items)
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1
    assert DETAIL not in str(capsys.readouterr())


def test_shuffled_latest_selection_is_deterministic(probe) -> None:
    items = evidence()
    newer = run(id=10, run_number=2)
    older = run(id=11)
    items[0]["run_number"] = 2
    newer["run_number"] = 3
    items += [newer, older]
    for ordered in [items, list(reversed(items)), items[2:] + items[:2]]:
        parsed = [HELPER.parse_run(item, REPOSITORY, SHA) for item in ordered]
        assert [item.id for item in HELPER.select_latest(parsed)] == [10, 2, 3]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 99),
        ("workflow_id", 99),
        ("run_number", 2),
        ("run_attempt", 2),
        ("run_attempt", 0),
        ("head_sha", "b2" * 20),
        ("repository", {"full_name": "other/repo"}),
        ("event", "workflow_dispatch"),
        ("head_branch", "v0.1.0"),
        ("path", HELPER.WORKFLOWS[1]),
        ("status", "in_progress"),
        ("conclusion", "failure"),
    ],
)
def test_refetch_identity_current_attempt_and_success(probe, field, value) -> None:
    current = run(**{field: value})
    probe.opener.open.side_effect = [listing(evidence()), response(current)]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 2


def test_refetch_later_failed_or_running_attempt(probe) -> None:
    for status, conclusion in [("in_progress", None), ("completed", "failure")]:
        probe.opener.open.side_effect = [
            listing(evidence()),
            response(run(run_attempt=2, status=status, conclusion=conclusion)),
        ]
        assert HELPER.main(ARGUMENTS) == 1


def paged_items() -> list[dict]:
    return [run(index) for index in range(4, 104)]


def test_success_only_on_later_page(probe) -> None:
    probe.opener.open.side_effect = [
        listing(paged_items(), 103, next_link(2)),
        listing(evidence(), 103),
        *(response(item) for item in evidence()),
    ]
    assert HELPER.main(ARGUMENTS) == 0
    assert probe.opener.open.call_args_list[1].args[0].full_url == (
        ENDPOINT + "?" + urlencode({**QUERY, "page": 2})
    )


def test_later_page_newer_failure_cannot_hide_behind_first_page_success(probe) -> None:
    first = evidence() + paged_items()[:97]
    newer = run(id=1000, run_number=2, conclusion="failure")
    probe.opener.open.side_effect = [listing(first, 101, next_link(2)), listing([newer], 101)]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 2


@pytest.mark.parametrize("total", [1001, 5000])
def test_page_limit_exhaustion(probe, total) -> None:
    probe.opener.open.side_effect = [listing(paged_items(), total, next_link(2))]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1


def test_exact_ten_pages_is_complete(probe) -> None:
    items = evidence() + [run(index) for index in range(4, 1001)]
    probe.opener.open.side_effect = [
        listing(
            items[offset : offset + 100],
            1000,
            next_link(offset // 100 + 2) if offset < 900 else None,
        )
        for offset in range(0, 1000, 100)
    ] + [response(item) for item in evidence()]
    assert HELPER.main(ARGUMENTS) == 0
    assert probe.opener.open.call_count == 13


@pytest.mark.parametrize(
    "link",
    [
        None,
        "",
        DETAIL,
        next_link(3),
        next_link(2) + "," + next_link(2),
        next_link(2).replace("api.github.com", "host.invalid"),
        next_link(2).replace("https:", "http:"),
        next_link(2).replace("page=2", "page=02"),
        next_link(2).replace("page=2", "page=2&page=3"),
        next_link(2).replace("branch=main", "branch=feature"),
        next_link(2).replace("/actions/runs?", "/actions/runs/1?"),
        next_link(2).replace(">; rel=", "#fragment>; rel="),
        next_link(2).replace("page=2", "invalid"),
        next_link(2).replace("api.github.com", "[malformed"),
        next_link(2).replace('rel="next"', 'rel="last"'),
    ],
)
def test_bad_or_truncated_pagination(probe, link, capsys) -> None:
    probe.opener.open.side_effect = [listing(paged_items(), 103, link)]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1
    assert DETAIL not in str(capsys.readouterr())


def test_changed_total_truncated_page_and_unexpected_next(probe) -> None:
    for second in [
        listing(evidence(), 104),
        listing(evidence()[:2], 103),
        listing(evidence(), 103, next_link(3)),
    ]:
        probe.opener.open.side_effect = [listing(paged_items(), 103, next_link(2)), second]
        assert HELPER.main(ARGUMENTS) == 1


@pytest.mark.parametrize("extra", ["&unexpected=", "\n", "\x7f"])
def test_malformed_link_query_and_control_characters(probe, extra) -> None:
    link = next_link(2).replace(">; rel=", extra + ">; rel=")
    probe.opener.open.side_effect = [listing(paged_items(), 103, link)]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1


def test_duplicate_run_across_pages_is_rejected(probe) -> None:
    first = evidence() + paged_items()[:97]
    probe.opener.open.side_effect = [listing(first, 101, next_link(2)), listing([run()], 101)]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 2


def test_body_read_failure_is_sanitized_and_closed(probe, capsys) -> None:
    class BrokenBody(io.BytesIO):
        def read(self, *args, **kwargs):
            raise IncompleteRead(DETAIL.encode())

    result = addinfourl(BrokenBody(), Message(), ENDPOINT, 200)
    result.headers["Content-Type"] = "application/json"
    probe.opener.open.side_effect = [result]
    assert HELPER.main(ARGUMENTS) == 1
    assert result.fp.closed
    assert DETAIL not in str(capsys.readouterr())


def test_untrusted_success_response_fields_are_never_logged(probe, capsys) -> None:
    items = evidence()
    for item in items:
        item.update(name=TOKEN, html_url=DETAIL, url=DETAIL)
    probe.opener.open.side_effect = [listing(items), *(response(item) for item in items)]
    assert HELPER.main(ARGUMENTS) == 0
    output = str(capsys.readouterr())
    assert TOKEN not in output and DETAIL not in output


@pytest.mark.parametrize("change", ["same", "attempt", "status", "number", "workflow", "path"])
def test_duplicate_ambiguity(probe, change) -> None:
    items = evidence()
    duplicate = copy.deepcopy(items[0])
    if change == "attempt":
        duplicate["run_attempt"] = 2
    elif change == "status":
        duplicate["conclusion"] = "failure"
    elif change == "number":
        duplicate["id"] = 99
    elif change == "workflow":
        duplicate.update(id=99, workflow_id=99, run_number=2)
    elif change == "path":
        duplicate.update(id=99, run_number=2, path=HELPER.WORKFLOWS[1])
    supply(probe, [*items, duplicate])
    assert HELPER.main(ARGUMENTS) == 1


@pytest.mark.parametrize("field", ["id", "workflow_id", "run_number", "run_attempt"])
@pytest.mark.parametrize("value", [None, True, False, 0, -1, 1.0, "1", [], {}])
def test_invalid_positive_integer_fields(probe, field, value) -> None:
    supply(probe, [run(**{field: value}), run(2), run(3)])
    assert HELPER.main(ARGUMENTS) == 1


@pytest.mark.parametrize("field", list(run()))
def test_missing_required_fields(probe, field) -> None:
    item = run()
    del item[field]
    supply(probe, [item, run(2), run(3)])
    assert HELPER.main(ARGUMENTS) == (0 if field == "name" else 1)


@pytest.mark.parametrize(
    "payload",
    [
        b"{",
        b"\xff",
        b'{"total_count": 0, "total_count": 3, "workflow_runs": []}',
        [],
        None,
        {},
        {"total_count": True, "workflow_runs": []},
        {"total_count": -1, "workflow_runs": []},
        {"total_count": 3, "workflow_runs": {}},
        {"total_count": 1, "workflow_runs": [None]},
        {"total_count": 0, "workflow_runs": [run()]},
        {"total_count": 1, "workflow_runs": [run(repository=None)]},
        {"total_count": 1, "workflow_runs": [run(path=True)]},
        {"total_count": 1, "workflow_runs": [run(status=None)]},
        {"total_count": 1, "workflow_runs": [run(conclusion=False)]},
    ],
)
def test_malformed_json_and_schemas(probe, payload) -> None:
    probe.opener.open.side_effect = [response(payload)]
    assert HELPER.main(ARGUMENTS) == 1


@pytest.mark.parametrize(
    "status", [201, 301, 302, 303, 307, 308, 401, 403, 404, 429, 500, 503, None, True, DETAIL]
)
def test_http_errors_do_not_retry_or_leak(probe, status, capsys) -> None:
    headers = Message()
    headers["Authorization"] = TOKEN
    headers["Location"] = "https://private.invalid/" + DETAIL
    body = io.BytesIO(DETAIL.encode())
    probe.opener.open.side_effect = HTTPError(ENDPOINT, status, DETAIL, headers, body)
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1
    assert body.closed
    output = str(capsys.readouterr())
    assert all(private not in output for private in [TOKEN, DETAIL, "Authorization", "Location"])


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError(DETAIL),
        URLError(DETAIL),
        ConnectionResetError(DETAIL),
        BadStatusLine(DETAIL),
        IncompleteRead(b"private"),
        ValueError(DETAIL),
    ],
)
def test_network_protocol_failures_are_sanitized(probe, error, capsys) -> None:
    probe.opener.open.side_effect = error
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 1
    assert DETAIL not in str(capsys.readouterr())


def test_body_size_content_type_and_duplicate_link_bounds(probe) -> None:
    oversized = response(b"x" * (HELPER.MAX_RESPONSE_BYTES + 1))
    wrong_type = response({})
    wrong_type.headers.replace_header("Content-Type", "text/html")
    links = listing(evidence())
    links.headers["Link"] = next_link(2)
    links.headers["Link"] = next_link(2)
    for result in [oversized, wrong_type, links]:
        probe.opener.open.side_effect = [result]
        assert HELPER.main(ARGUMENTS) == 1
        assert result.fp.closed


@pytest.mark.parametrize("length", [DETAIL, "-1", "99999999999", "8388609", "1", "100000"])
def test_malformed_oversized_or_truncated_content_length(probe, length, capsys) -> None:
    result = listing(evidence())
    result.headers["Content-Length"] = length
    probe.opener.open.side_effect = [result]
    assert HELPER.main(ARGUMENTS) == 1
    assert DETAIL not in str(capsys.readouterr())


def test_valid_and_duplicate_content_length(probe) -> None:
    results = [listing(evidence()), *(response(item) for item in evidence())]
    for result in results:
        result.headers["Content-Length"] = str(len(result.fp.getvalue()))
    probe.opener.open.side_effect = results
    assert HELPER.main(ARGUMENTS) == 0
    result = listing(evidence())
    result.headers["Content-Length"] = "1"
    result.headers["Content-Length"] = "1"
    probe.opener.open.side_effect = [result]
    assert HELPER.main(ARGUMENTS) == 1


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_real_http_handler_never_follows_redirect(probe, monkeypatch, status, capsys) -> None:
    requests = []

    class FakeHTTPS(HTTPSHandler):
        def https_open(self, request: Request) -> addinfourl:
            requests.append(request)
            assert request.full_url.startswith(ENDPOINT + "?")
            result = response(DETAIL.encode(), status=status)
            result.headers["Location"] = "https://private.invalid/" + TOKEN
            result.msg = DETAIL
            return result

    monkeypatch.setattr(
        HELPER,
        "build_opener",
        lambda redirect: build_opener(ProxyHandler({}), redirect, FakeHTTPS()),
    )
    assert HELPER.main(ARGUMENTS) == 1
    assert len(requests) == 1
    output = str(capsys.readouterr())
    assert TOKEN not in output and DETAIL not in output


@pytest.mark.parametrize(
    "repository",
    [
        "",
        "owner",
        "owner/repo/extra",
        "owner/..",
        "../repo",
        "owner/repo?x",
        "https://token@host/repo",
        "owner/repo\n",
        "owner/repo#fragment",
    ],
)
def test_invalid_repository_before_requests(probe, repository, capsys) -> None:
    assert HELPER.main(["--repository", repository, "--sha", SHA]) == 1
    probe.factory.assert_not_called()
    assert capsys.readouterr().err == "Release source CI: Repository must be an owner/name pair.\n"


@pytest.mark.parametrize(
    "sha", ["", "a" * 39, "a" * 41, "A" * 40, "g" * 40, SHA + "\n", " " + SHA, TOKEN]
)
def test_invalid_sha_before_requests(probe, sha) -> None:
    assert HELPER.main(["--repository", REPOSITORY, "--sha", sha]) == 1
    probe.factory.assert_not_called()


@pytest.mark.parametrize(
    "token",
    [
        None,
        "",
        " ",
        "token\nvalue",
        "token\rvalue",
        "token\tvalue",
        "nonascii-\u0100",
        "token\x00",
        "token\x7f",
    ],
)
def test_invalid_credentials_before_requests(probe, monkeypatch, token, capsys) -> None:
    if token is None:
        monkeypatch.delenv("GH_TOKEN")
    else:
        monkeypatch.setattr(HELPER.os, "environ", {"GH_TOKEN": token})
    assert HELPER.main(ARGUMENTS) == 1
    probe.factory.assert_not_called()
    assert TOKEN not in str(capsys.readouterr())


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--repository", REPOSITORY],
        [*ARGUMENTS, "--token", TOKEN],
        [*ARGUMENTS, "--api-base-url", TOKEN],
        ["--repos", REPOSITORY, "--sha", SHA],
        [*ARGUMENTS, TOKEN],
    ],
)
def test_safe_cli_errors(probe, args, capsys) -> None:
    with pytest.raises(SystemExit) as error:
        HELPER.main(args)
    assert error.value.code == 2
    assert TOKEN not in str(capsys.readouterr())
    probe.factory.assert_not_called()


def test_script_entrypoint_invalid_input_has_no_traceback(probe, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--repository", TOKEN, "--sha", SHA])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert error.value.code == 1
    output = str(capsys.readouterr())
    assert TOKEN not in output and "Traceback" not in output
    probe.forbidden.assert_not_called()
