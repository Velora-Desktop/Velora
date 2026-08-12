# AW0.231 Journey Finalization

## Проверено и завершено

- Studio открывается каталогом; существующий редактор карточки открывается только после выбора игры и имеет возврат в каталог.
- Основным workflow Journey стал визуальный Timeline. Скрытая таблица оставлена только как внутренний адаптер существующей модели, а не как пользовательский экран.
- Клик по карточке выбирает этап; двойной клик по названию переводит фокус в его Inspector. Добавление между этапами и в конце, перемещение, дублирование и удаление используют `JourneyConfiguration`.
- Перестановка сохраняет stable ID, дублирование создаёт новый ID. Пустые примерные названия остаются UI-placeholder и блокируют publish.
- Режимы «Редактирование» и Preview используют один экземпляр Timeline; Preview только скрывает управляющие элементы.
- Проверка и отдельная кнопка публикации используют Generic Journey Publish Bridge и не сохраняют несвязанные черновые поля карточки.
- Doom Eternal загружает утверждённые 13 русских этапов. Его Velora UI и пользовательский Journey не менялись.

## Catalog rollout

Использован только утверждённый `data/aw0231_journey_backfill.json`, без нового интернет-поиска. Legacy catalog ID проецируется в Schema 1 детерминированным UUID на границе bridge; исходный stable ID карточки не меняется.

- 13 игр опубликованы с подтверждёнными реальными этапами.
- 55 игр получили только назначение Template и корректный пустой список этапов.
- 17 игр оставлены Not Applicable без искусственного Timeline.
- 16 игр оставлены manual_review без выдуманных этапов.

Вся пачка применяется одной Schema 1 транзакцией после одного safety snapshot. SHA-256 `user.db` до и после rollout совпал.

## Проверки

- Studio visual/generic/UI targeted: 21/21 PASS.
- Velora Journey/runtime/persistence targeted: 52/52 PASS.
- Doom: 13 этапов, порядок и stable IDs PASS.
- Non-Doom: реальные 12-stage Journey и template-only payload прочитаны после повторного открытия PASS.
- Cross-game isolation и persistence PASS.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: без нарушений.
- `compileall`: PASS для Velora и Studio.
- `git diff --check`: PASS; только штатные предупреждения Git о будущей нормализации LF/CRLF.

## Итог

VISUAL EDITOR: PASS  
DOOM REFERENCE: PASS  
GENERIC PUBLISH: PASS

CATALOG GAMES: 101

Published Journey: 13  
Template only: 55  
Not Applicable: 17  
Manual Review: 16

Non-Doom Journey runtime: PASS  
Cross-game isolation: PASS  
Persistence: PASS  
Catalog integrity: PASS

## Оставшиеся ограничения

- Template-only игры намеренно не показывают фиктивные `Mission 1 / Chapter 1`; реальные этапы должны быть подтверждены отдельно.
- 16 неоднозначных игр остаются manual_review в утверждённом manifest.
- Визуальный редактор использует стрелки перемещения; drag-and-drop остаётся доступен внутренней модели, но не вынесен как обязательный основной жест.
