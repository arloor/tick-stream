from tick_stream.config import load_config
from tick_stream.detection.engine import DetectionEngine


def test_detection_event_includes_current_return_from_open_price():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    engine = DetectionEngine(config)
    rows = [
        {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:00+08:00", "last_price": 100.0, "open": 100.0},
        {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:01+08:00", "last_price": 100.5, "open": 100.0},
        {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:02+08:00", "last_price": 102.0, "open": 100.0},
    ]

    events = []
    for row in rows:
        _, row_events, _ = engine.process_raw(row)
        events.extend(row_events)

    assert events
    assert events[0].measurement["current_return_pct"] == 2.0
    assert events[0].measurement["current_return_basis"] == "开盘"
