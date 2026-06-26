from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .audit import AuditWriter
from .alerts import AlertWindowAggregator, apply_alert_suppression_key, attach_alert_window, split_reportable_events
from .config import RuntimeConfig, load_config, rule_for_symbol
from .detection.engine import DetectionEngine
from .detection.suppression import SuppressionEngine
from .models import AnomalyEvent, EventStatus, QualityStatus
from .notifier import FeishuNotifier
from .tick_store import read_tick_rows
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
    return read_tick_rows(path)


def run_replay(
    config: RuntimeConfig,
    ticks: Iterable[dict[str, Any]],
    dry_run_notify: bool = True,
    notifier: FeishuNotifier | None = None,
) -> ReplaySummary:
    engine = DetectionEngine(config)
    suppression = SuppressionEngine()
    audit = AuditWriter(Path(config.audit["dir"]))
    symbol_names = {item.symbol: item.name for item in config.watchlist if item.name}
    notifier = notifier or FeishuNotifier(config.feishu, symbol_names=symbol_names)
    summary = ReplaySummary(dry_run_notify=dry_run_notify)
    aggregator = AlertWindowAggregator()

    def emit_groups(groups: list[list[AnomalyEvent]]) -> None:
        for group in groups:
            if not group:
                continue
            primary = apply_alert_suppression_key(group)
            rule = rule_for_symbol(config, primary.symbol)
            decision = suppression.decide(primary, rule.cooldown_seconds, rule.opposite_direction_guard_seconds)
            if decision.suppressed:
                for event in group:
                    event.status = EventStatus.SUPPRESSED
                audit.write("suppression", {"events": group, "reason": decision.reason})
                continue
            for event in group:
                event.status = EventStatus.NOTIFICATION_PENDING
            message = notifier.build_message(group)
            summary.notifications_prepared += 1
            if not dry_run_notify:
                sent = notifier.send(message)
                if sent.delivery_status.value == "sent":
                    summary.notifications_sent += 1
                audit.write("notification", sent)
            else:
                audit.write("notification", message)

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
            emit_groups(aggregator.flush_due(feature.event_time))
        reportable: list[AnomalyEvent] = []
        for event in events:
            summary.anomalies_detected += 1
            audit.write("anomaly", event)
        if events and feature is not None:
            rule = rule_for_symbol(config, events[0].symbol)
            reportable, not_reportable = split_reportable_events(events, feature, rule)
            for event, reason in not_reportable:
                audit.write("suppression", {"event": event, "reason": reason})
        if reportable:
            rule = rule_for_symbol(config, reportable[0].symbol)
            attach_alert_window(reportable, rule.alert_aggregation_window_seconds)
            emit_groups(aggregator.add(reportable, rule.alert_aggregation_window_seconds))
    emit_groups(aggregator.flush_all())
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
