from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..models import (
    CardViewModel,
    GuiStateSnapshot,
    PendingEffectViewModel,
    SearchBranchViewModel,
    SearchResultSnapshot,
    SearchStepDetailViewModel,
    TriggerViewModel,
    build_branch_comparison,
)
from .card_tile import CardTileWidget


class StatusTabsWidget(QWidget):
    hand_card_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._tabs = QTabWidget(self)

        self._build_overview_widgets()
        self._build_piles_widgets()
        self._build_trigger_pending_widgets()
        self._build_search_widgets()

        self._tabs.addTab(self._build_overview_tab(), "总览")
        self._tabs.addTab(self._build_piles_tab(), "手牌与牌堆")
        self._tabs.addTab(self._build_trigger_pending_tab(), "Triggers / Pending")
        self._tabs.addTab(self._build_search_detail_tab(), "搜索结果详情")

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self._tabs)

        self._hand_card_lookup: dict[str, CardViewModel] = {}
        self._hand_tile_lookup: dict[str, CardTileWidget] = {}
        self._pile_card_lookup: dict[str, CardViewModel] = {}
        self._trigger_lookup: dict[str, TriggerViewModel] = {}
        self._pending_lookup: dict[str, PendingEffectViewModel] = {}
        self._branch_lookup: dict[str, SearchBranchViewModel] = {}
        self._recommended_step_lookup: dict[str, SearchStepDetailViewModel] = {}
        self._candidate_step_lookup: dict[str, SearchStepDetailViewModel] = {}
        self._selected_hand_card_key: str | None = None

    def _build_overview_widgets(self) -> None:
        self._turn_label = QLabel("-", self)
        self._player_hp_label = QLabel("-", self)
        self._player_energy_label = QLabel("-", self)
        self._player_block_label = QLabel("-", self)
        self._player_buffs_list = QListWidget(self)
        self._player_debuffs_list = QListWidget(self)
        self._enemy_hp_label = QLabel("-", self)
        self._enemy_block_label = QLabel("-", self)
        self._enemy_intent_label = QLabel("-", self)
        self._enemy_buffs_list = QListWidget(self)
        self._enemy_debuffs_list = QListWidget(self)

    def _build_piles_widgets(self) -> None:
        self._hand_scroll = QScrollArea(self)
        self._hand_scroll.setWidgetResizable(True)
        self._hand_cards_panel = QWidget(self)
        self._hand_cards_layout = QHBoxLayout(self._hand_cards_panel)
        self._hand_cards_layout.setAlignment(Qt.AlignLeft)
        self._hand_scroll.setWidget(self._hand_cards_panel)

        self._hand_detail_view = QPlainTextEdit(self)
        self._hand_detail_view.setReadOnly(True)

        self._pile_count_label = QLabel("-", self)
        self._draw_list = QListWidget(self)
        self._discard_list = QListWidget(self)
        self._exhaust_list = QListWidget(self)
        self._pile_detail_view = QPlainTextEdit(self)
        self._pile_detail_view.setReadOnly(True)

        self._pile_tab = QTabWidget(self)
        self._pile_tab.addTab(self._draw_list, "抽牌堆")
        self._pile_tab.addTab(self._discard_list, "弃牌堆")
        self._pile_tab.addTab(self._exhaust_list, "消耗堆")

        self._draw_list.itemSelectionChanged.connect(self._on_pile_selection_changed)
        self._discard_list.itemSelectionChanged.connect(self._on_pile_selection_changed)
        self._exhaust_list.itemSelectionChanged.connect(self._on_pile_selection_changed)

    def _build_trigger_pending_widgets(self) -> None:
        self._trigger_list = QListWidget(self)
        self._pending_list = QListWidget(self)
        self._trigger_pending_detail = QPlainTextEdit(self)
        self._trigger_pending_detail.setReadOnly(True)

        self._trigger_list.itemSelectionChanged.connect(self._on_trigger_selection_changed)
        self._pending_list.itemSelectionChanged.connect(self._on_pending_selection_changed)

    def _build_search_widgets(self) -> None:
        self._search_summary_label = QLabel("暂无搜索结果。", self)
        self._recommended_sequence_list = QListWidget(self)
        self._candidate_branch_list = QListWidget(self)
        self._candidate_branch_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._candidate_steps_list = QListWidget(self)
        self._branch_compare_view = QPlainTextEdit(self)
        self._branch_compare_view.setReadOnly(True)
        self._search_step_detail_view = QPlainTextEdit(self)
        self._search_step_detail_view.setReadOnly(True)

        self._recommended_sequence_list.itemSelectionChanged.connect(
            self._on_recommended_step_selected
        )
        self._candidate_branch_list.itemSelectionChanged.connect(self._on_candidate_branch_selected)
        self._candidate_steps_list.itemSelectionChanged.connect(self._on_candidate_step_selected)

    def _build_overview_tab(self) -> QWidget:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("当前回合", self))
        layout.addWidget(self._turn_label)

        body = QHBoxLayout()
        body.addWidget(
            self._build_overview_group(
                title="玩家",
                hp_label=self._player_hp_label,
                block_label=self._player_block_label,
                extra_label_name="能量",
                extra_label_widget=self._player_energy_label,
                buffs_list=self._player_buffs_list,
                debuffs_list=self._player_debuffs_list,
            )
        )
        body.addWidget(
            self._build_overview_group(
                title="敌人",
                hp_label=self._enemy_hp_label,
                block_label=self._enemy_block_label,
                extra_label_name="意图伤害",
                extra_label_widget=self._enemy_intent_label,
                buffs_list=self._enemy_buffs_list,
                debuffs_list=self._enemy_debuffs_list,
            )
        )
        layout.addLayout(body)
        return panel

    def _build_overview_group(
        self,
        title: str,
        hp_label: QLabel,
        block_label: QLabel,
        extra_label_name: str,
        extra_label_widget: QLabel,
        buffs_list: QListWidget,
        debuffs_list: QListWidget,
    ) -> QGroupBox:
        group = QGroupBox(title, self)
        layout = QVBoxLayout(group)

        stats = QWidget(group)
        stats_form = QFormLayout(stats)
        stats_form.addRow("HP", hp_label)
        stats_form.addRow("格挡", block_label)
        stats_form.addRow(extra_label_name, extra_label_widget)
        layout.addWidget(stats)

        buffs_box = QGroupBox("Buffs", group)
        buffs_layout = QVBoxLayout(buffs_box)
        buffs_layout.addWidget(buffs_list)
        layout.addWidget(buffs_box)

        debuffs_box = QGroupBox("Debuffs", group)
        debuffs_layout = QVBoxLayout(debuffs_box)
        debuffs_layout.addWidget(debuffs_list)
        layout.addWidget(debuffs_box)

        return group

    def _build_piles_tab(self) -> QWidget:
        panel = QWidget(self)
        root = QHBoxLayout(panel)

        left_group = QGroupBox("手牌卡牌方块", panel)
        left_layout = QVBoxLayout(left_group)
        left_layout.addWidget(self._hand_scroll)
        left_layout.addWidget(QLabel("已选手牌详情", panel))
        left_layout.addWidget(self._hand_detail_view)

        right_group = QGroupBox("牌堆详情", panel)
        right_layout = QVBoxLayout(right_group)
        right_layout.addWidget(self._pile_count_label)
        right_layout.addWidget(self._pile_tab)
        right_layout.addWidget(QLabel("已选牌详情", panel))
        right_layout.addWidget(self._pile_detail_view)

        root.addWidget(left_group, 6)
        root.addWidget(right_group, 4)
        return panel

    def _build_trigger_pending_tab(self) -> QWidget:
        panel = QWidget(self)
        root = QHBoxLayout(panel)

        trigger_group = QGroupBox("Triggers", panel)
        trigger_layout = QVBoxLayout(trigger_group)
        trigger_layout.addWidget(self._trigger_list)

        pending_group = QGroupBox("Pending Effects", panel)
        pending_layout = QVBoxLayout(pending_group)
        pending_layout.addWidget(self._pending_list)

        detail_group = QGroupBox("详情", panel)
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.addWidget(self._trigger_pending_detail)

        root.addWidget(trigger_group, 3)
        root.addWidget(pending_group, 3)
        root.addWidget(detail_group, 4)
        return panel

    def _build_search_detail_tab(self) -> QWidget:
        panel = QWidget(self)
        root = QVBoxLayout(panel)
        root.addWidget(self._search_summary_label)

        body = QHBoxLayout()

        left = QGroupBox("推荐动作序列", panel)
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._recommended_sequence_list)

        middle = QGroupBox("候选分支", panel)
        middle_layout = QVBoxLayout(middle)
        middle_layout.addWidget(self._candidate_branch_list)
        middle_layout.addWidget(QLabel("分支对比（选择两个分支）", panel))
        middle_layout.addWidget(self._branch_compare_view)
        middle_layout.addWidget(QLabel("分支步骤", panel))
        middle_layout.addWidget(self._candidate_steps_list)

        right = QGroupBox("步骤详情", panel)
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._search_step_detail_view)

        body.addWidget(left, 3)
        body.addWidget(middle, 4)
        body.addWidget(right, 4)
        root.addLayout(body)
        return panel

    def _clear_hand_tiles(self) -> None:
        while self._hand_cards_layout.count():
            item = self._hand_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _fill_counter_list(self, list_widget: QListWidget, rows: list[str]) -> None:
        list_widget.clear()
        if not rows:
            list_widget.addItem("<none>")
            return
        list_widget.addItems(rows)

    def _set_pile_rows(self, list_widget: QListWidget, prefix: str, cards: list[CardViewModel]) -> None:
        list_widget.clear()
        for index, card in enumerate(cards):
            key = f"{prefix}:{index}:{card.instance_key}"
            self._pile_card_lookup[key] = card
            item = QListWidgetItem(f"{card.name} | 费用{card.cost} | {card.card_type}")
            item.setData(Qt.UserRole, key)
            list_widget.addItem(item)
        if list_widget.count() == 0:
            list_widget.addItem("<empty>")

    def _on_hand_card_clicked(self, card_key: str) -> None:
        for key, tile in self._hand_tile_lookup.items():
            tile.set_selected(key == card_key)

        selected = self._hand_card_lookup.get(card_key)
        if selected is None:
            self._hand_detail_view.setPlainText("未找到卡牌详情。")
            return
        self._selected_hand_card_key = card_key
        self._hand_detail_view.setPlainText(selected.detail_text())
        self.hand_card_selected.emit(selected.card_id)

    def select_hand_card_by_card_id(self, card_id: str) -> bool:
        if not card_id:
            return False
        for card_key, card in self._hand_card_lookup.items():
            if card.card_id == card_id:
                self._on_hand_card_clicked(card_key)
                return True
        return False

    def current_selected_hand_card_id(self) -> str:
        if not self._selected_hand_card_key:
            return ""
        card = self._hand_card_lookup.get(self._selected_hand_card_key)
        if card is None:
            return ""
        return card.card_id

    def _on_pile_selection_changed(self) -> None:
        sender = self.sender()
        if not isinstance(sender, QListWidget):
            return

        items = sender.selectedItems()
        if not items:
            return
        item = items[0]
        key = item.data(Qt.UserRole)
        if not isinstance(key, str):
            self._pile_detail_view.setPlainText("无可展示详情。")
            return
        card = self._pile_card_lookup.get(key)
        if card is None:
            self._pile_detail_view.setPlainText("无可展示详情。")
            return
        self._pile_detail_view.setPlainText(card.detail_text())

    def _set_trigger_rows(self, rows: list[TriggerViewModel]) -> None:
        self._trigger_list.clear()
        self._trigger_lookup.clear()
        for index, trigger in enumerate(rows):
            key = f"trigger:{index}"
            self._trigger_lookup[key] = trigger
            item = QListWidgetItem(
                f"{trigger.label} | {trigger.event} | uses={trigger.remaining_uses} | expire={trigger.expire_turn}"
            )
            item.setData(Qt.UserRole, key)
            self._trigger_list.addItem(item)
        if self._trigger_list.count() == 0:
            self._trigger_list.addItem("<empty>")

    def _set_pending_rows(self, rows: list[PendingEffectViewModel]) -> None:
        self._pending_list.clear()
        self._pending_lookup.clear()
        for index, pending in enumerate(rows):
            key = f"pending:{index}"
            self._pending_lookup[key] = pending
            item = QListWidgetItem(f"T{pending.execute_turn} | {pending.label}")
            item.setData(Qt.UserRole, key)
            self._pending_list.addItem(item)
        if self._pending_list.count() == 0:
            self._pending_list.addItem("<empty>")

    def _on_trigger_selection_changed(self) -> None:
        items = self._trigger_list.selectedItems()
        if not items:
            return
        key = items[0].data(Qt.UserRole)
        if not isinstance(key, str):
            self._trigger_pending_detail.setPlainText("无可展示详情。")
            return
        trigger = self._trigger_lookup.get(key)
        if trigger is None:
            self._trigger_pending_detail.setPlainText("无可展示详情。")
            return
        self._trigger_pending_detail.setPlainText(trigger.detail_text())

    def _on_pending_selection_changed(self) -> None:
        items = self._pending_list.selectedItems()
        if not items:
            return
        key = items[0].data(Qt.UserRole)
        if not isinstance(key, str):
            self._trigger_pending_detail.setPlainText("无可展示详情。")
            return
        pending = self._pending_lookup.get(key)
        if pending is None:
            self._trigger_pending_detail.setPlainText("无可展示详情。")
            return
        self._trigger_pending_detail.setPlainText(pending.detail_text())

    def _set_recommended_steps(self, search: SearchResultSnapshot) -> None:
        self._recommended_sequence_list.clear()
        self._recommended_step_lookup.clear()
        if search.recommended_step_details:
            for index, detail in enumerate(search.recommended_step_details):
                key = f"recommended:{index}"
                self._recommended_step_lookup[key] = detail
                item = QListWidgetItem(detail.summary_text())
                item.setData(Qt.UserRole, key)
                self._recommended_sequence_list.addItem(item)
            return

        if search.recommended_steps:
            for index, step in enumerate(search.recommended_steps):
                item = QListWidgetItem(f"{index + 1}. {step}")
                item.setData(Qt.UserRole, step)
                self._recommended_sequence_list.addItem(item)
            return

        if search.sequence:
            for index, action in enumerate(search.sequence):
                item = QListWidgetItem(f"{index + 1}. {action}")
                item.setData(Qt.UserRole, action)
                self._recommended_sequence_list.addItem(item)
            return

        self._recommended_sequence_list.addItem("<pass>")

    def _set_candidate_branches(self, branches: list[SearchBranchViewModel]) -> None:
        self._candidate_branch_list.clear()
        self._candidate_steps_list.clear()
        self._branch_compare_view.setPlainText("选择两个候选分支后，将显示总分/动作序列/最终状态差异。")
        self._branch_lookup.clear()
        self._candidate_step_lookup.clear()
        for index, branch in enumerate(branches):
            key = f"branch:{index}"
            self._branch_lookup[key] = branch
            item = QListWidgetItem(branch.list_text())
            item.setData(Qt.UserRole, key)
            self._candidate_branch_list.addItem(item)
        if self._candidate_branch_list.count() == 0:
            self._candidate_branch_list.addItem("<none>")

    def _on_recommended_step_selected(self) -> None:
        items = self._recommended_sequence_list.selectedItems()
        if not items:
            return
        step = items[0].data(Qt.UserRole)
        if not isinstance(step, str):
            return
        detail = self._recommended_step_lookup.get(step)
        if detail is not None:
            self._search_step_detail_view.setPlainText(detail.detail_text())
            return
        self._search_step_detail_view.setPlainText(step)

    def _on_candidate_branch_selected(self) -> None:
        items = self._candidate_branch_list.selectedItems()
        if not items:
            self._candidate_steps_list.clear()
            self._branch_compare_view.setPlainText("选择两个候选分支后，将显示总分/动作序列/最终状态差异。")
            return

        branch_keys: list[str] = []
        for item in items:
            key = item.data(Qt.UserRole)
            if isinstance(key, str) and key in self._branch_lookup:
                branch_keys.append(key)

        if not branch_keys:
            self._candidate_steps_list.clear()
            self._branch_compare_view.setPlainText("无可比较分支。")
            return

        selected_branches = [self._branch_lookup[key] for key in branch_keys if key in self._branch_lookup]
        if len(selected_branches) >= 2:
            comparison = build_branch_comparison(selected_branches[0], selected_branches[1])
            self._branch_compare_view.setPlainText(comparison.detail_text())
        else:
            only = selected_branches[0]
            self._branch_compare_view.setPlainText(
                "当前仅选择了 1 个分支。再选择 1 个分支即可比较。\n\n"
                f"{only.branch_label} 最终状态:\n{only.final_state_summary or '-'}"
            )

        branch_key = branch_keys[0]
        branch = self._branch_lookup.get(branch_key)
        if branch is None:
            self._candidate_steps_list.clear()
            return

        self._candidate_steps_list.clear()
        self._candidate_step_lookup.clear()
        if branch.step_details:
            for index, detail in enumerate(branch.step_details):
                step_key = f"candidate:{branch_key}:{index}"
                self._candidate_step_lookup[step_key] = detail
                item = QListWidgetItem(detail.summary_text())
                item.setData(Qt.UserRole, step_key)
                self._candidate_steps_list.addItem(item)
            return

        steps = branch.step_summaries or branch.actions
        if not steps:
            self._candidate_steps_list.addItem("<none>")
            return
        for step in steps:
            item = QListWidgetItem(step)
            item.setData(Qt.UserRole, step)
            self._candidate_steps_list.addItem(item)

    def _on_candidate_step_selected(self) -> None:
        items = self._candidate_steps_list.selectedItems()
        if not items:
            return
        step = items[0].data(Qt.UserRole)
        if not isinstance(step, str):
            self._search_step_detail_view.setPlainText("无可展示详情。")
            return
        detail = self._candidate_step_lookup.get(step)
        if detail is not None:
            self._search_step_detail_view.setPlainText(detail.detail_text())
            return
        self._search_step_detail_view.setPlainText(step)

    def update_from_state(
        self,
        snapshot: GuiStateSnapshot | None,
        search: SearchResultSnapshot | None,
    ) -> None:
        if snapshot is None:
            self._turn_label.setText("-")
            self._player_hp_label.setText("-")
            self._player_energy_label.setText("-")
            self._player_block_label.setText("-")
            self._enemy_hp_label.setText("-")
            self._enemy_block_label.setText("-")
            self._enemy_intent_label.setText("-")
            self._fill_counter_list(self._player_buffs_list, [])
            self._fill_counter_list(self._player_debuffs_list, [])
            self._fill_counter_list(self._enemy_buffs_list, [])
            self._fill_counter_list(self._enemy_debuffs_list, [])
            self._clear_hand_tiles()
            self._selected_hand_card_key = None
            self._pile_card_lookup.clear()
            self._set_pile_rows(self._draw_list, "draw", [])
            self._set_pile_rows(self._discard_list, "discard", [])
            self._set_pile_rows(self._exhaust_list, "exhaust", [])
            self._hand_detail_view.setPlainText("尚未载入状态，请先点击“运行 demo”。")
            self._pile_detail_view.setPlainText("尚未载入状态。")
            self._set_trigger_rows([])
            self._set_pending_rows([])
            self._trigger_pending_detail.setPlainText("暂无 trigger / pending 详情。")
            self._search_summary_label.setText("暂无搜索结果。")
            self._recommended_sequence_list.clear()
            self._candidate_branch_list.clear()
            self._candidate_steps_list.clear()
            self._recommended_step_lookup.clear()
            self._candidate_step_lookup.clear()
            self._branch_compare_view.setPlainText("暂无可比较分支。")
            self._search_step_detail_view.setPlainText("暂无搜索结果。")
            return

        self._turn_label.setText(str(snapshot.turn_index))
        self._player_hp_label.setText(f"{snapshot.player_hp}/{snapshot.player_max_hp}")
        self._player_energy_label.setText(str(snapshot.energy))
        self._player_block_label.setText(str(snapshot.block))
        self._enemy_hp_label.setText(f"{snapshot.enemy_hp}/{snapshot.enemy_max_hp}")
        self._enemy_block_label.setText(str(snapshot.enemy_block))
        self._enemy_intent_label.setText(str(snapshot.enemy_intent_damage))

        self._fill_counter_list(self._player_buffs_list, snapshot.player_buffs)
        self._fill_counter_list(self._player_debuffs_list, snapshot.player_debuffs)
        self._fill_counter_list(self._enemy_buffs_list, snapshot.enemy_buffs)
        self._fill_counter_list(self._enemy_debuffs_list, snapshot.enemy_debuffs)

        self._clear_hand_tiles()
        self._hand_card_lookup.clear()
        self._hand_tile_lookup.clear()
        for card in snapshot.hand_cards:
            tile = CardTileWidget(card, self._hand_cards_panel)
            tile.clicked.connect(self._on_hand_card_clicked)
            self._hand_cards_layout.addWidget(tile)
            self._hand_card_lookup[card.instance_key] = card
            self._hand_tile_lookup[card.instance_key] = tile
        self._hand_cards_layout.addStretch(1)

        if snapshot.hand_cards:
            initial_key = snapshot.hand_cards[0].instance_key
            if self._selected_hand_card_key in self._hand_card_lookup:
                initial_key = self._selected_hand_card_key
            self._on_hand_card_clicked(initial_key)
        else:
            self._selected_hand_card_key = None
            self._hand_detail_view.setPlainText("手牌为空。")

        self._pile_card_lookup.clear()
        self._set_pile_rows(self._draw_list, "draw", snapshot.draw_pile_cards)
        self._set_pile_rows(self._discard_list, "discard", snapshot.discard_pile_cards)
        self._set_pile_rows(self._exhaust_list, "exhaust", snapshot.exhaust_pile_cards)
        self._pile_count_label.setText(
            (
                f"抽牌堆: {len(snapshot.draw_pile_cards)} | "
                f"弃牌堆: {len(snapshot.discard_pile_cards)} | "
                f"消耗堆: {len(snapshot.exhaust_pile_cards)}"
            )
        )
        self._pile_detail_view.setPlainText("选择某张牌查看详情。")

        self._set_trigger_rows(snapshot.triggers)
        self._set_pending_rows(snapshot.pending_effects)
        self._trigger_pending_detail.setPlainText("选择 trigger 或 pending 查看详情。")

        if search is None:
            self._search_summary_label.setText("暂无搜索结果。")
            self._recommended_sequence_list.clear()
            self._candidate_branch_list.clear()
            self._candidate_steps_list.clear()
            self._recommended_step_lookup.clear()
            self._candidate_step_lookup.clear()
            self._branch_compare_view.setPlainText("暂无可比较分支。")
            self._search_step_detail_view.setPlainText("暂无搜索结果。")
            return

        self._search_summary_label.setText(search.summary_text())
        self._set_recommended_steps(search)
        self._set_candidate_branches(search.candidate_branches)
        self._search_step_detail_view.setPlainText("选择步骤查看详情。")
