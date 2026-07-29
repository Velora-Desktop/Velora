# AW0.21 — Doom Eternal Reference UX Report

## Результат

Doom Eternal остаётся внутри существующей `GameDetailPage`, но её личный
AW0.2-блок теперь воспринимается как единый путь прохождения. Параллельная
страница и Doom-specific backend не создавались.

## Изменённые файлы

- `app/application/journey_templates.py`
- `app/application/journey_presentation.py`
- `app/application/creator_sources.py`
- `app/ui/game_detail/journey_widgets.py`
- `app/ui/game_detail/doom_aw02_panel.py`
- `app/ui/game_detail/game_detail_page.py`
- `tests/test_aw021_journey_templates.py`
- `tools/render_aw021_journey_states.py`
- `docs/PATCH_NOTES_AW0.21.md`
- этот отчёт и визуальные fixtures.

## Единая карточка

Старые вкладки «Обзор», «Прохождения», «Journey», «Впечатления» и «Оценки»
удалены из личного блока. Вместо них используются:

1. компактная строка текущего прохождения;
2. переключатель повторных прохождений;
3. единый горизонтальный Journey;
4. одна карточка выбранной миссии;
5. встроенный быстрый редактор.

Официальные сведения, профессиональные оценки, системные требования и
хронология серии остаются существующими секциями общей страницы.

## JourneyTimeline

Универсальный `JourneyView` использует один контролируемый горизонтальный
`QScrollArea`. Для Doom Reference Template конфигурация задаёт 13 миссий.
Каждая миссия представлена компактным `JourneyTimelineNode`; между узлами
рисуется единая соединительная линия. Стрелки и клавиши Left/Right меняют
выбранную миссию, после чего узел автоматически становится видимым.

Позиция и выбранный `stage_id` сохраняются при обновлении presentation model.
Вся страница и Timeline при выборе узла не пересоздаются.

## Заполнение пути

Заполненная часть определяется по последней миссии, содержащей материалы
Journey. Для завершённого прохождения заполнены все 13 узлов. Состояния:

- `future` — приглушённая будущая миссия;
- `active` — текущая миссия с фиолетовым акцентом;
- `complete` — завершённая часть пути;
- `selected` — отдельное выбранное состояние поверх доменного состояния.

Выбранный этап показывает не более трёх последних материалов, чтобы карточка
не превращалась в журнал. Дополнительные данные остаются в read model.

## Быстрое заполнение

`JourneyQuickEditor` — постоянный, не пересоздаваемый inline-компонент:

- статус;
- оценка;
- короткое впечатление;
- сохранение одной кнопкой или Enter.

Он отправляет typed UI-сигнал в `DoomAw02Panel`, а панель вызывает только
существующие методы `DoomVerticalSlice`. Прямого SQL и нового persistence
слоя в UI нет. Завершение промежуточной миссии создаёт milestone, но не
завершает всё прохождение; только финальная миссия переводит прохождение в
`completed`.

## Повторные прохождения

Компактный selector переключает presentation между существующими
прохождениями. Истории фильтруются по `playthrough_sequence`. Прошлые
прохождения доступны только для чтения; быстрый редактор активен лишь для
текущего прохождения, поэтому запись не может случайно попасть в другой run.

## Creator

Ручные кнопки «В Creator», badges и session-level marks удалены из Journey
UX. `CreatorSourceBuilder` автоматически включает все релевантные материалы
`JourneyPresentation` в `CreatorSourceModel`. Deprecated
`CreatorMarkSession` оставлен только как совместимый shim и не участвует в
отборе источников. Schema 1 не расширялась.

Поток:

`Journey Read Model → JourneyPresentation → CreatorSourceModel`

## Описание и официальная информация

Для эталонной карточки длинная энциклопедическая статья заменена компактным
описанием игрового опыта. Верхняя метаинформация не дублируется внутри
Journey. Магазины сохраняются в существующем блоке; вымышленные URL не
создаются. Ранее удалённое поле `DirectX / API` не возвращалось.

## Header и чёрные поверхности

Journey не владеет `GameHeader` и не пересоздаёт status control. Смена
Journey-состояния обновляет существующие labels и стабильный
`JourneyQuickEditor`. В Timeline и detail используются оформленные
прозрачные viewport/container surfaces; неоформленные placeholder-виджеты
не вставляются.

## Переиспользование компонентов

Расширены:

- `JourneyView`;
- `JourneyEntryCard`;
- `EmptyStatePanel`;
- `DoomAw02Panel`;
- `JourneyPresentationBuilder`;
- `JourneyTemplate`.

Добавлены универсальные:

- `JourneyTimelineNode`;
- `JourneyQuickEditor`.

Они не содержат проверок названия Doom и получают структуру через template и
presentation model.

## Визуальные fixtures

- `docs/implementation/screenshots/aw021_journey/empty_playthrough.png`
- `docs/implementation/screenshots/aw021_journey/active_playthrough.png`
- `docs/implementation/screenshots/aw021_journey/selected_mission.png`
- `docs/implementation/screenshots/aw021_journey/completed_playthrough.png`
- `docs/implementation/screenshots/aw021_journey/repeat_playthrough.png`

Fixtures формируются только в offscreen demo-режиме и не записываются в
пользовательскую базу.

## Известные ограничения

- Schema 1 различает три checkpoint-типа (`start`, `middle`, `end`), поэтому
  точная миссия промежуточного milestone восстанавливается из сохранённого
  названия миссии в review/checkpoint material. Полноценная отдельная
  mission-state persistence требует будущей нормативной миграции.
- Впечатление Schema 1 привязывает к checkpoint, а не к произвольному
  `stage_id`; UI не подменяет это скрытой второй историей.
- Эталонный Journey подключён только к Doom Eternal; компоненты готовы к
  повторному использованию после появления template/configuration у других
  игр.
- Полноценный Creator UI, правила отбора, монтажный timeline и экспорт
  остаются отдельным циклом.

## Проверки

- Journey + status stability: 15/15.
- Velora regression suite: 151/151.
- Studio regression suite: 14/14.
- Velora и Studio `compileall`: success.
- Velora и Studio `git diff --check`: success; показаны только штатные
  предупреждения Git о будущей нормализации LF/CRLF.
- Source startup smoke: приложение оставалось активным без traceback до
  контролируемого завершения процесса.
- Offscreen fixtures: 5/5 созданы. Offscreen Qt в текущем окружении не
  обнаруживает системные Windows-шрифты, поэтому fixtures подтверждают
  геометрию и состояния; финальная проверка кириллицы выполняется в обычном
  Windows runtime.
