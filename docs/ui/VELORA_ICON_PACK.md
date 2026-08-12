# Velora Icon Pack

Интерфейс получает иконки только по semantic key через `IconProvider`.
Абсолютные пути за пределами provider запрещены. Provider использует общий
`IconRegistry`, кэширует pixmap и при неизвестном или отсутствующем SVG
возвращает прозрачный fallback без исключения.

Journey keys имеют пространства `journey.*`, `status.*`, `navigation.*`,
`rating.*`. SVG имеют `viewBox="0 0 24 24"`, единый stroke и не содержат
брендовых знаков. Для добавления ресурса: положить SVG в пакет, зарегистрировать
semantic key и добавить проверку `IconProvider.exists`.

## Asset Pack 1.0 (AW0.23)

Asset Pack встроен в тот же `IconRegistry`; отдельного реестра или второго UI
Kit нет. Нормативный манифест находится в
`assets/icons/asset_pack_1/manifest.json`, а runtime по-прежнему получает
ресурс исключительно по semantic ID.

- `service.boosty.dark|light|color` — три варианта логотипа Boosty без tint;
- `common.exit` — выход из приложения; используется только для команды завершения работы;
- `metadata.dlc` — DLC/дополнение; контроллер со стрелкой загрузки, источник Icons8;
- `genre.rpg` — скрещённые мечи; `genre.action` — кулак;
- `genre.racing`, `genre.strategy`, `genre.adventure` — флаг, шахматный конь и компас;
- `genre.system`, `genre.graphics` — процессор и графический редактор;
- `genre.drama`, `genre.comedy`, `genre.fantasy` — драматический профиль, маски и книга;
- `genre.*` — action, racing, strategy, adventure, fighting, drama, comedy,
  fantasy; существующая RPG-иконка остаётся fallback;
- `metadata.*` — external_link, system, engine, dlc, release, game_support,
  players и graphics;
- `service.*` — Netflix, Amediateka, Kinopoisk и Premier в исходных цветах;
- `animated.budget` — hover-анимация бюджета.

Tint применяется только к монохромным ресурсам. Brand и service assets всегда
сохраняют исходные цвета. GIF запускаются только при наведении через единый
`HoverAnimatedIcon`, останавливаются при уходе курсора/скрытии виджета и при
`VELORA_REDUCED_MOTION=1` остаются на первом кадре. Отсутствующий либо
повреждённый ресурс не завершает приложение: используется прозрачный fallback,
а предупреждение логируется один раз для semantic ID.

Длительности микродвижения централизованы в `Motion`: 120/180/220 мс,
`OutCubic`. Pulse избранного меняет только `iconSize`, поэтому геометрия кнопки
и layout не сдвигаются. Contact sheet для визуальной проверки:
`VELORA_ICON_PACK_AW023_CONTACT_SHEET.png`.

## Company Logo Pack 1.0 (AW0.23)

Логотипы компаний регистрируются в существующем `IconRegistry` под ключами
`company.*`. Runtime использует только локальные SVG из `assets/icons/company`;
Wikimedia Commons не вызывается при запуске приложения. Исходные страницы,
имена файлов и статус отбора зафиксированы в
`company_logos_manifest.json`.

Сопоставление выполняется только по проверенным exact/normalized aliases через
`app.core.company_logos`. Неизвестное или неоднозначное имя безопасно отображается
обычным текстом. Фирменные цвета сохраняются, SVG вписывается в общий bounding box
с `KeepAspectRatio`, а кэширование обеспечивает существующий `IconRegistry`.
