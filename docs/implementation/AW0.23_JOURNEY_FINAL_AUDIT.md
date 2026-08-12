# AW0.23 Journey — Final Baseline Audit

Дата аудита: 2026-08-04  
Нормативный визуальный источник: `docs/ui/references/journey_aw023_reference.png`

## Результат baseline-аудита

Текущая реализация визуально близка к утверждённой композиции, но read model
по-прежнему восстанавливает часть персонального состояния из текстов и
технической истории. Поэтому окончательная доводка UI без нормализации домена
будет нестабильной.

### 1. `_stage_from_text()`

`JourneyPresentationBuilder` определяет этап для части `JourneyEvent` и
`user_ratings` поиском названия этапа и слов «начало/середина/финал» в тексте.
Это неоднозначно, зависит от локализации и ломается после редактирования текста.
Для legacy-записей допустим отдельный fallback-adapter, но новые события должны
иметь обязательный `stage_id` в payload.

### 2. `JourneyEntry.kind`

Все обычные Journey events сейчас превращаются в `kind="event"`. Реальные
типы note, screenshot, achievement, favorite/difficult moment, music,
rating_change и other теряются. UI поэтому не может надёжно выбирать иконку,
контекст и редактор.

### 3. Tags contract

`JourneyEntry` не содержит `tags`, хотя UI читает их через
`getattr(entry, "tags", ())`. При сохранении теги дописываются в текст через
`#`, то есть структура теряется. Нужен явный `tuple[str, ...]` в read model и
payload.

### 4. Favorite

Текущее значение favorite восстанавливается повторным проигрыванием
`stage_favorite_set` из immutable Journey history. Отдельной state projection
нет. Это смешивает историю и текущее состояние и усложняет миграции.

### 5. Difficult

Явного difficult-state нет. Analytics считает сложными этапы с rating <= 6,
что нарушает независимость впечатления, сложности и оценки.

### 6. Stage rating

Текущая оценка этапа берётся из `user_ratings`: этап определяется через
`review_text` или checkpoint start/middle/end. Явной пары
`(playthrough_id, stage_id)` нет. Нужна отдельная projection
`journey_stage_ratings`, при сохранении которой история изменения остаётся
отдельным event.

### 7. Stage state auto-advance

`JourneyService.set_stage_state()` меняет только один stage. Application-level
переход current -> completed и next not_started -> current отсутствует. UI не
должен самостоятельно выполнять две несвязанные записи.

### 8. Timeline geometry

События группируются внутри колонки этапа, а canvas использует геометрию,
основанную преимущественно на фиксированной ширине карточек. Отдельной модели
segment between stages нет; при нескольких событиях widget layout и линия
могут расходиться.

### 9. Context Viewer

Нижняя область является постоянным Stage Editor. Явных selection contracts
STAGE / EVENT / EVENT_GROUP нет. Event нельзя устойчиво выбрать, отредактировать
или удалить с сохранением контекста и scroll position.

### 10. Time in Journey

Время отображается в Summary Card, StageCard/QuickEditor и Detail Context;
Journey UI также содержит ручной ввод playtime. Общая модель времени нужна
другим разделам и сохраняется, но Journey AW0.23 должен перестать читать,
показывать и запрашивать её.

## Storage baseline

В user.db уже существуют `journey_stage_states` и `journey_stage_moods`.
Отсутствуют явные таблицы stage ratings и stage flags. AW0.23 optional extension
создаёт только states/moods. Удаление playthrough уже каскадно очищает связанные
таблицы через foreign keys и дополнительно обрабатывается repository layer.

## Безопасная последовательность исправлений

1. Добавить idempotent user.db extensions ratings/flags и typed repositories.
2. Перевести services/read state на явные projections и explicit payload.
3. Добавить атомарный auto-advance.
4. Ввести typed visible timeline event policy и selection contracts.
5. После стабилизации данных перестроить timeline segments/context viewer.
6. Только затем выполнить pixel/reference pass и screenshots.

Catalog.db и официальный Journey Template изменять не требуется.
