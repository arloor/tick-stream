from __future__ import annotations

from tick_stream.models import AnomalyRuleSet, TickRecord
from tick_stream.utils import parse_time


def is_ignored_session(tick: TickRecord, rule: AnomalyRuleSet) -> bool:
    if tick.event_time is None:
        return False
    current = tick.event_time.timetz().replace(tzinfo=None)
    for window in rule.ignored_sessions:
        start = parse_time(window["start"])
        end = parse_time(window["end"])
        if start <= current <= end:
            return True
    return False


def orderbook_available(tick: TickRecord) -> bool:
    return bool(tick.order_book and tick.order_book.depth_available)
