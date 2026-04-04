# Beget API — план полного покрытия

Источник: https://beget.com/ru/kb/api/

## Сводка

| Раздел | В API | Реализовано | Не хватает |
|--------|-------|-------------|------------|
| **user** | 2 | 2 | 0 |
| **backup** | 9 | 9 | 0 |
| **cron** | 7 | 7 | 0 |
| **dns** | 2 | 2 | 0 |
| **ftp** | 4 | 4 | 0 |
| **mysql** | 6 | 6 | 0 |
| **site** | 8 | 8 | 0 |
| **domain** | 13 | 13 | 0 |
| **mail** | 10 | 10 | 0 |
| **stat** | 4 | 4 | 0 |
| **ИТОГО** | **65** | **65** | **0** |

## Недостающие методы

### user (1)
- [x] `user/toggleSsh` — вкл/выкл SSH (params: status 0|1, ftplogin?)

### backup (5)
- [x] `backup/getFileList` — файлы внутри бэкапа (params: backup_id?, path?)
- [x] `backup/getMysqlList` — БД внутри бэкапа (params: backup_id?)
- [x] `backup/downloadFile` — скачать файлы из бэкапа в корень (params: backup_id?, paths[])
- [x] `backup/downloadMysql` — скачать дамп БД в корень (params: backup_id?, bases[])
- [x] `backup/getLog` — статусы заданий восстановления

### cron (4)
- [x] `cron/edit` — редактировать задачу (params: id, minutes?, hours?, days?, months?, weekdays?, command?)
- [x] `cron/changeHiddenState` — вкл/выкл задачу (params: row_number, is_hidden 0|1)
- [x] `cron/getEmail` — получить email уведомлений
- [x] `cron/setEmail` — установить email (params: email)

### mysql (2)
- [x] `mysql/addAccess` — добавить доступ к БД (params: suffix, access, password)
- [x] `mysql/dropAccess` — удалить доступ к БД (params: suffix, access)

### site (3)
- [x] `site/freeze` — заморозить сайт (params: id, excludedPaths?)
- [x] `site/unfreeze` — разморозить (params: id)
- [x] `site/isSiteFrozen` — проверить заморозку (params: site_id)

### domain (6)
- [x] `domain/addSubdomainVirtual` — добавить поддомен (params: subdomain, domain_id)
- [x] `domain/deleteSubdomain` — удалить поддомен (params: id)
- [x] `domain/checkDomainToRegister` — проверить доступность (params: hostname, zone_id, period)
- [x] `domain/getDirectives` — PHP-директивы домена (params: full_fqdn)
- [x] `domain/addDirectives` — добавить директивы (params: full_fqdn, directives_list[])
- [x] `domain/removeDirectives` — удалить директивы (params: full_fqdn, directives_list[])

### mail (8)
- [x] `mail/changeMailboxPassword` — сменить пароль (params: domain, mailbox, mailbox_password)
- [x] `mail/dropMailbox` — удалить ящик (params: domain, mailbox)
- [x] `mail/changeMailboxSettings` — настройки ящика (params: domain, mailbox, spam_filter_status?, spam_filter?, forward_mail_status?)
- [x] `mail/forwardListAddMailbox` — добавить пересылку (params: domain, mailbox, forward_mailbox)
- [x] `mail/forwardListDeleteMailbox` — удалить пересылку (params: domain, mailbox, forward_mailbox)
- [x] `mail/forwardListShow` — список пересылки (params: domain, mailbox)
- [x] `mail/setDomainMail` — установить почту домена (params: domain, domain_mailbox)
- [x] `mail/clearDomainMail` — сбросить почту домена (params: domain)

### stat (3)
- [x] `stat/getDbListLoad` — нагрузка по всем БД
- [x] `stat/getSiteLoad` — детальная нагрузка сайта (params: site_id)
- [x] `stat/getDbLoad` — детальная нагрузка БД (params: db_name)
