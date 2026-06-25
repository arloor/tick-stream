from pathlib import Path

import pytest

from tick_stream.config import ConfigError, load_config


FIXTURES = Path("tests/fixtures/config")


def test_valid_config_loads():
    config = load_config(FIXTURES / "valid_watchlist.yml")
    assert len(config.watchlist) == 2
    assert config.active_symbols[0].symbol == "SHSE.600519"
    assert "default" in config.rules


def test_invalid_config_fails_without_exposing_secret():
    with pytest.raises(ConfigError) as exc:
        load_config(FIXTURES / "invalid_watchlist.yml")
    assert "invalid config" in str(exc.value)
    assert "secret-test" not in str(exc.value)
