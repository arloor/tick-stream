from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from tick_stream.detection.reporting import is_reportable
from tick_stream.detection.suppression import SEVERITY_RANK
from tick_stream.models import AnomalyEvent, AnomalyRuleSet, FeatureSnapshot


def split_reportable_events(
    events: list[AnomalyEvent],
    feature: FeatureSnapshot,
    rule: AnomalyRuleSet,
) -> tuple[list[AnomalyEvent], list[tuple[AnomalyEvent, str]]]:
    reportable: list[AnomalyEvent] = []
    suppressed: list[tuple[AnomalyEvent, str]] = []
    for event in events:
        if is_reportable(event, feature, rule, events):
            reportable.append(event)
        else:
            suppressed.append((event, "not reportable"))
    return reportable, suppressed


def primary_event(events: list[AnomalyEvent]) -> AnomalyEvent:
    return max(events, key=lambda event: SEVERITY_RANK[event.severity])


def apply_alert_suppression_key(events: list[AnomalyEvent]) -> AnomalyEvent:
    primary = primary_event(events)
    primary.suppression_key = f"{primary.symbol}:alert:{primary.direction.value}"
    for event in events:
        event.suppression_key = primary.suppression_key
    return primary


@dataclass(slots=True)
class _AlertBuffer:
    started_at: datetime
    events: list[AnomalyEvent] = field(default_factory=list)


class AlertWindowAggregator:
    def __init__(self) -> None:
        self._buffers: dict[str, _AlertBuffer] = {}

    def add(self, events: list[AnomalyEvent], window_seconds: int) -> list[list[AnomalyEvent]]:
        if not events:
            return []
        event_time = min(event.trigger_time for event in events)
        symbol = events[0].symbol
        flushed = self.flush_due(event_time)
        buffer = self._buffers.get(symbol)
        if buffer is None:
            self._buffers[symbol] = _AlertBuffer(started_at=event_time, events=list(events))
            return flushed
        if event_time > buffer.started_at + timedelta(seconds=window_seconds):
            flushed.append(_compact_events(buffer.events))
            self._buffers[symbol] = _AlertBuffer(started_at=event_time, events=list(events))
            return flushed
        buffer.events.extend(events)
        return flushed

    def flush_due(self, now: datetime) -> list[list[AnomalyEvent]]:
        flushed: list[list[AnomalyEvent]] = []
        for symbol, buffer in list(self._buffers.items()):
            window = max(event_window_seconds(event) for event in buffer.events)
            if now > buffer.started_at + timedelta(seconds=window):
                flushed.append(_compact_events(buffer.events))
                del self._buffers[symbol]
        return flushed

    def flush_all(self) -> list[list[AnomalyEvent]]:
        flushed = [_compact_events(buffer.events) for buffer in self._buffers.values()]
        self._buffers.clear()
        return flushed


def event_window_seconds(event: AnomalyEvent) -> int:
    value = event.measurement.get("alert_aggregation_window_seconds")
    if value is None:
        return 30
    return int(value)


def attach_alert_window(events: list[AnomalyEvent], window_seconds: int) -> None:
    for event in events:
        event.measurement["alert_aggregation_window_seconds"] = window_seconds


def _compact_events(events: list[AnomalyEvent]) -> list[AnomalyEvent]:
    best: dict[str, AnomalyEvent] = {}
    for event in events:
        key = event.anomaly_type.value
        previous = best.get(key)
        if previous is None:
            best[key] = event
            continue
        if (SEVERITY_RANK[event.severity], event.trigger_time) >= (SEVERITY_RANK[previous.severity], previous.trigger_time):
            best[key] = event
    return sorted(best.values(), key=lambda event: event.trigger_time)
