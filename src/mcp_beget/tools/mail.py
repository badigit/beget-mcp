from ..app import mcp
from ..client import get_client
from . import _json
from .annotations import DESTRUCTIVE, MUTATING, READ_ONLY


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
