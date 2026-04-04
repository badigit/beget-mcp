from ..app import mcp
from ..client import get_client
from . import _json


@mcp.tool()
def ftp_list() -> str:
    """Все FTP-аккаунты на хостинге."""
    return _json(get_client().call("ftp", "getList"))


@mcp.tool()
def ftp_add(suffix: str, homedir: str, password: str) -> str:
    """Добавить FTP-аккаунт. Итоговый логин: login_suffix.

    Args:
        suffix: Суффикс логина
        homedir: Домашняя директория (например: site.ru/public_html)
        password: Пароль FTP
    """
    return _json(
        get_client().call(
            "ftp",
            "add",
            {
                "suffix": suffix,
                "homedir": homedir,
                "password": password,
            },
        )
    )


@mcp.tool()
def ftp_delete(suffix: str) -> str:
    """Убрать FTP-аккаунт.

    Args:
        suffix: Суффикс логина FTP
    """
    return _json(get_client().call("ftp", "delete", {"suffix": suffix}))


@mcp.tool()
def ftp_change_password(suffix: str, password: str) -> str:
    """Сменить пароль FTP-аккаунта.

    Args:
        suffix: Суффикс логина FTP
        password: Новый пароль
    """
    return _json(
        get_client().call(
            "ftp",
            "changePassword",
            {
                "suffix": suffix,
                "password": password,
            },
        )
    )
