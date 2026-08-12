# AW0.231 — Catalog Quality Backfill Report

## Статус

**PARTIAL / BLOCKED** — обложки каталога и проверяемая часть обложек хронологий
готовы, но массовый официальный Journey backfill нельзя безопасно записать через
существующий publish path без изменения Studio/AW0.2 bridge.

## Что проверено

- `data/catalog.db`: 397 объектов, из них 100 игр.
- Описания: пустых нет, но обнаружены 12 слишком коротких, 30 чрезмерно длинных
  и 3 группы дословных дублей у разных игр.
- Обнаружены ошибочные метаданные отдельных изданий/лет; поэтому существующие
  описания нельзя считать полностью проверенным backfill.
- Хронологии: 66 серий, 301 уникальный узел, 77 связанных карточек каталога.
- Обложки хронологий: 273/301 локальных валидных файлов, 0 битых путей,
  28 узлов без обложки и в `manual_review`.
- Dishonored: все три узла (`Dishonored`, `Dishonored 2`,
  `Death of the Outsider`) имеют локальные обложки.
- `user.db` не изменялся.

## Реальная блокирующая несовместимость

Официальный Journey хранится в Schema 1 как `catalog_payloads` с типом
`journey_template`. Рабочий `data/catalog.db` — legacy-каталог с таблицами
`catalog_items` и `metadata`; таблицы payload в нём нет. Runtime Schema 1
`%LOCALAPPDATA%/Velora/data/catalog.db` содержит только Doom Eternal. Текущий
`AW02CatalogBridge.save_if_supported()` также намеренно принимает только Doom.

Следовательно, массовая запись Journey для остальных 99 игр потребовала бы
изменить Studio bridge/import/publish path — это прямо запрещено задачей
(`Studio` и архитектуру Journey не менять). Запись payload в `chronology_json`
или иной неподходящий столбец создала бы несовместимые данные и не используется
Velora.

Минимальное необходимое отдельное решение: утверждённый импорт всех игровых
записей legacy-каталога в Schema 1 и расширение Studio bridge с Doom-only до
универсальной публикации `journey_template`. До этого официальный массовый
Journey backfill должен оставаться `manual_review`, а не имитироваться.

## Проверка разнородной выборки (20 игр)

| Игра | Тип | Результат |
|---|---|---|
| Doom Eternal | FPS / линейная кампания | PASS: эталонный Journey, 13 миссий |
| Titanfall 2 | FPS / кампания | manual_review: применим, нужен официальный payload |
| Dishonored 2 | immersive sim | manual_review: применим, нужен официальный payload |
| Alan Wake 2 | horror/adventure | manual_review: применим, главы/сюжетные части |
| Baldur's Gate 3 | RPG | manual_review: нелинейные акты, нельзя копировать Doom |
| Cyberpunk 2077 | open-world RPG | manual_review: сюжетные арки, описание слишком короткое |
| Elden Ring | open-world action RPG | manual_review: регионы/вехи, неверный год в legacy данных |
| Hades | roguelike | manual_review: runs, описание слишком короткое |
| Dead Cells | roguelike/metroidvania | manual_review: runs/биомы, описание слишком короткое |
| Forza Horizon 5 | racing/open world | manual_review: фестивальные серии, неверный год |
| Gran Turismo 7 | racing simulator | manual_review: меню/книги, не линейные миссии |
| Cities: Skylines | city builder | NOT_APPLICABLE для фиксированной кампании |
| Europa Universalis IV | grand strategy | NOT_APPLICABLE для фиксированных этапов |
| Hearts of Iron IV | grand strategy | NOT_APPLICABLE для фиксированных этапов |
| Minecraft | sandbox | NOT_APPLICABLE для официальных stage instances |
| No Man's Sky | sandbox/exploration | NOT_APPLICABLE для фиксированной кампании |
| Counter-Strike 2 | multiplayer | NOT_APPLICABLE для фиктивной кампании |
| Apex Legends | battle royale | системный template без официальных миссий; manual_review |
| Sea of Thieves | multiplayer sandbox | системный template без фиктивной кампании; manual_review |
| Stardew Valley | life/farm sim | manual_review: сезоны/личные вехи, не 13 миссий |

Выборка не проходит критерий готовности микропатча: структура игр различается
логично, но publish path не позволяет сохранить официальный результат для 99
карточек. Поэтому статус `PASS` не заявляется.

## Хронологии и обложки

- Загружено и нормализовано 196 внешних обложек хронологий.
- Каталожные узлы используют канонические обложки из
  `assets/covers/catalog`.
- 28 сомнительных/будущих/недоступных узлов перечислены в
  `assets/covers/chronology/aw0231_chronology_cover_sources.json`.
- Случайные изображения, логотипы и fan art ради 100% покрытия не применялись.
- Игры без осмысленной серии не получили искусственную хронологию.

## Результат

- CATALOG: 100 игр
- DESCRIPTIONS: 0/100 подтверждённых этим проходом; 100 требуют нормализованного publish path/provenance
- JOURNEY APPLICABLE: 86 (предварительная классификация)
- JOURNEY COMPLETE: 1
- NOT APPLICABLE: 14 (предварительная классификация)
- MANUAL REVIEW: 99 для официального Journey payload
- CHRONOLOGY COVERS: 273/301
- CHRONOLOGY MISSING: 28
- CHRONOLOGY MANUAL REVIEW: 28
- INTEGRITY: PASS

## Ограничения

До утверждения универсальной публикации Schema 1 нельзя честно считать полный
catalog quality backfill завершённым. `manual_review` здесь означает отсутствие
безопасного publish path либо неоднозначную структуру игры, а не ошибку UI.

## Проверки

- Catalog/chronology tests: **6/6 PASS**.
- Full regression suite: **272 PASS, 2 skipped, 1 FAIL** из 275. Сбой находится
  в `HoverAnimatedIcon.eventFilter`: Qt-событие обращается к уже удалённому
  объекту во время `test_changelog_dialog`; каталог и хронологии в traceback не
  участвуют. В рамках data-backfill посторонний UI-код не изменялся.
- `compileall`: **PASS**.
- `git diff --check`: **PASS** (только предупреждения Git о будущей нормализации
  окончаний строк в ранее изменённых файлах).
- SQLite `integrity_check`: **PASS**; foreign-key violations: **0**.
