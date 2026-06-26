from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class QualityStatus(StrEnum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    OUT_OF_ORDER = "out_of_order"
    MALFORMED = "malformed"
    STALE = "stale"
    IGNORED = "ignored"


class Severity(StrEnum):
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class AnomalyType(StrEnum):
    PRICE_JUMP = "price_jump"
    MOMENTUM_SPIKE = "momentum_spike"
    ORDERBOOK_LIQUIDITY = "orderbook_liquidity"


class EventStatus(StrEnum):
    DETECTED = "detected"
    SUPPRESSED = "suppressed"
    NOTIFICATION_PENDING = "notification_pending"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"
    RESOLVED = "resolved"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    ABANDONED = "abandoned"
    SUPPRESSED = "suppressed"


@dataclass(slots=True)
class WatchlistSymbol:
    symbol: str
    name: str | None = None
    market: str | None = None
    active: bool = True
    rule_profile: str = "default"
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SeverityThreshold:
    price_return_pct: float
    momentum_z: float
    orderbook_cancel_ratio: float
    orderbook_imbalance_ratio: float


@dataclass(slots=True)
class AnomalyRuleSet:
    name: str
    price_window_seconds: int = 30
    price_return_threshold_pct: float = 1.5
    momentum_impulse_seconds: int = 10
    momentum_baseline_seconds: int = 180
    momentum_z_threshold: float = 3.0
    momentum_min_return_pct: float = 0.3
    momentum_min_nonzero_baseline_samples: int = 5
    momentum_zero_mad_min_return_pct: float = 0.8
    momentum_notify_min_return_pct: float = 0.8
    momentum_notify_volume_burst_ratio: float = 2.0
    momentum_notify_orderbook_min_volume_burst_ratio: float = 1.0
    momentum_notify_orderbook_imbalance_ratio: float = 0.90
    momentum_notify_cancel_add_ratio: float = 0.60
    alert_aggregation_window_seconds: int = 30
    orderbook_window_seconds: int = 30
    orderbook_min_consecutive_ticks: int = 2
    orderbook_cancel_ratio_threshold: float = 0.35
    orderbook_imbalance_ratio_threshold: float = 0.70
    orderbook_standalone_min_severity: str = "high"
    orderbook_notify_min_return_pct: float = 0.4
    orderbook_notify_volume_burst_ratio: float = 2.0
    min_ticks_short_window: int = 3
    min_ticks_baseline_window: int = 20
    cooldown_seconds: int = 180
    severity_thresholds: dict[str, SeverityThreshold] = field(default_factory=dict)
    ignored_sessions: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class RuntimeConfig:
    gm: dict[str, Any]
    feishu: dict[str, Any]
    watchlist: list[WatchlistSymbol]
    rules: dict[str, AnomalyRuleSet]
    audit: dict[str, Any]

    @property
    def active_symbols(self) -> list[WatchlistSymbol]:
        return [item for item in self.watchlist if item.active]

    def symbol_map(self) -> dict[str, WatchlistSymbol]:
        return {item.symbol: item for item in self.watchlist}


@dataclass(slots=True)
class OrderBookLevel:
    price: float
    quantity: float


@dataclass(slots=True)
class OrderBookSnapshot:
    bid_levels: list[OrderBookLevel] = field(default_factory=list)
    ask_levels: list[OrderBookLevel] = field(default_factory=list)
    total_bid_quantity: float = 0.0
    total_ask_quantity: float = 0.0
    bid_added_quantity: float = 0.0
    bid_cancelled_quantity: float = 0.0
    ask_added_quantity: float = 0.0
    ask_cancelled_quantity: float = 0.0
    imbalance_ratio: float = 0.0
    depth_available: bool = False


@dataclass(slots=True)
class TickRecord:
    symbol: str
    event_time: datetime | None
    received_time: datetime
    last_price: float | None
    volume: float | None = None
    turnover: float | None = None
    order_book: OrderBookSnapshot | None = None
    source_sequence: str | None = None
    quality_status: QualityStatus = QualityStatus.ACCEPTED
    quality_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.quality_status == QualityStatus.ACCEPTED


@dataclass(slots=True)
class FeatureSnapshot:
    symbol: str
    event_time: datetime
    price_return_short_pct: float = 0.0
    momentum_z: float = 0.0
    realized_volatility_ratio: float = 0.0
    volume_burst_ratio: float = 0.0
    order_flow_imbalance: float = 0.0
    queue_imbalance_ratio: float = 0.0
    spread_ratio: float = 0.0
    depth_collapse_ratio: float = 0.0
    cancel_add_ratio: float = 0.0
    relative_strength_residual: float | None = None
    feature_availability: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AnomalyEvent:
    event_id: str
    symbol: str
    anomaly_type: AnomalyType
    direction: Direction
    severity: Severity
    trigger_time: datetime
    trigger_price: float
    measurement: dict[str, Any]
    reason: str
    status: EventStatus = EventStatus.DETECTED
    suppression_key: str | None = None
    created_at: datetime | None = None
    feature_snapshot_ref: str | None = None


@dataclass(slots=True)
class NotificationMessage:
    notification_id: str
    event_ids: list[str]
    receive_id_type: str
    receive_id: str
    msg_type: str
    content: dict[str, Any]
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    feishu_message_id: str | None = None
    failure_code: str | int | None = None
    failure_reason: str | None = None


@dataclass(slots=True)
class FeishuTokenCache:
    tenant_access_token: str | None = None
    expires_at: datetime | None = None
    refresh_margin_seconds: int = 300
    last_refresh_status: str | None = None


@dataclass(slots=True)
class MonitoringHealthState:
    started_at: datetime
    last_tick_at: datetime | None = None
    last_anomaly_at: datetime | None = None
    last_notification_at: datetime | None = None
    gm_connection_status: str = "unknown"
    feishu_status: str = "unknown"
    active_symbol_count: int = 0
    pending_notification_count: int = 0
    error_summary: list[str] = field(default_factory=list)
