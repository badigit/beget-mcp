"""Несозданный поддомен, catch-all зоны и факт у авторитативного NS.

Покрывает beget-mcp-82z, beget-mcp-c5l и beget-mcp-h6t: ошибка записи обязана
называть настоящее лекарство, а «принято панелью» — отличаться от «отдаётся
миру». Всё на моках API: живые зоны аккаунта боевые.
"""

import pytest

from mcp_beget.errors import BegetAPIError
from mcp_beget.tools import dns

from .conftest import ok_change, unwrap_tool_json, wrap_getdata

# ---------------------------------------------------------------------------
# Несозданный поддомен на пути записи (beget-mcp-82z)
# ---------------------------------------------------------------------------


def _subdomain_missing(fake_client, domains=None):
    """getData падает на поддомене, читается на родителе; getList знает родителя."""
    parent_answer = wrap_getdata({"A": [{"address": "1.2.3.4", "ttl": 600}]})
    domain_list = [{"id": 7684388, "fqdn": "site.ru"}] if domains is None else domains

    def fake_call(section, method, params=None):
        fake_client.calls.append((section, method, params))
        if (section, method) == ("dns", "getData"):
            if params["fqdn"] == "site.ru":
                return parent_answer
            raise BegetAPIError("Failed to get DNS records", code="METHOD_FAILED")
        if (section, method) == ("domain", "getList"):
            return {"status": "success", "result": domain_list}
        raise AssertionError(f"unexpected call {section}/{method}")

    fake_client.call = fake_call
    return fake_client


def test_write_to_missing_subdomain_names_add_subdomain(fake_client):
    """Лечение — domain_add_subdomain с готовым domain_id, а не replace_all."""
    _subdomain_missing(fake_client)

    with pytest.raises(BegetAPIError) as exc:
        dns.dns_set_a("bsapp.site.ru", "94.102.89.170")

    err = exc.value
    assert err.code == "SUBDOMAIN_NOT_CREATED"
    assert "domain_add_subdomain(subdomain='bsapp', domain_id=7684388)" in err.message
    # replace_all упоминается как запрет, а не как совет
    assert "Do NOT use dns_set_records with replace_all=True" in err.message
    assert err.details["fix"] == {
        "tool": "domain_add_subdomain",
        "subdomain": "bsapp",
        "domain_id": 7684388,
    }
    assert not [c for c in fake_client.calls if c[1] == "changeRecords"]


def test_missing_subdomain_without_domain_id_still_names_the_tool(fake_client):
    """getList не знает родителя — команда называется, id ищется в domain_list."""
    _subdomain_missing(fake_client, domains=[])

    with pytest.raises(BegetAPIError) as exc:
        dns.dns_set_txt("bsapp.site.ru", "v=spf1 -all")

    assert exc.value.code == "SUBDOMAIN_NOT_CREATED"
    assert "domain_add_subdomain(subdomain='bsapp'" in exc.value.message
    assert exc.value.details["fix"]["domain_id"] is None


def test_patch_record_also_reports_missing_subdomain(fake_client):
    """Второй путь записи идёт через тот же _get_result."""
    _subdomain_missing(fake_client)

    with pytest.raises(BegetAPIError) as exc:
        dns.dns_patch_record("bsapp.site.ru", "TXT", add='[{"txtdata":"x"}]')

    assert exc.value.code == "SUBDOMAIN_NOT_CREATED"


def test_unreadable_zone_keeps_old_no_zone_data_advice(fake_client):
    """Прочие причины нечитаемой зоны — прежний текст и прежний код."""
    fake_client.set_response("dns", "getData", {"status": "success", "result": {}})

    with pytest.raises(BegetAPIError) as exc:
        dns.dns_set_a("example.com", "203.0.113.1")

    assert exc.value.code == "NO_ZONE_DATA"
    assert "replace_all=True" in exc.value.message


def test_parent_also_unreadable_is_not_reported_as_missing_subdomain(fake_client):
    """Родитель тоже не читается — сломана зона, а не отсутствует поддомен."""
    fake_client.set_error(
        "dns",
        "getData",
        BegetAPIError("Failed to get DNS records", code="METHOD_FAILED"),
    )

    with pytest.raises(BegetAPIError) as exc:
        dns.dns_set_a("bsapp.site.ru", "203.0.113.1")

    assert exc.value.code == "METHOD_FAILED"


# ---------------------------------------------------------------------------
# Catch-all зоны и факт у авторитативного NS (beget-mcp-c5l, beget-mcp-h6t)
# ---------------------------------------------------------------------------


def test_dns_get_exposes_effective_resolution(monkeypatch, fake_client):
    """Записи в зоне нет, а имя отвечает: расхождение должно быть видно сразу."""
    fake_client.set_response(
        "dns", "getData", wrap_getdata({"A": [{"address": "185.137.235.2", "ttl": 600}]})
    )
    monkeypatch.setattr(
        dns,
        "probe",
        lambda fqdn, rtype="A", timeout=5.0: {
            "type": "A",
            "values": ["87.236.16.28"],
            "nameserver": "ns1.beget.com",
        },
    )

    out = unwrap_tool_json(dns.dns_get("zzz-not-exist.itrobot.ru"))

    assert out["effective"]["values"] == ["87.236.16.28"]
    assert "catch-all" in out["effective_note"]


def test_dns_get_can_skip_the_probe(monkeypatch, fake_client):
    fake_client.set_response(
        "dns", "getData", wrap_getdata({"A": [{"address": "1.2.3.4", "ttl": 600}]})
    )
    monkeypatch.setattr(
        dns,
        "probe",
        lambda *a, **kw: pytest.fail("probe must not run with check_effective=False"),
    )

    out = unwrap_tool_json(dns.dns_get("example.com", check_effective=False))

    assert "effective" not in out


def test_set_warns_about_propagation_delay(fake_client):
    """success = принято панелью, а не отдаётся миру."""
    fake_client.set_response(
        "dns", "getData", wrap_getdata({"A": [{"address": "1.2.3.4", "ttl": 600}]})
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    out = unwrap_tool_json(dns.dns_set_a("example.com", "203.0.113.1"))

    assert any("dns_verify" in w for w in out["warnings"])


def test_dns_verify_matches_without_waiting(monkeypatch):
    monkeypatch.setattr(
        dns,
        "probe",
        lambda fqdn, rtype="A", timeout=5.0: {"type": "A", "values": ["94.102.89.170"]},
    )
    monkeypatch.setattr(
        dns.time, "sleep", lambda s: pytest.fail("must not sleep on a match")
    )

    out = unwrap_tool_json(dns.dns_verify("bsapp.site.ru", "94.102.89.170"))

    assert out["matched"] is True
    assert out["attempts"] == 1


def test_dns_verify_reports_stale_value_after_deadline(monkeypatch):
    """Старое значение у NS — честный ответ «ещё не распространилось»."""
    monkeypatch.setattr(
        dns,
        "probe",
        lambda fqdn, rtype="A", timeout=5.0: {"type": "A", "values": ["87.236.16.28"]},
    )

    out = unwrap_tool_json(dns.dns_verify("bsapp.site.ru", "94.102.89.170", timeout=0))

    assert out["matched"] is False
    assert "не распространена" in out["note"]


def test_dns_verify_without_expect_just_reports(monkeypatch):
    monkeypatch.setattr(
        dns,
        "probe",
        lambda fqdn, rtype="A", timeout=5.0: {"type": "A", "values": ["87.236.16.28"]},
    )

    out = unwrap_tool_json(dns.dns_verify("bsapp.site.ru"))

    assert out["matched"] is None
    assert out["observed"]["values"] == ["87.236.16.28"]
