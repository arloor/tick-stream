from tick_stream.config import load_config


def test_active_symbols_and_rule_profile():
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    assert [s.symbol for s in config.active_symbols] == ["SHSE.600519"]
    assert config.symbol_map()["SHSE.600519"].rule_profile == "default"
