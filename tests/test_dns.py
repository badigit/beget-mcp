"""Tests for DNS tools: merge semantics, normalization, CAA/SRV guard, fallback."""

import pytest

from mcp_beget.errors import BegetAPIError
from mcp_beget.tools import dns

from .conftest import ok_change, unwrap_tool_json, wrap_getdata

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def test_normalize_fqdn_strips_dot_and_lowers():
    assert dns._normalize_fqdn("Site.RU.") == "site.ru"
    assert dns._normalize_fqdn("  Example.COM  ") == "example.com"
    assert dns._normalize_fqdn("sub.DOMAIN.ru") == "sub.domain.ru"


def test_strip_trailing_dot():
    assert dns._strip_trailing_dot("mx.yandex.net.") == "mx.yandex.net"
    assert dns._strip_trailing_dot("mx.yandex.net") == "mx.yandex.net"
    assert dns._strip_trailing_dot(" site.ru. ") == "site.ru"


# ---------------------------------------------------------------------------
# Read-merge-write: all dns_set_* preserve untouched record types
# ---------------------------------------------------------------------------

def test_dns_set_txt_preserves_a_and_mx(fake_client):
    """Setting TXT must not wipe the zone's A and MX records (the core bug)."""
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "MX": [{"exchange": "mx.old", "preference": 10, "ttl": 600}],
            "TXT": [{"txtdata": "old", "ttl": 600}],
        }),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    out = unwrap_tool_json(dns.dns_set_txt("example.com", "v=spf1 -all"))

    _, _, params = fake_client.calls[-1]
    records = params["records"]
    assert records["A"] == [{"address": "1.2.3.4", "ttl": 600}]
    assert records["MX"] == [{"exchange": "mx.old", "preference": 10, "ttl": 600}]
    assert records["TXT"] == [{"txtdata": "v=spf1 -all", "ttl": 600}]
    assert out["status"] == "success"


def test_dns_set_mx_preserves_a_and_txt(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "TXT": [{"txtdata": "v=spf1 ~all", "ttl": 600}],
        }),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_set_mx("example.com", "mx.yandex.net.", preference=10)

    _, _, params = fake_client.calls[-1]
    records = params["records"]
    assert records["A"]
    assert records["TXT"]
    # trailing dot stripped
    assert records["MX"] == [{"exchange": "mx.yandex.net", "preference": 10, "ttl": 600}]


def test_dns_set_a_replaces_only_a(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "MX": [{"exchange": "mx.example.com", "preference": 10, "ttl": 600}],
        }),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_set_a("example.com", "5.6.7.8")
    _, _, params = fake_client.calls[-1]
    assert params["records"]["A"] == [{"address": "5.6.7.8", "ttl": 600}]
    assert params["records"]["MX"]  # preserved


def test_dns_set_cname_strips_trailing_dot(fake_client):
    fake_client.set_response("dns", "getData", wrap_getdata({}))
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_set_cname("www.example.com", "example.com.")
    _, _, params = fake_client.calls[-1]
    assert params["records"]["CNAME"] == [{"cname": "example.com", "ttl": 600}]


def test_dns_set_normalizes_fqdn(fake_client):
    fake_client.set_response("dns", "getData", wrap_getdata({}))
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_set_a("Example.COM.", "1.2.3.4")

    # Both getData and changeRecords should see normalized fqdn.
    for _section, _method, params in fake_client.calls:
        assert params["fqdn"] == "example.com"


# ---------------------------------------------------------------------------
# CAA / SRV guard
# ---------------------------------------------------------------------------

def test_dns_set_refuses_when_zone_has_caa(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "CAA": [{"flags": 0, "tag": "issue", "value": "letsencrypt.org", "ttl": 600}],
        }),
    )

    with pytest.raises(BegetAPIError) as exc:
        dns.dns_set_txt("example.com", "v=spf1 -all")
    assert exc.value.code == "UNWRITABLE_RECORDS_PRESENT"
    assert "CAA" in exc.value.message
    # No changeRecords call made
    methods = [m for _, m, _ in fake_client.calls]
    assert "changeRecords" not in methods


def test_dns_set_refuses_when_zone_has_srv(fake_client):
    srv = [{"priority": 10, "weight": 5, "port": 443, "target": "x.ru", "ttl": 600}]
    fake_client.set_response("dns", "getData", wrap_getdata({"SRV": srv}))
    with pytest.raises(BegetAPIError):
        dns.dns_set_a("example.com", "1.2.3.4")


def test_dns_set_force_bypasses_guard_and_emits_warning(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "CAA": [{"flags": 0, "tag": "issue", "value": "letsencrypt.org", "ttl": 600}],
        }),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    out = unwrap_tool_json(dns.dns_set_txt("example.com", "v=spf1 -all", force=True))

    _, _, params = fake_client.calls[-1]
    assert "CAA" not in params["records"]  # stripped before write
    assert any("CAA" in w for w in out["warnings"])


# ---------------------------------------------------------------------------
# Record limits
# ---------------------------------------------------------------------------

def test_dns_set_records_rejects_too_many(fake_client):
    fake_client.set_response("dns", "getData", wrap_getdata({}))

    too_many = '{"A":[' + ",".join(f'{{"address":"10.0.0.{i}"}}' for i in range(11)) + "]}"
    with pytest.raises(BegetAPIError) as exc:
        dns.dns_set_records("example.com", too_many)
    assert exc.value.code == "TOO_MANY_RECORDS"


# ---------------------------------------------------------------------------
# dns_set_records replace_all vs merge
# ---------------------------------------------------------------------------

def test_dns_set_records_replace_all_skips_getdata(fake_client):
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_set_records(
        "example.com",
        '{"A":[{"address":"1.2.3.4"}]}',
        replace_all=True,
    )
    methods = [m for _, m, _ in fake_client.calls]
    assert "getData" not in methods
    _, _, params = fake_client.calls[-1]
    # In replace_all the user's payload goes straight through.
    assert params["records"] == {"A": [{"address": "1.2.3.4"}]}


def test_dns_set_records_merge_preserves_others(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "MX": [{"exchange": "mx.old", "preference": 10, "ttl": 600}],
        }),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_set_records(
        "example.com",
        '{"TXT":[{"txtdata":"v=spf1 -all"}]}',
    )
    _, _, params = fake_client.calls[-1]
    assert params["records"]["A"]
    assert params["records"]["MX"]
    assert params["records"]["TXT"] == [{"txtdata": "v=spf1 -all"}]


# ---------------------------------------------------------------------------
# dns_patch_record
# ---------------------------------------------------------------------------

def test_patch_record_add(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({"TXT": [{"txtdata": "v=spf1 -all", "ttl": 600}]}),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_patch_record(
        "example.com",
        type="TXT",
        add='[{"txtdata":"google-site-verification=abc"}]',
    )
    _, _, params = fake_client.calls[-1]
    assert params["records"]["TXT"] == [
        {"txtdata": "v=spf1 -all", "ttl": 600},
        {"txtdata": "google-site-verification=abc"},
    ]


def test_patch_record_remove(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({"TXT": [
            {"txtdata": "v=spf1 ~all", "ttl": 600},
            {"txtdata": "keep-me", "ttl": 600},
        ]}),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_patch_record(
        "example.com",
        type="TXT",
        remove='[{"txtdata":"v=spf1 ~all"}]',
    )
    _, _, params = fake_client.calls[-1]
    assert params["records"]["TXT"] == [{"txtdata": "keep-me", "ttl": 600}]


def test_patch_record_replace_ignores_add_remove(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({"MX": [{"exchange": "mx.old", "preference": 10, "ttl": 600}]}),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    dns.dns_patch_record(
        "example.com",
        type="MX",
        add='[{"exchange":"mx.ignored","preference":20}]',
        replace='[{"exchange":"mx.new","preference":10}]',
    )
    _, _, params = fake_client.calls[-1]
    assert params["records"]["MX"] == [{"exchange": "mx.new", "preference": 10}]


# ---------------------------------------------------------------------------
# dns_get parent-zone fallback for subdomain METHOD_FAILED
# ---------------------------------------------------------------------------

def test_dns_get_falls_back_to_parent_on_failure(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({"TXT": [{"txtdata": "v=spf1 -all", "ttl": 600}]}),
    )
    # First call (subdomain) raises, second (parent) succeeds.
    original_call = fake_client.call
    call_count = {"n": 0}

    def flaky_call(section, method, params=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise BegetAPIError("Failed to get DNS records", code="METHOD_FAILED")
        return original_call(section, method, params)

    fake_client.call = flaky_call  # type: ignore[method-assign]
    out = unwrap_tool_json(dns.dns_get("mail._domainkey.example.com"))
    assert "note" in out
    assert out["parent_zone"] == "_domainkey.example.com"
    assert out["parent"]["result"]["records"]["TXT"]


def test_dns_get_reraises_when_parent_also_fails(fake_client):
    fake_client.set_error(
        "dns", "getData",
        BegetAPIError("Failed to get DNS records", code="METHOD_FAILED"),
    )
    with pytest.raises(BegetAPIError):
        dns.dns_get("mail._domainkey.example.com")


def test_dns_get_does_not_try_parent_for_registrable_zone(fake_client):
    """Root-domain getData failure should NOT try a parent (example.com → 'com')."""
    fake_client.set_error(
        "dns", "getData",
        BegetAPIError("boom", code="METHOD_FAILED"),
    )
    with pytest.raises(BegetAPIError):
        dns.dns_get("example.com")
    # Exactly one getData attempted — no parent attempt.
    assert sum(1 for _, m, _ in fake_client.calls if m == "getData") == 1
