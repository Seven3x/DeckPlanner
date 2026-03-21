from __future__ import annotations

from collections.abc import Callable
from PySide6.QtCore import Qt

from PySide6.QtWidgets import QFileDialog, QMainWindow, QSplitter, QVBoxLayout, QWidget

from .logging import GuiLogBus
from .services import CoreGameService
from .widgets import ActionPanelWidget, LogPanelWidget, StatusTabsWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Slay2 AI - 本地助手面板（Stage 4 MVP）")
        self.resize(1280, 860)

        self._log_bus = GuiLogBus()
        self._service = CoreGameService(self._log_bus)

        self._status_tabs = StatusTabsWidget(self)
        self._action_panel = ActionPanelWidget(self)
        self._log_panel = LogPanelWidget(self)

        self._build_layout()
        self._bind_signals()

        for channel in ("event", "effect", "search", "error"):
            self._log_bus.subscribe(channel, self._log_panel.append_entry)

        self._refresh_status_view()

    def _build_layout(self) -> None:
        top_splitter = QSplitter(self)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.addWidget(self._status_tabs)
        top_splitter.addWidget(self._action_panel)
        top_splitter.setStretchFactor(0, 7)
        top_splitter.setStretchFactor(1, 3)

        main_splitter = QSplitter(self)
        main_splitter.setOrientation(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self._log_panel)
        main_splitter.setStretchFactor(0, 6)
        main_splitter.setStretchFactor(1, 4)

        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(main_splitter)

        self.setCentralWidget(root)

    def _bind_signals(self) -> None:
        self._action_panel.run_demo_button.clicked.connect(
            lambda: self._guarded("运行 demo", self._on_run_demo)
        )
        self._action_panel.search_button.clicked.connect(
            lambda: self._guarded("搜索最优序列", self._on_search)
        )
        self._action_panel.manual_action_button.clicked.connect(
            lambda: self._guarded("手动执行动作", self._on_manual_action)
        )
        self._action_panel.manual_card_combo.currentIndexChanged.connect(
            lambda _index: self._guarded("同步手牌选择", self._on_manual_card_changed)
        )
        self._status_tabs.hand_card_selected.connect(self._on_hand_card_selected)
        self._action_panel.load_json_button.clicked.connect(
            lambda: self._guarded("加载 JSON", self._on_load_json)
        )
        self._action_panel.refresh_button.clicked.connect(
            lambda: self._guarded("刷新状态", self._on_refresh)
        )
        self._action_panel.clear_logs_button.clicked.connect(self._log_panel.clear_all)

    def _guarded(self, action_name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            self._log_bus.publish_exception(exc, context=action_name)

    def _on_run_demo(self) -> None:
        self._log_panel.clear_all()
        self._service.run_demo()
        self._refresh_status_view()

    def _on_search(self) -> None:
        self._service.search_best_sequence(max_depth=5, beam_width=6)
        self._refresh_status_view()

    def _on_manual_action(self) -> None:
        card_id = self._action_panel.current_manual_card_id()
        if not card_id:
            self._log_bus.publish("event", "请先选择一张可执行手牌。")
            return
        self._service.execute_manual_action(card_id)
        self._refresh_status_view()

    def _on_manual_card_changed(self) -> None:
        card_id = self._action_panel.current_manual_card_id()
        if not card_id:
            return
        self._status_tabs.select_hand_card_by_card_id(card_id)

    def _on_hand_card_selected(self, card_id: str) -> None:
        self._action_panel.set_current_manual_card_id(card_id, emit_signal=False)

    def _on_load_json(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 JSON 文件",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        if self._service.load_json_file(file_path):
            self._refresh_status_view()

    def _on_refresh(self) -> None:
        self._service.refresh_state()
        self._refresh_status_view()

    def _refresh_status_view(self) -> None:
        snapshot = self._service.get_state_snapshot()
        search = self._service.get_search_snapshot()
        self._action_panel.set_manual_card_options(self._service.list_manual_play_options())
        self._status_tabs.update_from_state(snapshot, search)
