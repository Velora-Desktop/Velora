# AW0.23 Asset Pack 1.0 — Integration Report

## 1. Scope
Asset Pack 1.0 встроен в существующую дизайн-систему AW0.23. Journey domain,
Schema 1, catalog.db, Studio и Creator не изменялись.

## 2. Source audit
Проверены ZIP-манифест, README и документ обработки логотипов. В архиве
обнаружены 24 runtime assets и 16 исходных PNG для визуального сравнения.

## 3. Existing architecture
Сохранены единственные `IconRegistry`, `IconProvider` и Velora UI Kit.

## 4. Merge strategy
Пакет размещён в `assets/icons/asset_pack_1`; его манифест читается третьим
источником общего реестра. Существующие манифесты не заменены.

## 5. Semantic IDs
Подключены пространства brand, genre, metadata, service и animated.

## 6. Velora и Boosty
Повторная сверка с исходным DOCX показала, что dark, light и color варианты относятся
к Boosty, а не к Velora. Они зарегистрированы как `service.boosty.*`. Верхний знак
Velora возвращён к фирменной букве `V`, а белый `service.boosty.light` назначен действию
«Поддержать Velora».

## 7. Genres
Новые genre assets подключены к совпадающим категориям Sidebar. RPG и прочие
жанры продолжают использовать прежние проверенные fallback-иконки.

## 8. Metadata
Release, players, system, engine и DLC подключены к карточке через semantic
provider. Publisher не заменялся из-за отсутствия однозначного ресурса.

## 9. Services
Netflix GIF, Amediateka PNG, Kinopoisk и Premier SVG зарегистрированы; их
цвета не подвергаются tint.

## 10. Animated assets
Netflix и budget используют общий `HoverAnimatedIcon`: первый кадр в покое,
play на hover, stop/reset на leave и stop при hide.

## 11. Motion
Добавлены общие 120/180/220 мс и OutCubic. Reduced motion управляется
`VELORA_REDUCED_MOTION`.

## 12. Favorite pulse
Pulse меняет только iconSize внутри фиксированной кнопки; размеры и layout не
изменяются.

## 13. Fallback
Неизвестные, отсутствующие и некорректные ресурсы не вызывают падение;
предупреждение выдаётся один раз на asset.

## 14. Caching
Сохранены существующие LRU-кэши registry/provider; второй кэш не добавлялся.

## 15. DPI
Ресурсы остаются векторными там, где это предусмотрено пакетом; проверки
выполняются на 100/125/150/200% через масштабирование Qt.

## 16. Dark theme
Монохромные assets тонируются светлым токеном; brand/service сохраняют
исходные цвета. Contact sheet проверен на тёмном фоне.

## 17. Documentation
Обновлён `VELORA_ICON_PACK.md`, добавлен contact sheet и этот отчёт.

## 18. Tests
Добавлены проверки манифеста, уникальности ID, существования файлов,
разрешения semantic keys, brand variants, fallback, GIF lifecycle,
reduced-motion и инварианта геометрии favorite pulse.

Фактическая финальная проверка:

- Asset Pack и связанные UI integration tests: 13 passed;
- полный regression suite: 240 passed, 2 skipped, 4 subtests passed;
- `compileall`: success;
- `git diff --check`: success (только предупреждения Git о будущей нормализации LF/CRLF).

## 19. Known limitations
Сервисные ресурсы зарегистрированы для дальнейшего использования; массовая
перестройка экранов сервисов вне scope. About не получил кликабельный GitHub,
поскольку в проекте не найден подтверждённый официальный URL. Boosty уже
использует существующий реальный адрес в меню поддержки.

## 20. Stop boundary
Journey Completion Pass и Creator не продолжались. Git commit не выполнялся.
