"""Render deterministic AW0.23 Journey geometry checkpoints offscreen."""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from app.application.journey_presentation import JourneyEntry, JourneyPresentationBuilder
from app.styles.theme import application_stylesheet
from app.ui.game_detail.journey_widgets import JourneyView
from tests.test_aw021_journey_templates import make_state


OUTPUT = ROOT / "docs" / "ui" / "screenshots" / "aw023_journey_geometry"


def render(name: str, width: int, height: int) -> None:
    view = JourneyView()
    view.resize(width, height)
    view.set_presentation(JourneyPresentationBuilder().build(make_state()))
    view.show()
    QApplication.processEvents()
    view.grab().save(str(OUTPUT / name), "PNG")
    view.close()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(application_stylesheet())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    render("journey_31_1366.png", 1366, 768)
    render("journey_31_fullhd.png", 1920, 1080)
    render("journey_31_2k.png", 2560, 1440)

    model = JourneyPresentationBuilder().build(make_state())
    entry = JourneyEntry(
        "preview-event", "note", "Тяжёлый бой в конце",
        "Сложное сражение, которое запомнилось.", "2026-08-04T12:00:00Z",
        model.stages[2].stage_id, model.playthrough_sequence,
        tags=("Сложный бой", "Новое оружие"),
    )
    group = tuple(replace(entry, source_id=f"preview-{index}", title=f"Событие {index}")
                  for index in range(1, 6))
    event_model = replace(
        model, stages=tuple(
            replace(stage, entries=group) if index == 2 else stage
            for index, stage in enumerate(model.stages)
        )
    )
    view = JourneyView()
    view.resize(1920, 875)
    view.set_presentation(event_model)
    view._select_event(group[0])
    view.show(); QApplication.processEvents()
    view.grab().save(str(OUTPUT / "journey_final_event_selected.png"), "PNG")
    view._select_event_group(group)
    QApplication.processEvents()
    view.grab().save(str(OUTPUT / "journey_final_event_group.png"), "PNG")
    view.close()

    empty = replace(
        model, playthrough_id=None, playthrough_sequence=None, status=None,
        playthroughs=(), playthrough_options=(),
        stages=tuple(replace(stage, entries=(), state="not_started", rating=None,
                             mood_id=None, favorite=False, difficult=False)
                     for stage in model.stages),
    )
    view = JourneyView(); view.resize(1920, 875)
    view.set_presentation(empty); view.show(); QApplication.processEvents()
    view.grab().save(str(OUTPUT / "journey_final_empty_playthrough.png"), "PNG")
    view.close()


if __name__ == "__main__":
    main()
