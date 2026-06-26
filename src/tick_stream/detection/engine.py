from __future__ import annotations

from datetime import datetime

from tick_stream.config import rule_for_symbol
from tick_stream.models import AnomalyEvent, OrderBookSnapshot, QualityStatus, RuntimeConfig, TickRecord
from tick_stream.utils import pct_change, to_float

from .features import compute_features
from .filters import is_ignored_session
from .momentum import detect_momentum
from .normalization import normalize_tick
from .orderbook import OrderBookLiquidityDetector
from .price import detect_price_jump
from .windows import RollingWindowStore


class DetectionEngine:
    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        max_window = max((rule.momentum_baseline_seconds for rule in config.rules.values()), default=600)
        self.windows = RollingWindowStore(max_seconds=max(max_window, 600))
        self.latest_times: dict[str, datetime] = {}
        self.previous_books: dict[str, OrderBookSnapshot] = {}
        self.orderbook_detector = OrderBookLiquidityDetector()

    def process_raw(self, raw: dict) -> tuple[TickRecord, list[AnomalyEvent], object | None]:
        tick = normalize_tick(raw, {s.symbol for s in self.config.active_symbols}, self.latest_times, self.previous_books)
        if tick.quality_status != QualityStatus.ACCEPTED:
            return tick, [], None
        rule = rule_for_symbol(self.config, tick.symbol)
        if is_ignored_session(tick, rule):
            tick.quality_status = QualityStatus.IGNORED
            tick.quality_reason = "ignored session"
            return tick, [], None
        self.windows.add(tick)
        ticks = self.windows.window(tick.symbol, rule.momentum_baseline_seconds)
        short_ticks = self.windows.window(tick.symbol, rule.price_window_seconds)
        feature = compute_features(ticks, rule)
        if feature is None:
            return tick, [], None
        events: list[AnomalyEvent] = []
        for event in (
            detect_price_jump(short_ticks, feature, rule),
            detect_momentum(ticks, feature, rule),
            self.orderbook_detector.detect(tick, feature, rule),
        ):
            if event is not None:
                _attach_current_return(event, tick)
                events.append(event)
        return tick, events, feature


def _attach_current_return(event: AnomalyEvent, tick: TickRecord) -> None:
    if tick.last_price is None:
        return
    direct = _direct_return_pct(tick.raw)
    if direct is not None:
        event.measurement.setdefault("current_return_pct", direct)
        event.measurement.setdefault("current_return_basis", "行情字段")
        return
    for key, basis in (
        ("pre_close", "昨收"),
        ("prev_close", "昨收"),
        ("previous_close", "昨收"),
        ("last_close", "昨收"),
        ("open", "开盘"),
    ):
        base = to_float(tick.raw.get(key))
        if base and base > 0:
            event.measurement.setdefault("current_return_pct", pct_change(base, tick.last_price))
            event.measurement.setdefault("current_return_basis", basis)
            return


def _direct_return_pct(raw: dict) -> float | None:
    for key in ("current_return_pct", "change_pct", "change_percent", "pct_change", "change_rate", "daily_return_pct"):
        value = to_float(raw.get(key))
        if value is not None:
            return value * 100 if abs(value) <= 1 else value
    return None
