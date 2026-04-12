from ..app import mcp
from ..client import get_client
from . import _json
from .annotations import MUTATING, READ_ONLY


@mcp.tool(annotations=READ_ONLY)
def account_info() -> str:
    """Сведения об аккаунте: баланс, тариф, ресурсы, сервер."""
    return _json(get_client().call("user", "getAccountInfo"))


@mcp.tool(annotations=MUTATING)
def toggle_ssh(status: int, ftplogin: str = "") -> str:
    """Переключить SSH-доступ для основного или FTP-аккаунта.

    Args:
        status: 1 = включить, 0 = выключить
        ftplogin: Логин FTP-аккаунта (если пусто — применяется к основному аккаунту)
    """
    params: dict = {"status": status}
    if ftplogin:
        params["ftplogin"] = ftplogin
    return _json(get_client().call("user", "toggleSsh", params))


@mcp.tool(annotations=READ_ONLY)
def stat_site_list_load() -> str:
    """Средняя нагрузка по всем сайтам за месяц."""
    return _json(get_client().call("stat", "getSitesListLoad"))


@mcp.tool(annotations=READ_ONLY)
def stat_db_list_load() -> str:
    """Средняя нагрузка по всем базам данных за месяц."""
    return _json(get_client().call("stat", "getDbListLoad"))


@mcp.tool(annotations=READ_ONLY)
def stat_site_load(site_id: int) -> str:
    """Детальная статистика нагрузки сайта (почасовая и посуточная за месяц).

    Args:
        site_id: ID сайта
    """
    return _json(get_client().call("stat", "getSiteLoad", {"site_id": site_id}))


@mcp.tool(annotations=READ_ONLY)
def stat_db_load(db_name: str) -> str:
    """Детальная статистика нагрузки БД: CPU, размер, почасовая и посуточная.

    Args:
        db_name: Имя базы данных
    """
    return _json(get_client().call("stat", "getDbLoad", {"db_name": db_name}))
