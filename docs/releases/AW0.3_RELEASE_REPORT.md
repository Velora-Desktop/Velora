# Velora AW0.3 / AW0.301 Release Report

## Release migration

- Внутренний цикл AW0.23 перенесён в базовый релиз AW0.3.
- Контентный цикл AW0.231 перенесён в текущий микропатч AW0.301.
- Исторические implementation reports не переименовывались и сохраняют исходную нумерацию.
- Runtime-visible версия Velora: AW0.301; базовый релиз: AW0.3; Studio: 0.2.

## Universal Journey architecture

Поток данных: `Game → official Journey payload → GameJourneySlice → Universal Journey UI`.

`catalog.db` хранит официальный template и ordered stages. `user.db` хранит playthrough, progress, stage state, rating, mood, events и notes. DoomVerticalSlice сохранён как compatibility adapter; общий presentation/runtime pipeline не привязан к Doom и поддерживает динамическое число этапов.

## Generic Journey infrastructure

- GameJourneySlice;
- JourneyPublishRequest;
- JourneyStagePublish;
- Generic Journey Publish Bridge;
- Journey Template Registry;
- stable stage IDs и dynamic stage count;
- идемпотентная публикация и безопасное удаление official Journey.

## UI Kit, assets and motion

UI Kit централизует tokens цветов, typography, spacing, dimensions и radii. IconRegistry/IconProvider предоставляют semantic IDs, SVG/APNG assets и fallback. Mood Pack и rating-компоненты переиспользуются Journey. Motion infrastructure использует 120/180/220 ms, reduced-motion, безопасный lifecycle Qt-анимаций и pulse без layout shift.

## Studio 0.2

Studio использует flow `дерево разделов → список карточек → существующий редактор`. Universal Visual Journey Editor работает через generic contracts и publish bridge, поддерживая Not Applicable, templates, inline structure editing, stable IDs, validation, Preview, republish и removal.

## Catalog content

- Games: 101.
- Descriptions: 101/101.
- Published Journey: 13.
- Template only: 55.
- Not Applicable: 17.
- Manual Review: 16.

## Verification

- Velora regression: 310 tests PASS, 2 historical skips.
- Studio regression: 43 tests PASS.
- Velora and Studio compileall: PASS.
- `catalog.db` integrity/foreign keys: PASS.
- `user.db` integrity/foreign keys: PASS.
- `git diff --check`: PASS before release commit.
