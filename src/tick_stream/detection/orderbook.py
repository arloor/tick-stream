from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from tick_stream.models import AnomalyEvent, AnomalyRuleSet, AnomalyType, Direction, FeatureSnapshot, Severity, TickRecord


class OrderBookLiquidityDetector:
    def __init__(self) -> None:
        self._streaks: dict[str, int] = defaultdict(int)

    def detect(self, tick: TickRecord, feature: FeatureSnapshot, rule: AnomalyRuleSet) -> AnomalyEvent | None:
        book = tick.order_book
        if not book or not book.depth_available or tick.event_time is None or tick.last_price is None:
            self._streaks[tick.symbol] = 0
            return None
        signal = feature.cancel_add_ratio >= rule.orderbook_cancel_ratio_threshold or feature.queue_imbalance_ratio >= rule.orderbook_imbalance_ratio_threshold
        if signal:
            self._streaks[tick.symbol] += 1
        else:
            self._streaks[tick.symbol] = 0
            return None
        if self._streaks[tick.symbol] < rule.orderbook_min_consecutive_ticks:
            return None
        direction = Direction.UP if book.total_bid_quantity >= book.total_ask_quantity else Direction.DOWN
        severity = self._severity(feature, rule)
        return AnomalyEvent(
            event_id=f"evt_{uuid4().hex}",
            symbol=tick.symbol,
            anomaly_type=AnomalyType.ORDERBOOK_LIQUIDITY,
            direction=direction,
            severity=severity,
            trigger_time=tick.event_time,
            trigger_price=tick.last_price,
            measurement={
                "cancel_add_ratio": feature.cancel_add_ratio,
                "queue_imbalance_ratio": feature.queue_imbalance_ratio,
                "order_flow_imbalance": feature.order_flow_imbalance,
            },
            reason="sustained order book cancellation/addition or side imbalance",
            suppression_key=f"{tick.symbol}:orderbook_liquidity:{direction.value}",
            created_at=datetime.now(timezone.utc),
            feature_snapshot_ref=f"{feature.symbol}:{feature.event_time.isoformat()}",
        )

    @staticmethod
    def _severity(feature: FeatureSnapshot, rule: AnomalyRuleSet) -> Severity:
        if (
            feature.cancel_add_ratio >= rule.severity_thresholds["critical"].orderbook_cancel_ratio
            or feature.queue_imbalance_ratio >= rule.severity_thresholds["critical"].orderbook_imbalance_ratio
        ):
            return Severity.CRITICAL
        if (
            feature.cancel_add_ratio >= rule.severity_thresholds["high"].orderbook_cancel_ratio
            or feature.queue_imbalance_ratio >= rule.severity_thresholds["high"].orderbook_imbalance_ratio
        ):
            return Severity.HIGH
        return Severity.WARNING
