from tick_stream.config import load_config
from tick_stream.detection.engine import DetectionEngine
from tick_stream.models import AnomalyType


def test_momentum_detector_emits_spike_after_flat_baseline():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    engine = DetectionEngine(config)
    events = []
    for i, price in enumerate([100, 100, 100, 100, 100, 105]):
        _, evts, _ = engine.process_raw({"symbol": "SHSE.600519", "event_time": f"2026-06-25T10:00:0{i}+08:00", "last_price": price})
        events.extend(evts)
    assert any(event.anomaly_type == AnomalyType.MOMENTUM_SPIKE for event in events)
