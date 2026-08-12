from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtGui import QEnterEvent, QImage
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from app.core.icon_registry import ICON_ROOT, IconRegistry
from app.ui.velora_ui.components.animated_icon import HoverAnimatedIcon
from app.ui.velora_ui.icons import IconProvider
from app.ui.velora_ui.motion import animate_icon_pulse, reduced_motion_enabled
from app.ui.widgets.platform_icons import PlatformIconRow
from app.ui.sidebar.sidebar import Sidebar
from app.application.journey_presentation import JourneyEntry, JourneyStage
from app.ui.game_detail.journey_widgets import (
    JourneyEntryDialog, JourneyEventMarker, JourneyView,
)


class AssetPack1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.manifest_path = ICON_ROOT / "asset_pack_1" / "manifest.json"
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_manifest_assets_are_unique_and_present(self) -> None:
        ids = [item["id"] for item in self.manifest["assets"]]
        self.assertEqual(len(ids), len(set(ids)))
        for item in self.manifest["assets"]:
            self.assertTrue((self.manifest_path.parent / item["file"]).is_file())
            if item.get("dark_theme_path"):
                self.assertTrue((self.manifest_path.parent / item["dark_theme_path"]).is_file())

    def test_all_semantic_assets_resolve(self) -> None:
        for item in self.manifest["assets"]:
            category = item["id"].partition(".")[0]
            self.assertIsNotNone(IconRegistry.path(item["id"], category=category))

    def test_provider_exposes_integrated_keys(self) -> None:
        expected = {
            "service.boosty.color", "common.exit", "genre.rpg", "genre.action", "genre.racing",
            "metadata.engine", "metadata.dlc", "service.netflix",
            "animated.budget", "animated.search", "animated.settings",
            "animated.navigation_arrow_left", "animated.navigation_arrow_right",
            "animated.user_avatar",
            "animated.language_flag",
            "animated.genre_comedy",
            "animated.developer",
            "animated.plus",
            "animated.cinema",
            "animated.info",
            "animated.genre_animation",
            "animated.exit",
            "animated.platform",
            "animated.ticket",
        }
        self.assertTrue(expected.issubset(IconProvider.keys()))
        self.assertTrue(all(IconProvider.exists(key) for key in expected))

    def test_boosty_variants_are_distinct_files(self) -> None:
        paths = {
            IconRegistry.path(f"service.boosty.{variant}", category="service")
            for variant in ("dark", "light", "color")
        }
        self.assertEqual(len(paths), 3)

    def test_missing_asset_fallback_is_non_fatal(self) -> None:
        fallback = IconProvider.pixmap("does.not.exist", 20)
        self.assertEqual((fallback.width(), fallback.height()), (20, 20))

    def test_hover_movie_lifecycle_and_reduced_motion(self) -> None:
        widget = HoverAnimatedIcon("service.netflix", 24)
        self.assertIsNotNone(widget._movie)
        self.assertFalse(widget.pixmap().isNull())
        self.assertEqual(widget.pixmap().toImage().pixelColor(0, 0).alpha(), 0)
        with patch.dict(os.environ, {"VELORA_REDUCED_MOTION": "1"}):
            self.assertTrue(reduced_motion_enabled())
            widget.enterEvent(QEnterEvent(QPointF(), QPointF(), QPointF()))
            self.assertNotEqual(widget._movie.state().name, "Running")
        widget.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertFalse(widget.pixmap().isNull())
        widget.hide()
        self.assertNotEqual(widget._movie.state().name, "Running")

    def test_netflix_service_uses_hover_animation_in_platform_row(self) -> None:
        row = PlatformIconRow("Netflix")
        icons = row.findChildren(HoverAnimatedIcon)
        self.assertEqual(len(icons), 1)
        self.assertEqual(icons[0].objectName(), "netflixServiceIcon")
        self.assertEqual(icons[0].toolTip(), "Netflix")

    def test_film_and_series_services_use_named_brand_icons(self) -> None:
        row = PlatformIconRow(
            "Амедиатека; Кинопоиск HD; Premier", max_icons=5
        )
        labels = {label.objectName(): label for label in row.findChildren(QLabel)}
        self.assertIn("amediatekaServiceIcon", labels)
        self.assertIn("kinopoiskServiceIcon", labels)
        self.assertIn("premierServiceIcon", labels)
        self.assertTrue(all(not labels[name].pixmap().isNull() for name in (
            "amediatekaServiceIcon", "kinopoiskServiceIcon", "premierServiceIcon"
        )))
        self.assertEqual(labels["amediatekaServiceIcon"].toolTip(), "Амедиатека")
        self.assertEqual(labels["kinopoiskServiceIcon"].toolTip(), "Кинопоиск HD")
        self.assertEqual(labels["premierServiceIcon"].toolTip(), "Premier")
        kinopoisk_image = labels["kinopoiskServiceIcon"].pixmap().toImage()
        visible_colors = [
            kinopoisk_image.pixelColor(x, y)
            for y in range(kinopoisk_image.height())
            for x in range(kinopoisk_image.width())
            if kinopoisk_image.pixelColor(x, y).alpha() > 80
        ]
        self.assertTrue(visible_colors)
        self.assertGreater(
            sum(color.lightness() for color in visible_colors) / len(visible_colors),
            180,
        )

    def test_budget_animation_is_loadable(self) -> None:
        widget = HoverAnimatedIcon("animated.budget", 18)
        self.assertIsNotNone(widget._movie)
        self.assertTrue(widget._movie.isValid())
        self.assertEqual(widget._movie.currentPixmap().toImage().pixelColor(0, 0).alpha(), 0)
        self.assertFalse(
            widget.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        )
        widget.enterEvent(QEnterEvent(QPointF(), QPointF(), QPointF()))
        self.assertEqual(widget._movie.state().name, "Running")
        widget.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertNotEqual(widget._movie.state().name, "Running")

    def test_netflix_hover_animation_uses_red_frames(self) -> None:
        widget = HoverAnimatedIcon("service.netflix", 21, display_width=60)
        self.assertFalse(
            widget.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        )
        self.assertGreaterEqual(len(widget._sequence_frames), 100)
        widget.enterEvent(QEnterEvent(QPointF(), QPointF(), QPointF()))
        self.assertTrue(widget._sequence_timer.isActive())
        first = widget._sequence_frames[0].toImage()
        middle = widget._sequence_frames[len(widget._sequence_frames) // 2].toImage()
        last = widget._sequence_frames[-1].toImage()
        image = middle
        colors = [
            image.pixelColor(x, y)
            for y in range(image.height())
            for x in range(image.width())
            if image.pixelColor(x, y).alpha() > 80
        ]
        self.assertTrue(colors)
        self.assertTrue(any(color.red() > color.green() * 1.5 for color in colors))
        middle_visible = [
            x for x in range(image.width()) for y in range(image.height())
            if image.pixelColor(x, y).alpha() > 80
        ]
        first_visible = [
            x for x in range(first.width()) for y in range(first.height())
            if first.pixelColor(x, y).alpha() > 80
        ]
        last_visible = [
            x for x in range(last.width()) for y in range(last.height())
            if last.pixelColor(x, y).alpha() > 80
        ]
        self.assertGreater(
            max(middle_visible) - min(middle_visible),
            2 * (max(first_visible) - min(first_visible)),
        )
        self.assertEqual(
            (min(first_visible), max(first_visible)),
            (min(last_visible), max(last_visible)),
        )
        widget.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertFalse(widget._sequence_timer.isActive())

    def test_search_animation_is_loadable_and_transparent(self) -> None:
        widget = HoverAnimatedIcon("animated.search", 20)
        self.assertIsNotNone(widget._movie)
        self.assertTrue(widget._movie.isValid())
        image = widget._movie.currentPixmap().toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)

    def test_settings_animation_uses_archive_frames_and_hover_lifecycle(self) -> None:
        widget = HoverAnimatedIcon("animated.settings", 20)
        self.assertEqual(len(widget._sequence_frames), 28)
        self.assertIsNotNone(widget._movie)
        self.assertFalse(widget._movie.currentPixmap().isNull())
        self.assertEqual(
            widget._movie.currentPixmap().toImage().pixelColor(0, 0).alpha(), 0
        )
        widget.enterEvent(QEnterEvent(QPointF(), QPointF(), QPointF()))
        self.assertTrue(widget._sequence_timer.isActive())
        widget.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertFalse(widget._sequence_timer.isActive())

    def test_navigation_arrows_use_transparent_mirrored_archive_frames(self) -> None:
        left = HoverAnimatedIcon("animated.navigation_arrow_left", 18)
        right = HoverAnimatedIcon("animated.navigation_arrow_right", 18)
        self.assertEqual(len(left._sequence_frames), 25)
        self.assertEqual(len(right._sequence_frames), 25)
        left_image = left._sequence_frames[12].toImage()
        right_image = right._sequence_frames[12].toImage()
        self.assertEqual(left_image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(right_image.pixelColor(0, 0).alpha(), 0)
        native_left = QImage(str(
            self.manifest_path.parent
            / "animated/navigation_arrow_left_frames/frame_012.png"
        ))
        native_right = QImage(str(
            self.manifest_path.parent
            / "animated/navigation_arrow_right_frames/frame_012.png"
        ))
        self.assertEqual(native_left, native_right.flipped(Qt.Orientation.Horizontal))
        right.enterEvent(QEnterEvent(QPointF(), QPointF(), QPointF()))
        self.assertTrue(right._sequence_timer.isActive())
        right.leaveEvent(QEvent(QEvent.Type.Leave))
        self.assertFalse(right._sequence_timer.isActive())

    def test_default_avatar_animation_is_transparent_and_autoplays(self) -> None:
        widget = HoverAnimatedIcon(
            "animated.user_avatar", 88, autoplay=True, frame_interval_ms=40
        )
        widget.show()
        self.app.processEvents()
        self.assertEqual(len(widget._sequence_frames), 25)
        self.assertEqual(widget._sequence_frames[0].toImage().pixelColor(0, 0).alpha(), 0)
        self.assertTrue(widget._sequence_timer.isActive())
        widget.hide()
        self.assertFalse(widget._sequence_timer.isActive())
        widget.deleteLater()
        self.app.processEvents()

    def test_interface_language_uses_constant_apng_animation(self) -> None:
        widget = HoverAnimatedIcon(
            "animated.language_flag", 26, autoplay=True, frame_interval_ms=41
        )
        widget.show()
        self.app.processEvents()
        self.assertEqual(len(widget._sequence_frames), 28)
        self.assertTrue(widget._sequence_timer.isActive())
        self.assertLess(
            widget._sequence_frames[0].toImage().pixelColor(0, 0).alpha(),
            64,
        )
        widget.hide()
        self.assertFalse(widget._sequence_timer.isActive())
        widget.deleteLater()
        self.app.processEvents()

    def test_developer_metadata_icon_uses_constant_apng_animation(self) -> None:
        widget = HoverAnimatedIcon(
            "animated.developer", 18, autoplay=True, frame_interval_ms=41
        )
        widget.show()
        self.app.processEvents()
        self.assertEqual(len(widget._sequence_frames), 28)
        self.assertTrue(widget._sequence_timer.isActive())
        widget.hide()
        self.assertFalse(widget._sequence_timer.isActive())
        widget.deleteLater()
        self.app.processEvents()

    def test_cinema_metadata_icon_uses_constant_apng_animation(self) -> None:
        widget = HoverAnimatedIcon(
            "animated.cinema", 18, autoplay=True, frame_interval_ms=41
        )
        widget.show()
        self.app.processEvents()
        self.assertEqual(len(widget._sequence_frames), 28)
        self.assertTrue(widget._sequence_timer.isActive())
        widget.hide()
        self.assertFalse(widget._sequence_timer.isActive())
        widget.deleteLater()
        self.app.processEvents()

    def test_information_icon_uses_constant_apng_animation(self) -> None:
        widget = HoverAnimatedIcon(
            "animated.info", 20, autoplay=True, frame_interval_ms=41
        )
        widget.show()
        self.app.processEvents()
        self.assertEqual(len(widget._sequence_frames), 28)
        self.assertTrue(widget._sequence_timer.isActive())
        widget.hide()
        self.assertFalse(widget._sequence_timer.isActive())
        widget.deleteLater()
        self.app.processEvents()

    def test_comedy_category_uses_hover_apng_and_drama_has_bold_outline(self) -> None:
        sidebar = Sidebar({"КОМЕДИЯ": 12, "АНИМАЦИЯ": 12, "ДРАМА": 8})
        comedy = sidebar.category_buttons["КОМЕДИЯ"]
        animated = comedy.findChild(
            HoverAnimatedIcon, "animatedComedyCategoryIcon"
        )
        self.assertIsNotNone(animated)
        self.assertEqual(len(animated._sequence_frames), 28)
        QApplication.sendEvent(comedy, QEvent(QEvent.Type.Enter))
        self.assertTrue(animated._sequence_timer.isActive())
        QApplication.sendEvent(comedy, QEvent(QEvent.Type.Leave))
        self.assertFalse(animated._sequence_timer.isActive())
        animation = sidebar.category_buttons["АНИМАЦИЯ"]
        illustrator = animation.findChild(
            HoverAnimatedIcon, "animatedAnimationCategoryIcon"
        )
        self.assertIsNotNone(illustrator)
        self.assertEqual(len(illustrator._sequence_frames), 28)
        QApplication.sendEvent(animation, QEvent(QEvent.Type.Enter))
        self.assertTrue(illustrator._sequence_timer.isActive())
        QApplication.sendEvent(animation, QEvent(QEvent.Type.Leave))
        self.assertFalse(illustrator._sequence_timer.isActive())
        drama_svg = (
            self.manifest_path.parent / "genres" / "drama.svg"
        ).read_text(encoding="utf-8")
        self.assertIn('stroke-width="10"', drama_svg)
        sidebar.deleteLater()
        self.app.processEvents()

    def test_favorite_pulse_never_changes_widget_geometry(self) -> None:
        button = QPushButton()
        button.setFixedSize(40, 40)
        button.setIconSize(QSize(20, 20))
        before = button.size()
        animation = animate_icon_pulse(button, adding=True)
        self.assertEqual(button.size(), before)
        self.assertIsNotNone(animation)
        self.assertEqual(animation.keyValueAt(0.38), QSize(34, 34))
        animation.stop()
        removal = animate_icon_pulse(button, adding=False)
        self.assertGreater(removal.keyValueAt(0.38).width(), button.iconSize().width())
        self.assertEqual(button.size(), before)
        removal.stop()

    def test_journey_event_preview_prefers_theme_and_compacts_note_body(self) -> None:
        generic_note = JourneyEntry(
            "event-1", "note", "Заметка",
            "Очень длинное воспоминание об этапе, которое не должно растягивать таймлайн",
            "2026-08-11T12:00:00", "stage-01", 1,
        )
        preview = JourneyEventMarker.preview_text(generic_note)
        self.assertTrue(preview.startswith("Очень длинное"))
        self.assertTrue(preview.endswith("..."))
        self.assertLessEqual(len(preview), JourneyEventMarker.PREVIEW_MAX_CHARS)
        self.assertEqual(JourneyEventMarker.heading_text(generic_note), "Заметка")

        authored_theme = JourneyEntry(
            "event-2", "note", "Главная битва",
            "Подробный текст, который остаётся в описании",
            "2026-08-11T12:01:00", "stage-01", 1,
        )
        self.assertEqual(JourneyEventMarker.heading_text(authored_theme), "Главная битва")
        self.assertTrue(
            JourneyEventMarker.preview_text(authored_theme).startswith("Подробный текст")
        )
        duplicate = JourneyEntry(
            "event-3", "difficult_moment", "Сложный момент", "",
            "2026-08-11T12:02:00", "stage-01", 1, rating=7.0,
        )
        marker = JourneyEventMarker(duplicate)
        self.assertEqual(JourneyEventMarker.heading_text(duplicate), "Сложный момент")
        self.assertEqual(JourneyEventMarker.preview_text(duplicate), "")
        marker.deleteLater()

    def test_active_journey_event_rating_uses_event_revision(self) -> None:
        entry = JourneyEntry(
            "event-rating", "note", "Тема", "Текст", "2026-08-11T12:00:00",
            "stage-01", 1, rating=6.0, tags=("важное",), mood_id="positive",
        )
        view = JourneyView()
        view._model = SimpleNamespace(
            stages=(JourneyStage("stage-01", "Этап", (entry,)),)
        )
        view._selected_stage_id = "stage-01"
        view._selected_event_id = "event-rating"
        revisions = []
        stage_changes = []
        view.event_revision_requested.connect(revisions.append)
        view.stage_rating_requested.connect(
            lambda stage_id, rating: stage_changes.append((stage_id, rating))
        )
        view._select_event(entry)
        self.assertEqual(view.preview_caption.text(), "Тема")

        view._request_stage_rating(10.0)

        self.assertEqual(stage_changes, [])
        self.assertEqual(len(revisions), 1)
        event_id, draft = revisions[0]
        self.assertEqual(event_id, "event-rating")
        self.assertEqual(draft.rating, 10.0)
        self.assertEqual(draft.title, "Тема")
        self.assertEqual(draft.body, "Текст")
        self.assertEqual(draft.tags, ("важное",))
        self.assertEqual(draft.mood_id, "positive")
        view.deleteLater()
        self.app.processEvents()

    def test_every_journey_event_can_have_a_separate_title_and_note(self) -> None:
        stage = JourneyStage("stage-01", "Этап", ())
        dialog = JourneyEntryDialog(stage, "note", 1)
        self.assertTrue(dialog.title_edit.isVisibleTo(dialog))
        dialog.title_edit.setText("Главная тема")
        dialog.body_edit.setPlainText("Короткое описание заметки")
        draft = dialog.draft()
        self.assertEqual(draft.title, "Главная тема")
        self.assertEqual(draft.body, "Короткое описание заметки")
        marker_entry = JourneyEntry(
            "event-title", "note", draft.title, draft.body,
            "2026-08-11T12:00:00", "stage-01", 1,
        )
        marker = JourneyEventMarker(marker_entry)
        self.assertEqual(marker.kind_label.text(), "Главная тема")
        self.assertEqual(marker.title_label.text(), "Короткое описание зам...")
        self.assertEqual(marker.title_label.toolTip(), "Короткое описание заметки")
        self.assertFalse(marker.description_label.isVisible())
        marker.deleteLater()
        dialog.deleteLater()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
