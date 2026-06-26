from __future__ import annotations

from tick_stream.models import AnomalyEvent, AnomalyRuleSet, AnomalyType, FeatureSnapshot, Severity


SEVERITY_RANK = {Severity.WARNING: 1, Severity.HIGH: 2, Severity.CRITICAL: 3}


def is_reportable(event: AnomalyEvent, feature: FeatureSnapshot, rule: AnomalyRuleSet, sibling_events: list[AnomalyEvent]) -> bool:
    if event.anomaly_type == AnomalyType.PRICE_JUMP:
        return True
    if event.anomaly_type == AnomalyType.ORDERBOOK_LIQUIDITY:
        minimum = Severity(rule.orderbook_standalone_min_severity)
        if SEVERITY_RANK[event.severity] < SEVERITY_RANK[minimum]:
            return False
        if any(sibling.anomaly_type == AnomalyType.PRICE_JUMP for sibling in sibling_events if sibling is not event):
            return True
        price_confirmed = abs(feature.price_return_short_pct) >= rule.orderbook_notify_min_return_pct
        volume_confirmed = feature.volume_burst_ratio >= rule.orderbook_notify_volume_burst_ratio
        return price_confirmed and volume_confirmed
    if event.anomaly_type != AnomalyType.MOMENTUM_SPIKE:
        return True

    impulse_return = abs(float(event.measurement.get("impulse_return_pct", 0.0)))
    if impulse_return >= rule.momentum_notify_min_return_pct:
        return True
    if feature.volume_burst_ratio >= rule.momentum_notify_volume_burst_ratio:
        return True
    orderbook_pressure = (
        feature.queue_imbalance_ratio >= rule.momentum_notify_orderbook_imbalance_ratio
        or feature.cancel_add_ratio >= rule.momentum_notify_cancel_add_ratio
    )
    if orderbook_pressure and feature.volume_burst_ratio >= rule.momentum_notify_orderbook_min_volume_burst_ratio:
        return True
    return any(sibling.anomaly_type == AnomalyType.PRICE_JUMP for sibling in sibling_events if sibling is not event)
