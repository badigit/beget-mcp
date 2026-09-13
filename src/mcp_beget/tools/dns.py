"""DNS tools with read-merge-write semantics.

Beget's ``dns/changeRecords`` is a zone-wide replace: any record type not
included in the request gets wiped. These tools fetch the current zone state
first, merge the requested change into it, and only then write back — so
calling ``dns_set_txt`` no longer deletes your A/MX/etc.

CAA and SRV records cannot be written via ``changeRecords``. If present in the
zone, tools refuse to proceed (set ``force=True`` to write anyway and lose them).
"""

import json
import time

from ..app import mcp
from ..client import get_client
from ..dnsprobe import probe
from ..errors import BegetAPIError, BegetError
from . import _json
from .annotations import DESTRUCTIVE, READ_ONLY

# Max records per type — source: Beget KB + go.beget.api/api/dns constants.
_LIMITS = {"A": 10, "AAAA": 10, "MX": 10, "TXT": 10, "CNAME": 1, "NS": 10}

# Types that changeRecords cannot round-trip — silently wiped on any write.
_UNWRITABLE_TYPES = ("CAA", "SRV")

# Запись принята панелью != запись отдаётся миру. Между ними — несколько минут.
_PROPAGATION_WARNING = (
    "Принято панелью Beget. Авторитативный NS может отдавать старое значение ещё "
    "несколько минут: dns_get подтвердит запись сразу, потому что читает тот же "
    "источник, куда писал. Перед шагами, зависящими от DNS (выпуск сертификата "
    "Let's Encrypt), подтвердите факт: dns_verify(fqdn, expect=...)."
)

# Зона может отдавать имена, которых в getData нет вовсе.
_CATCHALL_WARNING = (
    "Отсутствие записи в зоне НЕ означает, что имя не резолвится: у зоны может "
    "быть catch-all на shared-хостинг Beget, невидимый для dns/getData. "
    "Поле effective — фактический ответ авторитативного NS по запрошенному FQDN."
)


def _normalize_fqdn(fqdn: str) -> str:
    return fqdn.strip().rstrip(".").lower()


def _strip_trailing_dot(s: str) -> str:
    return s.strip().rstrip(".")


def _get_data(fqdn: str) -> dict:
    """Raw dns/getData. Returns the ``answer`` envelope ({status, result})."""
    return get_client().call("dns", "getData", {"fqdn": fqdn})


def _parent_zone(fqdn: str) -> str | None:
    """Родительская зона поддомена: sub.site.ru -> site.ru. Для site.ru — None."""
    if fqdn.count(".") < 2:
        return None
    return fqdn.split(".", 1)[1]


def _parent_domain_id(parent: str) -> int | None:
    """id родительского домена из domain/getList — сопоставление по fqdn.

    Нужен, чтобы ошибка называла ГОТОВУЮ команду создания поддомена, а не
    отправляла агента искать domain_id самостоятельно.
    """
    try:
        answer = get_client().call("domain", "getList")
    except BegetError:
        return None
    result = answer.get("result") if isinstance(answer, dict) else None
    if not isinstance(result, list):
        return None
    for item in result:
        if not isinstance(item, dict):
            continue
        if str(item.get("fqdn", "")).strip().rstrip(".").lower() != parent:
            continue
        try:
            return int(item.get("id"))
        except (TypeError, ValueError):
            return None
    return None


def _missing_subdomain_error(fqdn: str, cause: str) -> BegetAPIError | None:
    """Ошибка «сущности поддомена нет», если родительская зона при этом читается.

    У Beget поддомен — отдельная сущность, а не запись в зоне родителя. Пока её
    нет, getData по FQDN отвечает METHOD_FAILED. Совет «запишите зону целиком
    через replace_all» для этого случая неверен и опасен: сущность так не
    создаётся, а слепая запись — ровно то, от чего защищает read-merge-write.
    Возвращает None, если причина другая (тогда остаётся прежний NO_ZONE_DATA).
    """
    parent = _parent_zone(fqdn)
    if parent is None:
        return None
    try:
        parent_answer = _get_data(parent)
    except BegetError:
        return None
    parent_result = parent_answer.get("result") if isinstance(parent_answer, dict) else None
    if not isinstance(parent_result, dict) or not parent_result:
        return None

    prefix = fqdn.split(".", 1)[0]
    domain_id = _parent_domain_id(parent)
    call_hint = (
        f"domain_add_subdomain(subdomain='{prefix}', domain_id={domain_id})"
        if domain_id is not None
        else (
            f"domain_add_subdomain(subdomain='{prefix}', domain_id=<id {parent} "
            f"из domain_list>)"
        )
    )
    return BegetAPIError(
        f"{cause} Parent zone {parent} reads fine, so the zone is not broken — "
        f"the subdomain entity {fqdn} was never created in Beget. Create it "
        f"first: {call_hint}, then retry this call. Do NOT use dns_set_records "
        f"with replace_all=True: it does not create the entity.",
        code="SUBDOMAIN_NOT_CREATED",
        details={
            "queried_fqdn": fqdn,
            "parent_zone": parent,
            "fix": {
                "tool": "domain_add_subdomain",
                "subdomain": prefix,
                "domain_id": domain_id,
            },
        },
    )


def _get_result(fqdn: str) -> dict:
    """dns/getData unwrapped to the ``result`` dict (records, set_type, ...).

    Raises BegetAPIError if the zone could not be read. Returning ``{}`` here
    would make read-merge-write silently degrade into a zone-wide wipe: the
    merge would preserve nothing and changeRecords would drop every record
    the caller did not pass.

    Несозданный поддомен отделяется от прочих причин: он лечится
    domain_add_subdomain, а не записью зоны целиком.
    """
    try:
        answer = _get_data(fqdn)
    except BegetAPIError as e:
        # METHOD_FAILED — единственный код, который у Beget значит «такой
        # сущности нет». INVALID_DATA, лимиты и транзиентные сбои отдаём как
        # есть, иначе настоящая причина спрячется за советом создать поддомен.
        if e.code == "METHOD_FAILED":
            hint = _missing_subdomain_error(fqdn, f"dns/getData failed: {e.message}.")
            if hint is not None:
                raise hint from e
        raise

    result = answer.get("result") if isinstance(answer, dict) else None
    if not isinstance(result, dict) or not result:
        hint = _missing_subdomain_error(
            fqdn, f"dns/getData returned no zone data for {fqdn}."
        )
        if hint is not None:
            raise hint
        raise BegetAPIError(
            f"dns/getData returned no zone data for {fqdn} — refusing to write "
            f"blind, as changeRecords would wipe the existing records. To write "
            f"the full zone intentionally, use dns_set_records with "
            f"replace_all=True.",
            code="NO_ZONE_DATA",
            details={"answer": answer},
        )
    return result


def _detect_unwritable(result: dict) -> list[str]:
    records = result.get("records") or {}
    return [t for t in _UNWRITABLE_TYPES if records.get(t)]


def _preserved_records(result: dict) -> dict:
    """Existing records minus types that can't be sent to changeRecords."""
    records = dict(result.get("records") or {})
    for t in _UNWRITABLE_TYPES:
        records.pop(t, None)
    return records


def _merge_set(
    fqdn: str,
    overrides: dict[str, list[dict]],
    force: bool = False,
) -> dict:
    """Read existing zone, replace listed types with ``overrides``, write back.

    Raises BegetAPIError if zone has CAA/SRV and ``force`` is False.
    """
    fqdn = _normalize_fqdn(fqdn)

    current = _get_result(fqdn)
    unwritable = _detect_unwritable(current)
    warnings: list[str] = []

    if unwritable and not force:
        raise BegetAPIError(
            f"Zone {fqdn} contains {'/'.join(unwritable)} records — "
            f"dns/changeRecords cannot preserve them and would wipe them. "
            f"Re-call with force=True to proceed and accept the loss.",
            code="UNWRITABLE_RECORDS_PRESENT",
            details={"types": unwritable, "records": current.get("records", {})},
        )
    if unwritable and force:
        warnings.append(
            f"{'/'.join(unwritable)} records present and WILL BE LOST: "
            f"Beget's changeRecords cannot write them back."
        )

    merged = _preserved_records(current)

    for t, recs in overrides.items():
        limit = _LIMITS.get(t)
        if limit is not None and len(recs) > limit:
            raise BegetAPIError(
                f"Too many {t} records: {len(recs)} > max {limit}",
                code="TOO_MANY_RECORDS",
                details={"type": t, "count": len(recs), "limit": limit},
            )
        merged[t] = recs

    response = get_client().call(
        "dns", "changeRecords", {"fqdn": fqdn, "records": merged}
    )

    ttl_in_overrides = any(
        any("ttl" in r for r in recs) for recs in overrides.values()
    )
    if ttl_in_overrides:
        warnings.append(
            "TTL is set per-zone by Beget (typically clamped to 600s). "
            "Per-record TTL in the request may be ignored — verify with dns_get."
        )
    warnings.append(_PROPAGATION_WARNING)

    return {"status": "success", "warnings": warnings, "records_sent": merged, "api": response}


@mcp.tool(annotations=READ_ONLY)
def dns_get(fqdn: str, check_effective: bool = True) -> str:
    """DNS-записи FQDN плюс фактический ответ авторитативного NS.

    В Beget поддомен — отдельная сущность со своим getData. Если прямой запрос
    вернул METHOD_FAILED, функция пробует родительскую зону и возвращает её
    records с пометкой (актуально для DKIM типа mail._domainkey.site.ru,
    которые иногда хранятся на уровне родителя).

    ВАЖНО: отсутствие записи в зоне НЕ означает, что имя не резолвится. У зоны
    бывает catch-all на shared-хостинг Beget, невидимый для dns/getData: имя
    отвечает чужим адресом, хотя в выдаче API его нет. Поле ``effective`` —
    фактический ответ авторитативного NS зоны, запрошенный напрямую по UDP
    мимо кеша резолвера. Расхождение «в зоне нет, а отвечает» видно сразу.

    Args:
        fqdn: Имя домена (site.ru или sub.site.ru)
        check_effective: Спросить авторитативный NS (по умолчанию да)
    """
    fqdn_n = _normalize_fqdn(fqdn)
    effective = probe(fqdn_n) if check_effective else None

    def _with_effective(payload: dict) -> dict:
        if effective is None:
            return payload
        return {**payload, "effective": effective, "effective_note": _CATCHALL_WARNING}

    try:
        return _json(_with_effective(_get_data(fqdn_n)))
    except BegetAPIError as e:
        # Только METHOD_FAILED значит «такой сущности нет». INVALID_DATA,
        # rate-limit и транзиентные сбои отдаём как есть: иначе фолбэк подменит
        # их записями родителя и note про несуществующий поддомен, спрятав
        # настоящую причину.
        if e.code != "METHOD_FAILED":
            raise
        parent = _parent_zone(fqdn_n)
        if parent is None:
            raise
        try:
            parent_answer = _get_data(parent)
        except BegetAPIError:
            raise e from None
        return _json(
            _with_effective(
                {
                    "note": (
                        f"getData({fqdn_n}) failed: {e.message}. "
                        f"Subdomain entity likely does not exist in Beget "
                        f"(create it with domain_add_subdomain). "
                        f"Returning parent zone {parent} so you can see what is there."
                    ),
                    "queried_fqdn": fqdn_n,
                    "parent_zone": parent,
                    "parent": parent_answer,
                }
            )
        )


@mcp.tool(annotations=READ_ONLY)
def dns_verify(
    fqdn: str, expect: str = "", type: str = "A", timeout: int = 120
) -> str:
    """Подтвердить факт у авторитативного NS зоны: отдаётся ли значение миру.

    success от dns_set_* означает «принято панелью», а dns_get подтверждает
    ровно это — он читает тот же источник, куда писал. Авторитативный NS может
    отдавать старое значение ещё несколько минут. Запуск certbot в этом окне
    сжигает попытку и приближает лимит Let's Encrypt на домен.

    Тул опрашивает авторитативные NS зоны напрямую по UDP (мимо кеша любого
    резолвера) до совпадения с ``expect`` или до дедлайна.

    Вручную сверять надо ``nslookup``, а НЕ ``Resolve-DnsName -Server``: флаг
    -Server не обходит клиентский кеш Windows и отдаёт устаревшее значение.

    Args:
        fqdn: Имя, которое проверяем
        expect: Ожидаемое значение (IP для A, имя для CNAME/MX). Пусто — просто
            вернуть текущий ответ NS одним запросом, без ожидания
        type: Тип записи (A, AAAA, CNAME, MX, TXT, NS)
        timeout: Сколько секунд ждать совпадения (по умолчанию 120)
    """
    fqdn_n = _normalize_fqdn(fqdn)
    type_u = type.upper()
    expect_n = _strip_trailing_dot(expect).lower() if expect else ""

    deadline = time.monotonic() + max(0, timeout)
    attempts = 0
    started = time.monotonic()
    while True:
        attempts += 1
        observed = probe(fqdn_n, type_u)
        values = [str(v).lower() for v in observed.get("values", [])]
        matched = bool(expect_n) and expect_n in values
        if matched or not expect_n or time.monotonic() >= deadline:
            return _json(
                {
                    "fqdn": fqdn_n,
                    "type": type_u,
                    "expect": expect_n or None,
                    "matched": matched if expect_n else None,
                    "observed": observed,
                    "attempts": attempts,
                    "waited_seconds": round(time.monotonic() - started, 1),
                    "note": (
                        _CATCHALL_WARNING
                        if not expect_n
                        else (
                            "Совпало: значение отдаётся авторитативным NS."
                            if matched
                            else (
                                "Не совпало за отведённое время. Запись может быть "
                                "принята панелью и ещё не распространена — повторите "
                                "dns_verify позже, до действий, зависящих от DNS."
                            )
                        )
                    ),
                }
            )
        time.sleep(min(5, max(1, deadline - time.monotonic())))


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_a(fqdn: str, address: str, ttl: int = 600, force: bool = False) -> str:
    """Задать A-запись (IPv4) для FQDN.

    Безопасно: делает getData → merge → changeRecords. Прочие записи (MX, TXT,
    CNAME, NS) в зоне сохраняются. Прежние A-записи заменяются на переданную.

    TTL: Beget управляет TTL на уровне зоны (типичный минимум 600 сек) и может
    игнорировать значение в запросе. Параметр оставлен для совместимости.

    Если в зоне есть CAA/SRV — вернёт ошибку (changeRecords их затирает).
    Передайте force=True, чтобы продолжить и потерять их.

    Args:
        fqdn: Имя домена
        address: IPv4-адрес (203.0.113.1)
        ttl: TTL в секундах (может быть проигнорирован; по умолчанию 600)
        force: Продолжить при наличии CAA/SRV (они будут удалены)
    """
    return _json(_merge_set(fqdn, {"A": [{"address": address, "ttl": ttl}]}, force))


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_cname(fqdn: str, cname: str, ttl: int = 600, force: bool = False) -> str:
    """Задать CNAME-запись для поддомена.

    Безопасно мерджится с существующими записями. ВАЖНО: у Beget set_type у зоны
    при CNAME становится эксклюзивным (A/MX/TXT при этом не работают). Используйте
    CNAME только на поддоменах, где у вас нет других записей.

    Args:
        fqdn: Имя поддомена (www.site.ru)
        cname: Каноническое имя (site.ru — автоматически без trailing dot)
        ttl: TTL в секундах (см. dns_set_a)
        force: Продолжить при наличии CAA/SRV
    """
    cname_n = _strip_trailing_dot(cname)
    return _json(_merge_set(fqdn, {"CNAME": [{"cname": cname_n, "ttl": ttl}]}, force))


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_txt(fqdn: str, txtdata: str, ttl: int = 600, force: bool = False) -> str:
    """Задать TXT-запись (SPF, верификация, DKIM и пр.).

    Заменяет все TXT-записи одной. Если нужно добавить к существующим (верификация
    + SPF, например) — используйте dns_patch_record с add=...

    Прочие записи (A/MX/CNAME/NS) сохраняются.

    Args:
        fqdn: Имя домена
        txtdata: Содержимое TXT-записи (v=spf1 redirect=_spf.yandex.net)
        ttl: TTL в секундах (см. dns_set_a)
        force: Продолжить при наличии CAA/SRV
    """
    return _json(_merge_set(fqdn, {"TXT": [{"txtdata": txtdata, "ttl": ttl}]}, force))


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_mx(
    fqdn: str, exchange: str, preference: int = 10, ttl: int = 600, force: bool = False
) -> str:
    """Задать MX-запись (почтовый сервер) домена.

    Заменяет все MX-записи одной. Прочие типы записей в зоне сохраняются.
    Для нескольких MX за один вызов — используйте dns_set_records.

    Args:
        fqdn: Имя домена
        exchange: Имя сервера (mx.yandex.net — trailing dot снимается автоматически)
        preference: Приоритет (меньше = выше)
        ttl: TTL в секундах (см. dns_set_a)
        force: Продолжить при наличии CAA/SRV
    """
    exchange_n = _strip_trailing_dot(exchange)
    return _json(
        _merge_set(
            fqdn,
            {"MX": [{"exchange": exchange_n, "preference": preference, "ttl": ttl}]},
            force,
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
def dns_set_records(
    fqdn: str, records: str, replace_all: bool = False, force: bool = False
) -> str:
    """Задать несколько типов DNS-записей одним вызовом.

    По умолчанию — безопасный merge: типы, отсутствующие в records, сохраняются.
    replace_all=True — полная замена зоны (как делает голый dns/changeRecords):
    ВСЕ записи, кроме переданных, будут удалены.

    Args:
        fqdn: Имя домена
        records: JSON с записями, например:
            {"A": [{"address": "1.2.3.4"}],
             "MX": [{"exchange": "mx.yandex.net", "preference": 10}]}
        replace_all: True — полная замена зоны; по умолчанию False (merge)
        force: Продолжить при наличии CAA/SRV (будут удалены)
    """
    parsed = json.loads(records)
    fqdn_n = _normalize_fqdn(fqdn)

    if replace_all:
        return _json(
            get_client().call(
                "dns", "changeRecords", {"fqdn": fqdn_n, "records": parsed}
            )
        )
    return _json(_merge_set(fqdn_n, parsed, force))


@mcp.tool(annotations=DESTRUCTIVE)
def dns_patch_record(
    fqdn: str,
    type: str,
    add: str = "[]",
    remove: str = "[]",
    replace: str = "",
    force: bool = False,
) -> str:
    """Частично изменить записи одного типа (add/remove/replace).

    Внутри: getData → merge → changeRecords. Прочие типы в зоне не затрагиваются.
    Удобно для многозначных TXT (SPF + DKIM + verification) и нескольких MX.

    - ``add`` — JSON-массив записей для добавления к существующим
    - ``remove`` — JSON-массив записей для удаления (match по полям кроме ttl)
    - ``replace`` — JSON-массив для полной замены массива этого типа (если задан,
      add и remove игнорируются)

    Примеры:
        type="TXT", add='[{"txtdata":"google-site-verification=abc"}]' — добавить
            к существующим TXT-записям
        type="TXT", remove='[{"txtdata":"v=spf1 include:old.example"}]' — снять
            старую SPF
        type="MX", replace='[{"exchange":"mx.yandex.net","preference":10}]' —
            заменить весь массив MX одной записью

    Args:
        fqdn: Имя домена
        type: Тип записи (A, AAAA, MX, TXT, CNAME, NS)
        add: JSON-массив для добавления
        remove: JSON-массив для удаления
        replace: JSON-массив для полной замены этого типа
        force: Продолжить при наличии CAA/SRV
    """
    fqdn_n = _normalize_fqdn(fqdn)
    type_u = type.upper()

    current = _get_result(fqdn_n)
    existing = list((current.get("records") or {}).get(type_u, []) or [])

    if replace:
        new_list = json.loads(replace)
    else:
        add_list = json.loads(add) if add else []
        remove_list = json.loads(remove) if remove else []

        def _eq_ignore_ttl(a: dict, b: dict) -> bool:
            return {k: v for k, v in a.items() if k != "ttl"} == {
                k: v for k, v in b.items() if k != "ttl"
            }

        kept = [r for r in existing if not any(_eq_ignore_ttl(r, rm) for rm in remove_list)]
        new_list = kept + add_list

    return _json(_merge_set(fqdn_n, {type_u: new_list}, force))
