from tick_stream.config import load_config
from tick_stream.replay import read_jsonl, run_replay


def test_variant_config_reduces_alerts(tmp_path):
    strict = load_config("tests/fixtures/config/watchlist_variant.yml")
    strict.audit["dir"] = str(tmp_path / "strict")
    base = load_config("tests/fixtures/config/valid_watchlist.yml")
    base.audit["dir"] = str(tmp_path / "base")
    ticks = read_jsonl("tests/fixtures/ticks/sample.jsonl")
    base_summary = run_replay(base, ticks, dry_run_notify=True)
    strict_summary = run_replay(strict, ticks, dry_run_notify=True)
    assert strict_summary.anomalies_detected <= base_summary.anomalies_detected
