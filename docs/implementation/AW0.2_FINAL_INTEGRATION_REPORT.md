# AW0.2 Final Integration Report

## Подключено

- Нормальный source-run запуск Velora AW0.2 без feature flags.
- Catalog 0.21, user.db Schema 1 и Core Generation 1.
- Безопасный one-time reset legacy-профиля: verified snapshot, архив,
  recovery journal, quarantine и active generation pointer.
- Doom Eternal как единственная полная вертикаль нового ядра.
- Read-side: `GamesRowQueryService` → typed state/DTO → ViewModel →
  presentation → существующий `GameRow`.
- Write-side существующих элементов управления Doom: статус, суммарное
  игровое время и итоговая оценка через application services и Unit of Work.
- Checkpoint, impression, rating history, Journey и повторное прохождение
  поддерживаются application facade и сохраняются в Schema 1.
- Velora Studio 0.1: редактирование основных полей Doom в Catalog 0.21 с
  обязательным snapshot; `user.db` Studio не изменяет.

## Оставлено в legacy

- Все карточки, кроме Doom Eternal.
- Остальные разделы каталога, их write handlers, Quick View и подробные
  страницы используют существующее поведение AW0.1.

## Резервные копии и восстановление

- Snapshots: `%LOCALAPPDATA%\Velora\backups\snapshots`.
- Архив legacy-профиля: `%LOCALAPPDATA%\Velora\legacy\<operation_id>`.
- Reset journal: `%LOCALAPPDATA%\Velora\profile\reset_state.json`.
- Active pointer: `%LOCALAPPDATA%\Velora\profile\active_generation.json`.
- Quarantine: `%LOCALAPPDATA%\Velora\profile\quarantine`.

## Запуск из PowerShell / терминала VS Code

```powershell
& "C:\Program Files\Python312\python.exe" "C:\Velora\main.py"
& "C:\Program Files\Python312\python.exe" "C:\Velora studio\main.py"
```

Переменные `VELORA_AW02_SINGLE_ROW_READ` и
`VELORA_AW02_SINGLE_ROW_DIAGNOSTIC` больше не нужны.

## Ограничения

- Массовый перевод остальных строк Games на новое ядро не выполнялся.
- Для checkpoint и impression пока нет новых отдельных видимых редакторов;
  application API и persistence готовы.
- Studio 0.1 подключена к Schema 1 только для утверждённой вертикали Doom;
  остальной каталог продолжает редактироваться существующим Studio workflow.

## Проверки

- Final integration tests: `3/3`.
- Полный Velora regression suite: `125/125`.
- Полный Studio regression suite: `12/12`.
- `compileall`: success.
- Velora offscreen source-run smoke: процесс стабильно работает.
- Studio offscreen source-run smoke: процесс стабильно работает.
