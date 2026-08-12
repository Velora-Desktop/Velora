# AW0.23 — Velora UI Kit 1.0

## Результат

Создан независимый от данных пакет `app/ui/velora_ui`. Первая миграция
Journey выполнена без изменения его компоновки: карточки этапов, карточки
быстрых действий, иконки событий и график теперь используют общий UI Kit.

## Проверка обязательных критериев

| Критерий | Статус | Доказательство |
|---|---|---|
| Цвета и размеры компонентов Journey не дублируются | выполнено для мигрированных stage/action/chart компонентов | semantic tokens в `theme/tokens.py`; адаптер Journey больше не оформляет эти компоненты |
| Этапы и быстрые действия собраны из UI Kit | выполнено | `JourneyTimelineNode(VeloraStageCard)`, `JourneyActionCard(VeloraActionCard)` |
| Иконки загружаются через реестр | выполнено | `IconProvider` является semantic-слоем над общим `IconRegistry` |
| Системные emoji удалены из постоянного Journey UI | выполнено | stage, events, arrows и итоговый score не содержат emoji/случайных glyph icons |
| Настроение представлено стабильным ID | выполнено | `MoodDefinition.id`, `VeloraMoodSelector.mood_id`, `MoodChartPoint.mood_id` |
| График использует Mood Pack | выполнено | `MoodChart` разрешает ID через `MoodRegistry`; rating остаётся независимым полем |
| Потерянная SVG не приводит к падению | выполнено | прозрачный pixmap fallback и warning в `IconProvider` |
| UI Kit не обращается к БД | выполнено | AST boundary test запрещает `sqlite3`, `app.storage`, `app.application` |

## Созданные части

- semantic theme tokens и `VisualState`;
- базовая карточка, stage card и action card;
- semantic IconProvider и локальный Journey SVG pack;
- Mood Registry, stable mood IDs и Mood Selector;
- data-driven `MoodChart` и `MoodChartPoint`;
- четыре документа использования и миграции;
- шесть автоматических UI Kit checks.

## Осознанные ограничения первого этапа

- В существующем Journey остаются legacy layout-containers и редактор записи.
  Они не дублируют уже мигрированные карточки и не переносились, чтобы не
  выполнять запрещённый визуальный редизайн в техническом этапе.
- Настроение пока не добавлено в Schema 1. UI Kit передаёт и возвращает stable
  ID; persistence должна быть подключена отдельным application/storage
  контрактом, а не прямым доступом компонента к БД.
- Не все страницы Velora мигрированы на UI Kit; это намеренно поэтапная
  миграция.

## Проверки

- `python -m unittest discover -s tests -v` — 169/169;
- `python -m compileall -q app tests` — success;
- `git diff --check` — success.
