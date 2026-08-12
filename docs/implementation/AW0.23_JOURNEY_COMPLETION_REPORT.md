# AW0.23 Journey Completion Pass — отчёт

## Результат

Journey нормализован как персональная история прохождения поверх официального
шаблона. `catalog.db` хранит структуру этапов; состояния, оценки, mood, флаги и
события остаются в `user.db`. Прямых SQL-вызовов из UI не добавлено.

## 1. Explicit state и rating

- `journey_stage_states` — состояние этапа.
- `journey_stage_ratings` — оценка этапа в десятых, 1.0–10.0.
- `journey_stage_moods` — стабильный Mood ID.
- `journey_stage_flags` — независимые `favorite` и `difficult`.
- Теги, media reference и история изменения оценки входят в typed event payload.

Legacy `stage_favorite_set` безопасно проецируется при запуске расширения схемы;
история при этом не удаляется.

## 2. Progression

`JourneyService.set_stage_state()` записывает завершение текущего этапа и
перевод следующего `not_started` в `current` в одной транзакции `user.db`.
Другие прохождения не меняются. Последний этап не завершает прохождение молча:
UI отдельно запрашивает подтверждение.

## 3. Visible Timeline events

Стабильные типы: `note`, `screenshot`, `achievement`, `favorite_moment`,
`difficult_moment`, `music`, `rating_change`, `other`. Новая запись обязательно
содержит явный `stage_id`. Technical mutations остаются в истории, но исключены
presentation policy. Редактирование и удаление оформлены append-only событиями
`timeline_event_revised` и `timeline_event_deleted`.

## 4. Events между этапами и +N

`JourneyTimelineLayoutModel` является общей детерминированной policy для
виджетов и canvas. После каждого StageCard создаётся event segment. Видимы не
более трёх событий; остаток отображается как `+N`. Ширина сегмента зависит от
числа видимых событий, а центры StageCard передаются canvas после layout pass.

## 5. Context Viewer

- Stage: изображение, состояние, rating, впечатления, теги и быстрые действия.
- Event: title/body/tags/media и действия «Изменить»/«Удалить».
- Event Group: список событий выбранного сегмента.

Выбор события и позиция горизонтального маршрута сохраняются при refresh.

## 6. Analytics

- предварительная оценка — среднее только явно оценённых этапов;
- favorite/difficult — только явные флаги;
- notes — только `note`;
- events — только visible Timeline event types;
- mood graph получает отдельные mood IDs и не выводит их из оценки.

## 7. Creator/history

`GamePlaythroughHistoryQueryService` возвращает все прохождения независимо от
выбора в Journey UI, включая normalized stage ratings, flags, moods, states,
visible events, notes и исходную immutable history.

## 8. Миграции

`SchemaManager.ensure_aw023_user_extensions()` идемпотентно добавляет
`journey_stage_ratings` и `journey_stage_flags`. Новые Timeline events используют
существующий append-only `journey_events`, поэтому смена поколения схемы не
потребовалась.

## 9. Основные изменённые файлы

- `app/application/game_services.py`
- `app/application/doom_vertical_slice.py`
- `app/application/journey_presentation.py`
- `app/application/journey_layout.py`
- `app/application/playthrough_history.py`
- `app/storage/models.py`
- `app/storage/repositories.py`
- `app/storage/schema.py`
- `app/storage/unit_of_work.py`
- `app/ui/game_detail/doom_aw02_panel.py`
- `app/ui/game_detail/journey_widgets.py`
- `app/ui/velora_ui/components/cards.py`
- `tests/test_aw023_journey_moods.py`
- `tests/test_aw023_playthrough_flow.py`

## 10. Проверки

- focused playthrough/completion tests: 21 passed;
- full regression: 215 passed, 2 skipped, 4 subtests passed;
- `compileall`: success;
- `git diff --check`: success (только предупреждения Git о будущей CRLF-конверсии);
- offscreen MainWindow smoke: success.

## 11. Скриншоты

Каталог: `docs/ui/screenshots/aw023_journey_geometry/`.

- `journey_final_event_selected.png`
- `journey_final_event_group.png`
- `journey_final_empty_playthrough.png`

Ограничение offscreen-среды: доступный системный шрифт не содержит русские
глифы, поэтому автоматические изображения используются для проверки геометрии;
текст проверяется тестами и в обычной Windows-среде приложения.
