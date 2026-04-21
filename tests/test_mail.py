"""Tests for mail tools: setup helpers, domain normalization."""

from mcp_beget.tools import mail

from .conftest import ok_change, unwrap_tool_json, wrap_getdata

# ---------------------------------------------------------------------------
# mail_setup_yandex / mail_setup_mailru
# ---------------------------------------------------------------------------

def test_mail_setup_yandex_replaces_mx_and_spf_preserving_dkim_like_txt(fake_client):
    """Yandex setup must keep unrelated TXT (DKIM, verification) and replace
    only any existing SPF + all MX."""
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({
            "A": [{"address": "1.2.3.4", "ttl": 600}],
            "MX": [{"exchange": "mx.old", "preference": 10, "ttl": 600}],
            "TXT": [
                {"txtdata": "v=spf1 include:old.example ~all", "ttl": 600},
                {"txtdata": "google-site-verification=abc", "ttl": 600},
            ],
        }),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    unwrap_tool_json(mail.mail_setup_yandex("example.com"))

    _, _, params = fake_client.calls[-1]
    records = params["records"]

    assert records["A"] == [{"address": "1.2.3.4", "ttl": 600}]
    assert records["MX"] == [{"exchange": "mx.yandex.net", "preference": 10}]

    spf = [r for r in records["TXT"] if r["txtdata"].startswith("v=spf1")]
    assert spf == [{"txtdata": "v=spf1 redirect=_spf.yandex.net"}]
    # DKIM-like TXT preserved
    assert {"txtdata": "google-site-verification=abc", "ttl": 600} in records["TXT"]


def test_mail_setup_mailru_sets_correct_values(fake_client):
    fake_client.set_response("dns", "getData", wrap_getdata({}))
    fake_client.set_response("dns", "changeRecords", ok_change())

    mail.mail_setup_mailru("example.com")
    _, _, params = fake_client.calls[-1]
    assert params["records"]["MX"] == [{"exchange": "emx.mail.ru", "preference": 10}]
    assert params["records"]["TXT"] == [{"txtdata": "v=spf1 redirect=_spf.mail.ru"}]


def test_mail_setup_yandex_adds_spf_when_none_existed(fake_client):
    fake_client.set_response(
        "dns", "getData",
        wrap_getdata({"TXT": [{"txtdata": "unrelated", "ttl": 600}]}),
    )
    fake_client.set_response("dns", "changeRecords", ok_change())

    mail.mail_setup_yandex("example.com")
    _, _, params = fake_client.calls[-1]
    spf = [r for r in params["records"]["TXT"] if r["txtdata"].startswith("v=spf1")]
    assert spf == [{"txtdata": "v=spf1 redirect=_spf.yandex.net"}]


# ---------------------------------------------------------------------------
# Domain normalization in mail_*
# ---------------------------------------------------------------------------

def test_mail_list_normalizes_domain(fake_client):
    fake_client.set_response("mail", "getMailboxList", {"status": "success", "result": []})
    mail.mail_list("Example.COM.")
    _, _, params = fake_client.calls[-1]
    assert params == {"domain": "example.com"}


def test_mail_create_normalizes_domain(fake_client):
    fake_client.set_response("mail", "createMailbox", {"status": "success", "result": True})
    mail.mail_create("Example.COM.", "info", "password123")
    _, _, params = fake_client.calls[-1]
    assert params["domain"] == "example.com"
    assert params["mailbox"] == "info"
    assert params["mailbox_password"] == "password123"


def test_mail_change_password_normalizes_domain(fake_client):
    fake_client.set_response("mail", "changeMailboxPassword", {"status": "success", "result": True})
    mail.mail_change_password("Site.RU.", "info", "newpwd")
    _, _, params = fake_client.calls[-1]
    assert params["domain"] == "site.ru"


def test_mail_delete_normalizes_domain(fake_client):
    fake_client.set_response("mail", "dropMailbox", {"status": "success", "result": True})
    mail.mail_delete("Site.RU.", "info")
    _, _, params = fake_client.calls[-1]
    assert params["domain"] == "site.ru"


def test_mail_change_settings_normalizes_domain(fake_client):
    fake_client.set_response("mail", "changeMailboxSettings", {"status": "success", "result": True})
    mail.mail_change_settings("Site.RU.", "info", spam_filter_status=1)
    _, _, params = fake_client.calls[-1]
    assert params["domain"] == "site.ru"
    assert params["spam_filter_status"] == 1
    # Sentinel defaults are not sent
    assert "spam_filter" not in params
    assert "forward_mail_status" not in params


def test_mail_forward_add_normalizes_domain(fake_client):
    fake_client.set_response("mail", "forwardListAddMailbox", {"status": "success", "result": True})
    mail.mail_forward_add("Site.RU.", "info", "target@example.com")
    _, _, params = fake_client.calls[-1]
    assert params["domain"] == "site.ru"


def test_mail_clear_domain_mail_normalizes_domain(fake_client):
    fake_client.set_response("mail", "clearDomainMail", {"status": "success", "result": True})
    mail.mail_clear_domain_mail("Site.RU.")
    _, _, params = fake_client.calls[-1]
    assert params == {"domain": "site.ru"}
