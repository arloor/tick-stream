from __future__ import annotations

from .runner import LiveRunner


_runner: LiveRunner | None = None


def configure(runner: LiveRunner) -> None:
    global _runner
    _runner = runner


def init(context) -> None:  # noqa: ANN001 - GM SDK callback signature
    if _runner is None:
        raise RuntimeError("live strategy runner is not configured")
    symbols = _runner.gm_client.subscribe_active()
    _runner.health.gm_connection_status = "healthy"
    _runner.health.feishu_status = "healthy"
    _runner.health.active_symbol_count = len(symbols)
    _runner.audit.write("health", _runner.health)


def on_tick(context, tick) -> None:  # noqa: ANN001 - GM SDK callback signature
    if _runner is None:
        raise RuntimeError("live strategy runner is not configured")
    _runner.handle_tick(_runner.gm_client.adapt_tick(tick))
