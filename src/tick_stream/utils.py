from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
import json
from typing import Any


SENSITIVE_KEYS = {
    "token",
    "tenant_access_token",
    "app_secret",
    "receive_id",
    "authorization",
    "password",
    "secret",
}


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_time(value: str) -> time:
    return time.fromisoformat(value)


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if result != result:
        return None
    return result


def pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end - start) / start * 100.0


def stable_json(data: Any) -> str:
    return json.dumps(to_jsonable(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def to_jsonable(data: Any) -> Any:
    if is_dataclass(data):
        return to_jsonable(asdict(data))
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, time):
        return data.isoformat()
    if isinstance(data, Mapping):
        return {str(k): to_jsonable(v) for k, v in data.items()}
    if isinstance(data, (str, int, float, bool)) or data is None:
        return data
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    if isinstance(data, Iterable):
        return [to_jsonable(v) for v in data]
    return str(data)


def redact(data: Any) -> Any:
    if is_dataclass(data):
        data = asdict(data)
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            key_text = str(key).lower()
            if key_text in SENSITIVE_KEYS or any(s in key_text for s in ("secret", "token")):
                redacted[str(key)] = "***REDACTED***"
            else:
                redacted[str(key)] = redact(value)
        return redacted
    if isinstance(data, list):
        return [redact(v) for v in data]
    return to_jsonable(data)
