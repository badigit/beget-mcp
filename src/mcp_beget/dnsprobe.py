"""Опрос авторитативного NS зоны — факт вместо намерения.

Beget API отвечает `success` на запись, а `dns/getData` подтверждает её, потому
что читает тот же источник, куда писал. Мир в этот момент может ещё получать
старое значение: авторитативный NS обновляется с задержкой в несколько минут.
Отдельно у зоны бывает catch-all на shared-хостинг, которого в `dns/getData` не
видно вовсе — имя резолвится, хотя записи в зоне нет.

Модуль ходит к авторитативным NS напрямую по UDP, минуя рекурсивный резолвер и
его кеш. dnspython — обязательная зависимость, но её отсутствие не должно ронять
DNS-тулы целиком: `probe()` в этом случае возвращает поле ``error``.
"""

DEFAULT_TIMEOUT = 5.0


class ProbeUnavailable(Exception):
    """Факт получить не удалось — сеть, отсутствие NS или нет dnspython."""


def _dnspython():
    try:
        import dns.message  # noqa: F401
        import dns.query  # noqa: F401
        import dns.rcode  # noqa: F401
        import dns.rdatatype  # noqa: F401
        import dns.resolver  # noqa: F401
    except ImportError as e:  # pragma: no cover - зависит от окружения
        raise ProbeUnavailable(
            "dnspython is not installed — authoritative DNS probing disabled"
        ) from e
    import dns

    return dns


def authoritative_nameservers(
    fqdn: str, timeout: float = DEFAULT_TIMEOUT
) -> tuple[str, list[str]]:
    """(зона, её NS) — идём вверх по меткам до первой зоны с NS-записями.

    Для ``sub.site.ru`` NS обычно делегированы на уровне ``site.ru``, поэтому
    запрос по самому поддомену ничего не даёт и подниматься обязательно.
    """
    dns = _dnspython()
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    labels = fqdn.split(".")
    for i in range(len(labels) - 1):
        zone = ".".join(labels[i:])
        try:
            answer = resolver.resolve(zone, "NS")
        except Exception:
            continue
        servers = sorted({str(r.target).rstrip(".") for r in answer})
        if servers:
            return zone, servers
    raise ProbeUnavailable(f"no NS records found for {fqdn} or any parent zone")


def _nameserver_addresses(dns, resolver, name: str) -> list[str]:
    addresses: list[str] = []
    for rdtype in ("A", "AAAA"):
        try:
            answer = resolver.resolve(name, rdtype)
        except Exception:
            continue
        addresses.extend(str(r) for r in answer)
    return addresses


def query_authoritative(
    fqdn: str, rtype: str = "A", timeout: float = DEFAULT_TIMEOUT
) -> dict:
    """Спросить авторитативный NS зоны напрямую. Кеш резолвера не участвует.

    Raises:
        ProbeUnavailable: ни один авторитативный NS не ответил.
    """
    dns = _dnspython()
    zone, nameservers = authoritative_nameservers(fqdn, timeout)

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    errors: list[str] = []
    for ns in nameservers:
        for address in _nameserver_addresses(dns, resolver, ns):
            try:
                query = dns.message.make_query(fqdn, dns.rdatatype.from_text(rtype))
                response = dns.query.udp(query, address, timeout=timeout)
            except Exception as e:
                errors.append(f"{ns} ({address}): {type(e).__name__}: {e}")
                continue
            values: list[str] = []
            for rrset in response.answer:
                values.extend(str(item).rstrip(".") for item in rrset)
            return {
                "zone": zone,
                "nameserver": ns,
                "nameserver_ip": address,
                "type": rtype.upper(),
                "values": sorted(values),
                "rcode": dns.rcode.to_text(response.rcode()),
            }
    raise ProbeUnavailable(
        f"no authoritative nameserver of {zone} answered for {fqdn}: "
        + ("; ".join(errors) if errors else "no reachable NS addresses")
    )


def probe(fqdn: str, rtype: str = "A", timeout: float = DEFAULT_TIMEOUT) -> dict:
    """query_authoritative, но без исключений — для встраивания в ответ тула."""
    try:
        return query_authoritative(fqdn, rtype, timeout)
    except ProbeUnavailable as e:
        return {"type": rtype.upper(), "error": str(e)}
    except Exception as e:  # pragma: no cover - защита от неожиданного из dnspython
        return {"type": rtype.upper(), "error": f"{type(e).__name__}: {e}"}
