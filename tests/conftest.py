"""Shared pytest fixtures."""

import json

import pytest

from mcp_beget import client as client_module


class FakeBegetClient:
    """In-memory stand-in for BegetClient.

    - ``set_response(section, method, response)`` queues answers for a call.
    - ``set_error(section, method, exc)`` makes the call raise.
    - ``calls`` records every (section, method, params) invocation.
    """

    def __init__(self) -> None:
        self._responses: dict[tuple[str, str], list] = {}
        self._errors: dict[tuple[str, str], Exception] = {}
        self.calls: list[tuple[str, str, dict | None]] = []

    def set_response(self, section: str, method: str, response: dict) -> None:
        self._responses.setdefault((section, method), []).append(response)

    def set_error(self, section: str, method: str, exc: Exception) -> None:
        self._errors[(section, method)] = exc

    def call(self, section: str, method: str, params: dict | None = None) -> dict:
        self.calls.append((section, method, params))
        if (section, method) in self._errors:
            raise self._errors[(section, method)]
        queue = self._responses.get((section, method))
        if not queue:
            raise AssertionError(
                f"No FakeBegetClient response queued for {section}/{method}. "
                f"Queue state: {self._responses}"
            )
        if len(queue) > 1:
            return queue.pop(0)
        return queue[0]


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeBegetClient:
    """Replace ``get_client()`` with a FakeBegetClient for the duration of the test."""
    fake = FakeBegetClient()
    monkeypatch.setattr(client_module, "_client", fake)
    return fake


def wrap_getdata(records: dict, set_type: int = 1, **extras) -> dict:
    """Build a dns/getData ``answer`` envelope."""
    return {
        "status": "success",
        "result": {
            "fqdn": extras.pop("fqdn", "example.com"),
            "is_under_control": True,
            "is_beget_dns": True,
            "is_subdomain": False,
            "set_type": set_type,
            "records": records,
            **extras,
        },
    }


def ok_change() -> dict:
    """Build a dns/changeRecords success envelope."""
    return {"status": "success", "result": True}


def unwrap_tool_json(s: str) -> dict:
    """Tools return JSON strings — parse into a dict."""
    return json.loads(s)
