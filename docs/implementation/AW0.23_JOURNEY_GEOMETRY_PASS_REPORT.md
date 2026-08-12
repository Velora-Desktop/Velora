# AW0.23 Journey Geometry Pass

## Root cause of Journey compression

Journey не использовал свободную высоту родительского viewport из-за трёх
независимых жёстких ограничений:

- `journeyRoutePanel`, `journeyStageDetail` и `journeyAnalytics` имели
  `setFixedHeight()`;
- карточки этапов и область событий использовали компактные размеры первого
  прохода (`120 px` и `92 px`), поэтому Timeline визуально сжимался;
- корневой layout не имел stretch-факторов между смысловыми уровнями;
- левая карточка прохождения повторяла фиксированную высоту route;
- preview впечатления и изображение этапа были рассчитаны на низкий detail.

В результате увеличение окна не влияло на геометрию Journey: свободная область
оставалась ниже Analytics.

## Исправленные layout constraints

- три уровня переведены с fixed height на `minimumHeight` / `maximumHeight`;
- корневой layout распределяет высоту в пропорции `45 / 35 / 20`;
- route, detail, analytics и Summary Card получили вертикальный
  `QSizePolicy.Expanding`;
- Timeline scroll растягивается только вертикально внутри route и сохраняет
  существующую горизонтальную навигацию;
- event-area получила адаптивный диапазон `100–150 px`;
- кнопка нового прохождения закреплена у нижней границы Summary Card через
  layout stretch;
- изображение этапа увеличено до `310×174` (примерно 16:9);
- preview впечатления и Quick Add получили нормальную читаемую высоту.

## UI Kit tokens

Добавлены/уточнены:

- `JOURNEY_ROUTE_MIN/BASELINE/MAX_HEIGHT`: `330 / 410 / 450`;
- `JOURNEY_DETAIL_MIN/BASELINE/MAX_HEIGHT`: `225 / 250 / 275`;
- `JOURNEY_ANALYTICS_MIN/BASELINE/MAX_HEIGHT`: `130 / 170 / 195`;
- `JOURNEY_STAGE_CARD_WIDTH/HEIGHT`: `190×160`;
- `JOURNEY_EVENT_AREA_HEIGHT`: `150`;
- `JOURNEY_ACTION_CARD_WIDTH/HEIGHT`: `88×76`;
- `JOURNEY_COMPACT_IMAGE_WIDTH`: `330`.

## Адаптивное поведение

- **1366×768:** используется controlled compact range; три уровня остаются
  видимыми, stage cards не уменьшаются до нечитаемого состояния.
- **1920×1080:** Journey использует Full HD baseline, события и Timeline имеют
  самостоятельную вертикальную область.
- **2560×1440:** рост ограничивается max-токенами, поэтому панели не становятся
  чрезмерно высокими.

Внутренний вертикальный scrollbar в `JourneyView` отсутствует. Горизонтальный
scroll Timeline сохранён и синхронизирован с существующими стрелками.

## Screenshots

- `docs/ui/screenshots/aw023_journey_geometry/journey_1366x768.png`
- `docs/ui/screenshots/aw023_journey_geometry/journey_1920x1080.png`
- `docs/ui/screenshots/aw023_journey_geometry/journey_2560x1440.png`

Скриншоты формируются детерминированным offscreen-инструментом
`tools/render_aw023_journey_geometry.py`; fixture не записывается в user.db.

## Проверки

Итоговые проверки:

- полный regression suite: `201 passed, 2 skipped, 4 subtests passed`;
- `python -m compileall -q app tests tools`: успешно;
- `git diff --check`: успешно (только существующие предупреждения Git о
  последующей нормализации LF/CRLF в рабочем дереве).

`catalog.db`, Studio и storage-контракты этим проходом не изменялись.
