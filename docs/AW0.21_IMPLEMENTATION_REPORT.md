# AW0.21 implementation report

## Реализовано

- 21 Journey Template на общей композиционной модели.
- UI-neutral Journey Presentation Builder поверх существующего AW0.2 slice.
- Doom Eternal Reference Template: Story Campaign + Arena Shooter, mission
  stages, encounters, collectibles, boss moments и Creator extraction rules.
- Переиспользуемые JourneyView, JourneyEntryCard и EmptyStatePanel.
- Структурированные этапы, impressions, ratings и key moments.
- Стабильные Creator source IDs и автоматическое включение материалов Journey.
- Creator Source Model на реальных данных текущего Doom Journey.
- Каталог и preview Journey Templates в Studio.

## Переиспользование

Сохранены `DoomVerticalSlice`, существующие action dialogs, сервисы, Unit of
Work, repositories, Schema 1 и контейнер карточки. `DoomAw02Panel` остаётся
тонким Qt-адаптером; новая Journey-логика не находится в нём.

## Новые компоненты и причина

- `JourneyTemplateRegistry`: декларативная композиция вместо 21 независимой
  архитектуры.
- `JourneyPresentationBuilder`: запрещает UI самостоятельно интерпретировать
  domain events.
- `CreatorSourceBuilder`: исключает чтение Creator из виджетов.
- `JourneyView` и `JourneyEntryCard`: существующие большие HTML-label не
  поддерживали единый интерактивный маршрут и выбранный этап.
- Studio `JourneyTemplatesPanel`: отдельная зона ответственности preview без
  изменения редактора официальных полей.

## Изменённый UX

Большой технический журнал Journey заменён горизонтальным путём миссий.
Journey получил приоритет в эталонном AW0.2-блоке. Данные автоматически
подготавливаются для будущего Creator без ручных действий в Journey.

## Проверки универсальности

21 шаблон охватывает кампании, open world, RPG, extraction, sandbox, survival,
strategy, city builder, racing, sports, simulator, puzzle, visual novel,
MMORPG и live service. Новая игра подключается выбором конфигурации, без
Doom-specific widget/backend.

## Проверки

- Velora: 139 tests — OK.
- Studio: 14 tests — OK.
- Target Journey tests: 5 + 2 — OK.
- `compileall`: Velora и Studio — OK.
- Headless UI smoke: Velora и Studio — OK.
- `git diff --check`: OK (только предупреждения CRLF).

## Ограничения Schema 1

Выбор Studio Journey preview не сохраняется после завершения процесса.
Ручные Creator marks больше не являются частью UX или условием попадания
материала в source model; скрытая схема не добавлялась. Полноценные Creator
Outline, Script, Footage, AI и Export не реализованы.
Массовое подключение всех игровых карточек отложено до проверки эталона Doom.

## Следующий этап Creator

Следующий цикл должен определить правила отбора уже автоматически доступных
источников и реализовать Outline. Генерацию текста и экспорт подключать
только поверх стабильного Creator Source Model.
