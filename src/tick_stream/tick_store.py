from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from .utils import parse_dt, to_jsonable


@dataclass(slots=True)
class SymbolPartitionSummary:
    path: str
    tick_count: int = 0
    first_event_time: str | None = None
    last_event_time: str | None = None


@dataclass(slots=True)
class DatePartitionSummary:
    trading_date: str
    tick_count: int = 0
    symbol_count: int = 0
    symbols: dict[str, SymbolPartitionSummary] = field(default_factory=dict)
    merged_path: str | None = None
    manifest_path: str | None = None


@dataclass(slots=True)
class TickPartitionSummary:
    status: str = "completed"
    ticks_read: int = 0
    ticks_written: int = 0
    ticks_skipped: int = 0
    dates: dict[str, DatePartitionSummary] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def read_tick_rows(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.is_dir():
        rows: list[dict[str, Any]] = []
        for item in sorted(source.rglob("*.jsonl")):
            if item.name == "manifest.jsonl":
                continue
            rows.extend(_read_jsonl_file(item))
        rows.sort(key=lambda row: (_event_sort_key(row), str(row.get("symbol") or "")))
        return rows
    return _read_jsonl_file(source)


def partition_tick_file(
    input_path: str | Path,
    out_dir: str | Path,
    merged_dir: str | Path | None = None,
    dates: set[str] | None = None,
) -> TickPartitionSummary:
    summary = TickPartitionSummary()
    output_root = Path(out_dir)
    merged_root = Path(merged_dir) if merged_dir else None
    handles: dict[tuple[str, str], Any] = {}
    date_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    try:
        for row in _iter_jsonl_file(input_path):
            summary.ticks_read += 1
            trading_date = _trading_date(row)
            symbol = str(row.get("symbol") or "").strip()
            if not trading_date or not symbol or (dates and trading_date not in dates):
                summary.ticks_skipped += 1
                continue
            date_summary = summary.dates.setdefault(trading_date, DatePartitionSummary(trading_date=trading_date))
            symbol_summary = date_summary.symbols.get(symbol)
            if symbol_summary is None:
                partition_path = output_root / f"trading_date={trading_date}" / f"{_safe_symbol_filename(symbol)}.jsonl"
                partition_path.parent.mkdir(parents=True, exist_ok=True)
                symbol_summary = SymbolPartitionSummary(path=str(partition_path))
                date_summary.symbols[symbol] = symbol_summary
            key = (trading_date, symbol)
            if key not in handles:
                handles[key] = open(symbol_summary.path, "w", encoding="utf-8")
            line = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            handles[key].write(line + "\n")
            event_text = _event_time_text(row)
            event_key = _event_sort_key(row)
            symbol_summary.tick_count += 1
            if event_text and (symbol_summary.first_event_time is None or event_key < _sort_key_from_text(symbol_summary.first_event_time)):
                symbol_summary.first_event_time = event_text
            if event_text and (symbol_summary.last_event_time is None or event_key > _sort_key_from_text(symbol_summary.last_event_time)):
                symbol_summary.last_event_time = event_text
            date_summary.tick_count += 1
            summary.ticks_written += 1
            if merged_root:
                date_rows[trading_date].append(row)
    finally:
        for handle in handles.values():
            handle.close()

    for trading_date, date_summary in summary.dates.items():
        date_summary.symbol_count = len(date_summary.symbols)
        if merged_root:
            merged_root.mkdir(parents=True, exist_ok=True)
            merged_path = merged_root / f"watchlist_{trading_date}.jsonl"
            rows = sorted(date_rows.get(trading_date, []), key=lambda row: (_event_sort_key(row), str(row.get("symbol") or "")))
            with merged_path.open("w", encoding="utf-8") as out:
                for row in rows:
                    out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            date_summary.merged_path = str(merged_path)
        manifest_path = output_root / f"trading_date={trading_date}" / "manifest.json"
        date_summary.manifest_path = str(manifest_path)
        manifest_path.write_text(json.dumps(to_jsonable(date_summary), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return summary


def _read_jsonl_file(path: str | Path) -> list[dict[str, Any]]:
    return list(_iter_jsonl_file(path))


def _iter_jsonl_file(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as src:
        for line in src:
            if line.strip():
                yield json.loads(line)


def _event_time_text(row: dict[str, Any]) -> str | None:
    value = row.get("event_time") or row.get("created_at") or row.get("time")
    return str(value) if value is not None else None


def _event_sort_key(row: dict[str, Any]) -> str:
    dt = parse_dt(row.get("event_time") or row.get("created_at") or row.get("time"))
    return dt.isoformat() if dt else ""


def _sort_key_from_text(value: str) -> str:
    dt = parse_dt(value)
    return dt.isoformat() if dt else value


def _trading_date(row: dict[str, Any]) -> str | None:
    dt = parse_dt(row.get("event_time") or row.get("created_at") or row.get("time"))
    return dt.date().isoformat() if dt else None


def _safe_symbol_filename(symbol: str) -> str:
    return symbol.replace("/", "_").replace("\\", "_")
