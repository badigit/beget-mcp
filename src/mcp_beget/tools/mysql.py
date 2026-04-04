from ..app import mcp
from ..client import get_client
from . import _json


@mcp.tool()
def mysql_list() -> str:
    """Все базы данных MySQL на аккаунте."""
    return _json(get_client().call("mysql", "getList"))


@mcp.tool()
def mysql_add(suffix: str, password: str) -> str:
    """Добавить базу MySQL. Итоговое имя: login_suffix.

    Args:
        suffix: Суффикс имени БД
        password: Пароль для доступа к БД
    """
    return _json(
        get_client().call(
            "mysql",
            "addDb",
            {
                "suffix": suffix,
                "password": password,
            },
        )
    )


@mcp.tool()
def mysql_delete(suffix: str) -> str:
    """Убрать базу данных MySQL.

    Args:
        suffix: Суффикс имени БД
    """
    return _json(get_client().call("mysql", "dropDb", {"suffix": suffix}))


@mcp.tool()
def mysql_change_password(suffix: str, password: str, access: str = "localhost") -> str:
    """Сменить пароль к базе MySQL.

    Args:
        suffix: Суффикс имени БД
        password: Новый пароль
        access: Хост доступа (по умолчанию localhost)
    """
    return _json(
        get_client().call(
            "mysql",
            "changeAccessPassword",
            {
                "suffix": suffix,
                "access": access,
                "password": password,
            },
        )
    )


@mcp.tool()
def mysql_add_access(suffix: str, access: str, password: str) -> str:
    """Открыть доступ к базе MySQL с указанного хоста.

    Args:
        suffix: Суффикс имени БД
        access: Откуда разрешить доступ (IP, домен, localhost или * для всех)
        password: Пароль (минимум 6 символов)
    """
    return _json(
        get_client().call(
            "mysql",
            "addAccess",
            {
                "suffix": suffix,
                "access": access,
                "password": password,
            },
        )
    )


@mcp.tool()
def mysql_drop_access(suffix: str, access: str) -> str:
    """Отозвать доступ к базе MySQL с указанного хоста.

    Args:
        suffix: Суффикс имени БД
        access: Хост доступа для удаления (IP, домен, localhost или *)
    """
    return _json(
        get_client().call(
            "mysql",
            "dropAccess",
            {
                "suffix": suffix,
                "access": access,
            },
        )
    )
