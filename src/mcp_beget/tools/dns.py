import json

from ..app import mcp
from ..client import get_client
from . import _json
from .annotations import DESTRUCTIVE, READ_ONLY


@mcp.tool(annotations=READ_ONLY)
def dns_get(fqdn: str) -> str:
    """DNS-записи домена.

    Args:
        fqdn: Имя домена (например: site.ru или sub.site.ru)
    """
    return _json(get_client().call("dns", "getData", {"fqdn": fqdn}))


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_a(fqdn: str, address: str, ttl: int = 300) -> str:
    """Задать A-запись (IPv4) для домена. Перезаписывает прежние A-записи.

    Args:
        fqdn: Имя домена (например: site.ru или mcp.site.ru)
        address: IPv4-адрес (например: 203.0.113.1)
        ttl: Время жизни записи в секундах (по умолчанию 300)
    """
    return _json(
        get_client().call(
            "dns",
            "changeRecords",
            {
                "fqdn": fqdn,
                "records": {"A": [{"address": address, "ttl": ttl}]},
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_cname(fqdn: str, cname: str, ttl: int = 300) -> str:
    """Задать CNAME-запись для поддомена. Применимо только к поддоменам.

    Args:
        fqdn: Имя поддомена (например: www.site.ru)
        cname: Каноническое имя (например: site.ru)
        ttl: Время жизни записи в секундах (по умолчанию 300)
    """
    return _json(
        get_client().call(
            "dns",
            "changeRecords",
            {
                "fqdn": fqdn,
                "records": {"CNAME": [{"cname": cname, "ttl": ttl}]},
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_txt(fqdn: str, txtdata: str, ttl: int = 300) -> str:
    """Задать TXT-запись домена (SPF, верификация и пр.).

    Args:
        fqdn: Имя домена
        txtdata: Содержимое TXT-записи (например: v=spf1 include:mail.ru ~all)
        ttl: Время жизни записи в секундах (по умолчанию 300)
    """
    return _json(
        get_client().call(
            "dns",
            "changeRecords",
            {
                "fqdn": fqdn,
                "records": {"TXT": [{"txtdata": txtdata, "ttl": ttl}]},
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_mx(fqdn: str, exchange: str, preference: int = 10, ttl: int = 300) -> str:
    """Задать MX-запись (почтовый сервер) домена.

    Args:
        fqdn: Имя домена
        exchange: Имя почтового сервера (например: mx1.beget.com.)
        preference: Приоритет (чем меньше, тем выше приоритет)
        ttl: Время жизни записи в секундах (по умолчанию 300)
    """
    return _json(
        get_client().call(
            "dns",
            "changeRecords",
            {
                "fqdn": fqdn,
                "records": {"MX": [{"exchange": exchange, "preference": preference, "ttl": ttl}]},
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_records(fqdn: str, records: str) -> str:
    """Произвольная замена DNS-записей домена.

    Перезаписывает записи указанных типов. Остальные не затрагиваются.

    Args:
        fqdn: Имя домена
        records: JSON с записями, например:
            {"A": [{"address": "1.2.3.4", "ttl": 300}]}
    """
    return _json(
        get_client().call(
            "dns",
            "changeRecords",
            {
                "fqdn": fqdn,
                "records": json.loads(records),
            },
        )
    )
