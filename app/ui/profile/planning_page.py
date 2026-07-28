from __future__ import annotations

import random

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSpinBox, QTabWidget, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from app.data.personal_library_repository import PersonalLibraryRepository
from app.core.paths import resolve_resource_path
from app.models.personal_library import ManualList, QueueEntry, ReviewDraft
from app.services.library_recommendation_service import LibraryRecommendationService


class PlanningPage(QTabWidget):
    catalog_item_requested = Signal(str)

    def __init__(self, repository: PersonalLibraryRepository, parent=None) -> None:
        super().__init__(parent); self.repository=repository; self.items=[]; self.by_id={}; self._lists=[]; self.setDocumentMode(True)
        self.addTab(self._choice_tab(),"ВЫБРАТЬ ЗА МЕНЯ")
        self.addTab(self._drafts_tab(),"ЧЕРНОВИКИ И ШАБЛОНЫ")
        self.addTab(self._journal_tab(),"ДНЕВНИК")
        self.addTab(self._archive_tab(),"АРХИВ И КОРЗИНА")

    def _queue_tab(self):
        tab=QWidget(); root=QHBoxLayout(tab); left=QVBoxLayout(); self.queue_list=QListWidget(); self.queue_list.setDragDropMode(QListWidget.DragDropMode.InternalMove); self.queue_list.model().rowsMoved.connect(self._save_queue_order); self.queue_list.itemDoubleClicked.connect(lambda item:self.catalog_item_requested.emit(item.data(Qt.ItemDataRole.UserRole))); left.addWidget(self.queue_list,1); remove=QPushButton("УБРАТЬ ИЗ ОЧЕРЕДИ"); remove.clicked.connect(self._remove_queue); left.addWidget(remove); root.addLayout(left,2)
        form=QFormLayout(); self.queue_object=QComboBox(); form.addRow("Объект",self.queue_object); self.queue_kind=QComboBox(); self.queue_kind.addItems(("Пройти следующим","Посмотреть вечером","После текущего объекта","На выходных","Использовать позже","Без даты")); form.addRow("План",self.queue_kind); self.queue_priority=QComboBox(); self.queue_priority.addItems(("Высокий","Обычный","Низкий")); form.addRow("Приоритет",self.queue_priority); self.queue_date=QDateEdit(); self.queue_date.setCalendarPopup(True); self.queue_date.setSpecialValueText("Без даты"); form.addRow("Дата",self.queue_date); self.queue_reason=QLineEdit(); form.addRow("Причина",self.queue_reason); add=QPushButton("ДОБАВИТЬ В ОЧЕРЕДЬ"); add.setProperty("primary",True); add.clicked.connect(self._save_queue_entry); form.addRow(add); root.addLayout(form,1); return tab

    def _lists_tab(self):
        tab=QWidget(); root=QHBoxLayout(tab); left=QVBoxLayout(); self.manual_lists=QListWidget(); self.manual_lists.currentRowChanged.connect(self._load_manual_list); left.addWidget(self.manual_lists,1); actions=QHBoxLayout(); create=QPushButton("+ СПИСОК"); create.clicked.connect(self._create_list); actions.addWidget(create); delete=QPushButton("В КОРЗИНУ"); delete.clicked.connect(self._trash_list); actions.addWidget(delete); left.addLayout(actions); root.addLayout(left,1)
        right=QVBoxLayout(); self.list_description=QLabel(); self.list_description.setObjectName("muted"); right.addWidget(self.list_description); self.list_items=QListWidget(); self.list_items.setDragDropMode(QListWidget.DragDropMode.InternalMove); self.list_items.model().rowsMoved.connect(self._save_list_order); self.list_items.itemDoubleClicked.connect(lambda item:self.catalog_item_requested.emit(item.data(Qt.ItemDataRole.UserRole))); right.addWidget(self.list_items,1); addrow=QHBoxLayout(); self.list_object=QComboBox(); addrow.addWidget(self.list_object,1); add=QPushButton("ДОБАВИТЬ ОБЪЕКТ"); add.clicked.connect(self._add_to_list); addrow.addWidget(add); right.addLayout(addrow); root.addLayout(right,3); return tab

    def _choice_tab(self):
        tab=QWidget(); tab.setObjectName("veloraPanel"); root=QVBoxLayout(tab); root.setContentsMargins(20,18,20,20); root.setSpacing(14)
        title=QLabel("ЛОКАЛЬНЫЙ ПОМОЩНИК ВЫБОРА"); title.setObjectName("sectionTitle"); root.addWidget(title)
        hint=QLabel("Выберите тип контента — Velora покажет пять случайных вариантов из локальной библиотеки. Нажмите на обложку, чтобы открыть карточку."); hint.setObjectName("muted"); hint.setWordWrap(True); root.addWidget(hint)
        controls=QHBoxLayout(); self.choice_media=QComboBox(); self.choice_media.addItems(("Игры","Фильмы","Сериалы","Программы","Все типы")); controls.addWidget(self.choice_media)
        random_button=QPushButton("ВЫБРАТЬ 5 ВАРИАНТОВ"); random_button.setProperty("primary",True); random_button.clicked.connect(self._random_choice); controls.addWidget(random_button); controls.addStretch(1); root.addLayout(controls)
        self.choice_cards=QGridLayout(); self.choice_cards.setHorizontalSpacing(14); root.addLayout(self.choice_cards)
        self.choice_result=QLabel("Нажмите кнопку, чтобы сформировать новую пятёрку."); self.choice_result.setObjectName("muted"); root.addWidget(self.choice_result)
        root.addStretch(1); self._choice_catalog_id=None
        return tab

    def _drafts_tab(self):
        tab=QWidget(); root=QHBoxLayout(tab); left=QVBoxLayout(); self.draft_media=QComboBox(); self.draft_media.addItems(("Игры","Фильмы","Сериалы","Программы")); self.draft_media.currentTextChanged.connect(self._refresh_draft_objects); left.addWidget(self.draft_media); self.draft_object=QComboBox(); self.draft_object.currentIndexChanged.connect(self._load_draft); left.addWidget(self.draft_object); self.draft_title=QLineEdit(); self.draft_title.setPlaceholderText("Заголовок обзора"); left.addWidget(self.draft_title); self.draft_body=QTextEdit(); self.draft_body.setPlaceholderText("Черновик сохраняется локально. Можно продолжить позже."); self.draft_body.textChanged.connect(self._draft_changed); left.addWidget(self.draft_body,1); self.draft_counter=QLabel("0 символов"); self.draft_counter.setObjectName("muted"); left.addWidget(self.draft_counter); save=QPushButton("СОХРАНИТЬ ЧЕРНОВИК"); save.setProperty("primary",True); save.clicked.connect(self._save_draft); left.addWidget(save); root.addLayout(left,2)
        right=QVBoxLayout(); right.addWidget(QLabel("ШАБЛОНЫ ОБЗОРОВ")); self.template_list=QListWidget(); right.addWidget(self.template_list,1); actions=QHBoxLayout(); new=QPushButton("+ СОЗДАТЬ"); new.clicked.connect(self._create_template); actions.addWidget(new); edit=QPushButton("ИЗМЕНИТЬ"); edit.clicked.connect(self._edit_template); actions.addWidget(edit); delete=QPushButton("УДАЛИТЬ"); delete.clicked.connect(self._delete_template); actions.addWidget(delete); right.addLayout(actions); apply=QPushButton("ВСТАВИТЬ ШАБЛОН"); apply.clicked.connect(self._apply_template); right.addWidget(apply); root.addLayout(right,1); self._loading_draft=False; return tab

    def _journal_tab(self):
        tab=QWidget(); root=QVBoxLayout(tab); self.journal_object=QComboBox(); self.journal_object.currentIndexChanged.connect(self._load_journal); root.addWidget(self.journal_object); self.journal_entries=QListWidget(); root.addWidget(self.journal_entries,1); self.journal_text=QTextEdit(); self.journal_text.setMaximumHeight(130); self.journal_text.setPlaceholderText("Что изменилось в ваших впечатлениях?"); root.addWidget(self.journal_text); row=QHBoxLayout(); self.journal_progress=QLineEdit(); self.journal_progress.setPlaceholderText("Прогресс: 3 глава / S2E4 / 12 часов"); row.addWidget(self.journal_progress); add=QPushButton("ДОБАВИТЬ ЗАПИСЬ"); add.clicked.connect(self._add_journal); row.addWidget(add); root.addLayout(row); return tab

    def _archive_tab(self):
        tab=QWidget(); root=QHBoxLayout(tab); archive=QVBoxLayout(); archive.addWidget(QLabel("АРХИВ ОБЪЕКТОВ")); self.archive_list=QListWidget(); archive.addWidget(self.archive_list,1); self.archive_object=QComboBox(); archive.addWidget(self.archive_object); archive_action=QPushButton("ОТПРАВИТЬ В АРХИВ"); archive_action.clicked.connect(self._archive_object); archive.addWidget(archive_action); restore=QPushButton("ВОССТАНОВИТЬ"); restore.clicked.connect(self._restore_archive); archive.addWidget(restore); root.addLayout(archive,1); trash=QVBoxLayout(); trash.addWidget(QLabel("КОРЗИНА · 30 ДНЕЙ")); self.trash_list=QListWidget(); trash.addWidget(self.trash_list,1); hint=QLabel("Окончательное удаление выполняется только после отдельного подтверждения."); hint.setObjectName("muted"); hint.setWordWrap(True); trash.addWidget(hint); root.addLayout(trash,1); return tab

    def refresh(self, items) -> None:
        self.items=list(items); self.by_id={value.catalog_id:value for value in self.items}
        for combo in (self.journal_object,self.archive_object):
            current=combo.currentData(); combo.blockSignals(True); combo.clear()
            for value in sorted(self.items,key=lambda x:x.title.casefold()):combo.addItem(f"{value.media_type} · {value.title}",value.catalog_id)
            index=combo.findData(current); combo.setCurrentIndex(max(0,index)); combo.blockSignals(False)
        self._refresh_draft_objects(); self._refresh_templates(); self._load_draft(); self._load_journal(); self._refresh_archive()

    def _refresh_draft_objects(self):
        if not hasattr(self,"draft_object"):return
        current=self.draft_object.currentData(); self.draft_object.blockSignals(True); self.draft_object.clear()
        for value in sorted((item for item in self.items if item.media_type==self.draft_media.currentText()),key=lambda item:item.title.casefold()):self.draft_object.addItem(value.title,value.catalog_id)
        index=self.draft_object.findData(current); self.draft_object.setCurrentIndex(index if index>=0 else 0); self.draft_object.blockSignals(False); self._load_draft()

    def _refresh_queue(self):
        self.queue_list.clear(); colors={"Высокий":"#FF5A5A","Обычный":"#B875FF","Низкий":"#8794A0"}
        for entry in self.repository.queue():
            game=self.by_id.get(entry.catalog_id); title=game.title if game else entry.catalog_id; suffix=f" · {entry.planned_date}" if entry.planned_date else ""; item=QListWidgetItem(f"{entry.position}. {title} · {entry.plan_kind}{suffix}"); item.setData(Qt.ItemDataRole.UserRole,entry.catalog_id); item.setForeground(__import__('PySide6.QtGui',fromlist=['QColor']).QColor(colors.get(entry.priority,"#B875FF"))); item.setToolTip(entry.reason); self.queue_list.addItem(item)

    def _save_queue_entry(self):
        catalog_id=self.queue_object.currentData()
        if catalog_id:self.repository.save_queue_entry(QueueEntry(catalog_id,0,self.queue_kind.currentText(),self.queue_date.date().toString("yyyy-MM-dd"),self.queue_priority.currentText(),self.queue_reason.text().strip()));self._refresh_queue()

    def _save_queue_order(self,*_):self.repository.reorder_queue([self.queue_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.queue_list.count())]);self._refresh_queue()
    def _remove_queue(self):
        item=self.queue_list.currentItem()
        if item:self.repository.remove_queue_entry(item.data(Qt.ItemDataRole.UserRole));self._refresh_queue()

    def _choice_media_key(self):
        return {"Игры":"games","Фильмы":"movies","Сериалы":"series","Программы":"software"}.get(self.choice_media.currentText())

    def _recommend(self):
        item,reasons=LibraryRecommendationService.recommend(self.items,self.repository.queue(),media_type=self._choice_media_key(),only_unstarted=False); self._show_choice(item,reasons)

    def _random_choice(self):
        selected=self.choice_media.currentText(); candidates=[item for item in self.items if selected=="Все типы" or item.media_type==selected]
        chosen=random.SystemRandom().sample(candidates,min(5,len(candidates))) if candidates else []
        while self.choice_cards.count():
            child=self.choice_cards.takeAt(0)
            if child.widget():child.widget().deleteLater()
        for column,item in enumerate(chosen):
            button=QToolButton(); button.setObjectName("randomCoverCard"); button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon); button.setText(item.title); button.setIconSize(QSize(150,210)); button.setMinimumSize(170,250)
            cover_path = resolve_resource_path(item.cover_path) if item.cover_path else None
            if cover_path and cover_path.is_file() and not QPixmap(str(cover_path)).isNull():button.setIcon(QIcon(str(cover_path)))
            button.clicked.connect(lambda checked=False,catalog_id=item.catalog_id:self.catalog_item_requested.emit(catalog_id)); self.choice_cards.addWidget(button,0,column)
        self.choice_result.setText(f"Показано вариантов: {len(chosen)}" if chosen else "В выбранном разделе пока нет объектов.")

    def _show_choice(self,item,reasons):
        if not item:self._choice_catalog_id=None;self.choice_result.setText("В очереди нет объектов, подходящих под выбранный тип.");self.choice_open.setEnabled(False);return
        self._choice_catalog_id=item.catalog_id; explanation="\n".join(f"— {value}" for value in reasons); self.choice_result.setText(f"СЕГОДНЯ ЛУЧШЕ ВЫБРАТЬ\n\n{item.title}\n\nПочему предложено:\n{explanation}"); self.choice_open.setEnabled(True)

    def _open_choice(self):
        if self._choice_catalog_id:self.catalog_item_requested.emit(self._choice_catalog_id)

    def _refresh_queue_duration(self):
        count,minutes=LibraryRecommendationService.queue_duration(self.items,self.repository.queue()); text=f"В очереди: {count} объектов"
        if minutes is not None:text+=f" · примерно {minutes / 60:g} ч"
        elif count:text+=" · длительность показана не будет, пока данных недостаточно"
        self.queue_duration.setText(text)

    def _refresh_lists(self):
        current=self.manual_lists.currentRow();self._lists=self.repository.manual_lists();self.manual_lists.clear()
        for value in self._lists:self.manual_lists.addItem(("★ " if value.is_pinned else "")+value.name)
        if self._lists:self.manual_lists.setCurrentRow(max(0,min(current,len(self._lists)-1)))

    def _create_list(self):
        name,ok=QInputDialog.getText(self,"Новый список","Название")
        if not ok or not name.strip():return
        description,_=QInputDialog.getMultiLineText(self,"Новый список","Описание"); ranked=QMessageBox.question(self,"Рейтинг","Включить нумерованный рейтинг?")==QMessageBox.StandardButton.Yes;self.repository.save_manual_list(ManualList(None,name.strip(),description,is_ranked=ranked));self._refresh_lists()

    def _load_manual_list(self,row):
        self.list_items.clear()
        if row<0 or row>=len(self._lists):return
        value=self._lists[row];self.list_description.setText(value.description or "Ручная подборка")
        for entry in self.repository.list_items(value.list_id):
            game=self.by_id.get(entry["catalog_id"]);title=game.title if game else entry["catalog_id"];delta=""
            if value.is_ranked and entry["previous_position"]:
                change=entry["previous_position"]-entry["position"];delta=" · новинка" if not entry["previous_position"] else (f" · ↑{change}" if change>0 else f" · ↓{-change}" if change<0 else "")
            item=QListWidgetItem(f"{entry['position']}. {title}{delta}");item.setData(Qt.ItemDataRole.UserRole,entry["catalog_id"]);self.list_items.addItem(item)

    def _add_to_list(self):
        row=self.manual_lists.currentRow();catalog_id=self.list_object.currentData()
        if row>=0 and catalog_id:self.repository.add_list_item(self._lists[row].list_id,catalog_id);self._load_manual_list(row)

    def _save_list_order(self,*_):
        row=self.manual_lists.currentRow()
        if row>=0:self.repository.reorder_list(self._lists[row].list_id,[self.list_items.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_items.count())]);self._load_manual_list(row)

    def _trash_list(self):
        row=self.manual_lists.currentRow()
        if row>=0 and QMessageBox.question(self,"Корзина",f"Переместить «{self._lists[row].name}» в корзину на 30 дней?")==QMessageBox.StandardButton.Yes:self.repository.move_list_to_trash(self._lists[row].list_id);self._refresh_lists();self._refresh_archive()

    def _refresh_templates(self):
        self.template_list.clear()
        for value in self.repository.templates():item=QListWidgetItem(f"{value['media_type']} · {value['name']}");item.setData(Qt.ItemDataRole.UserRole,value);self.template_list.addItem(item)

    def _create_template(self):
        media,ok=QInputDialog.getItem(self,"Шаблон обзора","Тип контента",("Игры","Фильмы","Сериалы","Программы"),0,False)
        if not ok:return
        name,ok=QInputDialog.getText(self,"Шаблон обзора","Название")
        if not ok or not name.strip():return
        body,ok=QInputDialog.getMultiLineText(self,"Шаблон обзора","Структура шаблона")
        if ok:self.repository.save_template(name.strip(),media,body);self._refresh_templates()

    def _edit_template(self):
        item=self.template_list.currentItem()
        if not item:return
        value=item.data(Qt.ItemDataRole.UserRole); name,ok=QInputDialog.getText(self,"Изменить шаблон","Название",text=value["name"])
        if not ok or not name.strip():return
        body,ok=QInputDialog.getMultiLineText(self,"Изменить шаблон","Структура шаблона",value["body"])
        if ok:self.repository.save_template(name.strip(),value["media_type"],body,value["id"]);self._refresh_templates()

    def _delete_template(self):
        item=self.template_list.currentItem()
        if not item:return
        value=item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self,"Удалить шаблон",f"Удалить «{value['name']}»?")==QMessageBox.StandardButton.Yes:self.repository.delete_template(value["id"]);self._refresh_templates()

    def _apply_template(self):
        item=self.template_list.currentItem()
        if item:self.draft_body.insertPlainText(item.data(Qt.ItemDataRole.UserRole)["body"])

    def _load_draft(self,*_):
        if not hasattr(self,"draft_body"):return
        self._loading_draft=True;draft=self.repository.draft(self.draft_object.currentData()) if self.draft_object.currentData() else None;self.draft_title.setText(draft.title if draft else "");self.draft_body.setPlainText(draft.body if draft else "");self._loading_draft=False;self._draft_changed()

    def _draft_changed(self):self.draft_counter.setText(f"{len(self.draft_body.toPlainText())} символов")
    def _save_draft(self):
        catalog_id=self.draft_object.currentData()
        if catalog_id:self.repository.save_draft(ReviewDraft(catalog_id,self.draft_title.text().strip(),self.draft_body.toPlainText()));QMessageBox.information(self,"Черновик","Черновик сохранён локально.")

    def _load_journal(self,*_):
        if not hasattr(self,"journal_entries"):return
        self.journal_entries.clear();catalog_id=self.journal_object.currentData()
        if not catalog_id:return
        for value in self.repository.journal(catalog_id):self.journal_entries.addItem(f"{value['created_at'].replace('T',' ')[:16]} · {value['progress_value']}\n{value['body']}")

    def _add_journal(self):
        catalog_id=self.journal_object.currentData();body=self.journal_text.toPlainText().strip()
        if catalog_id and body:self.repository.add_journal_entry(catalog_id,body,self.journal_progress.text().strip());self.journal_text.clear();self.journal_progress.clear();self._load_journal()

    def _refresh_archive(self):
        self.archive_list.clear()
        for catalog_id in self.repository.archived_ids():item=QListWidgetItem(self.by_id.get(catalog_id).title if catalog_id in self.by_id else catalog_id);item.setData(Qt.ItemDataRole.UserRole,catalog_id);self.archive_list.addItem(item)
        self.trash_list.clear()
        for value in self.repository.trash():self.trash_list.addItem(f"{value['entity_type']} · {value['entity_id']} · до {value['expires_at'][:10]}")

    def _restore_archive(self):
        item=self.archive_list.currentItem()
        if item:self.repository.set_archived(item.data(Qt.ItemDataRole.UserRole),False);self._refresh_archive()

    def _archive_object(self):
        catalog_id=self.archive_object.currentData()
        if catalog_id:self.repository.set_archived(catalog_id,True);self._refresh_archive()
