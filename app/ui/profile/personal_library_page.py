from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from app.data.user_repository import UserRepository
from app.models.personal_library import SmartListDefinition, UserGoal
from app.services.smart_list_service import SmartListService
from app.services.taste_analytics_service import TasteAnalyticsService


class SmartListDialog(QDialog):
    def __init__(self, parent=None, definition: SmartListDefinition | None = None) -> None:
        super().__init__(parent); self.setWindowTitle("Умный список"); self.setMinimumWidth(480)
        root = QVBoxLayout(self); form = QFormLayout(); root.addLayout(form)
        self.name = QLineEdit(definition.name if definition else ""); form.addRow("Название", self.name)
        self.media = QComboBox(); self.media.addItems(("Все типы", "Игры", "Фильмы", "Сериалы", "Программы")); form.addRow("Тип", self.media)
        if definition and definition.media_type: self.media.setCurrentText(definition.media_type)
        self.status = QComboBox(); self.status.addItems(("Любой", "Не начато", "В процессе", "Завершено", "Брошено", "В избранном", "Жду продолжения", "Без заметки")); form.addRow("Состояние", self.status)
        self.personal_min = QDoubleSpinBox(); self.personal_min.setRange(0,10); self.personal_min.setDecimals(1); self.personal_min.setSpecialValueText("Любая"); form.addRow("Личная оценка от", self.personal_min)
        self.general_min = QDoubleSpinBox(); self.general_min.setRange(0,10); self.general_min.setDecimals(1); self.general_min.setSpecialValueText("Любая"); form.addRow("Общая оценка от", self.general_min)
        if definition:
            reverse={"not_started":"Не начато","in_progress":"В процессе","completed":"Завершено","dropped":"Брошено","favorite":"В избранном","waiting":"Жду продолжения","without_note":"Без заметки"}
            for key,label in reverse.items():
                if definition.rules.get(key): self.status.setCurrentText(label); break
            self.personal_min.setValue(float(definition.rules.get("personal_min",0)))
            self.general_min.setValue(float(definition.rules.get("general_min",0)))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def definition(self, list_id=None) -> SmartListDefinition:
        status_rules = {"Не начато":{"not_started":True},"В процессе":{"in_progress":True},"Завершено":{"completed":True},"Брошено":{"dropped":True},"В избранном":{"favorite":True},"Жду продолжения":{"waiting":True},"Без заметки":{"without_note":True}}
        rules = dict(status_rules.get(self.status.currentText(), {}))
        if self.personal_min.value() > 0: rules["personal_min"] = self.personal_min.value()
        if self.general_min.value() > 0: rules["general_min"] = self.general_min.value()
        return SmartListDefinition(list_id, self.name.text().strip() or "Новый список", "" if self.media.currentIndex()==0 else self.media.currentText(), rules)


class PersonalLibraryPage(QWidget):
    catalog_item_requested = Signal(str)

    def __init__(self, repository: UserRepository, parent=None) -> None:
        super().__init__(parent); self.repository=repository; self.items=[]; self._definitions=[]
        root=QVBoxLayout(self); root.setContentsMargins(4,4,4,4)
        heading=QLabel("УМНАЯ БИБЛИОТЕКА"); heading.setObjectName("profileSectionHeading"); root.addWidget(heading)
        self.tabs=QTabWidget(); self.tabs.setDocumentMode(True); root.addWidget(self.tabs,1)
        self.tabs.addTab(self._smart_tab(),"УМНЫЕ СПИСКИ")
        self.tabs.addTab(self._activity_tab(),"ИСТОРИЯ")
        self.tabs.addTab(self._goals_tab(),"ЦЕЛИ")
        self.tabs.addTab(self._tags_tab(),"ТЕГИ")
        self.tabs.addTab(self._notes_tab(),"ЗАМЕТКИ")
        self.tabs.addTab(self._analytics_tab(),"АНАЛИТИКА ВКУСА")

    def _smart_tab(self):
        tab=QWidget(); row=QHBoxLayout(tab); row.setContentsMargins(8,12,8,8)
        left=QVBoxLayout(); self.smart_lists=QListWidget(); self.smart_lists.currentRowChanged.connect(self._show_smart_results); left.addWidget(self.smart_lists,1)
        actions=QHBoxLayout(); add=QPushButton("+ СОЗДАТЬ"); add.clicked.connect(self._new_smart); actions.addWidget(add); edit=QPushButton("ИЗМЕНИТЬ"); edit.clicked.connect(self._edit_smart); actions.addWidget(edit); duplicate=QPushButton("ДУБЛИРОВАТЬ"); duplicate.clicked.connect(self._duplicate_smart); actions.addWidget(duplicate); delete=QPushButton("УДАЛИТЬ"); delete.clicked.connect(self._delete_smart); actions.addWidget(delete); left.addLayout(actions); row.addLayout(left,1)
        right=QVBoxLayout(); self.smart_description=QLabel(); self.smart_description.setObjectName("muted"); right.addWidget(self.smart_description); self.smart_table=self._table(("Тип","Название","Категория","Моя оценка","Статус")); self.smart_table.cellDoubleClicked.connect(lambda r,c:self._open_table(self.smart_table,r)); right.addWidget(self.smart_table,1); row.addLayout(right,3); return tab

    def _activity_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab); self.activity_table=self._table(("Когда","Объект","Событие","Изменение")); self.activity_table.cellDoubleClicked.connect(lambda r,c:self._open_table(self.activity_table,r)); layout.addWidget(self.activity_table); return tab

    def _goals_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab); actions=QHBoxLayout(); add=QPushButton("+ НОВАЯ ЦЕЛЬ"); add.clicked.connect(self._new_goal); actions.addWidget(add); actions.addStretch(); layout.addLayout(actions); self.goals_layout=QVBoxLayout(); layout.addLayout(self.goals_layout); layout.addStretch(); return tab

    def _tags_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab)
        create_row=QHBoxLayout(); self.tag_name=QLineEdit(); self.tag_name.setPlaceholderText("Название нового личного тега"); create_row.addWidget(self.tag_name,1)
        add=QPushButton("ДОБАВИТЬ ТЕГ"); add.clicked.connect(self._add_tag); create_row.addWidget(add); layout.addLayout(create_row)
        content=QHBoxLayout()
        left=QVBoxLayout(); self.tags_list=QListWidget(); self.tags_list.currentRowChanged.connect(self._show_tag_items); left.addWidget(self.tags_list,1)
        tag_actions=QHBoxLayout(); rename=QPushButton("ПЕРЕИМЕНОВАТЬ"); rename.clicked.connect(self._rename_tag); tag_actions.addWidget(rename)
        delete=QPushButton("УДАЛИТЬ"); delete.clicked.connect(self._delete_tag); tag_actions.addWidget(delete); left.addLayout(tag_actions); content.addLayout(left,1)
        right=QVBoxLayout(); self.tag_items_table=self._table(("Тип","Название","Категория","Статус"))
        self.tag_items_table.cellDoubleClicked.connect(lambda r,c:self._open_table(self.tag_items_table,r)); right.addWidget(self.tag_items_table,1); content.addLayout(right,3)
        layout.addLayout(content,1)
        assign=QHBoxLayout(); self.tag_item=QComboBox(); assign.addWidget(self.tag_item,2); self.tag_choice=QComboBox(); assign.addWidget(self.tag_choice,1)
        apply=QPushButton("НАЗНАЧИТЬ"); apply.clicked.connect(self._assign_tag); assign.addWidget(apply); layout.addLayout(assign)
        hint=QLabel("Теги назначаются объектам локально и участвуют в пользовательских умных списках."); hint.setObjectName("muted"); layout.addWidget(hint); return tab

    def _repeats_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab); heading=QLabel("ПОВТОРНЫЕ ПРОХОЖДЕНИЯ И ПРОСМОТРЫ"); heading.setObjectName("profileSectionHeading"); layout.addWidget(heading)
        text=QLabel("Зафиксируйте новый цикл отдельно от основной оценки и статуса. Событие появится в единой истории."); text.setObjectName("muted"); text.setWordWrap(True); layout.addWidget(text)
        row=QHBoxLayout(); self.repeat_item=QComboBox(); row.addWidget(self.repeat_item,2); self.repeat_value=QDoubleSpinBox(); self.repeat_value.setRange(0,100000); self.repeat_value.setSuffix(" ч"); row.addWidget(self.repeat_value); add=QPushButton("ЗАПИСАТЬ ПОВТОР"); add.clicked.connect(self._add_repeat); row.addWidget(add); layout.addLayout(row); layout.addStretch(); return tab

    def _notes_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab); self.note_item=QComboBox(); self.note_item.currentIndexChanged.connect(self._load_note); layout.addWidget(self.note_item); self.note_edit=QTextEdit(); self.note_edit.setPlaceholderText("Личная заметка хранится только на этом компьютере"); layout.addWidget(self.note_edit,1); save=QPushButton("СОХРАНИТЬ ЗАМЕТКУ"); save.setProperty("primary",True); save.clicked.connect(self._save_note); layout.addWidget(save,0,Qt.AlignmentFlag.AlignRight); return tab

    def _analytics_tab(self):
        tab=QWidget(); layout=QVBoxLayout(tab); self.analytics_summary=QLabel(); self.analytics_summary.setWordWrap(True); self.analytics_summary.setObjectName("analyticsSummary"); layout.addWidget(self.analytics_summary); self.analytics_table=self._table(("Объект","Моя","Общая","Разница")); self.analytics_table.cellDoubleClicked.connect(lambda r,c:self._open_table(self.analytics_table,r)); layout.addWidget(self.analytics_table,1); self.period_summary=QLabel(); self.period_summary.setObjectName("muted"); layout.addWidget(self.period_summary); return tab

    @staticmethod
    def _table(headers):
        table=QTableWidget(0,len(headers)); table.setHorizontalHeaderLabels(headers); table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); table.verticalHeader().hide(); table.setShowGrid(False); table.horizontalHeader().setStretchLastSection(True); return table

    def refresh(self, items) -> None:
        self.items=list(items); self._refresh_object_choices(); self._refresh_smart(); self._refresh_activity(); self._refresh_goals(); self._refresh_tags(); self._refresh_analytics()

    def _refresh_object_choices(self):
        for combo in (self.note_item, self.tag_item):
            current=combo.currentData()
            blocker = QSignalBlocker(combo)
            combo.clear()
            for game in sorted(self.items,key=lambda value:value.title.casefold()): combo.addItem(f"{game.media_type} · {game.title}",game.catalog_id)
            index=combo.findData(current)
            if index>=0:combo.setCurrentIndex(index)
            del blocker
        self._load_note()

    def _refresh_smart(self):
        selected=self.smart_lists.currentRow()
        self._definitions=list(SmartListService.BUILT_INS)+self.repository.smart_lists()
        blocker = QSignalBlocker(self.smart_lists)
        self.smart_lists.clear()
        for definition in self._definitions:
            count=len(SmartListService.filter(self.items,definition)); item=QListWidgetItem(f"{definition.name}   {count}"); item.setToolTip(SmartListService.describe(definition.rules)); self.smart_lists.addItem(item)
        target = max(0,min(selected,len(self._definitions)-1)) if self._definitions else -1
        self.smart_lists.setCurrentRow(target)
        del blocker
        self._show_smart_results(target)

    def _show_smart_results(self,row):
        if row<0 or row>=len(self._definitions): return
        definition=self._definitions[row]; values=SmartListService.filter(self.items,definition); self.smart_description.setText(SmartListService.describe(definition.rules)); self._fill(self.smart_table,[(g.media_type,g.title,g.category,g.personal_score,g.status,g.catalog_id) for g in values])

    def _new_smart(self):
        dialog=SmartListDialog(self)
        if dialog.exec(): self.repository.save_smart_list(dialog.definition()); self._refresh_smart()

    def _duplicate_smart(self):
        row=self.smart_lists.currentRow()
        if row<0:return
        source=self._definitions[row]; duplicate=SmartListDefinition(None,f"{source.name} — копия",source.media_type,dict(source.rules)); self.repository.save_smart_list(duplicate); self._refresh_smart()

    def _edit_smart(self):
        row=self.smart_lists.currentRow()
        if row<0:return
        source=self._definitions[row]
        if source.is_system: QMessageBox.information(self,"Системный список","Встроенный список можно дублировать, но нельзя изменить."); return
        dialog=SmartListDialog(self,source)
        if dialog.exec():self.repository.save_smart_list(dialog.definition(source.list_id));self._refresh_smart()

    def _delete_smart(self):
        row=self.smart_lists.currentRow()
        if row<0:return
        definition=self._definitions[row]
        if definition.is_system: QMessageBox.information(self,"Системный список","Встроенные списки нельзя удалить."); return
        if QMessageBox.question(self,"Удалить список",f"Удалить «{definition.name}»?")==QMessageBox.StandardButton.Yes: self.repository.delete_smart_list(definition.list_id); self._refresh_smart()

    def _refresh_activity(self):
        by_id={g.catalog_id:g for g in self.items}; rows=[]
        labels={"rating":"Изменена оценка","status":"Изменён статус","playtime":"Игровое время","favorite":"Избранное","watch_count":"Просмотры","series_progress":"Прогресс сериала","episode_map":"Эпизоды","note":"Заметка","tag":"Тег","repeat":"Повтор"}
        for event in self.repository.all_activity():
            game=by_id.get(event["catalog_id"]); title=game.title if game else event["catalog_id"]; when=event["created_at"].replace("T"," ")[:16]; change=f"{event['old_value'] or '—'} → {event['new_value'] or '—'}"; rows.append((when,title,labels.get(event["event_type"],event["event_type"]),change,event["catalog_id"]))
        self._fill(self.activity_table,rows)

    def _new_goal(self):
        title,ok=QInputDialog.getText(self,"Новая цель","Название цели")
        if not ok or not title.strip():return
        target,ok=QInputDialog.getDouble(self,"Новая цель","Целевое значение",10,1,100000,1)
        if ok:self.repository.save_goal(UserGoal(None,title.strip(),"objects",target)); self._refresh_goals()

    def _refresh_goals(self):
        while self.goals_layout.count():
            item=self.goals_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        interacted=[item for item in self.items if item.user_interacted]
        values={"objects":len(interacted),"rated":sum(item.personal_score!="—" for item in interacted),"completed":sum(item.status in SmartListService.COMPLETED for item in interacted),"hours":sum(item.playtime_hours for item in interacted)}
        for goal in self.repository.goals():
            calculated=float(values.get(goal.metric,goal.current_value))
            if calculated != goal.current_value: goal.current_value=calculated; self.repository.save_goal(goal)
            panel=QFrame(); panel.setObjectName("goalCard"); row=QHBoxLayout(panel); title=QLabel(goal.title); title.setMinimumWidth(240); row.addWidget(title); bar=QProgressBar(); bar.setRange(0,1000); progress=min(1.0,goal.current_value/max(goal.target_value,1)); bar.setValue(round(progress*1000)); bar.setFormat(f"{goal.current_value:g} / {goal.target_value:g}"); row.addWidget(bar,1); self.goals_layout.addWidget(panel)
        if not self.repository.goals(): self.goals_layout.addWidget(QLabel("Создайте личную цель — например, завершить 12 игр за год."))

    def _add_tag(self):
        if self.tag_name.text().strip():self.repository.add_tag(self.tag_name.text());self.tag_name.clear();self._refresh_tags()

    def _refresh_tags(self):
        selected_id = None
        selected_item = self.tags_list.currentItem()
        if selected_item:
            selected_id = selected_item.data(Qt.ItemDataRole.UserRole)
        blocker = QSignalBlocker(self.tags_list)
        self.tags_list.clear()
        current=self.tag_choice.currentData(); self.tag_choice.clear()
        for tag_id,name,color,count in self.repository.tags():
            item=QListWidgetItem(f"#{name}   {count}"); item.setData(Qt.ItemDataRole.UserRole,tag_id); self.tags_list.addItem(item); self.tag_choice.addItem(f"#{name}",tag_id)
        index=self.tag_choice.findData(current)
        if index>=0:self.tag_choice.setCurrentIndex(index)
        target = next((row for row in range(self.tags_list.count()) if self.tags_list.item(row).data(Qt.ItemDataRole.UserRole)==selected_id), 0)
        self.tags_list.setCurrentRow(target if self.tags_list.count() else -1)
        del blocker
        self._show_tag_items(self.tags_list.currentRow())

    def _show_tag_items(self, row: int) -> None:
        if row < 0 or row >= self.tags_list.count():
            self.tag_items_table.setRowCount(0); return
        tag_id = self.tags_list.item(row).data(Qt.ItemDataRole.UserRole)
        tag = next((name for current_id,name,_color,_count in self.repository.tags() if current_id==tag_id), "")
        values = [game for game in self.items if tag in game.tags]
        self._fill(self.tag_items_table,[(g.media_type,g.title,g.category,g.status,g.catalog_id) for g in values])

    def _rename_tag(self):
        item=self.tags_list.currentItem()
        if not item:return
        tag_id=int(item.data(Qt.ItemDataRole.UserRole))
        current=next((name for current_id,name,_color,_count in self.repository.tags() if current_id==tag_id),"")
        name,ok=QInputDialog.getText(self,"Переименовать тег","Новое название",text=current)
        if not ok:return
        try:self.repository.rename_tag(tag_id,name);self._refresh_tags()
        except ValueError as error:QMessageBox.warning(self,"Тег не изменён",str(error))

    def _delete_tag(self):
        item=self.tags_list.currentItem()
        if not item:return
        tag_id=int(item.data(Qt.ItemDataRole.UserRole)); name=item.text().split("   ",1)[0]
        if QMessageBox.question(self,"Удалить тег",f"Удалить {name} у всех объектов?")==QMessageBox.StandardButton.Yes:
            self.repository.delete_tag(tag_id)
            for game in self.items:
                game.tags=[tag for tag in game.tags if f"#{tag}" != name]
            self._refresh_tags();self._refresh_activity()

    def _assign_tag(self):
        catalog_id=self.tag_item.currentData(); tag_id=self.tag_choice.currentData()
        if catalog_id and tag_id:
            self.repository.assign_tag(catalog_id,int(tag_id))
            names={current_id:name for current_id,name,_color,_count in self.repository.tags()}
            game=next((value for value in self.items if value.catalog_id==catalog_id),None)
            if game and int(tag_id) in names and names[int(tag_id)] not in game.tags:game.tags.append(names[int(tag_id)])
            self._refresh_tags();self._refresh_activity()

    def _add_repeat(self):
        catalog_id=self.repeat_item.currentData()
        if not catalog_id:return
        game=next((value for value in self.items if value.catalog_id==catalog_id),None); session_type="rewatch" if game and game.media_type in ("Фильмы","Сериалы") else "replay"
        self.repository.add_interaction_session(catalog_id,session_type,self.repeat_value.value()); self._refresh_activity(); QMessageBox.information(self,"Повтор сохранён","Событие добавлено в личную историю.")

    def _load_note(self,*_):
        catalog_id=self.note_item.currentData(); game=next((value for value in self.items if value.catalog_id==catalog_id),None); self.note_edit.setPlainText(game.note if game else "")

    def _save_note(self):
        catalog_id=self.note_item.currentData()
        if not catalog_id:return
        note=self.note_edit.toPlainText().strip(); self.repository.save_note(catalog_id,note); game=next((value for value in self.items if value.catalog_id==catalog_id),None)
        if game:game.note=note
        self._refresh_activity();self._refresh_smart()

    def _refresh_analytics(self):
        analysis=TasteAnalyticsService.score_comparison(self.items); self.analytics_summary.setText(f"Согласие с общей оценкой: {analysis['agreement']:.0f}%     Среднее отклонение: {analysis['average_delta']:+.1f}")
        values=analysis["higher"]+analysis["lower"]; self._fill(self.analytics_table,[(g.title,g.personal_score,g.general_score,f"{delta:+.1f}",g.catalog_id) for g,delta in values])
        period=TasteAnalyticsService.periods(self.repository.all_activity()); self.period_summary.setText(f"Активность за последние {period['days']} дней: {period['current']} · предыдущий период: {period['previous']} · изменение: {period['delta']:+d}")

    @staticmethod
    def _fill(table,rows):
        table.setRowCount(len(rows))
        for r,values in enumerate(rows):
            catalog_id=values[-1] if values and len(values)>table.columnCount() else ""; shown=values[:table.columnCount()]
            for c,value in enumerate(shown):
                item=QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole,catalog_id); table.setItem(r,c,item)

    def _open_table(self,table,row):
        item=table.item(row,0)
        if item and item.data(Qt.ItemDataRole.UserRole): self.catalog_item_requested.emit(item.data(Qt.ItemDataRole.UserRole))
