from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from .audit import AuditWriter
from .config import RuntimeConfig
from .detection.engine import DetectionEngine
from .detection.suppression import SuppressionEngine
from .gm_client import GMClient
from .health import initial_health
from .notifier import FeishuNotifier
from .utils import to_jsonable


class LiveRunner:
    def __init__(self, config: RuntimeConfig, gm_client: GMClient | None = None, notifier: FeishuNotifier | None = None) -> None:
        self.config = config
        self.audit = AuditWriter(Path(config.audit["dir"]))
        self.engine = DetectionEngine(config)
        self.suppression = SuppressionEngine()
        self.notifier = notifier or FeishuNotifier(config.feishu)
        self.gm_client = gm_client or GMClient(config, tick_handler=self.handle_tick)
        self.health = initial_health(active_symbol_count=len(config.active_symbols))

    def start(self) -> dict[str, Any]:
        self.gm_client.initialize()
        symbols = self.gm_client.subscribe_active()
        self.health.gm_connection_status = "healthy"
        self.health.feishu_status = "healthy"
        self.health.active_symbol_count = len(symbols)
        self.audit.write("health", self.health)
        return {
            "status": "running",
            "active_symbol_count": len(symbols),
            "gm_connection_status": self.health.gm_connection_status,
            "feishu_status": self.health.feishu_status,
        }

    def run_forever(self) -> None:
        from gm.api import run as gm_run  # type: ignore
        from gm.enum import MODE_LIVE  # type: ignore

        from . import live_strategy

        live_strategy.configure(self)
        original_argv = sys.argv[:]
        try:
            # gm.api.run parses sys.argv internally; keep this CLI's arguments
            # from being interpreted as GM SDK options.
            sys.argv = [original_argv[0]]
            gm_run(
                strategy_id=self.config.gm["strategy_id"],
                filename=str(Path(live_strategy.__file__).resolve()),
                mode=MODE_LIVE,
                token=self.config.gm["token"],
                serv_addr=self.config.gm["serv_addr"],
            )
        finally:
            sys.argv = original_argv

    def handle_tick(self, raw: dict[str, Any]) -> None:
        tick, events, feature = self.engine.process_raw(raw)
        self.audit.write("tick", tick)
        if feature:
            self.audit.write("feature", feature)
        for event in events:
            decision = self.suppression.decide(event)
            if decision.suppressed:
                self.audit.write("suppression", decision)
                continue
            message = self.notifier.build_message([event])
            sent = self.notifier.send(message)
            self.audit.write("anomaly", event)
            self.audit.write("notification", sent)

    def health_dict(self) -> dict[str, Any]:
        return to_jsonable(self.health)
