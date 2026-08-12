# Velora UI Kit 1.0

`app/ui/velora_ui` — presentation-only пакет AW0.23. Он содержит semantic
tokens, карточки, controls, IconProvider, Mood Pack и charts. Пакет не знает о
SQLite, repositories, Unit of Work и application services.

Journey первым мигрирован на `VeloraStageCard`, `VeloraActionCard` и
`MoodChart`. Данные передаются через конструкторы и публичные методы.

## Токены

Используйте `Colors`, `Spacing`, `Radii`, `Dimensions`, `Typography`.
Новые цвета и размеры нельзя встраивать строковыми литералами в компоненты.

## Миграция

| Компонент | Старое место | Новое место | Статус | Риск |
|---|---|---|---|---|
| Этап Journey | `journey_widgets.JourneyTimelineNode` | `VeloraStageCard` | мигрирован через совместимый адаптер | низкий |
| Быстрое действие | `journey_widgets.JourneyActionCard` | `VeloraActionCard` | мигрировано | низкий |
| График | `journey_widgets.JourneyMoodGraph` | `MoodChart` | мигрирован через адаптер | низкий |
| Остальные страницы | локальные widgets | UI Kit | не мигрированы намеренно | контролируемый |
