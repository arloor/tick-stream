from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from .models import RuntimeConfig


class GMClient:
    def __init__(self, config: RuntimeConfig, tick_handler: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.config = config
        self.tick_handler = tick_handler
        self.subscribed_symbols: list[str] = []
        self.initialized = False

    def initialize(self) -> None:
        try:
            from gm.api import set_serv_addr, set_token  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"GM SDK initialization failed: {exc}") from exc
        set_token(self.config.gm["token"])
        set_serv_addr(self.config.gm["serv_addr"])
        strategy_setter = _find_strategy_setter()
        if strategy_setter is not None:
            try:
                strategy_setter(self.config.gm["strategy_id"])
            except Exception:
                pass
        self.initialized = True

    def subscribe_active(self) -> list[str]:
        self.subscribed_symbols = [item.symbol for item in self.config.active_symbols]
        try:
            from gm.api import subscribe  # type: ignore

            if self.subscribed_symbols:
                subscribe(symbols=",".join(self.subscribed_symbols), frequency="tick", count=1)
        except Exception as exc:
            raise RuntimeError(f"GM subscribe failed: {exc}") from exc
        return self.subscribed_symbols

    def adapt_tick(self, tick: Any) -> dict[str, Any]:
        if isinstance(tick, Mapping):
            return dict(tick.items())
        if hasattr(tick, "items"):
            try:
                return dict(tick.items())
            except Exception:
                pass
        data = {}
        for name in dir(tick):
            if name.startswith("_"):
                continue
            value = getattr(tick, name)
            if not callable(value):
                data[name] = value
        return data


def _find_strategy_setter() -> Callable[[str], Any] | None:
    candidates = (
        ("gm.csdk", "py_gmi_set_strategy_id"),
        ("gm.api.basic", "py_gmi_set_strategy_id"),
    )
    for module_name, attr_name in candidates:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            setter = getattr(module, attr_name, None)
        except Exception:
            continue
        if callable(setter):
            return setter
    return None
