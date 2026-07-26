from __future__ import annotations

from collections import defaultdict

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
)


class CustomSectionDialog(QDialog):
    """Add, rename or delete a user-owned top-level catalog section."""

    def __init__(self, sections: list[str], parent=None) -> None:
        super().__init__(parent)
        self.action = ""
        self.setWindowTitle("Пользовательские разделы")
        self.setMinimumWidth(500)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)
        title = QLabel("ПОЛЬЗОВАТЕЛЬСКИЕ РАЗДЕЛЫ")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        hint = QLabel(
            "Здесь создаётся только верхний раздел рядом с «Программами». "
            "Категории, подкатегории и карточки добавляются внутри выбранного раздела."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        root.addWidget(hint)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Название нового раздела, например: Футбол")
        root.addWidget(self.name)
        add = QPushButton("＋  ДОБАВИТЬ РАЗДЕЛ")
        add.setProperty("primary", True)
        add.clicked.connect(self._add)
        root.addWidget(add)
        root.addSpacing(8)
        self.existing = QComboBox()
        self.existing.addItems(sections)
        self.existing.setPlaceholderText("Выберите ранее созданный раздел")
        self.existing.currentTextChanged.connect(self._prepare_rename)
        root.addWidget(self.existing)
        self.rename_name = QLineEdit()
        self.rename_name.setPlaceholderText("Новое название выбранного раздела")
        self.rename_name.setEnabled(bool(sections))
        root.addWidget(self.rename_name)
        rename = QPushButton("ПЕРЕИМЕНОВАТЬ ВЫБРАННЫЙ РАЗДЕЛ")
        rename.setEnabled(bool(sections))
        rename.clicked.connect(self._rename)
        root.addWidget(rename)
        delete = QPushButton("УДАЛИТЬ ВЫБРАННЫЙ РАЗДЕЛ")
        delete.setProperty("danger", True)
        delete.setEnabled(bool(sections))
        delete.clicked.connect(self._delete)
        root.addWidget(delete)
        close = QPushButton("ЗАКРЫТЬ")
        close.clicked.connect(self.reject)
        root.addWidget(close)

    @property
    def section_name(self) -> str:
        return (
            self.name.text().strip() if self.action == "add"
            else self.rename_name.text().strip() if self.action == "rename"
            else self.existing.currentText().strip()
        )

    @property
    def original_section_name(self) -> str:
        return self.existing.currentText().strip()

    def _add(self) -> None:
        if not self.name.text().strip():
            self.name.setFocus()
            return
        self.action = "add"
        self.accept()

    def _delete(self) -> None:
        if not self.existing.currentText().strip():
            return
        self.action = "delete"
        self.accept()

    def _prepare_rename(self, name: str) -> None:
        self.rename_name.setEnabled(bool(name))
        if name and not self.rename_name.hasFocus():
            self.rename_name.setPlaceholderText(f"Новое название для «{name}»")

    def _rename(self) -> None:
        if not self.existing.currentText().strip():
            self.existing.setFocus()
            return
        if not self.rename_name.text().strip():
            self.rename_name.setFocus()
            return
        self.action = "rename"
        self.accept()


class CustomBranchDialog(QDialog):
    """Create an empty category/subcategory branch inside a local section."""

    def __init__(self, section: str, parent=None) -> None:
        super().__init__(parent)
        self.section_name = section
        self.setWindowTitle("Добавить подкатегорию")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)
        title = QLabel("НОВАЯ ПОДКАТЕГОРИЯ")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        section_label = QLabel(f"Раздел: {section}")
        section_label.setObjectName("muted")
        root.addWidget(section_label)
        form = QFormLayout()
        form.setSpacing(12)
        self.category = QLineEdit()
        self.category.setPlaceholderText("Например: Клубы")
        self.subgroup = QLineEdit()
        self.subgroup.setPlaceholderText("Например: АПЛ")
        form.addRow("Категория*", self.category)
        form.addRow("Подкатегория*", self.subgroup)
        root.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("ДОБАВИТЬ ПОДКАТЕГОРИЮ")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept_if_valid(self) -> None:
        if not self.category.text().strip():
            self.category.setFocus()
            return
        if not self.subgroup.text().strip():
            self.subgroup.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return self.section_name, self.category.text().strip(), self.subgroup.text().strip()


class CustomCatalogDialog(QDialog):
    """Compact local card editor inspired by Studio without publishing tools."""

    def __init__(
        self,
        sections: list[str],
        parent=None,
        *,
        selected_section: str = "",
        branches: list[dict] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить локальный объект")
        self.setMinimumSize(620, 620)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)
        title = QLabel("ЛОКАЛЬНАЯ КАРТОЧКА")
        title.setObjectName("dialogTitle")
        root.addWidget(title)
        hint = QLabel(
            "Карточка хранится только в user.db и никогда не публикуется "
            "в официальный каталог Velora."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        root.addWidget(hint)
        form = QFormLayout()
        form.setSpacing(12)
        root.addLayout(form)

        self.section = QComboBox()
        self.section.addItems(sections)
        if selected_section in sections:
            self.section.setCurrentText(selected_section)
        form.addRow("Раздел*", self.section)

        self._branches_by_category: dict[str, list[str]] = defaultdict(list)
        for branch in branches or []:
            category = str(branch["category"])
            subgroup = str(branch["subgroup"])
            if subgroup not in self._branches_by_category[category]:
                self._branches_by_category[category].append(subgroup)

        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(self._branches_by_category)
        self.category.setPlaceholderText("Например: Клубы")
        self.category.currentTextChanged.connect(self._refresh_subgroups)
        form.addRow("Категория*", self.category)
        self.subgroup = QComboBox()
        self.subgroup.setEditable(True)
        self.subgroup.setPlaceholderText("Например: АПЛ")
        form.addRow("Подкатегория*", self.subgroup)
        self._refresh_subgroups(self.category.currentText())

        self.title = QLineEdit()
        self.title.setPlaceholderText("Например: Челси")
        form.addRow("Объект*", self.title)
        self.creator = QLineEdit()
        self.creator.setPlaceholderText("Автор, организация или разработчик")
        form.addRow("Создатель", self.creator)
        self.year = QSpinBox()
        self.year.setRange(0, 2200)
        self.year.setSpecialValueText("—")
        form.addRow("Год", self.year)
        self.age = QSpinBox()
        self.age.setRange(0, 21)
        self.age.setSuffix("+")
        form.addRow("Возраст", self.age)
        self.description = QTextEdit()
        self.description.setMaximumHeight(120)
        self.description.setPlaceholderText("Краткое описание пользовательского объекта")
        form.addRow("Описание", self.description)
        cover_row = QHBoxLayout()
        self.cover = QLineEdit()
        self.cover.setReadOnly(True)
        cover_row.addWidget(self.cover, 1)
        choose = QPushButton("ОБЗОР…")
        choose.clicked.connect(self._choose_cover)
        cover_row.addWidget(choose)
        form.addRow("Обложка", cover_row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("СОЗДАТЬ ЛОКАЛЬНУЮ КАРТОЧКУ")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _refresh_subgroups(self, category: str) -> None:
        previous = self.subgroup.currentText() if hasattr(self, "subgroup") else ""
        if not hasattr(self, "subgroup"):
            return
        self.subgroup.blockSignals(True)
        self.subgroup.clear()
        self.subgroup.addItems(self._branches_by_category.get(category.strip(), []))
        if previous and previous in self._branches_by_category.get(category.strip(), []):
            self.subgroup.setCurrentText(previous)
        self.subgroup.blockSignals(False)

    def _choose_cover(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите обложку",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp)",
        )
        if path:
            self.cover.setText(path)

    def _accept_if_valid(self) -> None:
        required = (
            self.section.currentText().strip(),
            self.category.currentText().strip(),
            self.subgroup.currentText().strip(),
            self.title.text().strip(),
        )
        if not all(required):
            QMessageBox.warning(self, "Локальная карточка", "Заполните все обязательные поля.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "section": self.section.currentText().strip(),
            "category": self.category.currentText().strip(),
            "subgroup": self.subgroup.currentText().strip(),
            "title": self.title.text().strip(),
            "creator": self.creator.text().strip(),
            "release_year": self.year.value() or None,
            "age_rating": self.age.value(),
            "description": self.description.toPlainText().strip(),
            "cover_path": self.cover.text().strip(),
        }
