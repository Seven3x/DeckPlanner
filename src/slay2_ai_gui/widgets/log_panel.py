from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget

from ..logging import LogEntry


class LogPanelWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._tab = QTabWidget(self)
        self._views = {
            "event": self._build_log_view(),
            "effect": self._build_log_view(),
            "search": self._build_log_view(),
            "error": self._build_log_view(),
        }

        self._tab.addTab(self._views["event"], "事件触发日志")
        self._tab.addTab(self._views["effect"], "效果执行日志")
        self._tab.addTab(self._views["search"], "搜索过程日志")
        self._tab.addTab(self._views["error"], "错误/异常日志")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tab)

    def _build_log_view(self) -> QPlainTextEdit:
        view = QPlainTextEdit(self)
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.NoWrap)
        return view

    def append_entry(self, entry: LogEntry) -> None:
        target = self._views[entry.channel]
        prefix = entry.timestamp.strftime("%H:%M:%S")
        target.appendPlainText(f"[{prefix}] {entry.message}")

    def clear_all(self) -> None:
        for view in self._views.values():
            view.clear()
