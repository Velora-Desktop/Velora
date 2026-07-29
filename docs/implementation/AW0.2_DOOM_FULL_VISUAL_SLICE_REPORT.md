# AW0.2 Doom Eternal — Full Visual Product Slice

## Результат

Doom Eternal подключён к Schema 1 как первый законченный визуальный срез
AW0.2. Остальные строки каталога продолжают работать через legacy-путь.

## Видимые возможности

- строка Doom Eternal получает название, состояние библиотеки, прохождение,
  игровое время, номер прохождения, личную оценку, checkpoint и признак Journey
  из нового read-side;
- меню строки строится из `resolve_row_actions(...)`;
- подробная страница содержит сводку и разделы «Обзор», «Прохождения»,
  `Journey`, «Впечатления» и «Оценки»;
- доступны начало и повтор прохождения, добавление времени, checkpoint,
  впечатления, личная оценка и завершение;
- после успешного commit обновляются только строка Doom Eternal и открытая
  страница Doom Eternal;
- каталог Studio остаётся источником названия и описания. Изменения видны
  после refresh или повторного открытия страницы.

## Граница данных

UI не читает SQLite и не импортирует repositories. Запись выполняется через
`DoomVerticalSlice`, существующие application services и Unit of Work.
Journey остаётся read-only лентой и отображается без UUID и JSON payload.
История оценок и прохождений не перезаписывается.

## Изменённые UI-файлы

- `app/ui/catalog/game_row.py`
- `app/ui/catalog/catalog_view.py`
- `app/ui/catalog/single_row_integration.py`
- `app/ui/catalog/doom_integration_controller.py`
- `app/ui/game_detail/game_detail_page.py`
- `app/ui/game_detail/doom_aw02_panel.py`
- `app/ui/main_window.py`

## Application/storage

- `app/application/doom_vertical_slice.py`
- `app/storage/repositories.py`

## Проверки

- критические интеграционные проверки: 9/9;
- полный regression suite: 125/125;
- реальный запуск `main.py`: приложение остаётся активным;
- сохранение и повторное открытие: проверено;
- rollback и отсутствие частичных данных: покрыто regression suite;
- визуальный smoke screenshot:
  `docs/implementation/aw02_doom_visual_smoke.png`.

## Известные ограничения

- визуальный срез включён только для Doom Eternal;
- остальные игровые строки и Quick View пока используют legacy-рендер;
- checkpoint title/description сохраняются в поддерживаемом поле текста
  checkpoint rating, поскольку Schema 1 не содержит отдельные колонки для
  этих значений;
- отдельного unread-состояния Journey в Schema 1 нет, поэтому строка показывает
  наличие событий Journey, а не счётчик непрочитанных;
- Studio визуально не расширялась.

