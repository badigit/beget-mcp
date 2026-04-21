"""Tests for domain tools: subdomain validation."""

import pytest

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


def test_domain_add_subdomain_accepts_plain_label(fake_client):
    fake_client.set_response("domain", "addSubdomainVirtual", {"status": "success", "result": True})
    domains.domain_add_subdomain("blog", 123)
    _, _, params = fake_client.calls[-1]
    assert params == {"subdomain": "blog", "domain_id": 123}


def test_domain_add_subdomain_normalizes_label(fake_client):
    """Label should be lowercased and trimmed."""
    fake_client.set_response("domain", "addSubdomainVirtual", {"status": "success", "result": True})
    domains.domain_add_subdomain("  Blog.  ", 123)
    # Dot at the end becomes stripped → pure 'blog'
    _, _, params = fake_client.calls[-1]
    assert params == {"subdomain": "blog", "domain_id": 123}
