from app.core.constants import ACCENT
from app.core.icon_registry import IconRegistry


def application_stylesheet() -> str:
    check_path = IconRegistry.path("check")
    check_image = check_path.as_posix() if check_path else ""
    return f"""
    QWidget {{ background: #05090D; color: #F1F2F4; font-family: 'Segoe UI'; font-size: 10.5pt; }}
    QLabel {{ background: transparent; }}
    QMainWindow, QDialog, QMessageBox {{ background: #030609; }}
    QFrame#panel, QFrame#catalogPanel, QFrame#quickView {{ background: #071016; border: 1px solid #1D2932; border-radius: 8px; }}
    QFrame#topBar {{ background: #020509; border: 0; border-bottom: 1px solid #111922; }}
    QPushButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 7px 11px; min-height: 22px; }}
    QPushButton:hover {{ background: #160B24; color: white; border-color:#552080; }}
    QPushButton:pressed {{ background: #24103A; border-color:{ACCENT}; }}
    QPushButton:focus {{ border-color: {ACCENT}; }}
    QPushButton:disabled {{ color: #56606A; background:#080D12; border-color:#151D24; }}
    QPushButton[primary="true"] {{ background:#6E1BC4; border:1px solid #A54BFF; color:white; font-weight:600; }}
    QPushButton[primary="true"]:hover {{ background:#7B25D5; }}
    QPushButton[danger="true"] {{ color:#FF7676; border:1px solid #713238; background:#211014; }}
    QPushButton[future="true"] {{ color:#73808C; border-color:#1A252E; background:#080E13; }}
    QPushButton[active="true"] {{ color: #D4A4FF; border-bottom: 3px solid {ACCENT}; border-radius: 0; background: rgba(139,44,245,0.08); }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget, QTableWidget {{ background: #091118; border: 1px solid #26333D; border-radius: 6px; padding: 7px 11px; min-height: 22px; selection-background-color:#5F1BAE; selection-color:white; }}
    QComboBox {{ padding-right:30px; }}
    QComboBox::drop-down {{ width:28px; border:0; background:transparent; }}
    QComboBox::down-arrow {{ width:9px; height:6px; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QListWidget:focus, QTableWidget:focus {{ border-color: {ACCENT}; }}
    QTabWidget::pane {{ border:1px solid #202D37; border-radius:7px; background:#060C11; top:-1px; }}
    QTabBar::tab {{ background:transparent; color:#909BA5; padding:10px 16px; border-bottom:2px solid transparent; }}
    QTabBar::tab:hover {{ color:#E7EAF0; background:#160B24; }}
    QTabBar::tab:selected {{ color:#E4C7FF; border-bottom-color:{ACCENT}; background:#100A1A; }}
    QCheckBox {{ spacing:9px; }}
    QCheckBox::indicator {{ width:17px; height:17px; border:1px solid #44515D; border-radius:4px; background:#091118; }}
    QCheckBox::indicator:checked {{ background:{ACCENT}; border-color:#B16CFF; image:url("{check_image}"); }}
    QLabel#muted {{ color: #8D98A3; }}
    QLabel#caption {{ color: #AAB2BA; font-size: 8.5pt; font-weight: 600; }}
    QLabel#groupHeader {{ color: #CCD1D6; font-size: 9pt; font-weight: 600; padding: 9px 12px 5px 12px; }}
    QScrollArea {{ border: 0; background: transparent; }}
    QScrollBar:vertical {{ background:#071016; width:8px; margin:0; }}
    QScrollBar::handle:vertical {{ background:#2B3540; border-radius:4px; min-height:30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar:horizontal {{ background:#071016; height:8px; margin:0; }}
    QScrollBar::handle:horizontal {{ background:#2B3540; border-radius:4px; min-width:30px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
    QMenu {{ background:#091118; border:1px solid #26333D; padding:6px; }}
    QMenu::item {{ padding:8px 24px 8px 12px; border-radius:4px; }}
    QMenu::item:selected {{ background:#160B24; color:white; }}
    QPushButton#groupToggle {{ color:#D7B7FF; background:transparent; border:1px solid transparent; font-size:15pt; padding:0; }}
    QPushButton#groupToggle:hover {{ color:white; background:#160B24; border-color:#6E2AA8; }}
    QPushButton#timeAction {{ background:#0B131A; border:1px solid #2A3540; text-align:left; }}
    QPushButton#timeAction:hover {{ background:#160B24; border-color:{ACCENT}; color:white; }}
    QPushButton#veloraLogo {{ color:#F3E8FF; background:transparent; border:0; }}
    QPushButton#veloraLogo:hover {{ color:white; background:#160B24; border:1px solid #58238A; }}
    QToolTip {{ background:#111A22; color:#F1F2F4; border:1px solid #33424E; padding:6px 8px; }}
    """
