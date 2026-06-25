from tick_stream.config import load_config
from tick_stream.replay import run_replay


def test_500_symbol_replay_smoke(tmp_path):
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    config.watchlist = [config.watchlist[0].__class__(symbol=f"SHSE.{600000+i:06d}", active=True, rule_profile="default") for i in range(500)]
    config.audit["dir"] = str(tmp_path)
    ticks = [{"symbol": item.symbol, "event_time": "2026-06-25T10:00:00+08:00", "last_price": 10.0} for item in config.watchlist]
    summary = run_replay(config, ticks, dry_run_notify=True)
    assert summary.ticks_accepted == 500
