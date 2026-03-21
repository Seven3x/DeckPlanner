from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QWidget

from ..models import CardViewModel


class CardTileWidget(QFrame):
    clicked = Signal(str)

    def __init__(self, card: CardViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._card = card
        self._selected = False

        self.setObjectName("cardTile")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(160)
        self.setMaximumWidth(180)

        layout = QVBoxLayout(self)

        self._name_label = QLabel(card.name, self)
        self._name_label.setWordWrap(True)
        self._cost_label = QLabel(f"费用: {card.cost}", self)
        self._type_label = QLabel(f"类型: {card.card_type}", self)
        self._tags_label = QLabel(f"标签: {card.tags_text}", self)
        self._effect_label = QLabel(card.effect_text, self)
        self._effect_label.setWordWrap(True)

        layout.addWidget(self._name_label)
        layout.addWidget(self._cost_label)
        layout.addWidget(self._type_label)
        layout.addWidget(self._tags_label)
        layout.addWidget(self._effect_label)
        layout.addStretch(1)

        self._apply_style()

    @property
    def card(self) -> CardViewModel:
        return self._card

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self.clicked.emit(self._card.instance_key)

    def _apply_style(self) -> None:
        border = "#d54c4c" if self._selected else "#87939f"
        bg = "#fff6eb" if self._selected else "#f4f6f8"
        self.setStyleSheet(
            (
                "QFrame#cardTile {"
                f"background: {bg};"
                f"border: 2px solid {border};"
                "border-radius: 8px;"
                "padding: 6px;"
                "}"
            )
        )
