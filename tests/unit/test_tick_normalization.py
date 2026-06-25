from tick_stream.detection.normalization import normalize_tick
from tick_stream.models import QualityStatus


def test_normalize_accepts_valid_tick_and_rejects_duplicate():
    latest = {}
    books = {}
    raw = {"symbol": "SHSE.600519", "event_time": "2026-06-25T10:00:00+08:00", "last_price": 100}
    tick = normalize_tick(raw, {"SHSE.600519"}, latest, books)
    dup = normalize_tick(raw, {"SHSE.600519"}, latest, books)
    assert tick.quality_status == QualityStatus.ACCEPTED
    assert dup.quality_status == QualityStatus.DUPLICATE


def test_normalize_ignores_outside_watchlist():
    tick = normalize_tick({"symbol": "SZSE.000001", "event_time": "2026-06-25T10:00:00+08:00", "last_price": 10}, {"SHSE.600519"}, {}, {})
    assert tick.quality_status == QualityStatus.IGNORED


def test_normalizes_gm_quotes_order_book():
    tick = normalize_tick(
        {
            "symbol": "SHSE.600519",
            "created_at": "2026-06-25T10:00:00+08:00",
            "price": 100.0,
            "cum_volume": 10,
            "quotes": [
                {"bid_p": 99.9, "bid_v": 1000, "ask_p": 100.1, "ask_v": 900},
                {"bid_p": 99.8, "bid_v": 800, "ask_p": 100.2, "ask_v": 700},
            ],
        },
        {"SHSE.600519"},
        {},
        {},
    )
    assert tick.quality_status == QualityStatus.ACCEPTED
    assert tick.order_book is not None
    assert tick.order_book.total_bid_quantity == 1800
