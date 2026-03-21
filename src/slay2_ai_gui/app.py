from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def _configure_font_for_cjk(app: QApplication) -> None:
    """Best-effort CJK font fallback for WSL/Linux environments."""
    candidates = [
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Microsoft YaHei",
        "SimHei",
    ]

    families = set(QFontDatabase().families())
    for family in candidates:
        if family in families:
            app.setFont(QFont(family, 10))
            return


def main() -> int:
    app = QApplication(sys.argv)
    _configure_font_for_cjk(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
