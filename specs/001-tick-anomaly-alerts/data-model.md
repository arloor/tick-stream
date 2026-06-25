# Data Model: Tick Anomaly Alerts

## WatchlistSymbol

Represents a stock selected for monitoring.

Fields:

- `symbol`: GM symbol, required, unique within the active watchlist.
- `name`: display name, optional until resolved from symbol metadata.
- `market`: exchange or market segment.
- `active`: whether the symbol is currently monitored.
- `rule_profile`: optional profile name for per-symbol thresholds.
- `tags`: optional labels such as sector, strategy bucket, or liquidity group.

Validation:

- `symbol` must be non-empty.
- Inactive symbols must not be subscribed for live monitoring.
- Per-symbol rule profile must reference an existing `AnomalyRuleSet`.

Relationships:

- Has many `TickRecord`.
- Has many `AnomalyEvent`.

## TickRecord

Represents one accepted market data update after normalization.

Fields:

- `symbol`: related watchlist symbol.
- `event_time`: market event timestamp.
- `received_time`: local processing timestamp.
- `last_price`: latest traded or quoted price, positive decimal.
- `volume`: optional tick volume.
- `turnover`: optional tick turnover.
- `order_book`: optional normalized `OrderBookSnapshot`.
- `source_sequence`: optional source sequence when available.
- `quality_status`: `accepted`, `duplicate`, `out_of_order`, `malformed`, `stale`, or `ignored`.
- `quality_reason`: human-readable reason when not accepted.

Validation:

- Accepted ticks require `symbol`, `event_time`, and `last_price > 0`.
- Accepted tick `event_time` must be newer than the latest accepted tick for the same symbol.
- Duplicate tick identity must not update detector windows.
- Missing order book data must not invalidate otherwise valid price and momentum detection.

Relationships:

- Belongs to one `WatchlistSymbol`.
- May trigger zero or more `AnomalyEvent`.

## OrderBookSnapshot

Represents bid/ask depth carried by a tick.

Fields:

- `bid_levels`: ordered list of bid price and quantity levels.
- `ask_levels`: ordered list of ask price and quantity levels.
- `total_bid_quantity`: total available bid quantity across configured levels.
- `total_ask_quantity`: total available ask quantity across configured levels.
- `bid_added_quantity`: quantity added to bid levels versus the previous accepted snapshot.
- `bid_cancelled_quantity`: quantity removed from bid levels versus the previous accepted snapshot.
- `ask_added_quantity`: quantity added to ask levels versus the previous accepted snapshot.
- `ask_cancelled_quantity`: quantity removed from ask levels versus the previous accepted snapshot.
- `imbalance_ratio`: absolute side imbalance between bid and ask depth.
- `depth_available`: whether sufficient bid/ask fields were present.

Validation:

- Quantities must be non-negative.
- Imbalance ratio must be between 0 and 1.
- Added/cancelled quantities are computed only when a previous accepted snapshot exists.

## AnomalyRuleSet

Defines detection behavior for one rule profile.

Fields:

- `name`: unique profile name.
- `price_window_seconds`: default 30.
- `price_return_threshold_pct`: default 1.5.
- `momentum_impulse_seconds`: default 10.
- `momentum_baseline_seconds`: default 180.
- `momentum_z_threshold`: default 3.0.
- `orderbook_window_seconds`: default 30.
- `orderbook_min_consecutive_ticks`: default 2.
- `orderbook_cancel_ratio_threshold`: default 0.35.
- `orderbook_imbalance_ratio_threshold`: default 0.70.
- `orderbook_standalone_min_severity`: default `high`.
- `min_ticks_short_window`: default 3.
- `min_ticks_baseline_window`: default 20.
- `severity_thresholds`: mapping for `warning`, `high`, and `critical`.
- `cooldown_seconds`: default 180.
- `ignored_sessions`: optional market time windows where detection is suppressed.

Validation:

- Window durations must be positive.
- Baseline window must be longer than impulse window.
- Order book standalone severity must be `warning`, `high`, or `critical`.
- Severity thresholds must be monotonic from `warning` to `critical`.
- Cooldown must be non-negative.

Relationships:

- Applied by one or more `WatchlistSymbol`.
- Produces `AnomalyEvent` through the detection engine.

## AnomalyEvent

Represents a detected abnormal market movement.

Fields:

- `event_id`: unique event identifier.
- `symbol`: related watchlist symbol.
- `anomaly_type`: `price_jump`, `momentum_spike`, or `orderbook_liquidity`.
- `direction`: `up` or `down`.
- `severity`: `warning`, `high`, or `critical`.
- `trigger_time`: timestamp of the triggering tick.
- `trigger_price`: latest accepted price at trigger time.
- `measurement`: structured values used by the detector, such as return percentage, z-score, window duration, and baseline value.
- `reason`: short human-readable trigger explanation.
- `status`: `detected`, `suppressed`, `notification_pending`, `notification_sent`, `notification_failed`, or `resolved`.
- `suppression_key`: `(symbol, anomaly_type, direction)`.
- `created_at`: local creation timestamp.

Validation:

- Measurement must include the detector-specific trigger value, such as price return, momentum z-score, cancellation ratio, added quantity, cancelled quantity, or imbalance ratio.
- Suppressed events must reference the active cooldown decision.
- Events eligible for notification must include all required notification fields.

State transitions:

```text
detected
├── suppressed
└── notification_pending
    ├── notification_sent
    └── notification_failed
        └── notification_pending
```

## NotificationMessage

Represents a Feishu alert generated from one or more anomaly events.

Fields:

- `notification_id`: unique notification identifier.
- `event_ids`: one or more related anomaly event IDs.
- `receive_id_type`: `chat_id`, `open_id`, `user_id`, `union_id`, or `email`, resolved from environment.
- `receive_id`: recipient identifier resolved from environment.
- `msg_type`: `post` for v1.
- `content`: structured Feishu message content before JSON serialization.
- `delivery_status`: `pending`, `sent`, `failed`, or `abandoned`.
- `attempt_count`: integer retry count.
- `last_attempt_at`: optional timestamp.
- `feishu_message_id`: returned message ID when sent.
- `failure_code`: optional Feishu or network error code.
- `failure_reason`: optional detail for operator review.

Validation:

- `receive_id_type`, `receive_id`, `msg_type`, and `content` are required before send.
- Feishu app ID, app secret, recipient type, recipient ID, retry attempts, retry backoff, and token refresh margin must be resolved from environment variables rather than source-controlled config values.
- Retry attempts must not exceed configured max attempts.
- Sent notifications require `feishu_message_id` when Feishu returns one.

## FeishuTokenCache

Represents cached tenant token state.

Fields:

- `tenant_access_token`: token value held only in memory or local secret cache.
- `expires_at`: local timestamp when the token should no longer be used.
- `refresh_margin_seconds`: time before expiry to proactively refresh, default 300.
- `last_refresh_status`: `success` or `failed`.

Validation:

- Token must not be written to source-controlled files.
- Token is invalid if current time is later than `expires_at - refresh_margin_seconds`.

## AuditRecord

Represents one append-only operational record.

Fields:

- `record_type`: `tick`, `anomaly`, `suppression`, `notification`, or `health`.
- `record_time`: local write timestamp.
- `payload`: type-specific JSON object.

Validation:

- Every record must be valid JSON on one line.
- Payload must include enough identifiers to trace symbol, event, or notification where applicable.

## MonitoringHealthState

Represents the current operating condition.

Fields:

- `started_at`: process start time.
- `last_tick_at`: latest accepted tick time.
- `last_anomaly_at`: latest anomaly event time.
- `last_notification_at`: latest notification attempt time.
- `gm_connection_status`: `unknown`, `healthy`, `degraded`, or `down`.
- `feishu_status`: `unknown`, `healthy`, `degraded`, or `down`.
- `active_symbol_count`: number of actively monitored symbols.
- `pending_notification_count`: current pending notification count.
- `error_summary`: latest notable errors.

Validation:

- Health output must not include secret values.
- Degraded/down status must include an operator-readable reason.
