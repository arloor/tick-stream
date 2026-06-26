from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import yaml

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - fallback for minimal environments
    Draft202012Validator = None

from .models import AnomalyRuleSet, RuntimeConfig, SeverityThreshold, WatchlistSymbol
from .utils import redact


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "specs/001-tick-anomaly-alerts/contracts/config.schema.json"


class ConfigError(ValueError):
    pass


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_raw_config(raw: dict[str, Any]) -> None:
    if Draft202012Validator is None:
        for key in ("gm", "feishu", "watchlist", "rules", "audit"):
            if key not in raw:
                raise ConfigError(f"missing required config section: {key}")
        return
    validator = Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ConfigError(f"invalid config at {path}: {first.message}; config={redact(raw)}")


def _thresholds(raw: dict[str, Any] | None) -> dict[str, SeverityThreshold]:
    raw = raw or {}
    result: dict[str, SeverityThreshold] = {}
    defaults = {
        "warning": (1.5, 3.0, 0.25, 0.60),
        "high": (2.5, 4.0, 0.35, 0.70),
        "critical": (3.5, 5.0, 0.50, 0.85),
    }
    for name, default in defaults.items():
        item = raw.get(name, {})
        result[name] = SeverityThreshold(
            price_return_pct=float(item.get("price_return_pct", default[0])),
            momentum_z=float(item.get("momentum_z", default[1])),
            orderbook_cancel_ratio=float(item.get("orderbook_cancel_ratio", default[2])),
            orderbook_imbalance_ratio=float(item.get("orderbook_imbalance_ratio", default[3])),
        )
    return result


def parse_config(raw: dict[str, Any]) -> RuntimeConfig:
    validate_raw_config(raw)
    watchlist = [
        WatchlistSymbol(
            symbol=item["symbol"],
            name=item.get("name"),
            market=item.get("market"),
            active=bool(item.get("active", True)),
            rule_profile=item.get("rule_profile", "default"),
            tags=list(item.get("tags", [])),
        )
        for item in raw.get("watchlist", [])
    ]
    rules: dict[str, AnomalyRuleSet] = {}
    for name, item in raw["rules"].items():
        rules[name] = AnomalyRuleSet(
            name=name,
            price_window_seconds=int(item.get("price_window_seconds", 30)),
            price_return_threshold_pct=float(item.get("price_return_threshold_pct", 1.5)),
            momentum_impulse_seconds=int(item.get("momentum_impulse_seconds", 10)),
            momentum_baseline_seconds=int(item.get("momentum_baseline_seconds", 180)),
            momentum_z_threshold=float(item.get("momentum_z_threshold", 3.0)),
            momentum_min_return_pct=float(item.get("momentum_min_return_pct", 0.3)),
            momentum_min_nonzero_baseline_samples=int(item.get("momentum_min_nonzero_baseline_samples", 5)),
            momentum_zero_mad_min_return_pct=float(item.get("momentum_zero_mad_min_return_pct", 0.8)),
            momentum_notify_min_return_pct=float(item.get("momentum_notify_min_return_pct", 0.8)),
            momentum_notify_volume_burst_ratio=float(item.get("momentum_notify_volume_burst_ratio", 2.0)),
            momentum_notify_orderbook_min_volume_burst_ratio=float(item.get("momentum_notify_orderbook_min_volume_burst_ratio", 1.0)),
            momentum_notify_orderbook_imbalance_ratio=float(item.get("momentum_notify_orderbook_imbalance_ratio", 0.90)),
            momentum_notify_cancel_add_ratio=float(item.get("momentum_notify_cancel_add_ratio", 0.60)),
            alert_aggregation_window_seconds=int(item.get("alert_aggregation_window_seconds", 30)),
            orderbook_window_seconds=int(item.get("orderbook_window_seconds", 30)),
            orderbook_min_consecutive_ticks=int(item.get("orderbook_min_consecutive_ticks", 2)),
            orderbook_cancel_ratio_threshold=float(item.get("orderbook_cancel_ratio_threshold", 0.35)),
            orderbook_imbalance_ratio_threshold=float(item.get("orderbook_imbalance_ratio_threshold", 0.70)),
            orderbook_standalone_min_severity=item.get("orderbook_standalone_min_severity", "high"),
            orderbook_notify_min_return_pct=float(item.get("orderbook_notify_min_return_pct", 0.4)),
            orderbook_notify_volume_burst_ratio=float(item.get("orderbook_notify_volume_burst_ratio", 2.0)),
            min_ticks_short_window=int(item.get("min_ticks_short_window", 3)),
            min_ticks_baseline_window=int(item.get("min_ticks_baseline_window", 20)),
            cooldown_seconds=int(item.get("cooldown_seconds", 180)),
            severity_thresholds=_thresholds(item.get("severity_thresholds")),
            ignored_sessions=list(item.get("ignored_sessions", [])),
        )
    for item in watchlist:
        if item.rule_profile not in rules:
            raise ConfigError(f"unknown rule_profile for {item.symbol}: {item.rule_profile}")
    return RuntimeConfig(
        gm=dict(raw["gm"]),
        feishu=dict(raw["feishu"]),
        watchlist=watchlist,
        rules=rules,
        audit=dict(raw["audit"]),
    )


def load_config(path: str | Path) -> RuntimeConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid yaml in {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a mapping")
    return parse_config(raw)


def rule_for_symbol(config: RuntimeConfig, symbol: str) -> AnomalyRuleSet:
    watch = config.symbol_map().get(symbol)
    profile = watch.rule_profile if watch else "default"
    return config.rules[profile]
