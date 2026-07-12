from app.core.constants import ACCENT


def application_stylesheet() -> str:
    return f"""
    QWidget {{ background: #111216; color: #E8E9ED; font-family: 'Segoe UI'; font-size: 13px; }}
    QFrame#panel, QFrame#topBar, QFrame#quickView {{ background: #17191F; border: 1px solid #292C35; }}
    QPushButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 7px 10px; }}
    QPushButton:hover {{ background: #232630; color: white; }}
    QPushButton:disabled {{ color: #555A66; }}
    QPushButton[active="true"] {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; border-radius: 0; }}
    QLineEdit, QComboBox {{ background: #1D2028; border: 1px solid #303440; border-radius: 6px; padding: 7px 10px; }}
    QLineEdit:focus {{ border-color: {ACCENT}; }}
    QLabel#muted {{ color: #9297A3; }}
    QLabel#groupHeader {{ color: #B5B8C2; font-size: 11px; font-weight: 600; padding: 8px 2px; }}
    QScrollArea {{ border: 0; }}
    """

