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
- Produces zero or one `FeatureSnapshot`.
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

## FeatureSnapshot

Represents the interpretable anomaly feature values computed from one accepted tick and recent rolling windows.

Fields:

- `symbol`: related watchlist symbol.
- `event_time`: timestamp of the source tick.
- `price_return_short_pct`: short-window return.
- `momentum_z`: robust z-score of short-term momentum against baseline.
- `realized_volatility_ratio`: short-window realized volatility divided by intraday baseline.
- `volume_burst_ratio`: short-window volume or turnover divided by baseline.
- `order_flow_imbalance`: net order book pressure when depth is available.
- `queue_imbalance_ratio`: bid-side versus ask-side displayed depth imbalance.
- `spread_ratio`: current spread relative to recent baseline or tick size.
- `depth_collapse_ratio`: current top-depth reduction versus recent baseline.
- `cancel_add_ratio`: cancellation quantity divided by addition quantity over the configured window.
- `relative_strength_residual`: optional symbol move after subtracting index, sector, or peer baseline.
- `feature_availability`: map of feature name to `available`, `missing_data`, or `not_configured`.

Validation:

- Feature values must be computed only from accepted ticks.
- Missing optional inputs must set feature availability rather than failing the whole snapshot.
- Feature snapshots must be safe for audit logs and must not include credentials or raw configuration values.

Relationships:

- Belongs to one `TickRecord`.
- Supplies measurements for zero or more `AnomalyEvent`.

## AnomalyRuleSet

Defines detection behavior for one rule profile.

Fields:

- `name`: unique profile name.
- `price_window_seconds`: default 30.
- `price_return_threshold_pct`: default 1.5.
- `momentum_impulse_seconds`: default 10.
- `momentum_baseline_seconds`: default 180.
- `momentum_z_threshold`: default 3.0.
- `momentum_min_return_pct`: minimum actual impulse return required before momentum can trigger.
- `momentum_min_nonzero_baseline_samples`: minimum non-zero baseline velocity samples required before trusting z-score in low-volatility windows.
- `momentum_zero_mad_min_return_pct`: stricter impulse return required when the baseline median absolute deviation is zero.
- `momentum_notify_min_return_pct`: actual impulse return that makes a momentum event reportable without other confirmation.
- `momentum_notify_volume_burst_ratio`: volume/turnover burst that confirms a momentum event for notification.
- `momentum_notify_orderbook_min_volume_burst_ratio`: minimum volume/turnover activity required when order book pressure is used to confirm a momentum event.
- `momentum_notify_orderbook_imbalance_ratio`: order book imbalance that can confirm a momentum event only when minimum volume/turnover activity is also present.
- `momentum_notify_cancel_add_ratio`: cancellation/addition pressure that can confirm a momentum event only when minimum volume/turnover activity is also present.
- `alert_aggregation_window_seconds`: time window for grouping reportable events of the same symbol into one notification.
- `orderbook_window_seconds`: default 30.
- `orderbook_min_consecutive_ticks`: default 2.
- `orderbook_cancel_ratio_threshold`: default 0.35.
- `orderbook_imbalance_ratio_threshold`: default 0.70.
- `orderbook_standalone_min_severity`: default `high`.
- `orderbook_notify_min_return_pct`: minimum short-window absolute price return required before a standalone order book event is reportable.
- `orderbook_notify_volume_burst_ratio`: minimum volume/turnover burst required before a standalone order book event is reportable.
- `min_ticks_short_window`: default 3.
- `min_ticks_baseline_window`: default 20.
- `severity_thresholds`: mapping for `warning`, `high`, and `critical`.
- `cooldown_seconds`: default 180.
- `ignored_sessions`: optional market time windows where detection is suppressed.

Validation:

- Window durations must be positive.
- Baseline window must be longer than impulse window.
- Momentum reportability thresholds and order book standalone confirmation thresholds must be non-negative, and ratio-style order book pressure thresholds must be between 0 and 1.
- Alert aggregation window must be non-negative.
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
- `feature_snapshot_ref`: optional reference to the feature snapshot that supplied measurements.
- `reason`: short human-readable trigger explanation.
- `status`: `detected`, `suppressed`, `notification_pending`, `notification_sent`, `notification_failed`, or `resolved`.
- `suppression_key`: notification suppression key. For aggregated alerts this is `(symbol, alert, direction)`; raw detector events may still carry detector-specific keys before aggregation.
- `created_at`: local creation timestamp.

Validation:

- Measurement must include the detector-specific trigger value, such as price return, momentum z-score, cancellation ratio, added quantity, cancelled quantity, or imbalance ratio.
- Suppressed events must reference the active cooldown decision.
- Events eligible for notification must pass reportability filtering. Momentum-only events require sufficient actual impulse return, direct volume/turnover burst, or order book pressure accompanied by minimum volume/turnover activity. Standalone order book events require configured severity plus short-window price movement and volume/turnover burst confirmation.

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

Represents a Feishu alert generated from one or more reportable anomaly events after aggregation.

Fields:

- `notification_id`: unique notification identifier.
- `event_ids`: one or more related anomaly event IDs.
- `receive_id_type`: `chat_id`, `open_id`, `user_id`, `union_id`, or `email`, loaded from local YAML configuration.
- `receive_id`: recipient identifier loaded from local YAML configuration.
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
- A notification may include multiple anomaly events for the same symbol when they occur within the configured alert aggregation window.
- Aggregated content must list all included signal types and measurements in one readable message.
- Feishu app ID, app secret, recipient type, recipient ID, retry attempts, retry backoff, and token refresh margin must be loaded from local YAML configuration and must not be printed in logs.
- Retry attempts must not exceed configured max attempts.
- Sent notifications require `feishu_message_id` when Feishu returns one.

## AlertAggregationWindow

Represents an in-memory grouping window for reportable events of the same symbol.

Fields:

- `symbol`: watchlist symbol being grouped.
- `started_at`: trigger time of the first reportable event in the window.
- `window_seconds`: aggregation duration from the active rule profile.
- `events`: reportable `AnomalyEvent` objects collected before flush.

Validation:

- Only events for the same symbol may be grouped in one window.
- When multiple events of the same anomaly type occur in one window, the most severe and latest event for that type is retained for notification content.
- Flushed windows must produce at most one `NotificationMessage` before cooldown suppression.

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

- `record_type`: `tick`, `feature`, `anomaly`, `suppression`, `notification`, or `health`.
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
