# Velora Component Guide

## Карточки

- `VeloraCard` — базовая поверхность.
- `VeloraStageCard` — этап Journey, принимает только presentation data.
- `VeloraActionCard` — клавиатурно доступное быстрое действие.

## Controls и charts

- `VeloraMoodSelector.mood_id()` возвращает стабильный ID.
- `MoodChart.set_points()` принимает `MoodChartPoint`.

Компоненты нельзя связывать с конкретной игрой или базой данных. Hover,
selected, focus и disabled не меняют геометрию. Для отсутствующего ресурса
используется fallback IconProvider.
