# Research: Tick Anomaly Alerts

## Decision: Python 3.12 with GM SDK for tick ingestion

Use Python 3.12 and the `gm` SDK as the market data integration. The live process will initialize GM credentials and terminal address from operator-provided configuration, subscribe to watchlist symbols, and route every accepted `on_tick` event into the detection engine.

**Rationale**: The user explicitly requested Python and pointed to `GM-API.md`, which states Python 3.12 and GM SDK are the prepared tools. `GM-API.md` lists `subscribe`, `context.data`, `run`, `set_token`, `set_serv_addr`, and related GM APIs as the expected integration surface.

**Alternatives considered**:

- Polling `current` snapshots: simpler, but misses tick-level movement and adds latency.
- Direct internal GM runtime APIs: useful for advanced gateway work, but unnecessary for a first alert-only strategy and more brittle than the public strategy flow.

## Decision: Alert-only strategy boundary

The implementation will not call GM trading APIs such as order placement, cancellation, cash, or positions. It will only use market data and symbol metadata APIs needed for subscription, filtering, and display.

**Rationale**: The spec requires clear separation from trade execution. Keeping this boundary sharp reduces operational risk and simplifies testing.

**Alternatives considered**:

- Include optional trading context in alerts: rejected for v1 because it expands scope and creates account-permission concerns.

## Decision: Deterministic anomaly detection rules

Use three independently testable detectors:

1. **Price jump detector**: For each symbol, maintain a rolling short window, default 30 seconds. Trigger when the latest valid price changes by at least the configured absolute return threshold, default 1.5%, against the earliest valid tick in the window, or exceeds a robust baseline threshold derived from recent short-window returns.
2. **Momentum detector**: Compute short-term velocity over a default 10-second impulse window and compare it with a default 3-minute baseline using a robust z-score based on median and median absolute deviation. Trigger when absolute z-score is at least 3.0 and there are enough ticks in both windows.
3. **Order book liquidity detector**: When bid/ask depth fields are available, maintain a default 30-second order book window. Trigger only when sustained large order additions, large cancellations, or buy/sell side imbalance exceeds configured thresholds for at least two consecutive accepted ticks. By default, order book anomalies can create standalone alerts only at `high` or `critical` severity; lower-severity order book signals enhance simultaneous price or momentum events.

Severity defaults:

- `warning`: price move >= 1.5%, momentum z-score >= 3.0, or order book signal qualifies as an enhancer
- `high`: price move >= 2.5%, momentum z-score >= 4.0, cancellation/addition ratio >= 35%, or one-side book imbalance >= 70%
- `critical`: price move >= 3.5%, momentum z-score >= 5.0, cancellation/addition ratio >= 50%, or one-side book imbalance >= 85%

**Rationale**: These rules are transparent, reproducible under replay, robust to outliers, and usable before labeled production data exists. The combination catches obvious jumps, gradual acceleration, and suspicious liquidity shifts while avoiding alerts from one-tick order book flicker.

**Alternatives considered**:

- Machine learning anomaly detection: rejected for v1 because it needs historical labeling, monitoring, and explainability work.
- Fixed percent-only rules: too noisy across stocks with different liquidity and volatility.
- Volume-only momentum: not reliable when tick volume fields are absent or inconsistent.
- Treat every large cancellation as an alert: rejected because normal A-share order book updates can be bursty; sustained confirmation and severity gating are needed.

## Decision: Tick quality and market-state filtering

Before detection, normalize ticks and reject records with missing symbol, non-positive price, duplicated timestamp/price identity, or event time older than the latest accepted tick for the symbol. Normalize available bid/ask depth into an order book snapshot; when depth is missing, mark the order book detector unavailable while continuing price and momentum detection. Suppress detection during explicitly configured ignored sessions and treat data gaps as baseline resets. Use daily metadata when available to flag suspension, limit-up, limit-down, and special opening/closing windows.

**Rationale**: Tick feeds can contain duplicates, out-of-order records, stale updates, and market microstructure effects. Filtering these before detection reduces false alerts.

**Alternatives considered**:

- Run detectors on raw ticks: rejected because it would produce noisy and hard-to-debug alerts.

## Decision: Cooldown plus aggregation for repeated alerts

Use a suppression key of `(symbol, anomaly_type, direction)`. During the default 180-second cooldown, suppress duplicate alerts unless severity increases. If severity increases, send an update notification that includes the previous severity and latest measurement. If order book anomalies enhance a price or momentum event, group them under the same notification instead of sending separate messages.

**Rationale**: This satisfies the spec's duplicate reduction target while still escalating meaningful changes.

**Alternatives considered**:

- Send every trigger: rejected due to alert storms.
- One alert per symbol per day: too coarse and likely to hide later important moves.

## Decision: Feishu message creation with tenant_access_token

Use Feishu message creation API `POST /open-apis/im/v1/messages` with query parameter `receive_id_type`, request header `Authorization: Bearer {tenant_access_token}`, and a JSON body containing `receive_id`, `msg_type`, and `content`. Use `msg_type=post` for structured rich text messages in v1.

Acquire `tenant_access_token` from the self-built app token endpoint with `app_id` and `app_secret`, cache it, and refresh it before expiry. The official token endpoint returns an expiry value; published documentation describes a two-hour validity window for self-built app tenant tokens.

**Rationale**: The user explicitly required `tenant_access_token` authentication. The official Feishu documentation lists `tenant_access_token` as a supported credential for sending messages and documents the message create endpoint. `post` messages are easier to validate and less complex than interactive cards while still structured enough for alert triage.

**Alternatives considered**:

- Incoming webhook robot: rejected because the user specifically requested OpenAPI and tenant token auth.
- Interactive card as v1 default: powerful, but larger schema and unnecessary for initial structured alert delivery.

## Decision: Configuration and secret handling

Use a YAML config file for watchlist, detector thresholds, GM connection settings, audit paths, and names of environment variables. All Feishu parameters must be supplied through environment variables, including app ID, app secret, recipient type, recipient ID, token refresh margin, max attempts, and retry backoff. Source-controlled examples must use environment variable names only.

**Rationale**: The GM and Feishu integrations require credentials and deployment-specific routing. Keeping values out of source reduces accidental disclosure and makes local/live environments easier to switch.

**Alternatives considered**:

- Hardcode values from `GM-API.md` or Feishu app settings: rejected because credentials and recipients should not be duplicated into source.
- Prompt interactively for secrets on every run: poor fit for unattended market monitoring.

## Decision: JSONL audit trail

Write append-only JSONL records for accepted ticks summary, anomaly events, suppression decisions, notification attempts, and health snapshots.

**Rationale**: JSONL is simple, replayable, diff-friendly, and sufficient for v1. It also supports post-incident review without introducing database operations.

**Alternatives considered**:

- SQLite: useful once query and retention needs grow, but unnecessary for the initial plan.
- No persistence: rejected because the spec requires auditability and failed notification review.

## References

- Local: [GM-API.md](../../GM-API.md)
- Feishu message create: https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN
- Feishu tenant token: https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
