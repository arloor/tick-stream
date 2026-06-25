from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from tick_stream.models import AnomalyEvent, EventStatus, Severity


SEVERITY_RANK = {Severity.WARNING: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}


@dataclass(slots=True)
class SuppressionDecision:
    event: AnomalyEvent
    suppressed: bool
    reason: str | None = None


class SuppressionEngine:
    def __init__(self, cooldown_seconds: int = 180) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._latest: dict[str, AnomalyEvent] = {}

    def decide(self, event: AnomalyEvent, cooldown_seconds: int | None = None) -> SuppressionDecision:
        key = event.suppression_key or f"{event.symbol}:{event.anomaly_type.value}:{event.direction.value}"
        cooldown = cooldown_seconds if cooldown_seconds is not None else self.cooldown_seconds
        previous = self._latest.get(key)
        if previous and previous.trigger_time + timedelta(seconds=cooldown) >= event.trigger_time:
            if SEVERITY_RANK[event.severity] <= SEVERITY_RANK[previous.severity]:
                event.status = EventStatus.SUPPRESSED
                return SuppressionDecision(event=event, suppressed=True, reason="cooldown duplicate")
        self._latest[key] = event
        return SuppressionDecision(event=event, suppressed=False)
