from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout


class TagEditorDialog(QDialog):
    def __init__(self, repository, catalog_id: str, parent=None) -> None:
        super().__init__(parent); self.repository=repository; self.catalog_id=catalog_id; self.setWindowTitle("Теги объекта"); self.setMinimumWidth(420)
        root=QVBoxLayout(self); self.checks=[]; self._fill(root)
        row=QHBoxLayout(); self.name=QLineEdit(); self.name.setPlaceholderText("Новый тег"); row.addWidget(self.name,1); add=QPushButton("ДОБАВИТЬ"); add.clicked.connect(self._add); row.addWidget(add); root.addLayout(row)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(self._save); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _fill(self, root):
        assigned=set(self.repository.tag_ids_for(self.catalog_id))
        for tag_id,name,color,count in self.repository.tags():
            check=QCheckBox(f"#{name}  ·  {count}"); check.setChecked(tag_id in assigned); check.setProperty("tagId",tag_id); root.addWidget(check); self.checks.append(check)

    def _add(self):
        name=self.name.text().strip()
        if not name:return
        tag_id=self.repository.add_tag(name); check=QCheckBox(f"#{name}"); check.setChecked(True); check.setProperty("tagId",tag_id); self.layout().insertWidget(max(0,self.layout().count()-2),check); self.checks.append(check); self.name.clear()

    def _save(self):
        assigned=set(self.repository.tag_ids_for(self.catalog_id))
        for check in self.checks:
            tag_id=int(check.property("tagId")); wanted=check.isChecked()
            if wanted != (tag_id in assigned):self.repository.assign_tag(self.catalog_id,tag_id,wanted)
        self.accept()
