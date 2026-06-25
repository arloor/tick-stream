from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from tick_stream.models import AnomalyEvent, AnomalyRuleSet, AnomalyType, Direction, FeatureSnapshot, Severity, TickRecord
from tick_stream.utils import pct_change


def _severity(value: float, rule: AnomalyRuleSet) -> Severity:
    abs_value = abs(value)
    if abs_value >= rule.severity_thresholds["critical"].price_return_pct:
        return Severity.CRITICAL
    if abs_value >= rule.severity_thresholds["high"].price_return_pct:
        return Severity.HIGH
    return Severity.WARNING


def detect_price_jump(ticks: list[TickRecord], feature: FeatureSnapshot, rule: AnomalyRuleSet) -> AnomalyEvent | None:
    if len(ticks) < rule.min_ticks_short_window:
        return None
    first = ticks[0]
    latest = ticks[-1]
    if first.last_price is None or latest.last_price is None or latest.event_time is None:
        return None
    ret = pct_change(first.last_price, latest.last_price)
    if abs(ret) < rule.price_return_threshold_pct:
        return None
    direction = Direction.UP if ret > 0 else Direction.DOWN
    severity = _severity(ret, rule)
    return AnomalyEvent(
        event_id=f"evt_{uuid4().hex}",
        symbol=latest.symbol,
        anomaly_type=AnomalyType.PRICE_JUMP,
        direction=direction,
        severity=severity,
        trigger_time=latest.event_time,
        trigger_price=latest.last_price,
        measurement={"price_return_pct": ret, "window_seconds": rule.price_window_seconds},
        reason=f"{rule.price_window_seconds}s price return {ret:.2f}% exceeds {rule.price_return_threshold_pct:.2f}%",
        suppression_key=f"{latest.symbol}:price_jump:{direction.value}",
        created_at=datetime.now(timezone.utc),
        feature_snapshot_ref=f"{feature.symbol}:{feature.event_time.isoformat()}",
    )
