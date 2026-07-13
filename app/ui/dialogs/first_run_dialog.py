from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget


class FirstRunDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent); self.setWindowTitle("Первый запуск Velora"); self.setModal(True); self.setMinimumSize(600, 390)
        self.custom_profile_created = False; self._display_name = "Velore"
        root=QVBoxLayout(self); self.pages=QStackedWidget(); root.addWidget(self.pages)
        self.pages.addWidget(self._profile_page()); self.pages.addWidget(self._content_page())

    def _profile_page(self) -> QWidget:
        page=QWidget(); layout=QVBoxLayout(page); layout.setSpacing(14)
        title=QLabel("ДОБРО ПОЖАЛОВАТЬ В VELORA"); title.setStyleSheet("font-size:18pt;font-weight:600;"); layout.addWidget(title)
        text=QLabel("Создайте имя для локального профиля или продолжите с именем Velore.\nВсе личные данные останутся только на этом компьютере."); text.setObjectName("muted"); text.setWordWrap(True); layout.addWidget(text)
        self.profile_name=QLineEdit(); self.profile_name.setPlaceholderText("Введите имя профиля"); self.profile_name.setMinimumHeight(40); layout.addWidget(self.profile_name); layout.addStretch()
        create=QPushButton("СОЗДАТЬ ЛОКАЛЬНЫЙ ПРОФИЛЬ"); create.setMinimumHeight(42); create.setStyleSheet("background:#6E1BC4;border:1px solid #A54BFF;font-weight:600;"); create.clicked.connect(self._create_profile); layout.addWidget(create)
        skip=QPushButton("ПРОДОЛЖИТЬ БЕЗ ПРОФИЛЯ"); skip.setMinimumHeight(40); skip.setStyleSheet("background:#171E25;border:1px solid #35414B;color:#BFC7CE;"); skip.clicked.connect(self._skip_profile); layout.addWidget(skip); return page

    def _content_page(self) -> QWidget:
        page=QWidget(); layout=QVBoxLayout(page); layout.setSpacing(14)
        title=QLabel("КОНТЕНТ 18+"); title.setStyleSheet("font-size:18pt;font-weight:600;"); layout.addWidget(title)
        text=QLabel("Выберите, должен ли взрослый контент отображаться в каталоге."); text.setObjectName("muted"); layout.addWidget(text)
        self.hide_adult=QCheckBox("Скрывать контент 18+ (рекомендуется)"); self.show_adult=QCheckBox("Показывать контент 18+"); self.hide_adult.setChecked(True)
        checkbox_style = """
            QCheckBox { spacing:10px; min-height:28px; }
            QCheckBox::indicator { width:18px; height:18px; border:1px solid #697680; border-radius:4px; background:#091118; }
            QCheckBox::indicator:hover { border-color:#B36BFF; }
            QCheckBox::indicator:checked { border-color:#A54BFF; background:#7A22D1; image:url("C:/Velora/assets/icons/check.svg"); }
        """
        self.hide_adult.setStyleSheet(checkbox_style); self.show_adult.setStyleSheet(checkbox_style)
        self.hide_adult.toggled.connect(lambda checked: checked and self.show_adult.setChecked(False)); self.show_adult.toggled.connect(lambda checked: checked and self.hide_adult.setChecked(False))
        layout.addWidget(self.hide_adult); layout.addWidget(self.show_adult)
        hint=QLabel("Вы сможете изменить выбор позже: Настройки → Контент."); hint.setObjectName("muted"); layout.addWidget(hint); layout.addStretch()
        finish=QPushButton("ЗАПУСТИТЬ VELORA"); finish.setMinimumHeight(42); finish.setStyleSheet("background:#6E1BC4;border:1px solid #A54BFF;font-weight:600;"); finish.clicked.connect(self._finish); layout.addWidget(finish); return page

    def _create_profile(self) -> None:
        name=self.profile_name.text().strip()
        if not name: self.profile_name.setFocus(); self.profile_name.setStyleSheet("border:1px solid #FF4D5A;"); return
        self.custom_profile_created=True; self._display_name=name; self.pages.setCurrentIndex(1)

    def _skip_profile(self) -> None:
        self.custom_profile_created=False; self._display_name="Velore"; self.pages.setCurrentIndex(1)

    def _finish(self) -> None:
        if not self.hide_adult.isChecked() and not self.show_adult.isChecked(): self.hide_adult.setChecked(True)
        self.accept()

    @property
    def profile_requested(self) -> bool: return self.custom_profile_created
    @property
    def display_name(self) -> str: return self._display_name
    @property
    def hide_adult_content(self) -> bool: return not self.show_adult.isChecked()
