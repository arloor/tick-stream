from tick_stream.config import load_config
from tick_stream.detection.engine import DetectionEngine
from tick_stream.detection.features import compute_features
from tick_stream.models import AnomalyRuleSet, TickRecord
from datetime import datetime, timedelta, timezone


def test_feature_snapshot_marks_missing_orderbook():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    engine = DetectionEngine(config)
    _, _, feature = engine.process_raw({"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:00+08:00", "last_price": 100})
    assert feature is not None
    assert feature.feature_availability["order_flow_imbalance"] == "missing_data"


def test_volume_burst_uses_short_window_average_activity():
    now = datetime.now(timezone.utc)
    rule = AnomalyRuleSet(name="test", price_window_seconds=30)
    ticks = [
        TickRecord("SHSE.600519", now - timedelta(seconds=90), now, 100, volume=100),
        TickRecord("SHSE.600519", now - timedelta(seconds=60), now, 100, volume=100),
        TickRecord("SHSE.600519", now - timedelta(seconds=20), now, 100, volume=400),
        TickRecord("SHSE.600519", now - timedelta(seconds=10), now, 100, volume=400),
        TickRecord("SHSE.600519", now, now, 100, volume=400),
    ]
    feature = compute_features(ticks, rule)
    assert feature is not None
    assert feature.volume_burst_ratio == 400 / 280
