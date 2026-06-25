from __future__ import annotations

from collections import defaultdict, deque
from datetime import timedelta

from tick_stream.models import TickRecord


class RollingWindowStore:
    def __init__(self, max_seconds: int = 600) -> None:
        self.max_seconds = max_seconds
        self._ticks: dict[str, deque[TickRecord]] = defaultdict(deque)

    def add(self, tick: TickRecord) -> None:
        if not tick.event_time:
            return
        q = self._ticks[tick.symbol]
        q.append(tick)
        cutoff = tick.event_time - timedelta(seconds=self.max_seconds)
        while q and q[0].event_time and q[0].event_time < cutoff:
            q.popleft()

    def window(self, symbol: str, seconds: int) -> list[TickRecord]:
        q = self._ticks.get(symbol)
        if not q:
            return []
        latest = q[-1].event_time
        if latest is None:
            return list(q)
        cutoff = latest - timedelta(seconds=seconds)
        return [tick for tick in q if tick.event_time and tick.event_time >= cutoff]
