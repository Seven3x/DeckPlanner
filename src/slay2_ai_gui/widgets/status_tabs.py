from __future__ import annotations

from typing import Iterable

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..models import GuiStateSnapshot, SearchResultSnapshot


class StatusTabsWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._tabs = QTabWidget(self)

        self._overview_view = QPlainTextEdit(self)
        self._overview_view.setReadOnly(True)

        self._hand_list = QListWidget(self)
        self._draw_list = QListWidget(self)
        self._discard_list = QListWidget(self)
        self._exhaust_list = QListWidget(self)

        self._trigger_list = QListWidget(self)
        self._pending_list = QListWidget(self)

        self._search_detail_view = QPlainTextEdit(self)
        self._search_detail_view.setReadOnly(True)

        self._tabs.addTab(self._build_overview_tab(), "总览")
        self._tabs.addTab(self._build_piles_tab(), "手牌与牌堆")
        self._tabs.addTab(self._build_trigger_pending_tab(), "Triggers / Pending")
        self._tabs.addTab(self._build_search_detail_tab(), "搜索结果详情")

        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)

    def _build_overview_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.addWidget(self._overview_view)
        return panel

    def _build_piles_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QHBoxLayout(panel)

        layout.addWidget(self._list_group("手牌", self._hand_list))
        layout.addWidget(self._list_group("抽牌堆", self._draw_list))
        layout.addWidget(self._list_group("弃牌堆", self._discard_list))
        layout.addWidget(self._list_group("消耗堆", self._exhaust_list))
        return panel

    def _build_trigger_pending_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QHBoxLayout(panel)
        layout.addWidget(self._list_group("Triggers", self._trigger_list))
        layout.addWidget(self._list_group("Pending Effects", self._pending_list))
        return panel

    def _build_search_detail_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        hint = QLabel("搜索详情预留区（trace / 分支对比 / 终局状态）")
        layout.addWidget(hint)
        layout.addWidget(self._search_detail_view)
        return panel

    def _list_group(self, title: str, list_widget: QListWidget) -> QGroupBox:
        group = QGroupBox(title, self)
        layout = QVBoxLayout(group)
        layout.addWidget(list_widget)
        return group

    def _fill_list(self, list_widget: QListWidget, rows: Iterable[str]) -> None:
        list_widget.clear()
        data = list(rows)
        if not data:
            list_widget.addItem("<empty>")
            return
        list_widget.addItems(data)

    def update_from_state(
        self,
        snapshot: GuiStateSnapshot | None,
        search: SearchResultSnapshot | None,
    ) -> None:
        if snapshot is None:
            self._overview_view.setPlainText("尚未载入状态，请先点击“运行 demo”。")
            self._fill_list(self._hand_list, [])
            self._fill_list(self._draw_list, [])
            self._fill_list(self._discard_list, [])
            self._fill_list(self._exhaust_list, [])
            self._fill_list(self._trigger_list, [])
            self._fill_list(self._pending_list, [])
            self._search_detail_view.setPlainText("暂无搜索结果。")
            return

        overview_lines = [
            f"Turn: {snapshot.turn_index}",
            (
                "Player: "
                f"HP {snapshot.player_hp}/{snapshot.player_max_hp}, "
                f"Energy {snapshot.energy}, Block {snapshot.block}"
            ),
            f"Player Buffs: {snapshot.player_buffs_text}",
            f"Player Debuffs: {snapshot.player_debuffs_text}",
            (
                "Enemy: "
                f"HP {snapshot.enemy_hp}/{snapshot.enemy_max_hp}, "
                f"Block {snapshot.enemy_block}, Intent {snapshot.enemy_intent_damage}"
            ),
            f"Enemy Buffs: {snapshot.enemy_buffs_text}",
            f"Enemy Debuffs: {snapshot.enemy_debuffs_text}",
        ]
        self._overview_view.setPlainText("\n".join(overview_lines))

        self._fill_list(self._hand_list, snapshot.hand)
        self._fill_list(self._draw_list, snapshot.draw_pile)
        self._fill_list(self._discard_list, snapshot.discard_pile)
        self._fill_list(self._exhaust_list, snapshot.exhaust_pile)
        self._fill_list(self._trigger_list, snapshot.triggers)
        self._fill_list(self._pending_list, snapshot.pending_effects)

        if search is None:
            self._search_detail_view.setPlainText("暂无搜索结果。")
        else:
            details = [search.summary_text(), "", *search.trace]
            self._search_detail_view.setPlainText("\n".join(details))
