#!/usr/bin/env python3
"""Smoke-тест: вызывает все read-only методы Beget API и проверяет что они отвечают.

Требует BEGET_API_LOGIN и BEGET_API_PASSWORD в окружении.
Не изменяет данные — только чтение.

Использование:
    BEGET_API_LOGIN=xxx BEGET_API_PASSWORD=yyy python scripts/smoke_test.py
"""

import sys
import time

from mcp_beget.client import init_client
from mcp_beget.config import load_config
from mcp_beget.errors import BegetAPIError, BegetAuthError


def main() -> None:
    try:
        config = load_config()
    except ValueError as e:
        print(f"SKIP  Config error: {e}")
        sys.exit(1)

    try:
        client = init_client(config)
    except Exception as e:
        print(f"SKIP  Client init error: {e}")
        sys.exit(1)

    passed = 0
    failed = 0
    skipped = 0

    def ok(name: str, result: object) -> None:
        nonlocal passed
        passed += 1
        detail = ""
        if isinstance(result, dict):
            r = result.get("result", result)
            if isinstance(r, list):
                detail = f" ({len(r)} items)"
            elif isinstance(r, dict):
                detail = f" ({len(r)} keys)"
        print(f"  OK    {name}{detail}")

    def fail(name: str, error: Exception) -> None:
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name} — {error}")

    def skip(name: str, reason: str) -> None:
        nonlocal skipped
        skipped += 1
        print(f"  SKIP  {name} — {reason}")

    def call(name: str, section: str, method: str, params: dict | None = None) -> object:
        try:
            r = client.call(section, method, params)
            ok(name, r)
            return r
        except BegetAuthError as e:
            fail(name, e)
            print("\n  AUTH ERROR — проверьте логин/пароль. Остальные тесты бессмысленны.")
            sys.exit(1)
        except BegetAPIError as e:
            fail(name, e)
            return None
        except Exception as e:
            fail(name, e)
            return None

    print("=" * 60)
    print("Beget API smoke test (read-only)")
    print("=" * 60)
    start = time.time()

    # --- user ---
    print("\n[user]")
    account = call("account_info", "user", "getAccountInfo")

    # --- site ---
    print("\n[site]")
    sites_resp = call("site_list", "site", "getList")
    site_id = None
    if sites_resp:
        sites = sites_resp.get("result", sites_resp)
        if isinstance(sites, list) and sites:
            site_id = sites[0]["id"]

    if site_id:
        call("site_is_frozen", "site", "isSiteFrozen", {"site_id": site_id})
    else:
        skip("site_is_frozen", "нет сайтов")

    # --- domain ---
    print("\n[domain]")
    domains_resp = call("domain_list", "domain", "getList")
    call("domain_zones", "domain", "getZoneList")
    call("domain_subdomains", "domain", "getSubdomainList")

    fqdn = None
    if domains_resp:
        domains = domains_resp.get("result", domains_resp)
        if isinstance(domains, list) and domains:
            fqdn = domains[0]["fqdn"]

    if fqdn:
        call("domain_php_version", "domain", "getPhpVersion", {"full_fqdn": fqdn})
        call("domain_get_directives", "domain", "getDirectives", {"full_fqdn": fqdn})
    else:
        skip("domain_php_version", "нет доменов")
        skip("domain_get_directives", "нет доменов")

    # --- mysql ---
    print("\n[mysql]")
    mysql_resp = call("mysql_list", "mysql", "getList")

    # --- ftp ---
    print("\n[ftp]")
    call("ftp_list", "ftp", "getList")

    # --- cron ---
    print("\n[cron]")
    call("cron_list", "cron", "getList")
    call("cron_get_email", "cron", "getEmail")

    # --- dns ---
    print("\n[dns]")
    if fqdn:
        call("dns_get", "dns", "getData", {"fqdn": fqdn})
    else:
        skip("dns_get", "нет доменов")

    # --- backup ---
    print("\n[backup]")
    backups_resp = call("backup_files_list", "backup", "getFileBackupList")
    call("backup_mysql_list", "backup", "getMysqlBackupList")
    call("backup_log", "backup", "getLog")
    call("backup_file_list_current", "backup", "getFileList")
    call("backup_mysql_db_list_current", "backup", "getMysqlList")

    backup_id = None
    if backups_resp:
        backups = backups_resp.get("result", backups_resp)
        if isinstance(backups, list) and backups:
            backup_id = backups[0]["backup_id"]

    if backup_id:
        call("backup_file_list_by_id", "backup", "getFileList", {"backup_id": backup_id})
        call("backup_mysql_db_list_by_id", "backup", "getMysqlList", {"backup_id": backup_id})
    else:
        skip("backup_file_list_by_id", "нет бэкапов")
        skip("backup_mysql_db_list_by_id", "нет бэкапов")

    # --- mail ---
    print("\n[mail]")
    if fqdn:
        call("mail_list", "mail", "getMailboxList", {"domain": fqdn})
    else:
        skip("mail_list", "нет доменов")

    # --- stat ---
    print("\n[stat]")
    call("stat_sites_list_load", "stat", "getSitesListLoad")
    call("stat_db_list_load", "stat", "getDbListLoad")

    if site_id:
        call("stat_site_load", "stat", "getSiteLoad", {"site_id": site_id})
    else:
        skip("stat_site_load", "нет сайтов")

    db_name = None
    if mysql_resp:
        dbs = mysql_resp.get("result", mysql_resp)
        if isinstance(dbs, list) and dbs:
            db_name = dbs[0]["name"]

    if db_name:
        call("stat_db_load", "stat", "getDbLoad", {"db_name": db_name})
    else:
        skip("stat_db_load", "нет баз данных")

    # --- итог ---
    elapsed = time.time() - start
    print("\n" + "=" * 60)
    total = passed + failed + skipped
    print(f"Итого: {total} тестов за {elapsed:.1f}с")
    print(f"  OK: {passed}  FAIL: {failed}  SKIP: {skipped}")
    print("=" * 60)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
