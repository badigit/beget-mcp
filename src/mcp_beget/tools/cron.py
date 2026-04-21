from ..app import mcp
from ..client import get_client
from . import _json
from .annotations import DESTRUCTIVE, MUTATING, READ_ONLY


@mcp.tool(annotations=READ_ONLY)
def cron_list() -> str:
    """Все cron-задачи аккаунта."""
    return _json(get_client().call("cron", "getList"))


@mcp.tool(annotations=MUTATING)
def cron_add(
    minutes: str,
    hours: str,
    days: str,
    months: str,
    weekdays: str,
    command: str,
) -> str:
    """Зарегистрировать новую cron-задачу.

    Args:
        minutes: Минуты (0-59, * или */N)
        hours: Часы (0-23, * или */N)
        days: Дни месяца (1-31, * или */N)
        months: Месяцы (1-12, * или */N)
        weekdays: Дни недели (0-7, 0 и 7 = воскресенье)
        command: Команда для выполнения
    """
    return _json(
        get_client().call(
            "cron",
            "add",
            {
                "minutes": minutes,
                "hours": hours,
                "days": days,
                "months": months,
                "weekdays": weekdays,
                "command": command,
            },
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def cron_delete(task_id: int) -> str:
    """Убрать cron-задачу.

    Args:
        task_id: ID задачи
    """
    return _json(get_client().call("cron", "delete", {"row_number": task_id}))


@mcp.tool(annotations=MUTATING)
def cron_edit(
    task_id: int,
    minutes: str | None = None,
    hours: str | None = None,
    days: str | None = None,
    months: str | None = None,
    weekdays: str | None = None,
    command: str | None = None,
) -> str:
    """Изменить параметры cron-задачи. Указывайте только обновляемые поля.

    Args:
        task_id: ID задачи
        minutes: Минуты (0-59, * или */N)
        hours: Часы (0-23, * или */N)
        days: Дни месяца (1-31, * или */N)
        months: Месяцы (1-12, * или */N)
        weekdays: Дни недели (0-7)
        command: Команда для выполнения
    """
    params: dict = {"id": task_id}
    if minutes is not None:
        params["minutes"] = minutes
    if hours is not None:
        params["hours"] = hours
    if days is not None:
        params["days"] = days
    if months is not None:
        params["months"] = months
    if weekdays is not None:
        params["weekdays"] = weekdays
    if command is not None:
        params["command"] = command
    return _json(get_client().call("cron", "edit", params))


@mcp.tool(annotations=MUTATING)
def cron_toggle(task_id: int, is_hidden: int) -> str:
    """Переключить активность cron-задачи.

    Args:
        task_id: ID задачи (полученный из cron_list)
        is_hidden: 1 = выключить (скрыть), 0 = включить
    """
    return _json(
        get_client().call(
            "cron",
            "changeHiddenState",
            {
                "row_number": task_id,
                "is_hidden": is_hidden,
            },
        )
    )


@mcp.tool(annotations=READ_ONLY)
def cron_get_email() -> str:
    """Адрес уведомлений о выполнении cron-задач."""
    return _json(get_client().call("cron", "getEmail"))


@mcp.tool(annotations=MUTATING)
def cron_set_email(email: str) -> str:
    """Назначить email для отчётов cron. Пустая строка отключает уведомления.

    Args:
        email: Email-адрес или пустая строка для отключения
    """
    return _json(get_client().call("cron", "setEmail", {"email": email}))
