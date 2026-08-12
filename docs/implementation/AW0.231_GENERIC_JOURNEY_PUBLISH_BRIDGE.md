# AW0.231 — Generic Journey Publish Bridge

## Проверено

- Studio Journey configuration и реестр Journey Templates.
- Schema 1: `catalog_items` и extensible `catalog_payloads`.
- существующий Doom Eternal publish и чтение `journey_template` в Velora.
- граница официальных данных `catalog.db` и персональных данных `user.db`.

## Что было Doom-specific

`AW02CatalogBridge.save_if_supported()` принимал только legacy ID Doom Eternal
или Contracts UUID Doom Eternal, всегда загружал UUID Doom и всегда записывал
payload в строку Doom. Любая другая игра возвращала `False` и не могла получить
официальный Journey через Studio.

## Что стало generic

- Добавлен типизированный контракт `JourneyPublishRequest`:
  `game_id`, `journey_template_id`, ordered stages и исходный официальный payload.
- Каждый `JourneyStagePublish` содержит stable ID, название, порядок и уже
  поддерживаемые Schema 1 metadata.
- Template ID проверяется через существующий Studio Journey Template Registry.
- Публикация выполняет универсальную связь `Game -> Template -> Stages` в
  `catalog_payloads` по фактическому `catalog_id` игры.
- Если Journey не выбран/неприменим, игра сохраняется без искусственного
  `journey_template`.
- Повторная публикация неизменённого payload не переписывает payload и сохраняет
  его revision.
- Historical `g-shooter-fps-002` остаётся только входным alias UUID Doom на
  границе обратной совместимости. Отдельной Doom-ветки записи больше нет.
- Studio stage configuration теперь явно сериализует стабильный `stage_id`.

Schema 1 не менялась. `catalog.db` хранит только официальный template.
`user.db` bridge не открывает и не изменяет.

## Изменённые файлы

- `C:/Velora studio/studio/services/aw02_catalog_bridge.py`
- `C:/Velora studio/studio/core/journey_configuration.py`
- `C:/Velora studio/tests/test_generic_journey_publish_bridge.py`
- `C:/Velora/docs/implementation/AW0.231_GENERIC_JOURNEY_PUBLISH_BRIDGE.md`

## Тесты

- Doom Eternal через generic pipeline: PASS.
- вторая линейная игра и изоляция Doom stages: PASS.
- другой Journey Template: PASS.
- игра без Journey: PASS.
- повторная публикация идемпотентна: PASS.
- foreign keys и SQLite integrity: PASS.
- `user.db` byte-for-byte неизменён: PASS.
- Studio suite: 33/33 PASS.
- Catalog/Journey targeted suites: 64 PASS, 2 SKIP.
- Full Velora regression: 275 PASS, 2 SKIP; 2 несвязанных сбоя уже
  существующей грязной рабочей директории: duplicate-title guard для двух
  корректно разделённых изданий `God of War` (2005/2018) и teardown race
  удалённого `HoverAnimatedIcon`.
- `compileall` Velora и Studio: PASS.
- `git diff --check` изменённых файлов: PASS.

Полный catalog backfill в эту задачу не входил и не выполнялся. Инфраструктура
теперь позволяет Studio публиковать официальный Journey любой поддерживаемой
игре без добавления game-specific веток.
