"""Deterministic artifact readiness checks without network access or real sleeps."""

import importlib.util
import io
import socket
from email.message import Message
from http.client import BadStatusLine
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, OpenerDirector, ProxyHandler, Request, build_opener
from urllib.response import addinfourl

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts/wait_for_release_artifact.py"
SPEC = importlib.util.spec_from_file_location("wait_for_release_artifact", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)

REPOSITORY = "sample-org/sample-repo"
ARTIFACT_ID = "12345"
ENDPOINT = f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{ARTIFACT_ID}/zip"
TOKEN = "synthetic-private-credential"
LOCATION = "https://objects.example.invalid/archive.zip?signature=private-example"
DETAIL = "synthetic-private-response-detail"
ARGUMENTS = ["--repository", REPOSITORY, "--artifact-id", ARTIFACT_ID]


class UnreadBody(io.BytesIO):
    def read(self, *args: object, **kwargs: object) -> bytes:
        raise AssertionError("Readiness checks must not read response bodies")


def http_error(status: object, location: str | None = None) -> HTTPError:
    headers = Message()
    headers["X-Sensitive-Detail"] = DETAIL
    if location is not None:
        headers["Location"] = location
    return HTTPError(ENDPOINT, status, DETAIL, headers, UnreadBody(DETAIL.encode()))


@pytest.fixture(autouse=True)
def probe(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    monkeypatch.setattr(
        socket, "create_connection", Mock(side_effect=AssertionError("Real network forbidden"))
    )
    opener = Mock(spec=OpenerDirector)
    factory = Mock(return_value=opener)
    pause = Mock()
    monkeypatch.setattr(HELPER, "build_opener", factory)
    monkeypatch.setattr(HELPER, "sleep", pause)
    return SimpleNamespace(opener=opener, factory=factory, pause=pause)


def test_immediate_readiness_is_authenticated_get(probe: SimpleNamespace) -> None:
    response = http_error(302, LOCATION)
    probe.opener.open.side_effect = response
    assert HELPER.main(ARGUMENTS) == 0
    probe.pause.assert_not_called()
    probe.opener.open.assert_called_once()
    request = probe.opener.open.call_args.args[0]
    assert request.full_url == ENDPOINT
    assert request.get_method() == "GET" and request.data is None
    assert request.get_header("Authorization") == f"Bearer {TOKEN}"
    assert probe.opener.open.call_args.kwargs == {"timeout": 5}
    assert response.fp.closed


@pytest.mark.parametrize("not_found_count", [1, 4])
def test_only_404_is_retried_until_ready(probe: SimpleNamespace, not_found_count: int) -> None:
    probe.opener.open.side_effect = [
        *(http_error(404) for _ in range(not_found_count)),
        http_error(302, LOCATION),
    ]
    assert HELPER.main(ARGUMENTS) == 0
    assert probe.opener.open.call_count == not_found_count + 1
    assert probe.pause.call_args_list == [call(5)] * not_found_count
    assert all(item.kwargs == {"timeout": 5} for item in probe.opener.open.call_args_list)


def test_exhausted_404_budget_fails(
    probe: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    probe.opener.open.side_effect = [http_error(404) for _ in range(5)]
    assert HELPER.main(ARGUMENTS) == 1
    assert probe.opener.open.call_count == 5
    assert probe.pause.call_args_list == [call(5)] * 4
    assert all(item.kwargs == {"timeout": 5} for item in probe.opener.open.call_args_list)
    assert "exhausted" in capsys.readouterr().err


@pytest.mark.parametrize("status", [200, 301, 303, 307, 308, 401, 403, 410, 429, 500, 503])
def test_other_http_responses_fail_immediately(probe: SimpleNamespace, status: int) -> None:
    if status == 200:
        probe.opener.open.return_value = addinfourl(
            UnreadBody(DETAIL.encode()), Message(), ENDPOINT, status
        )
    else:
        probe.opener.open.side_effect = http_error(status, LOCATION)
    assert HELPER.main(ARGUMENTS) == 1
    probe.opener.open.assert_called_once()
    probe.pause.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [TimeoutError(DETAIL), URLError(DETAIL), ConnectionResetError(DETAIL), BadStatusLine(DETAIL)],
)
def test_network_and_protocol_errors_are_not_retried(
    probe: SimpleNamespace, capsys: pytest.CaptureFixture[str], error: Exception
) -> None:
    probe.opener.open.side_effect = error
    assert HELPER.main(ARGUMENTS) == 1
    probe.opener.open.assert_called_once()
    probe.pause.assert_not_called()
    output = capsys.readouterr()
    assert DETAIL not in output.out + output.err


@pytest.mark.parametrize(
    "artifact_id", ["", "0", "-1", "01", "+1", " 1", "1 ", "1\n", "1,2", "abc", "*"]
)
def test_invalid_ids_fail_before_requests(probe: SimpleNamespace, artifact_id: str) -> None:
    assert HELPER.main(["--repository", REPOSITORY, "--artifact-id", artifact_id]) == 1
    probe.factory.assert_not_called()
    probe.pause.assert_not_called()


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
    ],
)
def test_invalid_repositories_fail_before_requests(probe: SimpleNamespace, repository: str) -> None:
    assert HELPER.main(["--repository", repository, "--artifact-id", ARTIFACT_ID]) == 1
    probe.factory.assert_not_called()
    probe.pause.assert_not_called()


@pytest.mark.parametrize("token", [None, "", " ", "token\nvalue", "nonascii-\u0100"])
def test_missing_or_invalid_credentials_fail_before_requests(
    probe: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, token: str | None
) -> None:
    if token is None:
        monkeypatch.delenv("GH_TOKEN")
    else:
        monkeypatch.setenv("GH_TOKEN", token)
    assert HELPER.main(ARGUMENTS) == 1
    probe.factory.assert_not_called()
    probe.pause.assert_not_called()


def test_credential_cli_argument_is_rejected_without_echo(
    probe: SimpleNamespace, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        HELPER.main([*ARGUMENTS, "--token", TOKEN])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert TOKEN not in output.out + output.err
    probe.factory.assert_not_called()


@pytest.mark.parametrize("location", [None, "", " \t", "https://example.invalid/\r\nmalformed"])
def test_missing_or_malformed_location_fails(probe: SimpleNamespace, location: str | None) -> None:
    probe.opener.open.side_effect = http_error(302, location)
    assert HELPER.main(ARGUMENTS) == 1
    probe.opener.open.assert_called_once()
    probe.pause.assert_not_called()


@pytest.mark.parametrize("status", [None, True, DETAIL])
def test_malformed_status_is_not_logged(
    probe: SimpleNamespace, capsys: pytest.CaptureFixture[str], status: object
) -> None:
    probe.opener.open.side_effect = http_error(status)
    assert HELPER.main(ARGUMENTS) == 1
    probe.opener.open.assert_called_once()
    probe.pause.assert_not_called()
    output = capsys.readouterr()
    assert DETAIL not in output.out + output.err


@pytest.mark.parametrize("status", [302, 404, 401, 503])
def test_response_details_are_never_logged(
    probe: SimpleNamespace, capsys: pytest.CaptureFixture[str], status: int
) -> None:
    probe.opener.open.side_effect = lambda *args, **kwargs: raise_response(status)
    assert HELPER.main(ARGUMENTS) == (0 if status == 302 else 1)
    output = capsys.readouterr()
    combined = output.out + output.err
    for private in (TOKEN, LOCATION, DETAIL, "Authorization", "X-Sensitive-Detail"):
        assert private not in combined


def raise_response(status: int) -> None:
    raise http_error(status, LOCATION)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_real_opener_does_not_follow_redirects(
    probe: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: int,
) -> None:
    requests = []

    class FakeHTTPS(HTTPSHandler):
        def https_open(self, request: Request) -> addinfourl:
            requests.append(request)
            assert request.full_url == ENDPOINT, "Signed redirect must not be requested"
            headers = Message()
            headers["Location"] = LOCATION
            response = addinfourl(UnreadBody(DETAIL.encode()), headers, ENDPOINT, status)
            response.msg = DETAIL
            return response

    monkeypatch.setattr(
        HELPER,
        "build_opener",
        lambda redirect: build_opener(ProxyHandler({}), redirect, FakeHTTPS()),
    )
    assert HELPER.main(ARGUMENTS) == (0 if status == 302 else 1)
    assert len(requests) == 1
    probe.pause.assert_not_called()
    output = capsys.readouterr()
    assert all(private not in output.out + output.err for private in (TOKEN, LOCATION, DETAIL))
