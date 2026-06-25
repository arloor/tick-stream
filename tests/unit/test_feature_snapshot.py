from tick_stream.config import load_config
from tick_stream.detection.engine import DetectionEngine


def test_feature_snapshot_marks_missing_orderbook():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    engine = DetectionEngine(config)
    _, _, feature = engine.process_raw({"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:00+08:00", "last_price": 100})
    assert feature is not None
    assert feature.feature_availability["order_flow_imbalance"] == "missing_data"
