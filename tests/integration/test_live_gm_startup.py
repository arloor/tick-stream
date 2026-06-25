from tick_stream.config import load_config
from tick_stream.gm_client import GMClient
from tick_stream.runner import LiveRunner


class MockGM(GMClient):
    def initialize(self):
        self.initialized = True

    def subscribe_active(self):
        self.subscribed_symbols = [s.symbol for s in self.config.active_symbols]
        return self.subscribed_symbols


def test_live_runner_startup_with_mock_gm(tmp_path):
    config = load_config("tests/fixtures/config/valid_watchlist.yml")
    config.audit["dir"] = str(tmp_path)
    gm = MockGM(config)
    status = LiveRunner(config, gm_client=gm).start()
    assert status["status"] == "running"
    assert status["active_symbol_count"] == 1
    assert gm.subscribed_symbols == ["SHSE.600519"]
