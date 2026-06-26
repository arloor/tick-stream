from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from uuid import uuid4

from tick_stream.models import AnomalyEvent, AnomalyRuleSet, AnomalyType, Direction, FeatureSnapshot, Severity, TickRecord
from tick_stream.utils import pct_change


def robust_z(value: float, samples: list[float], zero_mad_min_abs_value: float = 0.0) -> float:
    if not samples:
        return 0.0
    med = median(samples)
    deviations = [abs(x - med) for x in samples]
    mad = median(deviations)
    if mad == 0:
        return 99.0 if abs(value - med) >= zero_mad_min_abs_value and value != med else 0.0
    return 0.6745 * (value - med) / mad


def _severity(z: float, rule: AnomalyRuleSet) -> Severity:
    abs_z = abs(z)
    if abs_z >= rule.severity_thresholds["critical"].momentum_z:
        return Severity.CRITICAL
    if abs_z >= rule.severity_thresholds["high"].momentum_z:
        return Severity.HIGH
    return Severity.WARNING


def detect_momentum(ticks: list[TickRecord], feature: FeatureSnapshot, rule: AnomalyRuleSet) -> AnomalyEvent | None:
    if len(ticks) < rule.min_ticks_baseline_window:
        return None
    latest = ticks[-1]
    if latest.event_time is None or latest.last_price is None:
        return None
    impulse = [t for t in ticks if t.event_time and (latest.event_time - t.event_time).total_seconds() <= rule.momentum_impulse_seconds]
    if len(impulse) < rule.min_ticks_short_window or impulse[0].last_price is None:
        return None
    seconds = max((latest.event_time - impulse[0].event_time).total_seconds(), 1.0)
    impulse_return = pct_change(impulse[0].last_price, latest.last_price)
    if abs(impulse_return) < rule.momentum_min_return_pct:
        feature.momentum_z = 0.0
        return None
    velocity = impulse_return / seconds
    baseline = []
    for i in range(1, len(ticks)):
        prev, cur = ticks[i - 1], ticks[i]
        if prev.last_price is None or cur.last_price is None or prev.event_time is None or cur.event_time is None:
            continue
        dt = max((cur.event_time - prev.event_time).total_seconds(), 1.0)
        baseline.append(pct_change(prev.last_price, cur.last_price) / dt)
    nonzero_baseline = [value for value in baseline if abs(value) > 1e-9]
    if len(nonzero_baseline) < rule.momentum_min_nonzero_baseline_samples and abs(impulse_return) < rule.momentum_zero_mad_min_return_pct:
        feature.momentum_z = 0.0
        return None
    zero_mad_min_abs_value = rule.momentum_zero_mad_min_return_pct / seconds
    z = robust_z(velocity, baseline, zero_mad_min_abs_value=zero_mad_min_abs_value)
    feature.momentum_z = z
    if abs(z) < rule.momentum_z_threshold:
        return None
    direction = Direction.UP if velocity > 0 else Direction.DOWN
    severity = _severity(z, rule)
    return AnomalyEvent(
        event_id=f"evt_{uuid4().hex}",
        symbol=latest.symbol,
        anomaly_type=AnomalyType.MOMENTUM_SPIKE,
        direction=direction,
        severity=severity,
        trigger_time=latest.event_time,
        trigger_price=latest.last_price,
        measurement={
            "momentum_z": z,
            "impulse_seconds": rule.momentum_impulse_seconds,
            "impulse_return_pct": impulse_return,
            "velocity_pct_per_second": velocity,
            "nonzero_baseline_samples": len(nonzero_baseline),
        },
        reason=f"momentum z-score {z:.2f} exceeds {rule.momentum_z_threshold:.2f} with {impulse_return:.2f}% impulse return",
        suppression_key=f"{latest.symbol}:momentum_spike:{direction.value}",
        created_at=datetime.now(timezone.utc),
        feature_snapshot_ref=f"{feature.symbol}:{feature.event_time.isoformat()}",
    )
