"""Tests for BegetClient: POST auth in body, not query string; error parsing."""

import pytest
import responses

from mcp_beget.client import BegetClient
from mcp_beget.config import BegetConfig
from mcp_beget.errors import BegetAPIError, BegetAuthError


@pytest.fixture
def client() -> BegetClient:
    return BegetClient(BegetConfig(login="user", password="s3cret", timeout=5))


@responses.activate
def test_call_uses_post_and_sends_auth_in_body(client):
    responses.post(
        "https://api.beget.com/api/dns/getData",
        json={"status": "success", "answer": {"status": "success", "result": {}}},
    )
    client.call("dns", "getData", {"fqdn": "example.com"})

    req = responses.calls[0].request
    # URL must NOT contain password
    assert "passwd" not in req.url
    assert "s3cret" not in req.url
    # output_format stays in query
    assert "output_format=json" in req.url
    # Auth and payload in body
    body = req.body if isinstance(req.body, str) else req.body.decode()
    assert "login=user" in body
    assert "passwd=s3cret" in body
    assert "input_format=json" in body
    assert "input_data=" in body


@responses.activate
def test_call_returns_answer_envelope(client):
    responses.post(
        "https://api.beget.com/api/user/getAccountInfo",
        json={
            "status": "success",
            "answer": {"status": "success", "result": {"plan_name": "Start"}},
        },
    )
    out = client.call("user", "getAccountInfo")
    assert out == {"status": "success", "result": {"plan_name": "Start"}}


@responses.activate
def test_call_raises_auth_error_on_bad_credentials(client):
    responses.post(
        "https://api.beget.com/api/user/getAccountInfo",
        json={"status": "error", "error_code": "AUTH_ERROR", "error_text": "Bad login"},
    )
    with pytest.raises(BegetAuthError):
        client.call("user", "getAccountInfo")


@responses.activate
def test_call_raises_api_error_on_top_level_error(client):
    responses.post(
        "https://api.beget.com/api/dns/getData",
        json={"status": "error", "error_code": "METHOD_FAILED", "error_text": "boom"},
    )
    with pytest.raises(BegetAPIError) as exc:
        client.call("dns", "getData", {"fqdn": "x"})
    assert exc.value.code == "METHOD_FAILED"


@responses.activate
def test_call_raises_api_error_on_error_inside_answer(client):
    """Beget wraps method failures in a success envelope — must still raise.

    Live-verified against dns/getData on a www alias and cron/delete with a bad
    param: HTTP 200, top-level status "success", error only inside ``answer``.
    Returning that as a value made every ``except BegetAPIError`` unreachable —
    dns_get never reached its parent-zone fallback, and read-merge-write saw an
    empty zone and wiped records.
    """
    responses.post(
        "https://api.beget.com/api/dns/getData",
        json={
            "status": "success",
            "answer": {
                "status": "error",
                "errors": [
                    {"error_code": "METHOD_FAILED", "error_text": "Failed to get DNS records"}
                ],
            },
        },
    )
    with pytest.raises(BegetAPIError) as exc:
        client.call("dns", "getData", {"fqdn": "www.sub.example.com"})
    assert exc.value.code == "METHOD_FAILED"
    assert "Failed to get DNS records" in exc.value.message


@responses.activate
def test_call_returns_list_answer_untouched(client):
    """Answers that are not dicts must pass through the error check unharmed."""
    responses.post(
        "https://api.beget.com/api/domain/getList",
        json={"status": "success", "answer": [{"id": 1}, {"id": 2}]},
    )
    assert client.call("domain", "getList") == [{"id": 1}, {"id": 2}]


@responses.activate
def test_call_raises_auth_error_on_auth_error_inside_answer(client):
    """AUTH_ERROR must map to BegetAuthError on both paths, not just top level."""
    responses.post(
        "https://api.beget.com/api/user/getAccountInfo",
        json={
            "status": "success",
            "answer": {
                "status": "error",
                "errors": [{"error_code": "AUTH_ERROR", "error_text": "Bad login"}],
            },
        },
    )
    with pytest.raises(BegetAuthError):
        client.call("user", "getAccountInfo")


@responses.activate
def test_error_string_carries_the_code(client):
    """MCP surfaces only str(exc) — the code must ride along or the agent is blind."""
    responses.post(
        "https://api.beget.com/api/dns/getData",
        json={
            "status": "success",
            "answer": {
                "status": "error",
                "errors": [{"error_code": "METHOD_FAILED", "error_text": "Failed to get"}],
            },
        },
    )
    with pytest.raises(BegetAPIError) as exc:
        client.call("dns", "getData", {"fqdn": "x"})
    assert str(exc.value) == "[METHOD_FAILED] Failed to get"
