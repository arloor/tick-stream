import json
from pathlib import Path

from tick_stream.cli import main


def test_validate_config_success(capsys):
    code = main(["validate-config", "--config", "tests/fixtures/config/valid_watchlist.yml"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["status"] == "ok"
    assert out["symbol_count"] == 2


def test_validate_config_failure(capsys):
    code = main(["validate-config", "--config", "tests/fixtures/config/invalid_watchlist.yml"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["status"] == "error"


def test_replay_dry_run_cli(capsys):
    code = main([
        "replay",
        "--config",
        "tests/fixtures/config/valid_watchlist.yml",
        "--ticks",
        "tests/fixtures/ticks/sample.jsonl",
        "--dry-run-notify",
    ])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["status"] == "completed"
    assert out["notifications_sent"] == 0


def test_health_cli(capsys, tmp_path):
    code = main(["health", "--audit-dir", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["gm_connection_status"] == "unknown"
