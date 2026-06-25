from tick_stream.config import load_config
from tick_stream.replay import read_jsonl, run_replay


def test_success_criteria_fixture_detects_labeled_anomalies(tmp_path):
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    config.audit["dir"] = str(tmp_path)
    summary = run_replay(config, read_jsonl("tests/fixtures/ticks/labeled_anomalies.jsonl"), dry_run_notify=True)
    assert summary.anomalies_detected >= 1
    assert summary.notifications_prepared >= 1
