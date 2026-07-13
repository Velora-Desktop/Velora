from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout, QWidget


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
    def __init__(self,title,color):
        super().__init__(); self.setMinimumHeight(94); self.setStyleSheet("QFrame{background:#161629;border:1px solid #292A43;border-radius:10px;}")
        layout=QVBoxLayout(self); self.value=QLabel("0"); self.value.setStyleSheet(f"font-size:24pt;font-weight:700;color:{color};border:0;"); layout.addWidget(self.value)
        label=QLabel(title); label.setStyleSheet("color:#C5C6D2;border:0;"); layout.addWidget(label)


class StatisticsDashboard(QScrollArea):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWidgetResizable(True); self.setFrameShape(QFrame.Shape.NoFrame)
        content=QWidget(); content.setMinimumWidth(1100); content.setMaximumWidth(1800); content.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred); self.root=QVBoxLayout(content); self.root.setContentsMargins(8,12,8,24); self.root.setSpacing(16)
        heading=QHBoxLayout(); box=QVBoxLayout(); title=QLabel("Статистика"); title.setStyleSheet("font-size:23pt;font-weight:700;"); box.addWidget(title); sub=QLabel("Ваши достижения и аналитика библиотеки"); sub.setObjectName("muted"); box.addWidget(sub); heading.addLayout(box); heading.addStretch(); self.root.addLayout(heading)
        summary=self._panel("ОБЩАЯ СТАТИСТИКА"); grid=QGridLayout(); summary.layout().addLayout(grid); self.cards={}
        specs=(("objects","Объектов","#A95CFF"),("rated","Оценено","#FFC42E"),("started","Начато","#2D8CFF"),("completed","Завершено","#18D166"),("favorites","В избранном","#EC2B78"),("hours","Время в играх","#98A0CB"),("average","Средняя оценка","#A95CFF"))
        for i,(key,label,color) in enumerate(specs): card=StatCard(label,color); self.cards[key]=card; grid.addWidget(card,i//5,i%5)
        self.root.addWidget(summary)
        row1=QHBoxLayout(); row1.setSpacing(16); self.rating_panel=self._panel("РАСПРЕДЕЛЕНИЕ ОЦЕНОК"); self.rating_panel.setMinimumHeight(320); self.rating_layout=QVBoxLayout(); self.rating_panel.layout().addLayout(self.rating_layout); row1.addWidget(self.rating_panel,1)
        types=self._panel("ПО ТИПАМ"); tl=QHBoxLayout(); self.donut=DonutChart(); tl.addWidget(self.donut); self.type_labels=QLabel(); tl.addWidget(self.type_labels); types.layout().addLayout(tl); row1.addWidget(types,1)
        self.status_panel=self._panel("ПО СТАТУСУ"); self.status_panel.setMinimumHeight(320); self.status_layout=QVBoxLayout(); self.status_panel.layout().addLayout(self.status_layout); row1.addWidget(self.status_panel,1); self.root.addLayout(row1)
        row2=QHBoxLayout(); self.platforms=self._text_panel("ПО ПЛАТФОРМАМ"); self.years=self._text_panel("ПО ГОДАМ"); self.time_leaders=self._text_panel("ЛИДЕРЫ ПО ВРЕМЕНИ"); row2.addWidget(self.platforms); row2.addWidget(self.years); row2.addWidget(self.time_leaders); self.root.addLayout(row2)
        row3=QHBoxLayout(); self.genres=self._text_panel("ЛЮБИМЫЕ ЖАНРЫ"); self.records=self._text_panel("ЛИЧНЫЕ РЕКОРДЫ"); self.taste=self._text_panel("СТАТИСТИКА ВКУСА"); row3.addWidget(self.genres); row3.addWidget(self.records); row3.addWidget(self.taste); self.root.addLayout(row3); self.root.addStretch(); self.setWidget(content); self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    @staticmethod
    def _panel(title):
        panel=QFrame(); panel.setStyleSheet("QFrame{background:#111222;border:1px solid #292A43;border-radius:10px;}"); layout=QVBoxLayout(panel); layout.setContentsMargins(18,16,18,16); heading=QLabel(title); heading.setStyleSheet("font-size:10.5pt;font-weight:650;color:#E9E9F0;border:0;"); layout.addWidget(heading); return panel
    def _text_panel(self,title): panel=self._panel(title); text=QLabel(); text.setWordWrap(True); text.setAlignment(Qt.AlignmentFlag.AlignTop); text.setMinimumHeight(190); text.setStyleSheet("font-size:10.5pt;color:#BFC1D0;border:0;padding:12px;"); panel.layout().addWidget(text); panel.value_label=text; return panel
    @staticmethod
    def _clear(layout):
        while layout.count():
            item=layout.takeAt(0); widget=item.widget()
            if widget: widget.deleteLater()
    @staticmethod
    def _hours(value): return f"{value:g} ч"
    def _bar(self,layout,label,value,total,color=ACCENT):
        row=QHBoxLayout(); name=QLabel(label); name.setMinimumWidth(105); row.addWidget(name); bar=QProgressBar(); bar.setTextVisible(False); bar.setRange(0,max(total,1)); bar.setValue(value); bar.setStyleSheet(f"QProgressBar{{background:#25263A;border:0;border-radius:4px;height:8px;}}QProgressBar::chunk{{background:{color};border-radius:4px;}}"); row.addWidget(bar,1); row.addWidget(QLabel(str(value))); layout.addLayout(row)

    def refresh(self,games):
        all_games=list(games); games=[g for g in all_games if g.user_interacted]; rated=[g for g in games if g.personal_score!="—"]; started=[g for g in games if g.status!="НЕ НАЧИНАЛ"]; completed=[g for g in games if g.status=="ПРОШЁЛ"]; favorites=[g for g in games if g.favorite]; hours=sum(g.playtime_hours for g in games); average=sum(float(g.personal_score) for g in rated)/len(rated) if rated else None
        for key,value in {"objects":len(games),"rated":len(rated),"started":len(started),"completed":len(completed),"favorites":len(favorites),"hours":self._hours(hours),"average":f"{average:.1f}" if average is not None else "—"}.items(): self.cards[key].value.setText(str(value))
        self._clear(self.rating_layout); buckets=(("10–9",lambda x:x>=9),("8.9–7",lambda x:7<=x<9),("6.9–5",lambda x:5<=x<7),("4.9–3",lambda x:3<=x<5),("2.9–1",lambda x:x<3))
        for label,test in buckets: self._bar(self.rating_layout,label,sum(test(float(g.personal_score)) for g in rated),len(rated))
        self.rating_layout.addStretch(1)
        types=Counter(g.media_type for g in games); ordered=[types.get(x,0) for x in ("Игры","Фильмы","Сериалы","Программы")]; self.donut.set_values(ordered); self.type_labels.setText("\n".join(f"{name}: {value}" for name,value in zip(("Игры","Фильмы","Сериалы","Программы"),ordered)))
        self._clear(self.status_layout); statuses=Counter(g.status for g in games)
        for status in ("ПРОХОЖУ","ПРОШЁЛ","БРОСИЛ","НЕ НАЧИНАЛ"): self._bar(self.status_layout,status,statuses.get(status,0),len(games),"#18D166" if status=="ПРОШЁЛ" else ACCENT)
        self.status_layout.addStretch(1)
        platforms=Counter(token.strip() for g in games for token in g.platform.split(";") if token.strip()); self.platforms.value_label.setText(self._platform_rank(platforms))
        years=Counter(g.year for g in games if g.year and g.year!="—"); self.years.value_label.setText(self._rank(years,"Нет данных"))
        leaders=sorted((g for g in games if g.playtime_hours),key=lambda g:g.playtime_hours,reverse=True)[:5]; self.time_leaders.value_label.setText("\n".join(f"{i}. {g.title} — {g.playtime_hours:g} ч" for i,g in enumerate(leaders,1)) or "Нет данных")
        genres=Counter(g.category for g in rated); self.genres.value_label.setText(self._rank(genres,"Оцените объекты, чтобы увидеть любимые жанры"))
        top=max(rated,key=lambda g:float(g.personal_score),default=None); self.records.value_label.setText((f"Лучшая оценка\n{top.title} — {top.personal_score}\n\nБольше всего времени\n{leaders[0].title} — {leaders[0].playtime_hours:g} ч" if top and leaders else "Данных пока недостаточно"))
        differences=[(float(g.personal_score)-float(g.general_score),g) for g in rated]
        if differences:
            high=max(differences,key=lambda x:x[0]); low=min(differences,key=lambda x:x[0]); self.taste.value_label.setText(f"Цените выше критиков\n{high[1].title}: {high[0]:+.1f}\n\nЦените ниже критиков\n{low[1].title}: {low[0]:+.1f}")
        else:self.taste.value_label.setText("Появится после ваших оценок")

    @staticmethod
    def _rank(counter,empty): return "\n".join(f"{i}. {name} — {value}" for i,(name,value) in enumerate(counter.most_common(5),1)) or empty

    @staticmethod
    def _platform_rank(counter):
        if not counter: return "Нет данных"
        icon_root="C:/Velora/assets/icons/platforms"
        def icon(name):
            upper=name.upper()
            if upper.startswith("PS"): return f"{icon_root}/playstation.svg"
            if upper.startswith("X"): return f"{icon_root}/xbox.svg"
            if upper in ("SWITCH","SWITCH2","WII","WIIU","NDS","3DS"): return f"{icon_root}/nintendo.svg"
            return f"{icon_root}/pc.svg"
        return "<br>".join(f'<img src="{icon(name)}" width="17" height="17">&nbsp; {name} — {value}' for name,value in counter.most_common(6))
