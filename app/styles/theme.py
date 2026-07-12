from app.core.constants import ACCENT


def application_stylesheet() -> str:
    return f"""
    QWidget {{ background: #05090D; color: #F1F2F4; font-family: 'Segoe UI'; font-size: 10.5pt; }}
    QLabel {{ background: transparent; }}
    QMainWindow {{ background: #030609; }}
    QFrame#panel, QFrame#catalogPanel, QFrame#quickView {{ background: #071016; border: 1px solid #1D2932; border-radius: 8px; }}
    QFrame#topBar {{ background: #020509; border: 0; border-bottom: 1px solid #111922; }}
    QPushButton {{ background: transparent; border: 1px solid transparent; border-radius: 5px; padding: 6px 10px; }}
    QPushButton:hover {{ background: #111A22; color: white; }}
    QPushButton:disabled {{ color: #4B525B; }}
    QPushButton[active="true"] {{ color: #D4A4FF; border-bottom: 3px solid {ACCENT}; border-radius: 0; background: rgba(139,44,245,0.08); }}
    QLineEdit, QComboBox {{ background: #091118; border: 1px solid #26333D; border-radius: 6px; padding: 7px 11px; min-height: 22px; }}
    QComboBox {{ padding-right:30px; }}
    QComboBox::drop-down {{ width:28px; border:0; background:transparent; }}
    QComboBox::down-arrow {{ width:9px; height:6px; }}
    QLineEdit:focus {{ border-color: {ACCENT}; }}
    QLabel#muted {{ color: #8D98A3; }}
    QLabel#caption {{ color: #AAB2BA; font-size: 8.5pt; font-weight: 600; }}
    QLabel#groupHeader {{ color: #CCD1D6; font-size: 9pt; font-weight: 600; padding: 9px 12px 5px 12px; }}
    QScrollArea {{ border: 0; background: transparent; }}
    QScrollBar:vertical {{ background:#071016; width:8px; margin:0; }}
    QScrollBar::handle:vertical {{ background:#2B3540; border-radius:4px; min-height:30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QMenu {{ background:#091118; border:1px solid #26333D; padding:6px; }}
    QMenu::item {{ padding:8px 24px 8px 12px; border-radius:4px; }}
    QMenu::item:selected {{ background:#17212B; color:white; }}
    """
