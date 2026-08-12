# AW0.231 — Catalog Master Data Repair

## Проверено

- Зафиксирован baseline всех 101 активных игровых stable ID и создан backup
  `backups/aw0231-master-data-repair-20260812-163541/catalog.db` до изменений.
- Каждая игровая запись прошла machine audit всех фактически существующих полей Schema 1.
- Для сопоставления использовались точное нормализованное название и год; неоднозначные
  совпадения изданий не применялись автоматически.
- Проверены локальное наличие и декодирование 101/101 обложек, уникальность stable ID и
  пар `title/year`, chronology/Journey manifests и Company Logo Resolver.
- Выборочно отрендерены 20 разнотипных карточек. Артефакт:
  `docs/ui/screenshots/aw0231_catalog_master_sample.png`.

## Исправлено

- Выполнено 100 field-level исправлений `release_year`, `developer`, `publisher`.
- Удалены подмены компаний Wikidata ID, персоналиями и данными киноадаптаций.
- Исправлены критические смешения изданий, включая Elden Ring, Resident Evil 4 (remake),
  Final Fantasy VII Remake, The Last of Us Part I, God of War 2005/2018 и Forza Horizon 5.
- Stable ID, Schema 1, chronology relations, Journey IDs, обложки и `user.db` не изменялись.
- Repair повторно запущен без новых изменений: операция идемпотентна.

## Источники и confidence

- HIGH: официальные сайты разработчиков/издателей и продуктовые страницы платформ.
- MEDIUM: точное сопоставление основной игры со структурированными данными Steam.
- LOW: автоматическое изменение запрещено; пункты перечислены в
  `data/aw0231_catalog_manual_review.json`.
- Полный QA manifest: `data/aw0231_catalog_master_audit.json`; сетевой cache источников:
  `data/aw0231_steam_audit_cache.json`.

## Результат

- CATALOG GAMES: 101
- VERIFIED/CORRECTED titles: 101/101
- VERIFIED/CORRECTED release years: 68/101; missing 2; review 31
- VERIFIED/CORRECTED developers: 69/101; review 32
- VERIFIED/CORRECTED publishers: 63/101; review 38
- VERIFIED engines: 1/101; review 100
- VALID LOCAL COVERS: 101/101
- Journey: 13 publish-ready, 55 template-assigned, 17 not applicable, 16 manual review
- Company logo: 60/101 карточек имеют минимум один разрешаемый логотип; полное покрытие 8/101
- CORRECTED FIELDS: 100
- MANUAL REVIEW: 639 field findings across 100 games

## Ограничения

- Это честный частичный master-data repair, а не ложное объявление 101/101. Engine,
  системные требования, режимы, chronology и ряд описаний требуют отдельного подтверждения;
  значения LOW оставлены без изменения.
- Полный перечень manual review хранится на уровне поля в JSON manifest.
- Отсутствующий логотип не меняет официальное название компании и не блокирует карточку.

## Проверки

- Targeted catalog/cover/chronology/Journey audit: 16 passed.
- Velora regression: 309 passed, 2 skipped, 4 subtests passed.
- Studio regression: 38 passed.
- Velora/Studio compileall: PASS.
- Velora/Studio `git diff --check`: PASS (только существующие предупреждения LF/CRLF).
- `PRAGMA integrity_check`: ok; `foreign_key_check`: empty.
