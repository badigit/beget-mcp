from ..app import mcp
from ..client import get_client
from . import _json
from .annotations import DESTRUCTIVE, MUTATING, READ_ONLY
from .dns import _get_result, _merge_set, _normalize_fqdn


@mcp.tool(annotations=READ_ONLY)
def mail_list(domain: str) -> str:
    """Почтовые ящики на указанном домене.

    Args:
        domain: Домен (например: site.ru)
    """
    return _json(get_client().call("mail", "getMailboxList", {"domain": domain}))


@mcp.tool(annotations=MUTATING)
def mail_create(domain: str, mailbox: str, password: str) -> str:
    """Добавить почтовый ящик.

    Args:
        domain: Домен (например: site.ru)
        mailbox: Имя ящика (часть до @)
        password: Пароль
    """
    return _json(
        get_client().call(
            "mail",
            "createMailbox",
            {
                "domain": domain,
                "mailbox": mailbox,
                "mailbox_password": password,
            },
        )
    )


@mcp.tool(annotations=MUTATING)
def mail_change_password(domain: str, mailbox: str, password: str) -> str:
    """Сменить пароль почтового ящика.

    Args:
        domain: Домен (например: site.ru)
        mailbox: Имя ящика (часть до @)
        password: Новый пароль
    """
    return _json(
        get_client().call(
            "mail",
            "changeMailboxPassword",
            {
                "domain": domain,
                "mailbox": mailbox,
                "mailbox_password": password,
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def mail_delete(domain: str, mailbox: str) -> str:
    """Убрать почтовый ящик.

    Args:
        domain: Домен
        mailbox: Имя ящика (часть до @)
    """
    return _json(
        get_client().call(
            "mail",
            "dropMailbox",
            {
                "domain": domain,
                "mailbox": mailbox,
            },
        )
    )


@mcp.tool(annotations=MUTATING)
def mail_change_settings(
    domain: str,
    mailbox: str,
    spam_filter_status: int = -1,
    spam_filter: int = -1,
    forward_mail_status: str = "",
) -> str:
    """Настройки почтового ящика: спам-фильтр и пересылка.

    Args:
        domain: Домен
        mailbox: Имя ящика
        spam_filter_status: 1 = включить спам-фильтр, 0 = выключить (-1 = не менять)
        spam_filter: Уровень фильтрации (-1 = не менять)
        forward_mail_status: no_forward / forward / forward_and_delete (пусто = не менять)
    """
    params: dict = {"domain": domain, "mailbox": mailbox}
    if spam_filter_status >= 0:
        params["spam_filter_status"] = spam_filter_status
    if spam_filter >= 0:
        params["spam_filter"] = spam_filter
    if forward_mail_status:
        params["forward_mail_status"] = forward_mail_status
    return _json(get_client().call("mail", "changeMailboxSettings", params))


@mcp.tool(annotations=MUTATING)
def mail_forward_add(domain: str, mailbox: str, forward_mailbox: str) -> str:
    """Включить пересылку на указанный адрес.

    Args:
        domain: Домен
        mailbox: Имя ящика
        forward_mailbox: Email для пересылки
    """
    return _json(
        get_client().call(
            "mail",
            "forwardListAddMailbox",
            {
                "domain": domain,
                "mailbox": mailbox,
                "forward_mailbox": forward_mailbox,
            },
        )
    )


@mcp.tool(annotations=MUTATING)
def mail_forward_delete(domain: str, mailbox: str, forward_mailbox: str) -> str:
    """Снять пересылку на указанный адрес.

    Args:
        domain: Домен
        mailbox: Имя ящика
        forward_mailbox: Email для удаления из пересылки
    """
    return _json(
        get_client().call(
            "mail",
            "forwardListDeleteMailbox",
            {
                "domain": domain,
                "mailbox": mailbox,
                "forward_mailbox": forward_mailbox,
            },
        )
    )


@mcp.tool(annotations=READ_ONLY)
def mail_forward_list(domain: str, mailbox: str) -> str:
    """Адреса пересылки для ящика.

    Args:
        domain: Домен
        mailbox: Имя ящика
    """
    return _json(
        get_client().call(
            "mail",
            "forwardListShow",
            {
                "domain": domain,
                "mailbox": mailbox,
            },
        )
    )


@mcp.tool(annotations=MUTATING)
def mail_set_domain_mail(domain: str, domain_mailbox: str) -> str:
    """Назначить catch-all ящик для домена.

    Args:
        domain: Домен
        domain_mailbox: Имя ящика, на который будет приходить вся почта домена
    """
    return _json(
        get_client().call(
            "mail",
            "setDomainMail",
            {
                "domain": domain,
                "domain_mailbox": domain_mailbox,
            },
        )
    )


@mcp.tool(annotations=MUTATING)
def mail_clear_domain_mail(domain: str) -> str:
    """Отключить catch-all для домена.

    Args:
        domain: Домен
    """
    return _json(get_client().call("mail", "clearDomainMail", {"domain": domain}))


def _setup_mail_provider(
    fqdn: str,
    mx_exchange: str,
    mx_preference: int,
    spf_value: str,
    force: bool = False,
) -> dict:
    """Shared helper for mail provider setup: MX replaced, SPF added (existing
    non-SPF TXT preserved — DKIM/verification tokens stay intact)."""
    fqdn_n = _normalize_fqdn(fqdn)
    current = _get_result(fqdn_n)
    existing_txt = list((current.get("records") or {}).get("TXT") or [])

    non_spf_txt = [
        t for t in existing_txt
        if not t.get("txtdata", "").strip().lower().startswith("v=spf1")
    ]
    new_txt = non_spf_txt + [{"txtdata": spf_value}]

    overrides = {
        "MX": [{"exchange": mx_exchange, "preference": mx_preference}],
        "TXT": new_txt,
    }
    return _merge_set(fqdn_n, overrides, force=force)


@mcp.tool(annotations=DESTRUCTIVE)
def mail_setup_yandex(fqdn: str, force: bool = False) -> str:
    """Прописать MX и SPF для Яндекс 360 одним вызовом.

    Ставит:
      - MX: mx.yandex.net, preference 10 (заменяет существующие MX)
      - TXT SPF: v=spf1 redirect=_spf.yandex.net (заменяет существующую SPF,
        прочие TXT — DKIM, верификации — сохраняются)

    DKIM Яндекс настраивается отдельно (Я.Почта для домена → DKIM), там выдаётся
    ключ для mail._domainkey.<домен>. После получения ключа — dns_set_txt на
    соответствующий поддомен (либо сначала domain_add_subdomain).

    Не трогает A-записи, NS и прочие TXT. Если в зоне есть CAA/SRV — потребует
    force=True (они будут удалены).

    Args:
        fqdn: Имя домена (site.ru)
        force: Продолжить при наличии CAA/SRV
    """
    return _json(_setup_mail_provider(
        fqdn,
        mx_exchange="mx.yandex.net",
        mx_preference=10,
        spf_value="v=spf1 redirect=_spf.yandex.net",
        force=force,
    ))


@mcp.tool(annotations=DESTRUCTIVE)
def mail_setup_mailru(fqdn: str, force: bool = False) -> str:
    """Прописать MX и SPF для Mail.ru для бизнеса одним вызовом.

    Ставит:
      - MX: emx.mail.ru, preference 10
      - TXT SPF: v=spf1 redirect=_spf.mail.ru (прочие TXT сохраняются)

    DKIM настраивается в панели Mail.ru для бизнеса — ключ кладётся на
    mailru._domainkey.<домен>.

    Не трогает A-записи, NS и прочие TXT. Если в зоне есть CAA/SRV — потребует
    force=True.

    Args:
        fqdn: Имя домена
        force: Продолжить при наличии CAA/SRV
    """
    return _json(_setup_mail_provider(
        fqdn,
        mx_exchange="emx.mail.ru",
        mx_preference=10,
        spf_value="v=spf1 redirect=_spf.mail.ru",
        force=force,
    ))
