from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ActionPanelWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        title = QLabel("操作区")
        title.setObjectName("actionPanelTitle")
        layout.addWidget(title)

        self.run_demo_button = QPushButton("运行 demo")
        self.search_button = QPushButton("搜索最优序列")
        self.manual_action_button = QPushButton("手动执行动作")
        self.load_json_button = QPushButton("加载 JSON")
        self.refresh_button = QPushButton("刷新状态")
        self.clear_logs_button = QPushButton("清空日志")

        for button in (
            self.run_demo_button,
            self.search_button,
            self.manual_action_button,
            self.load_json_button,
            self.refresh_button,
            self.clear_logs_button,
        ):
            button.setMinimumHeight(34)
            layout.addWidget(button)

        layout.addStretch(1)
