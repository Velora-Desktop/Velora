from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from app.models.game import MEDIA_STATUSES
from app.core.icon_registry import IconRegistry
from app.ui.widgets.platform_icons import platform_icon
from app.core.platforms import platform_sort_key
from app.ui.profile.statistics_widgets import RankedBarList


ACCENT = "#8B2CF5"


class DonutChart(QWidget):
    COLORS = ("#8B2CF5", "#1677FF", "#FFC83D", "#18D166")
    def __init__(self): super().__init__(); self.values=[]; self.setFixedSize(220,220)
    def set_values(self, values): self.values=list(values); self.update()
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); size=min(self.width(),self.height())-48; rect=self.rect(); rect.setSize(__import__('PySide6.QtCore',fromlist=['QSize']).QSize(size,size)); rect.moveCenter(self.rect().center()); total=sum(self.values)
        painter.setPen(QPen(QColor("#25283B"),24)); painter.drawEllipse(rect)
        if total:
            start=90*16
            for value,color in zip(self.values,self.COLORS):
                span=-int(value/total*360*16); painter.setPen(QPen(QColor(color),24)); painter.drawArc(rect,start,span); start+=span
        painter.setPen(QColor("#F2F3F7")); painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,f"Всего\n{total}")


class StatCard(QFrame):
    def __init__(self,title,color,icon_id):
        super().__init__(); self.setObjectName("statCard"); self.setMinimumHeight(104); self.setStyleSheet("QFrame#statCard{background:#161629;border:1px solid #303149;border-radius:8px;}")
        layout=QVBoxLayout(self); top=QHBoxLayout(); icon=QLabel(); icon.setFixedSize(30,30); icon.setPixmap(IconRegistry.pixmap(icon_id,26,variant="dark")); top.addWidget(icon)
        self.value=QLabel("0"); self.value.setStyleSheet(f"font-size:27pt;font-weight:750;color:{color};border:0;background:transparent;"); top.addWidget(self.value); top.addStretch(); layout.addLayout(top)
        self.label=QLabel(title); self.label.setStyleSheet("font-size:10.5pt;color:#D5D6E0;border:0;background:transparent;"); layout.addWidget(self.label)


class StatisticsDashboard(QScrollArea):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWidgetResizable(True); self.setFrameShape(QFrame.Shape.NoFrame)
        content=QWidget(); content.setMinimumWidth(1100); content.setMaximumWidth(1800); content.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred); self.root=QVBoxLayout(content); self.root.setContentsMargins(8,12,8,24); self.root.setSpacing(16)
        self._all_items=[]
        heading=QHBoxLayout(); box=QVBoxLayout(); title=QLabel("Статистика"); title.setStyleSheet("font-size:23pt;font-weight:700;"); box.addWidget(title); sub=QLabel("Ваши достижения и аналитика по официальным разделам каталога"); sub.setObjectName("muted"); box.addWidget(sub); heading.addLayout(box); heading.addStretch()
        self.media_filter=QComboBox(); self.media_filter.addItems(("Все разделы", "Игры", "Фильмы", "Сериалы", "Программы")); self.media_filter.setMinimumWidth(210); self.media_filter.currentTextChanged.connect(self._refresh_selected); heading.addWidget(self.media_filter); self.root.addLayout(heading)
        summary=self._panel("ОБЩАЯ СТАТИСТИКА"); grid=QGridLayout(); summary.layout().addLayout(grid); self.cards={}
        specs=(("objects","Объектов","#A95CFF","user_data"),("rated","Оценено","#FFC42E","personal_rating"),("started","Начато","#2D8CFF","date_started"),("completed","Завершено","#18D166","date_completed"),("favorites","В избранном","#EC2B78","notification_bell"),("hours","Время в играх","#98A0CB","playtime"),("average","Средняя оценка","#A95CFF","general_rating"))
        for i,(key,label,color,icon_id) in enumerate(specs): card=StatCard(label,color,icon_id); self.cards[key]=card; grid.addWidget(card,i//5,i%5)
        self.root.addWidget(summary)
        row1=QHBoxLayout(); row1.setSpacing(16); self.rating_panel=self._panel("РАСПРЕДЕЛЕНИЕ ОЦЕНОК"); self.rating_panel.setMinimumHeight(340); self.rating_panel.setMaximumHeight(390); self.rating_layout=QVBoxLayout(); self.rating_layout.setSpacing(10); self.rating_panel.layout().addLayout(self.rating_layout); row1.addWidget(self.rating_panel,1)
        types=self._panel("ПО ТИПАМ"); tl=QHBoxLayout(); tl.setContentsMargins(8,4,8,4); tl.setSpacing(18); self.donut=DonutChart(); tl.addWidget(self.donut,0,Qt.AlignmentFlag.AlignCenter); self.type_labels=QLabel(); self.type_labels.setMinimumWidth(150); self.type_labels.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft); tl.addWidget(self.type_labels,1); types.layout().addLayout(tl); row1.addWidget(types,1)
        self.status_panel=self._panel("ПО СТАТУСУ"); self.status_panel.setMinimumHeight(340); self.status_panel.setMaximumHeight(390); self.status_layout=QVBoxLayout(); self.status_layout.setSpacing(8); self.status_panel.layout().addLayout(self.status_layout); row1.addWidget(self.status_panel,1); self.root.addLayout(row1)
        row2=QHBoxLayout(); self.platforms=self._ranked_panel("ПО ПЛАТФОРМАМ"); self.years=self._ranked_panel("ПО ГОДАМ"); self.time_leaders=self._text_panel("ЛИДЕРЫ ПО ВРЕМЕНИ"); row2.addWidget(self.platforms); row2.addWidget(self.years); row2.addWidget(self.time_leaders); self.root.addLayout(row2)
        row3=QHBoxLayout(); self.genres=self._text_panel("ЛЮБИМЫЕ ЖАНРЫ"); self.records=self._text_panel("ЛИЧНЫЕ РЕКОРДЫ"); self.taste=self._text_panel("СТАТИСТИКА ВКУСА"); row3.addWidget(self.genres); row3.addWidget(self.records); row3.addWidget(self.taste); self.root.addLayout(row3); self.root.addStretch(); self.setWidget(content); self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        row4=QHBoxLayout(); row4.setSpacing(16)
        self.country_panel=self._panel("ПО СТРАНАМ"); self.country_panel.setMinimumHeight(230); self.country_panel.setMaximumHeight(300); self.country_layout=QVBoxLayout(); self.country_layout.setSpacing(8); self.country_panel.layout().addLayout(self.country_layout); row4.addWidget(self.country_panel,1)
        self.language_panel=self._panel("ЯЗЫКИ ИНТЕРФЕЙСА"); self.language_panel.setMinimumHeight(230); self.language_panel.setMaximumHeight(300); self.language_layout=QVBoxLayout(); self.language_layout.setSpacing(8); self.language_panel.layout().addLayout(self.language_layout); row4.addWidget(self.language_panel,1)
        self.metadata_stats=self._text_panel("КОЛЛЕКЦИЯ И ДОПОЛНЕНИЯ"); row4.addWidget(self.metadata_stats,1)
        self.root.insertLayout(self.root.count()-1,row4)
        row5=QHBoxLayout(); row5.setSpacing(16)
        self.category_stats=self._ranked_panel("ПО КАТЕГОРИЯМ")
        self.category_scores=self._ranked_panel("СРЕДНЯЯ ОЦЕНКА ПО КАТЕГОРИЯМ")
        self.creator_stats=self._ranked_panel("ЛЮБИМЫЕ СОЗДАТЕЛИ")
        row5.addWidget(self.category_stats,1); row5.addWidget(self.category_scores,1); row5.addWidget(self.creator_stats,1)
        self.root.insertLayout(self.root.count()-1,row5)
        row6=QHBoxLayout(); row6.setSpacing(16)
        self.decades=self._ranked_panel("ПО ДЕСЯТИЛЕТИЯМ")
        self.library_progress=self._ranked_panel("ПРОГРЕСС ЛИЧНОЙ БИБЛИОТЕКИ")
        self.subgroup_stats=self._ranked_panel("ПО ПОДГРУППАМ")
        row6.addWidget(self.decades,1); row6.addWidget(self.library_progress,1); row6.addWidget(self.subgroup_stats,1)
        self.root.insertLayout(self.root.count()-1,row6)

    @staticmethod
    def _panel(title):
        panel=QFrame(); panel.setObjectName("statisticsPanel"); panel.setStyleSheet("QFrame#statisticsPanel{background:#111222;border:1px solid #292A43;border-radius:8px;}"); layout=QVBoxLayout(panel); layout.setContentsMargins(18,16,18,16); heading=QLabel(title); heading.setStyleSheet("font-size:10.5pt;font-weight:650;color:#E9E9F0;border:0;background:transparent;"); layout.addWidget(heading); return panel
    def _text_panel(self,title): panel=self._panel(title); text=QLabel(); text.setWordWrap(True); text.setAlignment(Qt.AlignmentFlag.AlignTop); text.setMinimumHeight(190); text.setStyleSheet("font-size:10.5pt;color:#BFC1D0;border:0;padding:12px;"); panel.layout().addWidget(text); panel.value_label=text; return panel
    def _ranked_panel(self,title):
        panel=self._panel(title); values=RankedBarList(); panel.layout().addWidget(values); panel.values=values; return panel
    @staticmethod
    def _clear(layout):
        while layout.count():
            item=layout.takeAt(0); widget=item.widget(); child=item.layout()
            if widget: widget.deleteLater()
            elif child: StatisticsDashboard._clear(child)
    @staticmethod
    def _hours(value): return f"{value:g} ч"
    def _bar(self,layout,label,value,total,color=ACCENT):
        container=QWidget(); container.setObjectName("statisticsBarRow"); container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True); container.setStyleSheet("QWidget#statisticsBarRow{background:transparent;border:0;}"); container.setFixedHeight(32); row=QHBoxLayout(container); row.setContentsMargins(0,0,0,0); row.setSpacing(10)
        name=QLabel(label); name.setFixedWidth(122); name.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft); name.setStyleSheet("font-size:10.5pt;color:#E3E4EC;border:0;background:transparent;"); row.addWidget(name)
        bar=QProgressBar(); bar.setTextVisible(False); bar.setRange(0,max(total,1)); bar.setValue(value)
        bar.setFixedHeight(12); bar.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        bar.setStyleSheet(f"QProgressBar{{background:#28293C;border:0;border-radius:2px;}}QProgressBar::chunk{{background:{color};border-radius:2px;}}"); row.addWidget(bar,1)
        count=QLabel(str(value)); count.setFixedWidth(46); count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); count.setStyleSheet(f"font-size:14pt;font-weight:750;border:0;background:transparent;color:{color};"); row.addWidget(count)
        layout.addWidget(container)

    def refresh(self,games):
        self._all_items=list(games); self._refresh_selected()

    def _refresh_selected(self,*_):
        selected=self.media_filter.currentText(); official=[g for g in self._all_items if selected=="Все разделы" or g.media_type==selected]
        games=[g for g in official if g.user_interacted]; rated=[g for g in games if g.personal_score!="—"]
        defaults={"Игры":"НЕ НАЧИНАЛ","Фильмы":"НЕ СМОТРЕЛ","Сериалы":"НЕ СМОТРЕЛ","Программы":"НЕ ИСПОЛЬЗОВАЛ"}
        completed_values={"ПРОШЁЛ","ПОСМОТРЕЛ","ИСПОЛЬЗОВАЛ"}
        started=[g for g in games if g.status!=defaults.get(g.media_type,"НЕ НАЧИНАЛ")]; completed=[g for g in games if g.status in completed_values]; favorites=[g for g in games if g.favorite]; hours=sum(g.playtime_hours for g in games if g.media_type=="Игры"); average=sum(float(g.personal_score) for g in rated)/len(rated) if rated else None
        activity_value=self._hours(hours); activity_label="Время в играх"
        if selected=="Фильмы": activity_value=str(sum(g.watch_count for g in games)); activity_label="Всего просмотров"
        elif selected=="Сериалы":
            activity_value=str(sum(sum(state=="watched" for state in g.episode_states.values()) for g in games))
            activity_label="Просмотрено серий"
        elif selected=="Программы": activity_value=str(len(games)); activity_label="Программ в профиле"
        elif selected=="Все разделы": activity_label="Общее время в играх"
        self.cards["hours"].label.setText(activity_label)
        for key,value in {"objects":len(games),"rated":len(rated),"started":len(started),"completed":len(completed),"favorites":len(favorites),"hours":activity_value,"average":f"{average:.1f}" if average is not None else "—"}.items(): self.cards[key].value.setText(str(value))
        self._clear(self.rating_layout); buckets=(("10–9",lambda x:x>=9,"#18D166"),("8.9–7",lambda x:7<=x<9,"#7ED957"),("6.9–5",lambda x:5<=x<7,"#FFC42E"),("4.9–3",lambda x:3<=x<5,"#FF8A32"),("2.9–1",lambda x:x<3,"#FF4D57"))
        for label,test,color in buckets: self._bar(self.rating_layout,label,sum(test(float(g.personal_score)) for g in rated),len(rated),color)
        self.rating_layout.addStretch(1)
        types=Counter(g.media_type for g in games); ordered=[types.get(x,0) for x in ("Игры","Фильмы","Сериалы","Программы")]; self.donut.set_values(ordered); self.type_labels.setText("\n".join(f"{name}: {value}" for name,value in zip(("Игры","Фильмы","Сериалы","Программы"),ordered)))
        self._clear(self.status_layout); statuses=Counter(g.status for g in games)
        status_order=[]
        media=(selected,) if selected!="Все разделы" else ("Игры","Фильмы","Сериалы","Программы")
        for media_type in media:
            for status in MEDIA_STATUSES.get(media_type,()):
                if status not in status_order: status_order.append(status)
        from app.ui.catalog.status_menu import status_visual
        for status in status_order:
            color, _border, _background = status_visual(status)
            self._bar(self.status_layout,status,statuses.get(status,0),len(games),color)
        self.status_layout.addStretch(1)
        platforms=Counter(token.strip() for g in games for token in g.platform.split(";") if token.strip())
        ordered_platforms=sorted(platforms.items(),key=lambda item:(-item[1],platform_sort_key(item[0])))[:7]
        self.platforms.values.set_items(
            ordered_platforms,
            color="#9B5CFF",
            icon_resolver=self._platform_icon_spec,
            empty_text="Платформы появятся после взаимодействия с объектами",
        )
        years=Counter(g.year for g in games if g.year and g.year!="—")
        self.years.values.set_items(years.most_common(6),color="#4DA3FF")
        leaders=sorted((g for g in games if g.media_type=="Игры" and g.playtime_hours),key=lambda g:g.playtime_hours,reverse=True)[:5]
        if selected=="Фильмы":
            watched=sorted((g for g in games if g.watch_count),key=lambda g:g.watch_count,reverse=True)[:5]; self.time_leaders.value_label.setText("\n".join(f"{i}. {g.title} — {g.watch_count} просмотров" for i,g in enumerate(watched,1)) or "Нет данных о просмотрах")
        elif selected=="Сериалы":
            progress=sorted(
                ((sum(state=="watched" for state in g.episode_states.values()),g) for g in games if g.episode_states),
                key=lambda item:item[0],reverse=True,
            )[:5]
            self.time_leaders.value_label.setText("\n".join(f"{i}. {g.title} — {count}/{max(1,g.seasons)*10} серий" for i,(count,g) in enumerate(progress,1)) or "Нет данных о сериях")
        else:self.time_leaders.value_label.setText("\n".join(f"{i}. {g.title} — {g.playtime_hours:g} ч" for i,g in enumerate(leaders,1)) or "Нет данных")
        genres=Counter(g.category for g in rated); self.genres.value_label.setText(self._rank(genres,"Оцените объекты, чтобы увидеть любимые жанры"))
        top=max(rated,key=lambda g:float(g.personal_score),default=None)
        details=[f"Лучшая оценка\n{top.title} — {top.personal_score}" if top else "Оценок пока нет"]
        if leaders: details.append(f"Больше всего времени\n{leaders[0].title} — {leaders[0].playtime_hours:g} ч")
        if selected=="Программы": details.append(f"Использовано программ: {sum(g.status!='НЕ ИСПОЛЬЗОВАЛ' for g in games)}")
        if selected=="Фильмы": details.append(f"Всего повторных просмотров: {sum(max(0, g.watch_count-1) for g in games)}")
        if selected=="Сериалы":
            details.append(f"Сериалов с прогрессом: {sum(bool(g.episode_states) for g in games)}")
            details.append(f"Брошено серий: {sum(sum(state=='dropped' for state in g.episode_states.values()) for g in games)}")
        self.records.value_label.setText("\n\n".join(details))
        differences=[(float(g.personal_score)-float(g.general_score),g) for g in rated]
        if differences:
            high=max(differences,key=lambda x:x[0]); low=min(differences,key=lambda x:x[0]); self.taste.value_label.setText(f"Цените выше критиков\n{high[1].title}: {high[0]:+.1f}\n\nЦените ниже критиков\n{low[1].title}: {low[0]:+.1f}")
        else:self.taste.value_label.setText("Появится после ваших оценок")
        countries=Counter(value for g in games for value in g.publisher_countries)
        self._clear(self.country_layout)
        for name,value in countries.most_common(6): self._bar(self.country_layout,name,value,len(games),"#4DA3FF")
        if not countries: self.country_layout.addWidget(QLabel("Данные появятся после взаимодействия с объектами"))
        self.country_layout.addStretch(1)
        languages=Counter(value for g in games for value in g.interface_languages)
        self._clear(self.language_layout)
        for name,value in languages.most_common(6): self._bar(self.language_layout,name,value,len(games),"#18D166")
        if not languages: self.language_layout.addWidget(QLabel("Для выбранных объектов языки не указаны"))
        self.language_layout.addStretch(1)
        self.metadata_stats.value_label.setText(
            f"Наград у выбранных объектов: {sum(len(g.awards) for g in games)}\n"
            f"DLC в библиотеке: {sum(len(g.dlc) for g in games)}\n"
            f"Актёров в карточках: {sum(len(g.cast) for g in games)}\n"
            f"С открытым исходным кодом: {sum(g.source_code_type=='Открытый' for g in games)}\n"
            f"Бесплатных продуктов: {sum(g.distribution_model=='Бесплатное' for g in games)}"
        )

        categories=Counter(g.category.title() for g in games if g.category)
        self.category_stats.values.set_items(categories.most_common(6),color="#A95CFF")
        category_ratings: dict[str,list[float]]={}
        for game in rated:
            category_ratings.setdefault(game.category.title(),[]).append(float(game.personal_score))
        category_averages=sorted(
            ((name,sum(values)/len(values)) for name,values in category_ratings.items()),
            key=lambda item:(-item[1],item[0]),
        )[:6]
        self.category_scores.values.set_items(
            category_averages,maximum=10,color="#FFC42E",formatter=lambda value:f"{value:.1f}"
        )
        creators=Counter(g.developer for g in rated if g.developer and g.developer!="—")
        creator_title={"Фильмы":"ЛЮБИМЫЕ РЕЖИССЁРЫ","Сериалы":"ЛЮБИМЫЕ СОЗДАТЕЛИ","Программы":"ЛЮБИМЫЕ РАЗРАБОТЧИКИ"}.get(selected,"ЛЮБИМЫЕ РАЗРАБОТЧИКИ")
        self.creator_stats.layout().itemAt(0).widget().setText(creator_title)
        self.creator_stats.values.set_items(creators.most_common(6),color="#18D166")
        decades=Counter()
        for game in games:
            try: decades[f"{int(game.year)//10*10}-е"]+=1
            except (TypeError,ValueError): pass
        self.decades.values.set_items(sorted(decades.items(),reverse=True)[:6],color="#4DA3FF")
        interacted=max(len(games),1)
        progress=(
            ("С оценкой",len(rated)/interacted*100),
            ("Начато",len(started)/interacted*100),
            ("Завершено",len(completed)/interacted*100),
            ("В избранном",len(favorites)/interacted*100),
        )
        self.library_progress.values.set_items(
            progress,maximum=100,color="#18D166",formatter=lambda value:f"{value:.0f}%",
            empty_text="Начните взаимодействовать с каталогом",
        )
        subgroups=Counter(g.subgroup.title() for g in games if g.subgroup)
        self.subgroup_stats.values.set_items(subgroups.most_common(6),color="#EC2B78")

    @staticmethod
    def _rank(counter,empty): return "\n".join(f"{i}. {name} — {value}" for i,(name,value) in enumerate(counter.most_common(5),1)) or empty

    @staticmethod
    def _platform_rank(counter):
        if not counter: return "Нет данных"
        def icon(name):
            icon_id, _tooltip = platform_icon(name)
            path = IconRegistry.path(icon_id, variant="dark", category="platforms")
            return path.as_posix() if path else ""
        ordered = sorted(counter.items(), key=lambda item: (-item[1], platform_sort_key(item[0])))[:6]
        return "<br>".join(f'<img src="{icon(name)}" width="17" height="17">&nbsp; {name} — {value}' for name,value in ordered)

    @staticmethod
    def _platform_icon_spec(name: str) -> tuple[str, str | None]:
        streaming_services = {
            "NETFLIX", "КИНОПОИСК", "ИВИ", "OKKO", "AMEDIATEKA",
            "PREMIER", "START", "WINK", "APPLE TV+", "HBO MAX",
        }
        if name.strip().upper() in streaming_services:
            return "movie", "media_types"
        icon_id, _tooltip = platform_icon(name)
        return icon_id, "platforms"
