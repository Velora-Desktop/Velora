"""Render deterministic AW0.21 Journey fixtures for visual review."""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from app.application.journey_presentation import JourneyPresentationBuilder
from app.styles.theme import application_stylesheet
from app.ui.game_detail.journey_widgets import JourneyView
from tests.test_aw021_journey_templates import make_state


OUTPUT = (
    ROOT
    / "docs"
    / "implementation"
    / "screenshots"
    / "aw021_journey"
)


def _save(name: str, model, *, selected: str | None = None) -> None:
    view = JourneyView()
    view.resize(1500, 410)
    view.set_presentation(model)
    if selected:
        view._select_stage(selected)
    view.show()
    QApplication.processEvents()
    view.grab().save(str(OUTPUT / name), "PNG")
    view.close()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(application_stylesheet())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    builder = JourneyPresentationBuilder()
    state = make_state()

    empty = replace(
        state,
        row=replace(
            state.row,
            playthrough_status="planned",
            total_playtime_minutes=0,
            current_personal_rating_tenths=None,
            latest_impression_preview=None,
        ),
        playthroughs=(),
        impressions=(),
        ratings=(),
        journey=(),
    )
    _save("empty_playthrough.png", builder.build(empty))
    active = builder.build(state)
    _save("active_playthrough.png", active)
    _save("selected_mission.png", active, selected="stage-02")

    completed = replace(
        state,
        row=replace(state.row, playthrough_status="completed"),
        playthroughs=(replace(state.playthroughs[0], status="completed"),),
    )
    _save("completed_playthrough.png", builder.build(completed))

    repeat = replace(
        state,
        playthroughs=(
            replace(
                state.playthroughs[0],
                playthrough_id="fixture-run-1",
                sequence_no=1,
                status="completed",
            ),
            replace(
                state.playthroughs[0],
                playthrough_id="fixture-run-2",
                sequence_no=2,
                status="playing",
            ),
        ),
        impressions=(
            replace(state.impressions[0], playthrough_sequence=2),
        ),
    )
    _save(
        "repeat_playthrough.png",
        builder.build(repeat, playthrough_sequence=2),
    )
    app.processEvents()


if __name__ == "__main__":
    main()
