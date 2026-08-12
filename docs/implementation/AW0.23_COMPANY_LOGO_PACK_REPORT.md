# AW0.23 Company Logo Pack Report

## Что реализовано

- Проанализирован переданный Wikimedia downloader и его 13 категорий.
- Общий запуск выполнен, но Wikimedia вернул HTTP 429 для категорий; интеграция
  продолжена безопасными точечными запросами к тому же официальному MediaWiki API.
- В существующий `IconRegistry` подключён локальный manifest компании без второго
  реестра или runtime-зависимости от Wikimedia.
- Добавлен строгий resolver exact/normalized aliases и безопасный текстовый fallback.
- В карточке игры и Quick View разработчик/издатель отображаются единым компонентом:
  локальный логотип, имя, максимум две компании и `+N`.
- В «О проекте» добавлена ссылка и атрибуция Wikimedia Commons.

## Отобранные SVG

Electronic Arts, Sony Interactive Entertainment, Bethesda Softworks, Xbox Game
Studios, 2K Games, Blizzard Entertainment, Deep Silver, Capcom, Warner Bros.
Games, Rockstar Games и Ubisoft. Источник каждого файла указан в
`assets/icons/company/company_logos_manifest.json`.

## Aliases

Добавлены проверенные варианты EA / Electronic Arts Inc., EA Black Box,
PlayStation PC LLC, Microsoft Studios / Microsoft Game Studios, 2K и Capcom Co.
Ltd. Агрессивное fuzzy-сопоставление не используется.

## Manual review

FromSoftware, id Software, Naughty Dog, Larian Studios, Paradox Interactive,
Riot Games, Sega, Square Enix и CD Projekt RED оставлены без случайной подстановки:
точный актуальный SVG не был надёжно подтверждён в текущем API-проходе.

## Покрытие каталога

- Уникальных непустых developer/publisher tokens: 148.
- Exact/normalized alias match: 11 уникальных токенов.
- Без логотипа (безопасный текст): 137.
- Manual review: 9.
- Зарегистрированных локальных SVG: 11.
- Дубликатов semantic ID: 0.

Низкое покрытие связано с качеством исходных catalog metadata: в полях компаний
также встречаются персоны, Wikidata ID и ошибочные сущности. Названия каталога не
менялись, чтобы presentation mapping не повреждал source-of-truth.

## Проверка

Проверены роли developer/publisher, отсутствие подмены неизвестной компании,
валидность SVG, сохранение aspect ratio, уникальность semantic ID и integrity
`catalog.db`. Полные результаты тестов зафиксированы финальным запуском задачи.

## Ограничения

- Subtle hover использует существующую CSS-подсветку контейнера без GIF и layout shift.
- Цветные бренды не tint-ятся.
- Дальнейшее расширение pack требует ручной проверки актуальности и лицензии
  конкретного Wikimedia-файла.
