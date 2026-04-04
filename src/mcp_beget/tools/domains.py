import json

from ..app import mcp
from ..client import get_client
from . import _json


@mcp.tool()
def domain_list() -> str:
    """Все домены, привязанные к аккаунту."""
    return _json(get_client().call("domain", "getList"))


@mcp.tool()
def domain_add(hostname: str, zone_id: int = 1) -> str:
    """Зарегистрировать виртуальный домен (без покупки).

    Args:
        hostname: Имя домена (например: example.com)
        zone_id: ID доменной зоны (1 = .ru). Получить список: domain_zones
    """
    return _json(
        get_client().call(
            "domain",
            "addVirtual",
            {
                "hostname": hostname,
                "zone_id": zone_id,
            },
        )
    )


@mcp.tool()
def domain_delete(domain_id: int) -> str:
    """Убрать домен из аккаунта.

    Args:
        domain_id: ID домена
    """
    return _json(get_client().call("domain", "delete", {"id": domain_id}))


@mcp.tool()
def domain_zones() -> str:
    """Доступные доменные зоны (.ru, .com и пр.)."""
    return _json(get_client().call("domain", "getZoneList"))


@mcp.tool()
def domain_subdomains() -> str:
    """Все поддомены аккаунта."""
    return _json(get_client().call("domain", "getSubdomainList"))


@mcp.tool()
def domain_php_version(full_fqdn: str) -> str:
    """Текущая версия PHP на домене.

    Args:
        full_fqdn: Полное имя домена (например: site.ru)
    """
    return _json(get_client().call("domain", "getPhpVersion", {"full_fqdn": full_fqdn}))


@mcp.tool()
def domain_change_php(full_fqdn: str, php_version: str) -> str:
    """Переключить версию PHP для домена.

    Args:
        full_fqdn: Полное имя домена (например: site.ru)
        php_version: Версия PHP (например: 8.1, 8.2, 8.3)
    """
    return _json(
        get_client().call(
            "domain",
            "changePhpVersion",
            {
                "full_fqdn": full_fqdn,
                "php_version": php_version,
            },
        )
    )


@mcp.tool()
def domain_add_subdomain(subdomain: str, domain_id: int) -> str:
    """Создать поддомен на базе существующего домена.

    Args:
        subdomain: Имя поддомена (например: blog)
        domain_id: ID родительского домена
    """
    return _json(
        get_client().call(
            "domain",
            "addSubdomainVirtual",
            {
                "subdomain": subdomain,
                "domain_id": domain_id,
            },
        )
    )


@mcp.tool()
def domain_delete_subdomain(subdomain_id: int) -> str:
    """Убрать поддомен.

    Args:
        subdomain_id: ID поддомена
    """
    return _json(get_client().call("domain", "deleteSubdomain", {"id": subdomain_id}))


@mcp.tool()
def domain_check_to_register(hostname: str, zone_id: int, period: int = 1) -> str:
    """Проверка доступности домена для покупки.

    Args:
        hostname: Имя домена (например: example)
        zone_id: ID доменной зоны
        period: Период регистрации в годах (по умолчанию 1)
    """
    return _json(
        get_client().call(
            "domain",
            "checkDomainToRegister",
            {
                "hostname": hostname,
                "zone_id": zone_id,
                "period": period,
            },
        )
    )


@mcp.tool()
def domain_get_directives(full_fqdn: str) -> str:
    """Пользовательские PHP-директивы домена.

    Args:
        full_fqdn: Полное имя домена (например: site.ru)
    """
    return _json(get_client().call("domain", "getDirectives", {"full_fqdn": full_fqdn}))


@mcp.tool()
def domain_add_directives(full_fqdn: str, directives: str) -> str:
    """Задать PHP-директивы для домена.

    Args:
        full_fqdn: Полное имя домена
        directives: JSON-массив директив, например: [{"name": "max_execution_time", "value": "60"}]
    """
    return _json(
        get_client().call(
            "domain",
            "addDirectives",
            {
                "full_fqdn": full_fqdn,
                "directives_list": json.loads(directives),
            },
        )
    )


@mcp.tool()
def domain_remove_directives(full_fqdn: str, directives: str) -> str:
    """Снять PHP-директивы с домена.

    Args:
        full_fqdn: Полное имя домена
        directives: JSON-массив директив, например:
            [{"name": "max_execution_time", "value": "60"}]
    """
    return _json(
        get_client().call(
            "domain",
            "removeDirectives",
            {
                "full_fqdn": full_fqdn,
                "directives_list": json.loads(directives),
            },
        )
    )
