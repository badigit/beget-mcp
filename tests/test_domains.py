"""Tests for domain tools: subdomain validation, provisioned records."""

import json

import pytest

from mcp_beget.errors import BegetAPIError
from mcp_beget.tools import domains


def test_domain_add_subdomain_rejects_fqdn(fake_client):
    with pytest.raises(ValueError) as exc:
        domains.domain_add_subdomain("blog.site.ru", 123)
    assert "label only" in str(exc.value)
    # No API call attempted
    assert fake_client.calls == []


def test_domain_add_subdomain_rejects_empty(fake_client):
    with pytest.raises(ValueError):
        domains.domain_add_subdomain("   ", 123)
    with pytest.raises(ValueError):
        domains.domain_add_subdomain(".", 123)


def _create_params(fake_client) -> dict:
    """Параметры вызова addSubdomainVirtual (после него тул читает зону)."""
    for section, method, params in fake_client.calls:
        if (section, method) == ("domain", "addSubdomainVirtual"):
            return params
    raise AssertionError(f"addSubdomainVirtual not called: {fake_client.calls}")


def test_domain_add_subdomain_accepts_plain_label(fake_client):
    fake_client.set_response("domain", "addSubdomainVirtual", {"status": "success", "result": True})
    fake_client.set_response("domain", "getList", {"status": "success", "result": []})
    domains.domain_add_subdomain("blog", 123)
    assert _create_params(fake_client) == {"subdomain": "blog", "domain_id": 123}


def test_domain_add_subdomain_normalizes_label(fake_client):
    """Label should be lowercased and trimmed."""
    fake_client.set_response("domain", "addSubdomainVirtual", {"status": "success", "result": True})
    fake_client.set_response("domain", "getList", {"status": "success", "result": []})
    domains.domain_add_subdomain("  Blog.  ", 123)
    # Dot at the end becomes stripped → pure 'blog'
    assert _create_params(fake_client) == {"subdomain": "blog", "domain_id": 123}


# ---------------------------------------------------------------------------
# Автопровижининг записей при создании поддомена (beget-mcp-ke3)
# ---------------------------------------------------------------------------

def test_domain_add_subdomain_returns_provisioned_records(fake_client):
    """Beget заводит A/MX/TXT сам — ответ обязан их показать, а не только id."""
    fake_client.set_response(
        "domain", "addSubdomainVirtual", {"status": "success", "result": 14651213}
    )
    fake_client.set_response(
        "domain", "getList",
        {"status": "success", "result": [{"id": 7684388, "fqdn": "site.ru"}]},
    )
    provisioned = {
        "A": [{"address": "87.236.16.28", "ttl": 600}],
        "MX": [{"exchange": "mx1.beget.com", "preference": 10, "ttl": 600}],
        "TXT": [{"txtdata": "v=spf1 redirect=beget.com", "ttl": 600}],
    }
    fake_client.set_response(
        "dns", "getData", {"status": "success", "result": {"records": provisioned}}
    )

    out = json.loads(domains.domain_add_subdomain("bsapp", 7684388))

    assert out["subdomain_id"] == 14651213
    assert out["fqdn"] == "bsapp.site.ru"
    assert out["records"] == provisioned
    assert "shared-хостинг" in out["note"]


def test_domain_add_subdomain_survives_unreadable_zone(fake_client):
    """Поддомен уже создан: провал чтения зоны не делает вызов неуспешным."""
    fake_client.set_response(
        "domain", "addSubdomainVirtual", {"status": "success", "result": 42}
    )
    fake_client.set_response(
        "domain", "getList",
        {"status": "success", "result": [{"id": 7, "fqdn": "site.ru"}]},
    )
    fake_client.set_error(
        "dns", "getData", BegetAPIError("Failed to get DNS records", code="METHOD_FAILED")
    )

    out = json.loads(domains.domain_add_subdomain("blog", 7))

    assert out["status"] == "success"
    assert out["subdomain_id"] == 42
    assert "METHOD_FAILED" in out["records_error"]
    assert "records" not in out


def test_domain_add_subdomain_without_known_parent(fake_client):
    """Родителя в getList нет — отдаём id и предупреждение, без выдуманного fqdn."""
    fake_client.set_response(
        "domain", "addSubdomainVirtual", {"status": "success", "result": 42}
    )
    fake_client.set_response("domain", "getList", {"status": "success", "result": []})

    out = json.loads(domains.domain_add_subdomain("blog", 999))

    assert out["subdomain_id"] == 42
    assert "fqdn" not in out
    assert out["note"]
