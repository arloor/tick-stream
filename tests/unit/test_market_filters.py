from tick_stream.config import load_config
from tick_stream.detection.filters import is_ignored_session
from tick_stream.models import TickRecord
from tick_stream.utils import parse_dt
from datetime import datetime, timezone


def test_ignored_session_filter():
    config = load_config("config/watchlist.example.yml")
    rule = config.rules["default"]
    tick = TickRecord("SHSE.600519", parse_dt("2026-06-25T09:26:00+08:00"), datetime.now(timezone.utc), 100)
    assert is_ignored_session(tick, rule)
