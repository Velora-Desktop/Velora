# AW0.23 Universal Journey Contract

## Проверено

- Один `JourneyView`, `StageCard`, Timeline, события, `+N`, Context Viewer,
  Quick Add, rating/mood, analytics и selector работают от `JourneyPresentation`.
- Количество и stable ID этапов поступают из официального `journey_template`.
- Проверены конфигурации Doom Eternal (13), другой игры (5) и длинной игры
  (21 этап) с тем же UI и горизонтальным Timeline.
- Персональные данные выбираются по `CatalogItemRef` и playthrough, поэтому
  состояния и события одной игры не попадают в другую.

## Найденные Doom-specific зависимости

- `DoomVerticalSlice` одновременно являлся общим application boundary и
  фиксировал `DOOM_ETERNAL_ID`.
- `set_stage_state()` всегда брал 13 stage ID из `doom_eternal()`.
- `JourneyPresentationBuilder` был типизирован через `DoomDetailState` и
  выбирал шаблон эвристикой по названию игры.
- Registry имел Doom-specific resolver `if "doom" in title`.

## Устранено

- Добавлен game-neutral `GameJourneySlice(catalog_db, user_db, ref)`.
- Общий state переименован в `GameJourneyDetailState`.
- Операции этапов используют ordered stable IDs официального payload.
- `JourneyTemplate` хранит `stage_ids`; payload принимает `stable_id` или
  `stage_id` с детерминированным fallback.
- Builder принимает общий state и не распознаёт игру по названию.
- Удалена Doom-specific ветка из общего template resolver.

## Legacy compatibility

- `DoomVerticalSlice` оставлен как тонкий адаптер над `GameJourneySlice`, чтобы
  не ломать существующий экран и тесты AW0.2/AW0.23.
- `DoomDetailState` оставлен как alias общего state.
- Для старых Doom-записей без catalog payload reference template выбирается
  только на data boundary по canonical Catalog ID. UI и presentation после
  этого получают обычный универсальный контракт.

## Идентичность Doom

Journey UI и его стили, размеры, spacing, Timeline, StageCard, иконки,
анимации и сценарии не изменялись. Doom по-прежнему получает 13 исходных
этапов с прежними stable ID и проходит существующие Journey/UI tests.

## Тесты

- Universal/Journey targeted: **65 passed, 2 skipped**.
- Full regression suite: **305 passed, 2 skipped, 4 subtests passed**.
- Конфигурации: 13 / 5 / 21 этап.
- Проверены completion + auto-next, event, rating, mood, reopen persistence,
  horizontal scrolling и межигровая изоляция.

## Ограничения

- Массовое назначение Journey играм и Studio не выполнялись.
- Legacy Doom adapter будет нужен до миграции старых записей на официальный
  catalog payload; он изолирован от универсального UI pipeline.
