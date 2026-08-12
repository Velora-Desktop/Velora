# Velora AW0.301

Velora — локальное Windows-приложение для личной медиатеки, оценок и истории прохождений. Пользовательские данные хранятся отдельно от обновляемого официального каталога.

## Текущие версии

- Current Velora version: `AW0.301`
- Base release: `AW0.3`
- Velora Studio: `0.2`
- Catalog: `101` игра, описания `101/101`
- Profile schema: `1`

## Основные возможности

- единый каталог игр, фильмов, сериалов и программ;
- личные статусы, оценки, избранное, время и статистика;
- подробные карточки с metadata, хронологиями и локальными обложками;
- Journey 1.0: несколько прохождений, динамические этапы, Timeline, rating, mood, события и аналитика;
- раздельное хранение официального Journey в `catalog.db` и личной истории в `user.db`;
- централизованные UI Kit, Icon/Asset Pack и безопасная motion-система;
- Studio 0.2 для редактирования и публикации официального каталога и Journey.

## Запуск

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Данные

- `data/catalog.db` — официальный каталог, templates и stages.
- `data/user.db` — локальный профиль, playthrough, progress, rating, mood, события и заметки.

## Графические ресурсы

Часть интерфейсных иконок предоставлена [Flaticon](https://www.flaticon.com/uicons) и [Icons8](https://icons8.com). Логотипы компаний получены из [Wikimedia Commons](https://commons.wikimedia.org/). Подробности приведены в `THIRD_PARTY_NOTICES.md` и manifests ресурсов.

## Документация релиза

- `docs/releases/AW0.3_PATCH_NOTES.md`
- `docs/releases/AW0.301_PATCH_NOTES.md`
- `docs/releases/AW0.3_RELEASE_REPORT.md`
