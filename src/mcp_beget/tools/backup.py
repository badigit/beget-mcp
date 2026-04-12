from ..app import mcp
from ..client import get_client
from . import _json
from .annotations import DESTRUCTIVE, MUTATING, READ_ONLY


@mcp.tool(annotations=READ_ONLY)
def backup_files_list() -> str:
    """Доступные файловые резервные копии."""
    return _json(get_client().call("backup", "getFileBackupList"))


@mcp.tool(annotations=READ_ONLY)
def backup_mysql_list() -> str:
    """Доступные резервные копии баз MySQL."""
    return _json(get_client().call("backup", "getMysqlBackupList"))


@mcp.tool(annotations=DESTRUCTIVE)
def backup_restore_file(backup_id: int, paths: list[str]) -> str:
    """Откатить файлы из резервной копии.

    Args:
        backup_id: ID бэкапа (получить через backup_files_list)
        paths: Список путей для восстановления
    """
    return _json(
        get_client().call(
            "backup",
            "restoreFile",
            {
                "backup_id": backup_id,
                "paths": paths,
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def backup_restore_mysql(backup_id: int, databases: list[str]) -> str:
    """Откатить базу MySQL из резервной копии.

    Args:
        backup_id: ID бэкапа (получить через backup_mysql_list)
        databases: Список имён баз для восстановления
    """
    return _json(
        get_client().call(
            "backup",
            "restoreMysql",
            {
                "backup_id": backup_id,
                "bases": databases,
            },
        )
    )


@mcp.tool(annotations=READ_ONLY)
def backup_file_list(backup_id: int | None = None, path: str = "") -> str:
    """Содержимое файлового бэкапа (файлы и каталоги).

    Args:
        backup_id: ID бэкапа (не указан = текущая копия)
        path: Путь от корня директории (пусто = корень)
    """
    params: dict = {}
    if backup_id is not None:
        params["backup_id"] = backup_id
    if path:
        params["path"] = path
    return _json(get_client().call("backup", "getFileList", params or None))


@mcp.tool(annotations=READ_ONLY)
def backup_mysql_db_list(backup_id: int | None = None) -> str:
    """Базы данных внутри резервной копии.

    Args:
        backup_id: ID бэкапа (не указан = текущая копия)
    """
    params: dict = {}
    if backup_id is not None:
        params["backup_id"] = backup_id
    return _json(get_client().call("backup", "getMysqlList", params or None))


@mcp.tool(annotations=MUTATING)
def backup_download_file(paths: list[str], backup_id: int | None = None) -> str:
    """Выгрузить файлы из бэкапа в корневую директорию аккаунта.

    Args:
        paths: Список путей для скачивания
        backup_id: ID бэкапа (не указан = текущая копия)
    """
    params: dict = {"paths": paths}
    if backup_id is not None:
        params["backup_id"] = backup_id
    return _json(get_client().call("backup", "downloadFile", params))


@mcp.tool(annotations=MUTATING)
def backup_download_mysql(bases: list[str], backup_id: int | None = None) -> str:
    """Выгрузить дамп MySQL из бэкапа в корневую директорию аккаунта.

    Args:
        bases: Список имён баз данных
        backup_id: ID бэкапа (не указан = текущая копия)
    """
    params: dict = {"bases": bases}
    if backup_id is not None:
        params["backup_id"] = backup_id
    return _json(get_client().call("backup", "downloadMysql", params))


@mcp.tool(annotations=READ_ONLY)
def backup_log() -> str:
    """Журнал операций восстановления и скачивания бэкапов."""
    return _json(get_client().call("backup", "getLog"))
