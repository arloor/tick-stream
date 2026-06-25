from pathlib import Path

from tick_stream.config import load_config
from tick_stream.replay import read_jsonl, run_replay


def test_replay_mixed_fixture_produces_anomalies(tmp_path):
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    config.audit["dir"] = str(tmp_path)
    summary = run_replay(config, read_jsonl("tests/fixtures/ticks/sample.jsonl"), dry_run_notify=True)
    assert summary.ticks_read == 12
    assert summary.ticks_accepted >= 8
    assert summary.anomalies_detected >= 1
    assert (tmp_path / "feature.jsonl").exists()
    assert (tmp_path / "anomaly.jsonl").exists()
