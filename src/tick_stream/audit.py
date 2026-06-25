from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .utils import redact, stable_json


@dataclass(slots=True)
class AuditWriter:
    audit_dir: Path

    def __post_init__(self) -> None:
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def write(self, record_type: str, payload: Any) -> None:
        record = {
            "record_type": record_type,
            "record_time": datetime.now(timezone.utc).isoformat(),
            "payload": redact(payload),
        }
        path = self.audit_dir / f"{record_type}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(stable_json(record) + "\n")


def latest_record(audit_dir: str | Path, record_type: str) -> dict[str, Any] | None:
    path = Path(audit_dir) / f"{record_type}.jsonl"
    if not path.exists():
        return None
    last = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            import json

            last = json.loads(line)
    return last
