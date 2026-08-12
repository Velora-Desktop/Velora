from __future__ import annotations

import unittest

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget

from app.ui.velora_ui.components.animated_icon import HoverAnimatedIcon


class AnimatedIconRaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_hover_filter_ignores_owner_destroyed_before_queued_event(self):
        owner = QWidget()
        icon = HoverAnimatedIcon("animated.search", 20)
        icon.attach_hover_source(owner)
        owner.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QCoreApplication.processEvents()
        self.assertFalse(icon.eventFilter(owner, QEvent(QEvent.Type.Enter)))
        icon.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    unittest.main()
