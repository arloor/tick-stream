from tick_stream.config import load_config
from tick_stream.detection.engine import DetectionEngine
from tick_stream.models import AnomalyType


def test_orderbook_detector_emits_after_sustained_imbalance():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    engine = DetectionEngine(config)
    rows = [
        {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:00+08:00", "last_price": 100, "bid_px1": 99.9, "bid_vol1": 1000, "ask_px1": 100.1, "ask_vol1": 1000},
        {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:01+08:00", "last_price": 100, "bid_px1": 99.9, "bid_vol1": 4000, "ask_px1": 100.1, "ask_vol1": 200},
        {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:02+08:00", "last_price": 100, "bid_px1": 99.9, "bid_vol1": 4500, "ask_px1": 100.1, "ask_vol1": 100},
    ]
    events = []
    for row in rows:
        _, evts, _ = engine.process_raw(row)
        events.extend(evts)
    assert any(event.anomaly_type == AnomalyType.ORDERBOOK_LIQUIDITY for event in events)
