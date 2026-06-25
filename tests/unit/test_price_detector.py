from tick_stream.config import load_config, rule_for_symbol
from tick_stream.detection.engine import DetectionEngine
from tick_stream.models import AnomalyType


def test_price_detector_emits_price_jump():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    engine = DetectionEngine(config)
    events = []
    for i, price in enumerate([100, 100, 100, 102]):
        _, evts, _ = engine.process_raw({"symbol": "SHSE.600519", "event_time": f"2026-06-25T10:00:0{i}+08:00", "last_price": price})
        events.extend(evts)
    assert any(event.anomaly_type == AnomalyType.PRICE_JUMP for event in events)
