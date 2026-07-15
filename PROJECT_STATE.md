# Velora project state

- Version: AW0.07 (Alpha Windows 0.07, completed)
- Python: 3.12.13
- PySide6: 6.11.1

## Каталог AW0.0711

- Текущий официальный микропатч: `AW0.0711`.
- В AW0.07 зафиксированы интеграция Icon Pack, ремонт статистики, счётчиков программ и пакетная публикация новых карточек Studio.

## AW0.07 — completed

- Ресурсы интерфейса выдаёт единый `IconRegistry` с безопасными fallback-иконками.
- Полосы статистики имеют фиксированную геометрию и не выходят за границы панелей при переключении разделов.
- Счётчики категорий программ закреплены в отдельной правой колонке.
- Studio сравнивает рабочий каталог с официальным и одним микропатчем публикует все новые и обновлённые карточки.
- Новые карточки помечаются синим `НОВОЕ`, изменённые существующие — жёлтым `ОБНОВЛЕНО`; общий фильтр называется `ИЗМЕНЕНИЯ`.
- Монохромные иконки нормализованы в белый цвет; цветные платформенные варианты остаются цветными только при явном запросе `variant="color"`.
- Quick View и полные карточки используют белые платформенные SVG; универсальное поле магазинов использует нейтральную витрину без логотипа Steam.
- Красный возрастной индикатор показывается после значения исключительно для рейтинга `18+`.
- Сетки всех типов каталога используют общие колонки; горизонтальная прокрутка доступна на компактной ширине и сбрасывается при перестроении раздела.
- Наведение на строку каталога теперь окрашивает всю строку единым тёмно-фиолетовым фоном; вложенный слой фиксированных колонок прозрачен и больше не создаёт серо-синий цветовой разрыв.
- Восстановлено сворачивание подгрупп кнопкой `−/+`; знак больше не зависит от кодировки шрифта.
- Hover, focus, меню, вкладки и кнопка изменения времени используют единый мягкий тёмно-фиолетовый акцент Velora; логотип `V` получил согласованную подсветку.
- У возрастного рейтинга устранён чёрный технический блок, а `18+` сохраняет центрирование и отдельную красную пиктограмму.
- Статус программ расширен для полного текста `НЕ ИСПОЛЬЗОВАЛ`; эквивалентные платформы (`iOS/iPhone`, `Windows/PC`) больше не создают дублирующиеся иконки.
- Диалог личной оценки одновременно принимает суммарное время взаимодействия для игр, фильмов, сериалов и программ и сохраняет его в общей хронологии.
- Заголовок каждой подгруппы и строки объектов используют один `COLUMN_AREA_WIDTH`, одинаковые интервалы и отдельное место под меню `•••`; геометрия защищена UI-тестом.
- Все фиксированные значения центрируются по оси соответствующего заголовка; тест проверяет восемь колонок отдельно для игр, фильмов, сериалов и программ.
- Локальные стили карточек ограничены точечными селекторами и больше не превращают вложенный текст в закруглённые капсулы.
- Шкалы статистики стали прямоугольными, получили крупные цветные счётчики и отдельные цвета оценочных диапазонов и статусов.
- Выполнен полный UI/UX-проход публичной альфы: адаптивная панель каталога, рабочий QSplitter, единые состояния темы и контекстные иконки.
- Проверены 1366×768, 1600×900, Full HD, 2K и масштабы Qt/Windows 100%, 125%, 150%, 175%, 200%.
- Диалоги и языковые заглушки приведены к общей визуальной системе; обязательная атрибуция Flaticon подтверждена.

## Каталог AW0.068 (previous)

- Подключена схема официальных метаданных Studio 0.03.
- Полные страницы показывают страны, языки, требования, награды, DLC, актёрский состав и сведения о ПО.
- Studio и полные страницы поддерживают бюджет с отдельной суммой и символом валюты; неизвестное значение показывается прочерком.
- Для всех 10 фильмов тестового каталога добавлены проверенные бюджеты съёмок; неподтверждённые бюджеты остальных типов остаются пустыми.
- Личная статистика дополнена распределением по странам и языкам, а также сводкой наград, DLC, актёров и открытого ПО.

## AW0.06 — completed

- Интегрирован официальный Velora Icon Pack v1.0 через единый кешируемый `IconRegistry` без абсолютных путей в виджетах.
- Каталог, Quick View, полные карточки, статистика, настройки и системные сообщения используют согласованные платформенные, возрастные и информационные иконки.
- Добавлены языковые флаги-заглушки; русский остаётся единственным активным языком.
- Добавлена обязательная атрибуция Flaticon и безопасный fallback отсутствующих ресурсов.

- Official catalog updates are independent database micro-patches (`AW0.061`, `.062`, and later).
- Studio publishes only `catalog.db`; local profiles, ratings, statuses, history and custom data remain in `user.db`.
- Catalog schema v2 reserves dynamic critic sources, watch availability, film duration and series season count.
- Status dictionaries are now media-aware for games, films, series and programs.
- Added `app/services` with age filtering and validated atomic catalog micro-patch installation.
- Added numbered SQLite migration chains for official catalog and local user data; `UserRepository` now runs user migrations.
- Added the stable assets structure for icons, logos, covers, placeholders, fonts, styles and composite UI resources.
- Catalog metadata keeps cumulative micro-patch history with per-media added counts plus updated/removed card totals.
- Built-in changelog renders entries such as `AW0.061 · +190 игр · +10 сериалов` directly from `catalog.db`.
- User workspace and fallback local profile are consistently named `Мой Velora` / `Velora`.
- User migration `002` renames only the legacy fallback profile `Velore`; custom profile names remain unchanged.
- Statistics bar counters use a fixed aligned column and no longer detach as a stray `0` when panels resize.
- Top navigation and the official catalog now support Games, Films, Series and Programs as live workspaces.
- Development catalog patch `AW0.062` contains 40 official cards: 10 per media type.
- Program catalog includes independently ratable Windows 10 (`Windows; PC`) and iOS 18 (`iOS; iPhone`) cards.
- Sidebar categories, subgroup rows, catalog columns, statuses and rating criteria are media-aware.
- My Velora statistics can be filtered by official media section while remaining based on personal interactions.
- Global search is a dedicated active workspace and resolves results through stable catalog IDs.
- Local media progress migration `003` stores film watch count and series season/episode independently from playtime.
- Quick View and full pages use media-aware metadata, descriptions, sources and interaction labels.
- Catalog micro-patch `AW0.063` adds four critic sources and expanded descriptions to all 40 official cards.

## AW0.03 completed

- Official SQLite `data/catalog.db` generated by Velora Studio 0.01.
- Stable readable catalog IDs such as `g-shooter-fps-001`.
- Official catalog data separated from local user data.
- Local `%LocalAppData%/Velora/user.db` profile and per-game state.
- New users start without ratings, playtime, favorites or completed statuses.
- Personal rating criteria, arithmetic mean, statuses, favorites and playtime history.
- Full game page with large cover area, metadata, description and critic score breakdown.
- Metacritic, IGN, DualShockers and PC Gamer score fields with a computed official mean.
- Full in-app `МОЙ VELORA` workspace with ratings, favorites, statistics and profile tabs.
- Direct top-level navigation between Games, Movies, Series and My Velora.
- Shared back/forward history for categories, items, details, profiles and workspaces.
- Quick View actions for opening and hiding an item.
- Settings split into General and Content, including 18+ filtering and hidden-item restore.
- Compact normalized platform/player-mode labels from Studio.
- Search, pagination, filters, collapsible groups and per-group column sorting.
- Interactive status editing from catalog, Quick View and full game page.
- V menu with settings, project information, changelog, Boosty support and exit.

## Placeholder or future scope

- Global search and custom catalog creation remain placeholders.
- Real cover assets have not yet been added through Studio.
- Studio and Velora packaging/installers are not included.

## AW0.04 architecture

- `GameData` and `GAME_STATUSES` moved from UI to `app/models/game.py`.
- Repositories and UI now depend on the domain model; the data layer no longer imports widgets.
- Persistent `user_activity` timeline stores old/new values for ratings, statuses, playtime, favorites and hidden state.
- Domain model stores playtime as numeric `playtime_hours: float`; localized text formatting is owned by UI widgets.
- First-run onboarding offers optional local profile creation and requires an explicit 18+ choice; adult content is hidden until completion.
- Quick View refactoring started: rating and playtime dialogs moved to dedicated modules.
- Animated V splash screen and two-step first-run profile/content choice.
- Settings can reset all local profile data with confirmation while preserving `catalog.db`.
- My Velora statistics replaced by a visual dashboard with KPI cards, rating/status bars, type donut, platform/year rankings, time leaders, favorite genres, records and taste comparison.
- Statistics use only user-interacted records, with a circular fixed-size donut, descending score ranges and SVG platform icons.
- Rating editor redesigned with SVG criteria icons, sliders, color feedback, live arithmetic mean and direct catalog-cell access.
- My Ratings and Favorites use responsive catalog-style sortable tables with explicit media type, category and subgroup columns.
- Titles in My Ratings and Favorites are hover-highlighted links to full item pages and remain correct after sorting.
- Internal item links resolve through stable `catalog_id` values, preparing canonical `velora://catalog/<id>` routes.
- Canonical routes are implemented as `velora://catalog/<id>`; navigation history stores IDs and central pages are mutually exclusive.
- Internal links restore their section and category from catalog data; history no longer hardcodes the Shooters category.
- AW0.05 release notes are available from the scrollable built-in changelog.

## Do not break

- Official catalog updates must never overwrite `user.db`.
- Stable catalog IDs must not change after publication.
- V menu overlays rather than shifting content.
- Star clicks do not select catalog rows.
- Quick View closes without clearing the selected item.
