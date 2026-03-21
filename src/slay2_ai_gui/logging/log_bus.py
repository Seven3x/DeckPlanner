from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Literal


LogChannel = Literal["event", "effect", "search", "error"]
LOG_CHANNELS: tuple[LogChannel, ...] = ("event", "effect", "search", "error")


@dataclass(frozen=True)
class LogEntry:
    channel: LogChannel
    message: str
    timestamp: datetime


class GuiLogBus:
    def __init__(self) -> None:
        self._subscribers: dict[LogChannel, list[Callable[[LogEntry], None]]] = defaultdict(list)

    def subscribe(self, channel: LogChannel, callback: Callable[[LogEntry], None]) -> None:
        self._subscribers[channel].append(callback)

    def publish(self, channel: LogChannel, message: str) -> None:
        if channel not in LOG_CHANNELS:
            raise ValueError(f"Unknown log channel: {channel}")

        entry = LogEntry(channel=channel, message=message, timestamp=datetime.now())
        for callback in list(self._subscribers[channel]):
            callback(entry)

    def publish_exception(self, exc: Exception, context: str = "") -> None:
        prefix = f"{context}: " if context else ""
        self.publish("error", f"{prefix}{type(exc).__name__}: {exc}")
