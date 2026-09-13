"""Опрос авторитативного NS: подъём по меткам и отказ без исключения.

Сети тут нет — dnspython подменяется заглушкой: тест про логику, а не про
доступность ns1.beget.com.
"""

from types import SimpleNamespace

from mcp_beget import dnsprobe


class _Target:
    def __init__(self, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return self._name + "."


def _fake_dnspython(ns_by_zone: dict[str, list[str]]):
    """Минимальный dnspython: resolve(zone, "NS") знает только заданные зоны."""

    class FakeResolver:
        timeout = 0
        lifetime = 0

        def resolve(self, name, rdtype):
            if rdtype == "NS":
                servers = ns_by_zone.get(name)
                if not servers:
                    raise LookupError(name)
                return [SimpleNamespace(target=_Target(s)) for s in servers]
            raise LookupError(name)

    return SimpleNamespace(resolver=SimpleNamespace(Resolver=FakeResolver))


def test_nameservers_are_looked_up_on_the_parent_zone(monkeypatch):
    """У поддомена своих NS нет — делегирование живёт на уровне site.ru."""
    monkeypatch.setattr(
        dnsprobe,
        "_dnspython",
        lambda: _fake_dnspython({"site.ru": ["ns2.beget.com", "ns1.beget.com"]}),
    )

    zone, servers = dnsprobe.authoritative_nameservers("bsapp.site.ru")

    assert zone == "site.ru"
    assert servers == ["ns1.beget.com", "ns2.beget.com"]


def test_missing_ns_raises_probe_unavailable(monkeypatch):
    monkeypatch.setattr(dnsprobe, "_dnspython", lambda: _fake_dnspython({}))

    try:
        dnsprobe.authoritative_nameservers("bsapp.site.ru")
    except dnsprobe.ProbeUnavailable as e:
        assert "no NS records found" in str(e)
    else:
        raise AssertionError("ProbeUnavailable expected")


def test_probe_reports_failure_as_data(monkeypatch):
    """Факт не получен — это поле error, а не падение тула, который зовёт пробу."""

    def boom(*args, **kwargs):
        raise dnsprobe.ProbeUnavailable("no reachable NS addresses")

    monkeypatch.setattr(dnsprobe, "query_authoritative", boom)

    out = dnsprobe.probe("bsapp.site.ru")

    assert out["type"] == "A"
    assert "no reachable NS addresses" in out["error"]
    assert "values" not in out
