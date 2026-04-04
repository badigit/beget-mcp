from ..app import mcp
from ..client import get_client
from . import _json


@mcp.tool()
def site_list() -> str:
    """Все сайты аккаунта и связанные с ними домены."""
    return _json(get_client().call("site", "getList"))


@mcp.tool()
def site_add(name: str) -> str:
    """Зарегистрировать сайт. В файловой системе появится каталог name/public_html.

    Args:
        name: Имя сайта (латиницей)
    """
    return _json(get_client().call("site", "add", {"name": name}))


@mcp.tool()
def site_delete(site_id: int) -> str:
    """Убрать сайт из аккаунта.

    Args:
        site_id: ID сайта (получить через site_list)
    """
    return _json(get_client().call("site", "delete", {"id": site_id}))


@mcp.tool()
def site_link_domain(site_id: int, domain_id: int) -> str:
    """Назначить домен для сайта.

    Args:
        site_id: ID сайта
        domain_id: ID домена
    """
    return _json(
        get_client().call(
            "site",
            "linkDomain",
            {
                "domain_id": domain_id,
                "site_id": site_id,
            },
        )
    )


@mcp.tool()
def site_unlink_domain(domain_id: int) -> str:
    """Снять привязку домена от сайта.

    Args:
        domain_id: ID домена
    """
    return _json(get_client().call("site", "unlinkDomain", {"domain_id": domain_id}))


@mcp.tool()
def site_freeze(site_id: int, excluded_paths: list[str] | None = None) -> str:
    """Блокировка изменений файлов сайта. Активируется в течение 5-10 минут.

    Args:
        site_id: ID сайта
        excluded_paths: Пути-исключения, где изменения останутся разрешены
    """
    params: dict = {"id": site_id}
    if excluded_paths:
        params["excludedPaths"] = excluded_paths
    return _json(get_client().call("site", "freeze", params))


@mcp.tool()
def site_unfreeze(site_id: int) -> str:
    """Снять блокировку изменений файлов сайта. Активируется в течение 5-10 минут.

    Args:
        site_id: ID сайта
    """
    return _json(get_client().call("site", "unfreeze", {"id": site_id}))


@mcp.tool()
def site_is_frozen(site_id: int) -> str:
    """Статус блокировки файлов сайта.

    Args:
        site_id: ID сайта
    """
    return _json(get_client().call("site", "isSiteFrozen", {"site_id": site_id}))
