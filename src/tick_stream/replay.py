from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json

from .audit import AuditWriter
from .config import RuntimeConfig, load_config, rule_for_symbol
from .detection.engine import DetectionEngine
from .detection.suppression import SuppressionEngine
from .models import AnomalyEvent, EventStatus, QualityStatus
from .notifier import FeishuNotifier
from .utils import to_jsonable


@dataclass(slots=True)
class ReplaySummary:
    status: str = "completed"
    ticks_read: int = 0
    ticks_accepted: int = 0
    anomalies_detected: int = 0
    orderbook_detector_status: str = "unavailable"
    notifications_prepared: int = 0
    notifications_sent: int = 0
    dry_run_notify: bool = True

    def as_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def run_replay(
    config: RuntimeConfig,
    ticks: Iterable[dict[str, Any]],
    dry_run_notify: bool = True,
    notifier: FeishuNotifier | None = None,
) -> ReplaySummary:
    engine = DetectionEngine(config)
    suppression = SuppressionEngine()
    audit = AuditWriter(Path(config.audit["dir"]))
    notifier = notifier or FeishuNotifier(config.feishu)
    summary = ReplaySummary(dry_run_notify=dry_run_notify)

    for raw in ticks:
        summary.ticks_read += 1
        tick, events, feature = engine.process_raw(raw)
        audit.write("tick", tick)
        if tick.quality_status == QualityStatus.ACCEPTED:
            summary.ticks_accepted += 1
        if feature is not None:
            audit.write("feature", feature)
            if feature.feature_availability.get("order_flow_imbalance") == "available":
                summary.orderbook_detector_status = "available"
        reportable: list[AnomalyEvent] = []
        for event in events:
            summary.anomalies_detected += 1
            rule = rule_for_symbol(config, event.symbol)
            decision = suppression.decide(event, rule.cooldown_seconds)
            if decision.suppressed:
                audit.write("suppression", {"event": decision.event, "reason": decision.reason})
            else:
                event.status = EventStatus.NOTIFICATION_PENDING
                reportable.append(event)
            audit.write("anomaly", event)
        if reportable:
            message = notifier.build_message(reportable)
            summary.notifications_prepared += 1
            if not dry_run_notify:
                sent = notifier.send(message)
                if sent.delivery_status.value == "sent":
                    summary.notifications_sent += 1
                audit.write("notification", sent)
            else:
                audit.write("notification", message)
    audit.write(
        "health",
        {
            "gm_connection_status": "replay",
            "feishu_status": "dry_run" if dry_run_notify else "attempted",
            "active_symbol_count": len(config.active_symbols),
            "last_tick_at": None,
            "pending_notification_count": 0,
        },
    )
    return summary


def replay_from_files(config_path: str | Path, ticks_path: str | Path, dry_run_notify: bool = True) -> ReplaySummary:
    config = load_config(config_path)
    return run_replay(config, read_jsonl(ticks_path), dry_run_notify=dry_run_notify)
