from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audit import latest_record
from .models import MonitoringHealthState
from .utils import redact, to_jsonable


def initial_health(active_symbol_count: int = 0) -> MonitoringHealthState:
    return MonitoringHealthState(
        started_at=datetime.now(timezone.utc),
        active_symbol_count=active_symbol_count,
    )


def health_to_dict(state: MonitoringHealthState) -> dict[str, Any]:
    return redact(to_jsonable(state))


def read_health(audit_dir: str | Path) -> dict[str, Any]:
    record = latest_record(audit_dir, "health")
    if not record:
        return {
            "gm_connection_status": "unknown",
            "feishu_status": "unknown",
            "active_symbol_count": 0,
            "last_tick_at": None,
            "pending_notification_count": 0,
        }
    payload = record.get("payload", {})
    return {
        "gm_connection_status": payload.get("gm_connection_status", "unknown"),
        "feishu_status": payload.get("feishu_status", "unknown"),
        "active_symbol_count": payload.get("active_symbol_count", 0),
        "last_tick_at": payload.get("last_tick_at"),
        "pending_notification_count": payload.get("pending_notification_count", 0),
    }
