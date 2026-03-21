from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget


class ActionPanelWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        title = QLabel("操作区")
        title.setObjectName("actionPanelTitle")
        layout.addWidget(title)

        self.run_demo_button = QPushButton("运行 demo")
        self.search_button = QPushButton("搜索最优序列")
        self.manual_card_label = QLabel("手动打牌：选择当前可执行手牌")
        self.manual_card_combo = QComboBox(self)
        self.manual_action_button = QPushButton("执行所选手牌")
        self.load_json_button = QPushButton("加载 JSON")
        self.refresh_button = QPushButton("刷新状态")
        self.clear_logs_button = QPushButton("清空日志")

        for button in (
            self.run_demo_button,
            self.search_button,
            self.load_json_button,
            self.refresh_button,
            self.clear_logs_button,
        ):
            button.setMinimumHeight(34)
            layout.addWidget(button)

        self.manual_card_combo.setMinimumHeight(34)
        layout.insertWidget(2, self.manual_card_label)
        layout.insertWidget(3, self.manual_card_combo)
        layout.insertWidget(4, self.manual_action_button)
        self.manual_action_button.setMinimumHeight(34)

        layout.addStretch(1)

        self.set_manual_card_options([])

    def set_manual_card_options(self, options: list[tuple[str, str]]) -> None:
        current_id = self.current_manual_card_id()
        blocker = QSignalBlocker(self.manual_card_combo)
        self.manual_card_combo.clear()
        if not options:
            self.manual_card_combo.addItem("<无可执行手牌>", "")
            self.manual_card_combo.setEnabled(False)
            self.manual_action_button.setEnabled(False)
            del blocker
            return

        self.manual_card_combo.setEnabled(True)
        self.manual_action_button.setEnabled(True)
        selected_index = 0
        for idx, (card_id, label) in enumerate(options):
            self.manual_card_combo.addItem(label, card_id)
            if current_id and current_id == card_id:
                selected_index = idx
        self.manual_card_combo.setCurrentIndex(selected_index)
        del blocker

    def current_manual_card_id(self) -> str:
        value = self.manual_card_combo.currentData()
        return value if isinstance(value, str) else ""

    def set_current_manual_card_id(self, card_id: str, emit_signal: bool = False) -> bool:
        if not card_id:
            return False

        if emit_signal:
            for idx in range(self.manual_card_combo.count()):
                if self.manual_card_combo.itemData(idx) == card_id:
                    self.manual_card_combo.setCurrentIndex(idx)
                    return True
            return False

        blocker = QSignalBlocker(self.manual_card_combo)
        for idx in range(self.manual_card_combo.count()):
            if self.manual_card_combo.itemData(idx) == card_id:
                self.manual_card_combo.setCurrentIndex(idx)
                del blocker
                return True
        del blocker
        return False
