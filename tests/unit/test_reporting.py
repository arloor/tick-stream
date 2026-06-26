from datetime import datetime, timezone
from datetime import timedelta

from tick_stream.config import load_config
from tick_stream.alerts import AlertWindowAggregator, apply_alert_suppression_key, attach_alert_window
from tick_stream.detection.reporting import is_reportable
from tick_stream.models import AnomalyEvent, AnomalyType, Direction, FeatureSnapshot, Severity


def test_momentum_requires_confirmation_to_report():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    rule = config.rules["default"]
    event = AnomalyEvent(
        "evt",
        "SHSE.600519",
        AnomalyType.MOMENTUM_SPIKE,
        Direction.UP,
        Severity.CRITICAL,
        datetime.now(timezone.utc),
        100,
        {"impulse_return_pct": 0.6},
        "test",
    )
    feature = FeatureSnapshot(symbol="SHSE.600519", event_time=datetime.now(timezone.utc), volume_burst_ratio=1.0)
    assert not is_reportable(event, feature, rule, [event])


def test_momentum_reports_with_volume_confirmation():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    rule = config.rules["default"]
    event = AnomalyEvent(
        "evt",
        "SHSE.600519",
        AnomalyType.MOMENTUM_SPIKE,
        Direction.UP,
        Severity.CRITICAL,
        datetime.now(timezone.utc),
        100,
        {"impulse_return_pct": 0.6},
        "test",
    )
    feature = FeatureSnapshot(symbol="SHSE.600519", event_time=datetime.now(timezone.utc), volume_burst_ratio=rule.momentum_notify_volume_burst_ratio)
    assert is_reportable(event, feature, rule, [event])


def test_momentum_orderbook_confirmation_requires_minimum_volume_activity():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    rule = config.rules["default"]
    event = AnomalyEvent(
        "evt",
        "SHSE.600519",
        AnomalyType.MOMENTUM_SPIKE,
        Direction.UP,
        Severity.CRITICAL,
        datetime.now(timezone.utc),
        100,
        {"impulse_return_pct": 0.6},
        "test",
    )
    weak_feature = FeatureSnapshot(
        symbol="SHSE.600519",
        event_time=datetime.now(timezone.utc),
        queue_imbalance_ratio=rule.momentum_notify_orderbook_imbalance_ratio,
        volume_burst_ratio=rule.momentum_notify_orderbook_min_volume_burst_ratio - 0.01,
    )
    confirmed_feature = FeatureSnapshot(
        symbol="SHSE.600519",
        event_time=datetime.now(timezone.utc),
        queue_imbalance_ratio=rule.momentum_notify_orderbook_imbalance_ratio,
        volume_burst_ratio=rule.momentum_notify_orderbook_min_volume_burst_ratio,
    )
    assert not is_reportable(event, weak_feature, rule, [event])
    assert is_reportable(event, confirmed_feature, rule, [event])


def test_orderbook_requires_price_and_volume_confirmation():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    rule = config.rules["default"]
    event = AnomalyEvent(
        "evt",
        "SHSE.600519",
        AnomalyType.ORDERBOOK_LIQUIDITY,
        Direction.UP,
        Severity.HIGH,
        datetime.now(timezone.utc),
        100,
        {},
        "test",
    )
    weak_feature = FeatureSnapshot(symbol="SHSE.600519", event_time=datetime.now(timezone.utc), price_return_short_pct=0.0, volume_burst_ratio=1.0)
    strong_feature = FeatureSnapshot(
        symbol="SHSE.600519",
        event_time=datetime.now(timezone.utc),
        price_return_short_pct=rule.orderbook_notify_min_return_pct,
        volume_burst_ratio=rule.orderbook_notify_volume_burst_ratio,
    )
    assert not is_reportable(event, weak_feature, rule, [event])
    assert is_reportable(event, strong_feature, rule, [event])


def test_alert_window_aggregates_same_symbol_events():
    now = datetime.now(timezone.utc)
    first = AnomalyEvent("evt1", "SHSE.600519", AnomalyType.MOMENTUM_SPIKE, Direction.UP, Severity.HIGH, now, 100, {}, "test")
    second = AnomalyEvent("evt2", "SHSE.600519", AnomalyType.ORDERBOOK_LIQUIDITY, Direction.UP, Severity.HIGH, now + timedelta(seconds=10), 101, {}, "test")
    third = AnomalyEvent("evt3", "SHSE.600519", AnomalyType.PRICE_JUMP, Direction.UP, Severity.CRITICAL, now + timedelta(seconds=40), 103, {}, "test")
    aggregator = AlertWindowAggregator()
    attach_alert_window([first, second, third], 30)
    assert aggregator.add([first], 30) == []
    assert aggregator.add([second], 30) == []
    flushed = aggregator.add([third], 30)
    assert len(flushed) == 1
    assert {event.anomaly_type for event in flushed[0]} == {AnomalyType.MOMENTUM_SPIKE, AnomalyType.ORDERBOOK_LIQUIDITY}


def test_alert_suppression_key_includes_primary_anomaly_type():
    now = datetime.now(timezone.utc)
    event = AnomalyEvent("evt1", "SHSE.600519", AnomalyType.MOMENTUM_SPIKE, Direction.UP, Severity.HIGH, now, 100, {}, "test")
    primary = apply_alert_suppression_key([event])
    assert primary.suppression_key == "SHSE.600519:alert:momentum_spike:up"
